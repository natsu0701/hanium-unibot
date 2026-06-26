import { useState } from 'react'

const DEFAULT_PROMPT =
  `당신은 정확하고 친절한 건국대학교 글로컬캠퍼스 학사 행정 비서입니다. 관련 학칙 및 공지에 근거하여만 답변하고, 근거를 찾을 수 없으면 솔직히 모르겠음을 알리세요. 학생에게 불친절하거나 과도한 확신 표현은 피합니다. 숫자·날짜·학점 규정은 반드시 인용 근청크와 일치시키세요.

검증: 신뢰도 임계치 미달 시 사용자에게 상담원 연결 또는 공식 학사처 안내를 권장합니다.`

function PromptPolicy() {
  const [systemPrompt, setSystemPrompt] = useState(DEFAULT_PROMPT)
  const [threshold, setThreshold] = useState(0.85)
  const [savedAt, setSavedAt] = useState(null)

  const [testQuestion, setTestQuestion] = useState('')
  const [testAnswer, setTestAnswer] = useState('')

  const handleSave = () => {
    setSavedAt(new Date().toLocaleString('ko-KR'))
  }

  const runSandbox = () => {
    const q = testQuestion.trim()
    if (!q) {
      setTestAnswer('테스트 질문을 입력해 주세요.')
      return
    }
    const short = `[샌드박스 목업]\n임계값 ${threshold}: Self-RAG 시뮬레이션\n\n질문: "${q.slice(0, 80)}${q.length > 80 ? '…' : ''}"\n\n응답: 설정된 페르소나와 근거 검색 규칙을 적용한 답변입니다. 실제 배포 환경에서는 벡터 검색·Retriever·Critique 파이프라인이 실행됩니다.`
    setTestAnswer(short)
  }

  return (
    <div className="flex h-full min-h-0 w-full flex-col overflow-hidden bg-slate-100">
      <div className="shrink-0 border-b border-slate-200 bg-white px-8 py-6">
        <h1 className="text-lg font-bold text-slate-800">프롬프트 정책</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          시스템 페르소나와 검증 임계값을 조정한 뒤 샌드박스에서 즉시 테스트합니다.
        </p>
      </div>

      <div className="flex min-h-0 flex-1 flex-row gap-6 overflow-hidden px-8 py-6">
        <aside className="flex min-h-0 w-full shrink-0 flex-col overflow-y-auto rounded-xl border border-slate-200 bg-white p-5 shadow-sm lg:w-[42%]">
          <h2 className="text-sm font-semibold text-slate-800">정책 설정</h2>

          <label className="mt-4 block text-xs font-medium text-slate-500">
            System Prompt (Persona)
          </label>
          <textarea
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            rows={12}
            className="mt-1 min-h-[200px] w-full resize-y rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-800 shadow-inner outline-none focus:border-violet-300 focus:bg-white focus:ring-2 focus:ring-violet-100"
            spellCheck={false}
          />

          <label className="mt-6 block text-xs font-medium text-slate-500">
            Self-RAG 엄격도 (Threshold) — {threshold.toFixed(2)}
          </label>
          <p className="mt-1 text-[11px] text-slate-400">
            예: 신뢰도 {Math.round(threshold * 100)}% 미만이면 답변 제한 또는 상담 안내
          </p>
          <input
            type="range"
            min={0}
            max={1}
            step={0.01}
            value={threshold}
            onChange={(e) => setThreshold(Number(e.target.value))}
            className="mt-3 h-2 w-full cursor-pointer accent-violet-600"
          />
          <div className="mt-1 flex justify-between text-[10px] text-slate-400">
            <span>0.0 관대</span>
            <span>1.0 엄격</span>
          </div>

          <div className="mt-6 flex shrink-0 items-center gap-3">
            <button
              type="button"
              onClick={handleSave}
              className="rounded-xl bg-violet-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-violet-700"
            >
              저장하기
            </button>
            {savedAt && <span className="text-xs text-emerald-600">저장됨 · {savedAt}</span>}
          </div>
        </aside>

        <section className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-800">프롬프트 테스트 샌드박스</h2>
          <p className="mt-1 text-xs text-slate-500">
            왼쪽에서 수정한 규칙을 반영한 미니 채팅 목업입니다. (실연동 전 UI 검증용)
          </p>

          <div className="mt-4 flex min-h-0 flex-1 flex-col gap-3">
            <div className="flex shrink-0 gap-2">
              <input
                type="text"
                value={testQuestion}
                onChange={(e) => setTestQuestion(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && runSandbox()}
                placeholder="테스트 질문을 입력하세요"
                className="min-w-0 flex-1 rounded-xl border border-slate-200 px-4 py-2.5 text-sm shadow-sm outline-none focus:border-violet-300 focus:ring-2 focus:ring-violet-100"
              />
              <button
                type="button"
                onClick={runSandbox}
                className="shrink-0 rounded-xl bg-slate-800 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-slate-900"
              >
                실행
              </button>
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto rounded-xl border border-slate-100 bg-slate-50 p-4">
              {testAnswer ? (
                <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-slate-700">
                  {testAnswer}
                </pre>
              ) : (
                <p className="text-sm text-slate-400">
                  실행을 누르면 여기에 샌드박스 응답이 표시됩니다.
                </p>
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}

export default PromptPolicy
