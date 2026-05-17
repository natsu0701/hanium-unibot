const WEEK_SCORES = [
  { day: '월', pct: 91 },
  { day: '화', pct: 93 },
  { day: '수', pct: 92 },
  { day: '목', pct: 95 },
  { day: '금', pct: 94 },
  { day: '토', pct: 96 },
  { day: '일', pct: 94 },
]

const WEAK_KEYWORDS = [
  { rank: 1, keyword: '다전공 이수', fails: 28, trend: '+12%' },
  { rank: 2, keyword: '휴학 연장', fails: 22, trend: '+8%' },
  { rank: 3, keyword: '등록금 환불 기준', fails: 19, trend: '+5%' },
  { rank: 4, keyword: '전공변경 학점 인정', fails: 17, trend: '+3%' },
  { rank: 5, keyword: '복수전공 졸업 요건', fails: 14, trend: '+2%' },
]

function ReliabilityAnalysis() {
  const maxPct = Math.max(...WEEK_SCORES.map((w) => w.pct))

  return (
    <div className="flex h-full min-h-0 w-full flex-col overflow-hidden bg-slate-100">
      <div className="shrink-0 border-b border-slate-200 bg-white px-8 py-6">
        <h1 className="text-lg font-bold text-slate-800">신뢰도 분석</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          Self-RAG 검증 결과를 바탕으로 답변 품질과 환각 위험을 통계적으로 모니터링합니다.
        </p>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-8 py-6">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <article className="rounded-xl border border-emerald-100 bg-white p-5 shadow-sm">
            <p className="text-sm font-medium text-slate-500">평균 검증 통과율</p>
            <p className="mt-2 text-3xl font-bold tabular-nums text-emerald-600">94.2%</p>
            <p className="mt-2 text-xs text-slate-400">조직 전체 세션 대비 자동 검증 Pass 비율</p>
          </article>
          <article className="rounded-xl border border-amber-100 bg-white p-5 shadow-sm">
            <p className="text-sm font-medium text-slate-500">환각(Hallucination) 의심 비율</p>
            <p className="mt-2 text-3xl font-bold tabular-nums text-amber-600">1.8%</p>
            <p className="mt-2 text-xs text-slate-400">
              근거 대비 과도한 추론·문서 불일치로 표시된 응답
            </p>
          </article>
          <article className="rounded-xl border border-violet-100 bg-white p-5 shadow-sm">
            <p className="text-sm font-medium text-slate-500">답변 불가(Fallback) 비율</p>
            <p className="mt-2 text-3xl font-bold tabular-nums text-violet-600">4.0%</p>
            <p className="mt-2 text-xs text-slate-400">
              관련 근거 청크 부재로 &quot;모르겠습니다&quot; 처리된 비율
            </p>
          </article>
        </div>

        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-5">
          <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm lg:col-span-3">
            <h2 className="text-sm font-semibold text-slate-800">주간 신뢰도 추이 (최근 7일)</h2>
            <p className="mt-1 text-xs text-slate-500">일별 평균 검증 점수 (목업 막대)</p>

            <div className="mt-6 flex h-52 items-end justify-between gap-2 px-2">
              {WEEK_SCORES.map(({ day, pct }) => (
                <div key={day} className="flex flex-1 flex-col items-center gap-2">
                  <div className="flex w-full flex-1 flex-col justify-end">
                    <div
                      className="w-full rounded-t-md bg-gradient-to-t from-violet-500 to-violet-400 transition-opacity hover:opacity-90"
                      style={{ height: `${(pct / maxPct) * 100}%`, minHeight: '12px' }}
                      title={`${pct}%`}
                    />
                  </div>
                  <span className="text-xs font-medium text-slate-600">{day}</span>
                  <span className="text-[10px] tabular-nums text-slate-400">{pct}%</span>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm lg:col-span-2">
            <h2 className="text-sm font-semibold text-slate-800">답변 취약 키워드 Top 5</h2>
            <p className="mt-1 text-xs text-slate-500">
              Fallback·Fail 비율이 높거나 재질문이 많은 표현입니다.
            </p>
            <ol className="mt-4 space-y-3">
              {WEAK_KEYWORDS.map((item) => (
                <li
                  key={item.keyword}
                  className="flex items-center gap-3 rounded-lg border border-slate-100 bg-slate-50 px-3 py-2"
                >
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-violet-100 text-xs font-bold text-violet-700">
                    {item.rank}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-slate-800">{item.keyword}</p>
                    <p className="text-xs text-slate-500">
                      이슈 {item.fails}건 · 이전 주 대비{' '}
                      <span className="font-medium text-amber-600">{item.trend}</span>
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          </section>
        </div>
      </div>
    </div>
  )
}

export default ReliabilityAnalysis
