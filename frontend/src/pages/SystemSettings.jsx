import { useState } from 'react'

function SystemSettings() {
  const [ocrKeyVisible, setOcrKeyVisible] = useState(false)
  const [llmKeyVisible, setLlmKeyVisible] = useState(false)
  const [vectorEpVisible, setVectorEpVisible] = useState(false)
  const [ocrKey, setOcrKey] = useState('')
  const [llmKey, setLlmKey] = useState('')
  const [vectorEndpoint, setVectorEndpoint] = useState('')
  const [llmProvider, setLlmProvider] = useState('gpt-4o')
  const [greeting, setGreeting] = useState(
    '안녕하세요! 학사 행정 규정 검색 AI Uni-Bot입니다. 무엇이 궁금하신가요?',
  )
  const [themeColor, setThemeColor] = useState('#654AEC')
  const [maintenance, setMaintenance] = useState(false)
  const [retention, setRetention] = useState('3y')
  const [savedAt, setSavedAt] = useState(null)

  const maskedPlaceholder = '••••••••••••••••'

  const handleSave = () => {
    setSavedAt(new Date().toLocaleString('ko-KR'))
  }

  return (
    <div className="flex h-full min-h-0 w-full flex-col overflow-hidden bg-slate-100">
      <div className="shrink-0 border-b border-slate-200 bg-white px-8 py-6">
        <h1 className="text-lg font-bold text-slate-800">시스템 설정</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          API 연동, 위젯 브랜딩, 운영 모드를 전역으로 구성합니다. 모든 테넌트에 공통으로 적용됩니다.
        </p>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-8 py-6 pb-8">
        <div className="w-full space-y-6">
          {savedAt && (
            <p className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm text-emerald-800">
              마지막 저장: {savedAt} (목업)
            </p>
          )}

          <section className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-slate-200/80">
            <h2 className="text-sm font-semibold text-slate-800">연동 및 API 설정</h2>
            <p className="mt-1 text-xs text-slate-500">
              키는 저장 시 암호화되며, 화면에는 마스킹되어 표시됩니다.
            </p>

            <label className="mt-5 block text-xs font-medium text-slate-600">Upstage OCR API Key</label>
            <div className="relative mt-1">
              <input
                type={ocrKeyVisible ? 'text' : 'password'}
                value={ocrKey}
                onChange={(e) => setOcrKey(e.target.value)}
                placeholder="sk-upstage••••••••"
                autoComplete="off"
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 pr-24 font-mono text-sm text-slate-800 outline-none focus:border-violet-300 focus:bg-white focus:ring-2 focus:ring-violet-100"
              />
              <button
                type="button"
                onClick={() => setOcrKeyVisible((v) => !v)}
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg px-2 py-1 text-xs font-medium text-violet-700 hover:bg-violet-50"
              >
                {ocrKeyVisible ? '숨기기' : '표시'}
              </button>
            </div>
            {!ocrKey && (
              <p className="mt-1 text-[11px] text-slate-400">저장됨: {maskedPlaceholder}</p>
            )}

            <label className="mt-4 block text-xs font-medium text-slate-600">LLM Provider</label>
            <select
              value={llmProvider}
              onChange={(e) => setLlmProvider(e.target.value)}
              className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm outline-none focus:border-violet-300 focus:ring-2 focus:ring-violet-100"
            >
              <option value="gpt-4o">OpenAI GPT-4o</option>
              <option value="gpt-4o-mini">OpenAI GPT-4o mini</option>
              <option value="claude-3-5-sonnet">Anthropic Claude 3.5 Sonnet</option>
              <option value="claude-3-opus">Anthropic Claude 3 Opus</option>
            </select>

            <label className="mt-4 block text-xs font-medium text-slate-600">LLM API Key</label>
            <div className="relative mt-1">
              <input
                type={llmKeyVisible ? 'text' : 'password'}
                value={llmKey}
                onChange={(e) => setLlmKey(e.target.value)}
                placeholder="sk••••••••••••••••"
                autoComplete="off"
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 pr-24 font-mono text-sm text-slate-800 outline-none focus:border-violet-300 focus:bg-white focus:ring-2 focus:ring-violet-100"
              />
              <button
                type="button"
                onClick={() => setLlmKeyVisible((v) => !v)}
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg px-2 py-1 text-xs font-medium text-violet-700 hover:bg-violet-50"
              >
                {llmKeyVisible ? '숨기기' : '표시'}
              </button>
            </div>
            {!llmKey && (
              <p className="mt-1 text-[11px] text-slate-400">저장됨: sk-••••••••••abcd</p>
            )}

            <label className="mt-4 block text-xs font-medium text-slate-600">
              Vector DB 엔드포인트 / Namespace
            </label>
            <div className="relative mt-1">
              <input
                type={vectorEpVisible ? 'text' : 'password'}
                value={vectorEndpoint}
                onChange={(e) => setVectorEndpoint(e.target.value)}
                placeholder="https://vector••••••••/collections/uni-bot"
                autoComplete="off"
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 pr-24 font-mono text-sm text-slate-800 outline-none focus:border-violet-300 focus:bg-white focus:ring-2 focus:ring-violet-100"
              />
              <button
                type="button"
                onClick={() => setVectorEpVisible((v) => !v)}
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg px-2 py-1 text-xs font-medium text-violet-700 hover:bg-violet-50"
              >
                {vectorEpVisible ? '숨기기' : '표시'}
              </button>
            </div>
            {!vectorEndpoint && (
              <p className="mt-1 text-[11px] text-slate-400">저장됨: {maskedPlaceholder}</p>
            )}
          </section>

          <section className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-slate-200/80">
            <h2 className="text-sm font-semibold text-slate-800">챗봇 위젯 브랜딩</h2>
            <p className="mt-1 text-xs text-slate-500">학생 화면에 노출되는 기본 문구와 테마입니다.</p>

            <label className="mt-5 block text-xs font-medium text-slate-600">기본 인사말</label>
            <textarea
              value={greeting}
              onChange={(e) => setGreeting(e.target.value)}
              rows={3}
              className="mt-1 w-full resize-y rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-800 outline-none focus:border-violet-300 focus:bg-white focus:ring-2 focus:ring-violet-100"
            />

            <label className="mt-4 block text-xs font-medium text-slate-600">테마 컬러 (Primary)</label>
            <div className="mt-2 flex flex-wrap items-center gap-4">
              <input
                type="color"
                value={themeColor}
                onChange={(e) => setThemeColor(e.target.value)}
                className="theme-color-input h-12 w-12 cursor-pointer overflow-hidden rounded-full border-2 border-slate-200 p-0 shadow-sm"
                title="색상 선택"
              />
              <input
                type="text"
                value={themeColor}
                onChange={(e) => setThemeColor(e.target.value)}
                pattern="^#([0-9A-Fa-f]{6})$"
                className="w-36 rounded-xl border border-slate-200 bg-white px-4 py-2 font-mono text-sm uppercase outline-none focus:border-violet-300 focus:ring-2 focus:ring-violet-100"
              />
              <div
                className="flex h-10 min-w-[120px] items-center justify-center rounded-xl px-4 text-sm font-medium text-white shadow-sm"
                style={{ backgroundColor: themeColor }}
              >
                미리보기
              </div>
            </div>

            <p className="mt-3 text-[11px] text-slate-400">
              마스코트 이미지는 자산 관리에서 업로드할 수 있습니다. (연동 예정)
            </p>
          </section>

          <section className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-slate-200/80">
            <h2 className="text-sm font-semibold text-slate-800">시스템 제어</h2>
            <p className="mt-1 text-xs text-slate-500">점검 모드 시 학생 위젯에 안내 문구가 표시됩니다.</p>

            <div className="mt-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm font-medium text-slate-800">시스템 점검 모드</p>
                <p className="mt-0.5 text-xs text-slate-500">
                  활성화 시 &quot;현재 시스템 점검 중입니다&quot; 메시지를 출력합니다.
                </p>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={maintenance}
                onClick={() => setMaintenance((m) => !m)}
                className={`relative inline-flex h-9 w-16 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition focus:outline-none focus:ring-2 focus:ring-violet-400 focus:ring-offset-2 ${
                  maintenance ? 'bg-amber-500' : 'bg-slate-200'
                }`}
              >
                <span
                  className={`pointer-events-none mt-0.5 inline-block h-7 w-7 rounded-full bg-white shadow-md ring-1 ring-slate-900/10 transition ${
                    maintenance ? 'translate-x-8' : 'translate-x-0.5'
                  }`}
                />
              </button>
            </div>
            {maintenance && (
              <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-900">
                점검 모드 ON — 모든 테넌트 학생 위젯에 점검 배너가 노출됩니다.
              </p>
            )}

            <label className="mt-6 block text-xs font-medium text-slate-600">대화·로그 데이터 보관 주기</label>
            <select
              value={retention}
              onChange={(e) => setRetention(e.target.value)}
              className="mt-1 w-full max-w-xs rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm outline-none focus:border-violet-300 focus:ring-2 focus:ring-violet-100"
            >
              <option value="1y">1년</option>
              <option value="3y">3년</option>
              <option value="forever">영구 보관</option>
            </select>
          </section>
        </div>
      </div>

      <div className="shrink-0 border-t border-slate-200 bg-white/95 px-8 py-4 shadow-[0_-4px_24px_rgba(15,23,42,0.06)] backdrop-blur supports-[backdrop-filter]:bg-white/80">
        <div className="flex w-full justify-end">
          <button
            type="button"
            onClick={handleSave}
            className="rounded-xl bg-violet-600 px-6 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-violet-700"
          >
            변경사항 저장
          </button>
        </div>
      </div>
    </div>
  )
}

export default SystemSettings
