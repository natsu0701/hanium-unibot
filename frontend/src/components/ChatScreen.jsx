import { FileText, Table } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { LINE_ICON } from '../constants/iconProps'
import { sendChatMessage } from '../api/chatApi'

const QUICK_QUESTIONS = ['학사 일정', '장학금 조회', '졸업 요건']

function isTableSource(source) {
  return Boolean(source) && source.is_table === true
}

function sourceLabel(source) {
  if (!source || typeof source !== 'object') {
    return '문서 · -페이지'
  }

  return (
    source.text ||
    `${source.doc_name || '문서'} · ${source.page || '-'}페이지`
  )
}

function sourceEvidence(source) {
  if (!source || typeof source !== 'object') {
    return ''
  }

  if (typeof source.evidence === 'string' && source.evidence.trim()) {
    return source.evidence
  }

  if (typeof source.text === 'string') {
    return source.text
  }

  return ''
}

function SourceChip({ source, onSelect, isActive }) {
  const safeSource = source && typeof source === 'object' ? source : {}
  const isTable = isTableSource(safeSource)
  const Icon = isTable ? Table : FileText

  return (
    <button
      type="button"
      onClick={() => onSelect?.(source)}
      className={`group relative inline-flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition ${
        isActive
          ? 'border-slate-400 bg-white text-slate-800'
          : 'border-slate-200 bg-slate-50 text-slate-600 hover:border-slate-300 hover:bg-slate-100'
      }`}
    >
      <Icon
        size={14}
        {...LINE_ICON}
        className={`shrink-0 ${isActive ? 'text-slate-700' : 'text-slate-500'}`}
        aria-hidden
      />

      {sourceLabel(safeSource)}

      {isTable && (
        <span
          role="tooltip"
          className="pointer-events-none absolute bottom-[calc(100%+8px)] left-1/2 z-20 -translate-x-1/2 whitespace-nowrap rounded-md bg-slate-800 px-2.5 py-1 text-[11px] font-medium text-white opacity-0 shadow-lg transition-opacity duration-200 group-hover:opacity-100"
        >
          표 자료입니다
          <span className="absolute left-1/2 top-full h-0 w-0 -translate-x-1/2 border-x-4 border-t-4 border-x-transparent border-t-slate-800" />
        </span>
      )}
    </button>
  )
}

function SourceEvidencePanel({ sources, onSourceClick }) {
  const safeSources = Array.isArray(sources)
    ? sources.filter((source) => source && typeof source === 'object')
    : []
  const [activeIndex, setActiveIndex] = useState(null)
  const activeSource = activeIndex == null ? null : safeSources[activeIndex]
  const evidence = activeSource ? sourceEvidence(activeSource) : ''

  const handleChipSelect = (source, index) => {
    setActiveIndex((current) => (current === index ? null : index))
    onSourceClick?.(source)
  }

  return (
    <div className="mt-3 w-full border-t border-slate-100 pt-3">
      <div className="flex w-full flex-wrap items-center gap-2">
        <span className="shrink-0 text-[11px] font-semibold text-slate-400">
          근거
        </span>

        {safeSources.map((source, index) => (
          <SourceChip
            key={`source-${index}`}
            source={source}
            isActive={activeIndex === index}
            onSelect={() => handleChipSelect(source, index)}
          />
        ))}
      </div>

      <div
        className={`grid w-full transition-all duration-300 ease-out ${
          activeSource
            ? 'mt-2 grid-rows-[1fr] opacity-100'
            : 'grid-rows-[0fr] opacity-0'
        }`}
      >
        <div className="min-h-0 overflow-hidden">
          <div className="w-full rounded-lg border border-slate-100 bg-slate-50 p-4 transition-all duration-300">
            <div className="mb-1.5 text-left text-[11px] font-medium text-slate-400">
              페이지: {activeSource?.page ?? '-'}쪽
            </div>
            <div className="my-2 border-t border-slate-200/60" />
            <pre className="m-0 w-full whitespace-pre-wrap text-left font-sans text-[12px] leading-relaxed text-slate-600">
              {evidence}
            </pre>
          </div>
        </div>
      </div>
    </div>
  )
}

