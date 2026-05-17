import { Check, FileText } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { LINE_ICON } from '../constants/iconProps'
import PdfViewer from './PdfViewer'

const QUICK_QUESTIONS = ['학사 일정', '장학금 조회', '졸업 요건']
const MOCK_BOT_META = {
  steps: ['Retrieve', 'Critique', 'Supported'],
  confidence: 'Confidence Score: 97%',
  referenceLabel: '장학규정 제3조 2항 보기',
  referencePage: 45,
}

const getMockReply = (question) => {
  if (question.includes('학사 일정')) {
    return '2026학년도 1학기 학사일정에 따르면, 수강신청 변경 기간은 3월 2일부터 3월 6일까지입니다.'
  }
  if (question.includes('장학금')) {
    return '성적우수 장학금을 받기 위해서는 직전 학기 평점이 3.5 이상이어야 하며, 15학점 이상을 이수해야 합니다.'
  }
  if (question.includes('졸업')) {
    return '졸업 요건은 전공 60학점, 교양 30학점 이상 이수 및 졸업 논문(또는 졸업 작품) 심사 통과입니다.'
  }
  return '해당 규정에 대해 문서를 검색 중입니다. 조금만 기다려주세요.'
}

function ChatScreen({ currentUser, activePdfFile = null, onPdfFileChange }) {
  const [input, setInput] = useState('')
  const [isBotTyping, setIsBotTyping] = useState(false)
  const [pdfPage, setPdfPage] = useState(1)
  const [animatedMetaMessageId, setAnimatedMetaMessageId] = useState(null)
  const [metaStage, setMetaStage] = useState(0)
  const [messages, setMessages] = useState([
    {
      id: crypto.randomUUID(),
      text: '안녕하세요! 학사 행정 관련 질문을 입력해 주세요.',
      sender: 'bot',
      meta: null,
    },
  ])
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isBotTyping])

  useEffect(() => {
    if (!animatedMetaMessageId) return

    setMetaStage(0)
    const retrieveDoneTimer = setTimeout(() => setMetaStage(1), 800)
    const critiqueDoneTimer = setTimeout(() => setMetaStage(2), 1600)
    const supportedDoneTimer = setTimeout(() => setMetaStage(3), 2400)

    return () => {
      clearTimeout(retrieveDoneTimer)
      clearTimeout(critiqueDoneTimer)
      clearTimeout(supportedDoneTimer)
    }
  }, [animatedMetaMessageId])

  const sendMessage = (text = input) => {
    const trimmed = text.trim()
    if (!trimmed) return

    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), text: trimmed, sender: 'user' },
    ])
    setInput('')
    setIsBotTyping(true)

    // Axios API call is temporarily disabled for mock response testing.
    // try {
    //   const response = await axios.post('http://localhost:8000/api/chat', {
    //     message: trimmed,
    //     user_id: 'tester',
    //   })
    //   const botReply = response.data?.reply ?? '메시지를 정상적으로 전달했어요.'
    // } catch (error) {
    //   console.error('채팅 전송 중 오류 발생:', error)
    // } finally {
    //   setIsBotTyping(false)
    // }

    setTimeout(() => {
      const botMessageId = crypto.randomUUID()
      const botReply = getMockReply(trimmed)
      setMessages((prev) => [
        ...prev,
        {
          id: botMessageId,
          text: botReply,
          sender: 'bot',
          meta: MOCK_BOT_META,
        },
      ])
      setAnimatedMetaMessageId(botMessageId)
      setIsBotTyping(false)
    }, 1000)
  }

  const handleQuickQuestion = (question) => {
    setInput(question)
    setTimeout(() => {
      sendMessage(question)
    }, 180)
  }

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="flex h-full min-h-0 w-full min-w-0 flex-1 flex-row overflow-hidden bg-slate-100">
        <section className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden border-r border-slate-200 bg-slate-100">
          <header className="border-b border-slate-200 bg-white px-4 py-3 shadow-sm">
          <h1 className="text-lg font-bold text-slate-800">Uni-Bot 채팅</h1>
          </header>

          <section className="flex-1 overflow-y-auto px-4 py-5">
            <div className="mx-auto flex w-full max-w-3xl flex-col gap-3">
              {messages.map((message) => (
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
                        : 'rounded-bl-md bg-white text-slate-700'
                    }`}
                  >
                    {message.text}
                    {message.sender === 'bot' && message.meta && (
                      <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-3">
                        <div className="relative px-2 pb-6 pt-1">
                          <div className="absolute left-0 right-0 top-3 h-[2px] bg-slate-200" />
                          <div
                            className={`absolute left-0 top-3 h-[2px] bg-orange-500 transition-all duration-700 ${
                              (message.id === animatedMetaMessageId ? metaStage : 3) >= 2
                                ? 'w-full'
                                : (message.id === animatedMetaMessageId ? metaStage : 3) >= 1
                                  ? 'w-1/2'
                                  : 'w-0'
                            }`}
                          />
                          <div className="relative grid grid-cols-3">
                            {message.meta.steps.map((step, index) => {
                              const stageForMessage =
                                message.id === animatedMetaMessageId ? metaStage : 3
                              const isDone =
                                index === 0
                                  ? stageForMessage >= 1
                                  : index === 1
                                    ? stageForMessage >= 2
                                    : stageForMessage >= 3
                              const isInProgress =
                                (index === 0 && stageForMessage === 0) ||
                                (index === 1 && stageForMessage === 1) ||
                                (index === 2 && stageForMessage === 2)

                              return (
                                <div key={step} className="flex flex-col items-center">
                                  <div
                                    className={`flex h-6 w-6 items-center justify-center rounded-full border text-xs font-semibold transition ${
                                      isDone
                                        ? index === 2
                                          ? 'border-emerald-500 bg-emerald-500 text-white'
                                          : 'border-orange-500 bg-orange-500 text-white'
                                        : isInProgress
                                          ? 'animate-pulse border-orange-500 bg-white text-orange-500'
                                          : 'border-slate-300 bg-white text-slate-400'
                                    }`}
                                  >
                                    {isDone ? (
                                      <Check size={12} className="text-current" {...LINE_ICON} aria-hidden />
                                    ) : (
                                      index + 1
                                    )}
                                  </div>
                                  <p className="mt-2 text-[11px] font-medium text-slate-600">
                                    {step}
                                  </p>
                                </div>
                              )
                            })}
                          </div>
                        </div>

                        <div
                          className={`mt-2 flex flex-wrap items-center gap-2 transition-all duration-500 ${
                            (message.id === animatedMetaMessageId ? metaStage : 3) >= 3
                              ? 'translate-y-0 opacity-100'
                              : 'pointer-events-none translate-y-1 opacity-0'
                          }`}
                        >
                          <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700">
                            {message.meta.confidence}
                          </span>
                          <button
                            type="button"
                            onClick={() => setPdfPage(message.meta.referencePage)}
                            className="inline-flex items-center gap-1 rounded-full border border-blue-300 px-3 py-1 text-xs font-medium text-blue-700 transition hover:bg-blue-50"
                          >
                            <FileText size={13} {...LINE_ICON} className="shrink-0" aria-hidden />
                            {message.meta.referenceLabel}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {isBotTyping && (
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
            <div className="mx-auto flex w-full max-w-3xl items-end gap-2">
              <textarea
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="메시지를 입력하세요..."
                rows={1}
                className="max-h-32 min-h-[44px] flex-1 resize-none rounded-xl border border-slate-300 px-4 py-2 text-sm text-slate-800 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              />
              <button
                type="button"
                onClick={sendMessage}
                className="h-11 rounded-xl bg-blue-600 px-5 text-sm font-semibold text-white transition hover:bg-blue-700 focus:outline-none focus:ring-4 focus:ring-blue-200"
              >
                전송
              </button>
            </div>
          </footer>
        </section>
        <PdfViewer
          targetPage={pdfPage}
          currentUser={currentUser}
          activePdfFile={activePdfFile}
          onPdfFileChange={onPdfFileChange}
        />
    </div>
  )
}

export default ChatScreen
