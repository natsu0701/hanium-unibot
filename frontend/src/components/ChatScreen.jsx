import {
  ChevronDown,
  CircleHelp,
  Copy,
  FileText,
  RefreshCw,
  Table,
} from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { LINE_ICON } from '../constants/iconProps'
import { sendChatMessage } from '../api/chatApi'

const QUICK_QUESTIONS = [
  '수강신청 이월학점은 몇 학점까지 인정되나요?',
  '제적된 학생도 재입학이 가능한가요?',
  '부전공은 총 몇 학점을 이수해야 하나요?',
  '이미 취득한 학점을 포기할 수 있는 제도가 있나요?',
  '8학기를 초과해서 등록하는 경우 등록금은 어떻게 계산되나요?',
  '본인 결혼이나 출산 등으로 인한 공인결석은 며칠까지 인정되나요?',
]

const FAIL_HINT =
  '다른 표현이나 구체적인 학사 용어로 다시 질문해 보세요'

const EMPTY_TITLE = 'Uni-Bot'
const EMPTY_SUBTITLE = '학사 규정 검색 AI Uni-Bot입니다!'

const CHIP_CLASS =
  'border border-slate-300 bg-slate-50 text-xs font-medium leading-snug text-slate-700 transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700'

const CHAT_GUTTER = 'px-4'

function BotAvatar() {
  return (
    <img
      src="/bot-avatar.png"
      alt="Uni-Bot"
      className="h-10 w-10 shrink-0 rounded-full bg-[#7C5CFF] object-contain p-[2px] ring-1 ring-black/10"
    />
  )
}

function QuickQuestionChips({ onSelect, disabled = false }) {
  const [expanded, setExpanded] = useState(false)
  const visibleQuestions = expanded
    ? QUICK_QUESTIONS
    : QUICK_QUESTIONS.slice(0, 2)

  return (
    <div className="flex w-full items-start gap-1.5">
      <div className="flex min-w-0 flex-1 flex-wrap items-start gap-2">
        {visibleQuestions.map((question) => (
          <button
            key={question}
            type="button"
            onClick={() => onSelect(question)}
            disabled={disabled}
            className={`unibot-box max-w-full whitespace-normal px-3 py-1.5 text-left disabled:cursor-not-allowed disabled:opacity-50 sm:text-sm ${CHIP_CLASS}`}
          >
            {question}
          </button>
        ))}
      </div>

      <button
        type="button"
        onClick={() => setExpanded((current) => !current)}
        aria-expanded={expanded}
        aria-label={expanded ? '추천 질문 접기' : '추천 질문 더보기'}
        className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-slate-500 transition hover:bg-slate-100 hover:text-slate-700"
      >
        <ChevronDown
          size={18}
          {...LINE_ICON}
          className={`transition ${expanded ? 'rotate-180' : ''}`}
          aria-hidden
        />
      </button>
    </div>
  )
}

function isTableSource(source) {
  return Boolean(source) && source.is_table === true
}

function unwrapExtraParens(value) {
  let text = String(value || '').trim()

  while (/^\(.*\)$/.test(text)) {
    const inner = text.slice(1, -1).trim()

    if (!inner.startsWith('(')) {
      break
    }

    text = inner
  }

  return text
}

function formatArticleLabel(article, articleTitle) {
  const articleRaw = String(article || '').trim()
  const numberMatch = articleRaw.match(/\d+/)
  const clause = numberMatch
    ? `제${numberMatch[0]}조`
    : articleRaw.replace(/\s+/g, '')

  const title = unwrapExtraParens(articleTitle)

  if (clause && title) {
    if (title.startsWith('(')) {
      return `${clause} ${title}`
    }

    return `${clause} (${title})`
  }

  return clause || title
}

function formatPageLabel(page) {
  const parsed = Number(page)

  if (!Number.isFinite(parsed) || parsed < 1) {
    return ''
  }

  return `${parsed}P`
}