function ChatScreen({
  onSourceClick,
  currentSchoolId = null,
  currentSchoolName = '',
}) {
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const [messages, setMessages] = useState([
    {
      id: crypto.randomUUID(),
      text: '안녕하세요! 학사 행정 관련 질문을 입력해 주세요.',
      sender: 'bot',
      sources: [],
      isGreeting: true,
    },
  ])

  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: 'smooth',
    })
  }, [messages, isLoading])

  const handleSendMessage = async (text = input) => {
    if (isLoading) {
      return
    }

    const trimmed = text.trim()

    if (!trimmed) {
      return
    }

    setMessages((previousMessages) => [
      ...previousMessages,
      {
        id: crypto.randomUUID(),
        text: trimmed,
        sender: 'user',
        sources: [],
      },
    ])

    setInput('')
    setIsLoading(true)

    try {
      const response = await sendChatMessage(trimmed, currentSchoolId)

      const answer =
        response?.answer ||
        '답변을 생성하지 못했습니다.'

      const sources = Array.isArray(response?.sources)
        ? response.sources.filter(
            (source) => source && typeof source === 'object',
          )
        : []

      setMessages((previousMessages) => [
        ...previousMessages,
        {
          id: crypto.randomUUID(),
          text: answer,
          sender: 'bot',
          sources,
        },
      ])
    } catch (error) {
      setMessages((previousMessages) => [
        ...previousMessages,
        {
          id: crypto.randomUUID(),
          text:
            error?.message ||
            '죄송합니다. 답변을 가져오는 중 오류가 발생했습니다.',
          sender: 'bot',
          sources: [],
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  const handleSubmit = (event) => {
    event.preventDefault()
    handleSendMessage()
  }

  const handleQuickQuestion = (question) => {
    if (isLoading) {
      return
    }

    handleSendMessage(question)
  }

  const handleKeyDown = (event) => {
    if (event.nativeEvent.isComposing) {
      return
    }

    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      event.currentTarget.form?.requestSubmit()
    }
  }

  const sourceBadgeLabel = currentSchoolId
    ? `[${currentSchoolName || '선택 학교'} 학사요람 기반]`
    : '[전체 문서 검색]'

  return (
    <section className="flex h-full min-h-0 w-full min-w-0 flex-1 flex-col overflow-hidden bg-slate-100">
      <header className="border-b border-slate-200 bg-white px-4 py-3 shadow-sm">
        <h1 className="text-lg font-bold text-slate-800">
          Uni-Bot 채팅
        </h1>
      </header>

      <section className="flex-1 overflow-y-auto px-4 py-5">
        <div className="mx-auto flex w-full max-w-3xl flex-col gap-3">
          {messages.map((message) => {
            const hasSources =
              Array.isArray(message.sources) &&
              message.sources.length > 0

            const isRefused =
              message.sender === 'bot' &&
              !hasSources &&
              !message.isGreeting

            return (
              <div
                key={message.id}
                className={`flex ${
                  message.sender === 'user'
                    ? 'justify-end'
                    : 'justify-start'
                }`}
              >
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-2 text-sm leading-relaxed shadow-sm ${
                    message.sender === 'user'
                      ? 'rounded-br-md bg-yellow-300 text-slate-900'
                      : isRefused
                        ? 'rounded-bl-md bg-slate-100 text-slate-500'
                        : 'rounded-bl-md bg-white text-slate-700'
                  }`}
                >
                  {message.sender === 'bot' && !message.isGreeting && (
                    <div className="mb-2">
                      <span className="inline-flex items-center rounded-full border border-slate-200 bg-transparent px-2.5 py-0.5 text-[10px] font-medium tracking-tight text-slate-500">
                        {sourceBadgeLabel}
                      </span>
                    </div>
                  )}

                  {message.text}

                  {message.sender === 'bot' && hasSources && (
                    <SourceEvidencePanel
                      sources={message.sources}
                      onSourceClick={onSourceClick}
                    />
                  )}
                </div>
              </div>
            )
          })}

          {isLoading && (
            <div className="flex justify-start">
              <div className="rounded-2xl rounded-bl-md bg-white px-4 py-3 shadow-sm">
                <div className="flex items-center gap-1.5">
                  <span className="h-2 w-2 animate-pulse rounded-full bg-slate-400 [animation-delay:0ms]" />
                  <span className="h-2 w-2 animate-pulse rounded-full bg-slate-400 [animation-delay:200ms]" />
                  <span className="h-2 w-2 animate-pulse rounded-full bg-slate-400 [animation-delay:400ms]" />
                </div>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </section>

      <footer className="shrink-0 border-t border-slate-200 bg-white px-4 py-3">
        <div className="mx-auto mb-3 flex w-full max-w-3xl gap-2 overflow-x-auto pb-1">
          {QUICK_QUESTIONS.map((question) => (
            <button
              key={question}
              type="button"
              onClick={() => handleQuickQuestion(question)}
              disabled={isLoading}
              className="shrink-0 rounded-full border border-slate-300 bg-slate-50 px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {question}
            </button>
          ))}
        </div>

        <form
          onSubmit={handleSubmit}
          className="mx-auto flex w-full max-w-3xl items-end gap-2"
        >
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="메시지를 입력하세요..."
            rows={1}
            disabled={isLoading}
            className="max-h-32 min-h-[44px] flex-1 resize-none rounded-xl border border-slate-300 px-4 py-2 text-sm text-slate-800 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:cursor-not-allowed disabled:bg-slate-100"
          />

          <button
            type="submit"
            disabled={isLoading}
            className="h-11 rounded-xl bg-blue-600 px-5 text-sm font-semibold text-white transition hover:bg-blue-700 focus:outline-none focus:ring-4 focus:ring-blue-200 disabled:cursor-not-allowed disabled:opacity-50"
          >
            전송
          </button>
        </form>
      </footer>
    </section>
  )
}

export default ChatScreen
