import { FileText } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { LINE_ICON } from '../constants/iconProps'
import { sendChatMessage } from '../api/chatApi'

const QUICK_QUESTIONS = ['학사 일정', '장학금 조회', '졸업 요건']

// 보라색 '근거 보기 칩' 컴포넌트.
// 클릭 시 source.page 값을 onSourceClick 콜백으로 부모에 전달합니다.
function SourceChip({ source, onSourceClick }) {
  return (
    <button
      type="button"
      onClick={() => onSourceClick?.(source.page)}
      className="inline-flex items-center gap-1 rounded-full border border-[#654AEC]/30 bg-violet-50 px-3 py-1 text-xs font-medium text-[#654AEC] transition hover:bg-violet-100"
    >
      <FileText size={13} {...LINE_ICON} className="shrink-0" aria-hidden />
      {source.text}
    </button>
  )
}

function ChatScreen({ onSourceClick }) {
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [messages, setMessages] = useState([
    {
      id: crypto.randomUUID(),
      text: '안녕하세요! 학사 행정 관련 질문을 입력해 주세요.',
      sender: 'bot',
      sources: [],
    },
  ])
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  const handleSendMessage = async (text = input) => {
    // 로딩 중에는(연타/엔터 꾹 누름) 즉시 튕겨내 중복 호출을 방지합니다.
    if (isLoading) return

    const trimmed = text.trim()
    if (!trimmed) return

    setMessages((prevMessages) => [
      ...prevMessages,
      { id: crypto.randomUUID(), text: trimmed, sender: 'user' },
    ])
    setInput('')
    setIsLoading(true)

    try {
      const { answer, sources } = await sendChatMessage(trimmed)
      setMessages((prevMessages) => [
        ...prevMessages,
        {
          id: crypto.randomUUID(),
          text: answer,
          sender: 'bot',
          sources: sources ?? [],
        },
      ])
    } catch (error) {
      console.error('채팅 전송 중 오류 발생:', error)
      setMessages((prevMessages) => [
        ...prevMessages,
        {
          id: crypto.randomUUID(),
          text: error.message ?? '죄송합니다. 답변을 가져오는 중 오류가 발생했습니다.',
          sender: 'bot',
          sources: [],
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  // 폼 제출/엔터/버튼 클릭을 단일 경로(onSubmit)로 통일해 중복 호출을 방지합니다.
  const handleSubmit = (event) => {
    event.preventDefault()
    handleSendMessage()
  }

  const handleQuickQuestion = (question) => {
    if (isLoading) return
    handleSendMessage(question)
  }

  const handleKeyDown = (event) => {
    // 한글 IME 조합 중에는 엔터를 무시해 마지막 글자 찌꺼기 버그를 방지합니다.
    if (event.nativeEvent.isComposing) return

    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      event.currentTarget.form?.requestSubmit()
    }
  }

  return (
        <section className="flex h-full min-h-0 w-full min-w-0 flex-1 flex-col overflow-hidden bg-slate-100">
          <header className="border-b border-slate-200 bg-white px-4 py-3 shadow-sm">
          <h1 className="text-lg font-bold text-slate-800">Uni-Bot 채팅</h1>
          </header>

          <section className="flex-1 overflow-y-auto px-4 py-5">
            <div className="mx-auto flex w-full max-w-3xl flex-col gap-3">
              {messages.map((message) => {
                // sources가 비어있거나 없는 봇 메시지는 '답변 거부' 상태로 간주합니다.
                const hasSources =
                  Array.isArray(message.sources) && message.sources.length > 0
                const isRefused = message.sender === 'bot' && !hasSources

                return (
                  <div
                    key={message.id}
                    className={`flex ${
                      message.sender === 'user' ? 'justify-end' : 'justify-start'
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
                      {message.text}
                      {message.sender === 'bot' && hasSources && (
                        <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-3">
                          <span className="text-[11px] font-semibold text-slate-400">
                            근거
                          </span>
                          {message.sources.map((source, index) => (
                            <SourceChip
                              key={`${message.id}-source-${index}`}
                              source={source}
                              onSourceClick={onSourceClick}
                            />
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="rounded-2xl rounded-bl-md bg-white px-4 py-3 shadow-sm">
                    <div className="flex items-center gap-1.5">
                      <span className="h-2 w-2 animate-pulse rounded-full bg-slate-400 [animation-delay:0ms]"></span>
                      <span className="h-2 w-2 animate-pulse rounded-full bg-slate-400 [animation-delay:200ms]"></span>
                      <span className="h-2 w-2 animate-pulse rounded-full bg-slate-400 [animation-delay:400ms]"></span>
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
                  className="shrink-0 rounded-full border border-slate-300 bg-slate-50 px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700"
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
                className="max-h-32 min-h-[44px] flex-1 resize-none rounded-xl border border-slate-300 px-4 py-2 text-sm text-slate-800 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
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