function sourceLabel(source) {
  if (!source || typeof source !== 'object') {
    return '건국대학교 학사 요람'
  }

  const parts = ['건국대학교 학사 요람']
  const pageLabel = formatPageLabel(source.page)
  const articleLabel = formatArticleLabel(
    source.article,
    source.article_title,
  )

  if (pageLabel) {
    parts.push(pageLabel)
  }

  if (articleLabel) {
    parts.push(articleLabel)
  }

  return parts.join(' · ')
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
      className={`group relative inline-flex max-w-full min-w-0 items-start gap-1.5 rounded-full px-3 py-1 text-left ${CHIP_CLASS} ${
        isActive ? 'border-slate-400' : ''
      }`}
    >
      <Icon
        size={14}
        {...LINE_ICON}
        className={`mt-0.5 shrink-0 ${isActive ? 'text-slate-700' : 'text-slate-500'}`}
        aria-hidden
      />

      <span className="min-w-0 whitespace-normal break-keep">
        {sourceLabel(safeSource)}
      </span>

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
    <div className="mt-3 min-w-0 w-full border-t border-slate-100 pt-3">
      <div className="flex min-w-0 w-full flex-wrap items-start gap-2">
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
          <div className="unibot-box w-full border border-slate-100 bg-slate-50 p-4 transition-all duration-300 sm:rounded-lg">
            <div className="mb-1.5 text-left text-[11px] font-medium text-slate-400">
              {formatPageLabel(activeSource?.page) || '-'}
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

  const [messages, setMessages] = useState([])
  const [copiedId, setCopiedId] = useState('')

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
          question: trimmed,
          isFailed: sources.length === 0,
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
          question: trimmed,
          isFailed: true,
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

  const handleCopyAnswer = async (message) => {
    const text = String(message?.text || '').trim()

    if (!text) {
      return
    }

    try {
      await navigator.clipboard.writeText(text)
      setCopiedId(message.id)
      window.setTimeout(() => {
        setCopiedId((current) => (current === message.id ? '' : current))
      }, 1500)
    } catch {
      setCopiedId('')
    }
  }

  const handleRegenerate = async (message) => {
    const question = String(message?.question || '').trim()

    if (!question || isLoading) {
      return
    }

    setIsLoading(true)

    try {
      const response = await sendChatMessage(question, currentSchoolId)
      const answer =
        response?.answer || '답변을 생성하지 못했습니다.'
      const sources = Array.isArray(response?.sources)
        ? response.sources.filter(
            (source) => source && typeof source === 'object',
          )
        : []

      setMessages((previousMessages) =>
        previousMessages.map((item) =>
          item.id === message.id
            ? {
                ...item,
                text: answer,
                sources,
                isFailed: sources.length === 0,
              }
            : item,
        ),
      )
    } catch (error) {
      setMessages((previousMessages) =>
        previousMessages.map((item) =>
          item.id === message.id
            ? {
                ...item,
                text:
                  error?.message ||
                  '죄송합니다. 답변을 가져오는 중 오류가 발생했습니다.',
                sources: [],
                isFailed: true,
              }
            : item,
        ),
      )
    } finally {
      setIsLoading(false)
    }
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

  const hasStarted = messages.some((message) => message.sender === 'user')

  return (
    <section className="flex h-full min-h-0 w-full min-w-0 flex-1 flex-col overflow-hidden bg-slate-100">
      <header className="border-b border-slate-200 bg-white px-4 py-3 shadow-sm">
        <h1 className="text-lg font-bold text-slate-800">
          Uni-Bot 채팅
        </h1>
      </header>

      <section className={`flex-1 overflow-y-auto py-4 ${CHAT_GUTTER}`}>
        {!hasStarted && !isLoading ? (
          <div className="flex w-full flex-col items-center pt-10 text-center sm:pt-14">
            <img
              src="/bot-avatar.png"
              alt=""
              className="h-20 w-20 rounded-full bg-[#7C5CFF] object-contain p-1 ring-1 ring-black/10"
            />
            <h2
              className="mt-4 text-3xl font-black tracking-tight text-slate-800"
              style={{ fontFamily: 'Arial Black, sans-serif' }}
            >
              {EMPTY_TITLE}
            </h2>
            <p className="mt-2 text-sm text-slate-500">{EMPTY_SUBTITLE}</p>
          </div>
        ) : null}

        <div className="flex w-full flex-col gap-3">
          {messages.map((message, index) => {
            const hasSources =
              Array.isArray(message.sources) &&
              message.sources.length > 0

            const isBot = message.sender === 'bot'
            const isFailed =
              isBot && (message.isFailed === true || !hasSources)
            const previousSender =
              index > 0 ? messages[index - 1].sender : null
            const showAvatar = isBot && previousSender !== 'bot'

            return (
              <div
                key={message.id}
                className={`flex items-start gap-2 ${
                  isBot ? 'justify-start' : 'justify-end'
                }`}
              >
                {isBot ? (
                  showAvatar ? (
                    <BotAvatar />
                  ) : (
                    <div className="h-10 w-10 shrink-0" aria-hidden />
                  )
                ) : null}

                <div
                  className={`relative min-w-0 max-w-[80%] ${
                    isBot ? 'text-slate-700' : 'text-slate-900'
                  }`}
                >
                  {isBot ? (
                    <span
                      className="absolute -left-[6px] top-3 h-0 w-0 border-y-[6px] border-r-[7px] border-y-transparent border-r-white"
                      aria-hidden
                    />
                  ) : null}

                  <div
                    className={`unibot-box relative min-w-0 px-4 py-2 text-sm leading-relaxed shadow-sm ${
                      isBot
                        ? 'rounded-tl-none bg-white'
                        : 'bg-yellow-300 max-sm:rounded-br-none sm:rounded-br-md'
                    }`}
                  >
                    {isBot && (
                      <div className="mb-2">
                        <span className="unibot-box inline-flex items-center border border-slate-200 bg-transparent px-2.5 py-0.5 text-[10px] font-medium tracking-tight text-slate-500 sm:rounded-full">
                          {sourceBadgeLabel}
                        </span>
                      </div>
                    )}

                    <div className="flex items-start gap-2">
                      {isFailed && (
                        <CircleHelp
                          size={16}
                          {...LINE_ICON}
                          className="mt-0.5 shrink-0 text-red-500"
                          aria-hidden
                        />
                      )}

                      <div className="min-w-0 flex-1">
                        <p className="m-0 whitespace-pre-wrap">{message.text}</p>

                        {isFailed && (
                          <p className="mt-2 text-xs leading-relaxed text-slate-500">
                            {FAIL_HINT}
                          </p>
                        )}
                      </div>
                    </div>

                    {isBot && (
                      <div className="mt-2 flex items-center gap-0.5">
                        <button
                          type="button"
                          onClick={() => handleCopyAnswer(message)}
                          className="inline-flex h-7 w-7 items-center justify-center rounded-md text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
                          aria-label="답변 복사"
                          title={copiedId === message.id ? '복사됨' : '복사'}
                        >
                          <Copy size={15} {...LINE_ICON} aria-hidden />
                        </button>
                        {message.question ? (
                          <button
                            type="button"
                            onClick={() => handleRegenerate(message)}
                            disabled={isLoading}
                            className="inline-flex h-7 w-7 items-center justify-center rounded-md text-slate-400 transition hover:bg-slate-100 hover:text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
                            aria-label="답변 새로 고침"
                            title="새로 고침"
                          >
                            <RefreshCw size={15} {...LINE_ICON} aria-hidden />
                          </button>
                        ) : null}
                      </div>
                    )}

                    {isBot && hasSources && (
                      <SourceEvidencePanel
                        sources={message.sources}
                        onSourceClick={onSourceClick}
                      />
                    )}
                  </div>
                </div>
              </div>
            )
          })}

          {isLoading && (
            <div className="flex items-start justify-start gap-2">
              {messages[messages.length - 1]?.sender === 'bot' ? (
                <div className="h-10 w-10 shrink-0" aria-hidden />
              ) : (
                <BotAvatar />
              )}
              <div className="relative">
                <span
                  className="absolute -left-[6px] top-3 h-0 w-0 border-y-[6px] border-r-[7px] border-y-transparent border-r-white"
                  aria-hidden
                />
                <div className="unibot-box rounded-tl-none bg-white px-4 py-3 shadow-sm">
                  <div className="flex items-center gap-1.5">
                    <span className="h-2 w-2 animate-pulse rounded-full bg-slate-400 [animation-delay:0ms]" />
                    <span className="h-2 w-2 animate-pulse rounded-full bg-slate-400 [animation-delay:200ms]" />
                    <span className="h-2 w-2 animate-pulse rounded-full bg-slate-400 [animation-delay:400ms]" />
                  </div>
                </div>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </section>

      <footer className={`shrink-0 border-t border-slate-200 bg-white py-3 ${CHAT_GUTTER}`}>
        <div className="mb-3 w-full">
          <p className="mb-1.5 text-[11px] font-medium text-slate-400">
            이런 질문도 가능해요!
          </p>
          <QuickQuestionChips
            disabled={isLoading}
            onSelect={handleQuickQuestion}
          />
        </div>

        <form
          onSubmit={handleSubmit}
          className="flex w-full items-end gap-2"
        >
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="메시지를 입력하세요..."
            rows={1}
            disabled={isLoading}
            className="unibot-box max-h-32 min-h-[44px] flex-1 resize-none border border-slate-300 px-4 py-2 text-sm text-slate-800 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:cursor-not-allowed disabled:bg-slate-100 sm:rounded-xl"
          />

          <button
            type="submit"
            disabled={isLoading}
            className="unibot-box h-11 bg-blue-600 px-5 text-sm font-semibold text-white transition hover:bg-blue-700 focus:outline-none focus:ring-4 focus:ring-blue-200 disabled:cursor-not-allowed disabled:opacity-50 sm:rounded-xl"
          >
            전송
          </button>
        </form>
      </footer>
    </section>
  )
}

export default ChatScreen
