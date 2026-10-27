import { useMemo, useRef, useState } from 'react'

const LOG_ROWS = [
  {
    id: '1',
    at: '2026-05-06 09:41:23',
    question: '다전공 이수 시 최소 학점은 어떻게 되나요?',
    answerSummary:
      '다전공은 전공 과목 합계 36학점 이상 이수해야 하며, 졸업요람 제4장에 따라...',
    refDoc: '장학금 규정집 §3조 (청크 #8841)',
    retrieveScore: 8,
    critiqueScore: 7,
    appropriateness: 9,
    status: 'Pass',
  },
  {
    id: '2',
    at: '2026-05-06 10:03:51',
    question: '휴학 연장 신청 마감이 언제인가요?',
    answerSummary:
      '매 학기 개시 후 4주 내에 신청하며, 2026학년도 1학기는 3월 31일까지입니다.',
    refDoc: '2026 학사요람 p.112 (청크 #2190)',
    retrieveScore: 9,
    critiqueScore: 9,
    appropriateness: 8,
    status: 'Pass',
  },
  {
    id: '3',
    at: '2026-05-06 10:52:07',
    question: '성적 장학금을 받으려면 학기당 몇 학점을 들어야 하나요?',
    answerSummary:
      '등록금 일부 면제를 받더라도 월별 분할 납부는 불가합니다. 카드 분할결제만 가능합니다.',
    refDoc: '장학금 규정집 §2조 (청크 #4402)',
    retrieveScore: 6,
    critiqueScore: 4,
    appropriateness: 5,
    status: 'Fail',
  },
  {
    id: '4',
    at: '2026-05-06 11:18:44',
    question: '수강변경 후 이수 과목 명세는 어디서 받나요?',
    answerSummary:
      '근거 문서에서 해당 정보를 확인하지 못해 상담원 연결 또는 학과 사무실 문의가 필요합니다.',
    refDoc: '— (근거 미매칭)',
    retrieveScore: 3,
    critiqueScore: 6,
    appropriateness: 7,
    status: 'Warning',
  },
]

function DateField({ label, value, onChange }) {
  const inputRef = useRef(null)

  const openPicker = () => {
    const input = inputRef.current

    if (!input) {
      return
    }

    if (typeof input.showPicker === 'function') {
      input.showPicker()
      return
    }

    input.focus()
  }

  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-slate-500">
        {label}
      </span>
      <span
        className="inline-flex cursor-pointer items-center rounded-xl border border-slate-200 bg-white px-3 py-2 shadow-sm transition hover:border-violet-300 focus-within:border-violet-300 focus-within:ring-2 focus-within:ring-violet-100"
        onClick={openPicker}
      >
        <input
          ref={inputRef}
          type="date"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onClick={(event) => {
            event.stopPropagation()
            event.currentTarget.showPicker?.()
          }}
          className="w-[11.5rem] cursor-pointer bg-transparent text-sm text-slate-800 outline-none"
        />
      </span>
    </label>
  )
}

function scoreBadge(value) {
  const color =
    value >= 8 ? 'bg-emerald-100 text-emerald-800' : value >= 5 ? 'bg-amber-100 text-amber-800' : 'bg-red-100 text-red-800'
  return (
    <span className={`rounded-md px-2 py-0.5 text-xs font-bold tabular-nums ${color}`}>
      {value}/10
    </span>
  )
}

function statusBadge(status) {
  if (status === 'Pass')
    return (
      <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-700">
        Pass
      </span>
    )
  if (status === 'Fail')
    return (
      <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-700">
        Fail
      </span>
    )
  return (
    <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800">
      Warning
    </span>
  )
}

function ValidationLogs() {
  const [statusFilter, setStatusFilter] = useState('All')
  const [fromDate, setFromDate] = useState('')
  const [toDate, setToDate] = useState('')

  const filtered = useMemo(() => {
    let rows = [...LOG_ROWS]
    if (statusFilter !== 'All') {
      rows = rows.filter((r) => r.status === statusFilter)
    }
    if (fromDate) {
      rows = rows.filter((r) => r.at.slice(0, 10) >= fromDate)
    }
    if (toDate) {
      rows = rows.filter((r) => r.at.slice(0, 10) <= toDate)
    }
    return rows
  }, [statusFilter, fromDate, toDate])

  return (
    <div className="flex h-full min-h-0 w-full flex-col overflow-hidden bg-slate-100">
      <div className="shrink-0 border-b border-slate-200 bg-white px-8 py-6">
        <h1 className="text-lg font-bold text-slate-800">검증 로그</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          질의별 Self-RAG 단계별 점수와 참조 근거를 추적합니다.
        </p>
      </div>

      <div className="flex min-h-0 flex-1 flex-col overflow-hidden px-8 py-6">
        <div className="mb-4 flex shrink-0 flex-wrap items-end gap-3">
          <DateField
            label="시작일"
            value={fromDate}
            onChange={setFromDate}
          />
          <DateField
            label="종료일"
            value={toDate}
            onChange={setToDate}
          />
          <div className="min-w-[140px]">
            <label className="mb-1 block text-xs font-medium text-slate-500">상태</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm focus:border-violet-300 focus:outline-none focus:ring-2 focus:ring-violet-100"
            >
              <option value="All">All</option>
              <option value="Pass">Pass</option>
              <option value="Fail">Fail</option>
              <option value="Warning">Warning</option>
            </select>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="h-full min-h-0 overflow-auto">
            <table className="w-full min-w-[1100px] table-fixed text-left text-sm">
              <colgroup>
                <col className="w-[140px]" />
                <col className="w-[36%]" />
                <col className="w-[22%]" />
                <col className="w-[17%]" />
                <col className="w-24" />
                <col className="w-[7rem]" />
                <col className="w-20" />
                <col className="w-24" />
              </colgroup>
              <thead className="sticky top-0 z-10 bg-slate-50 shadow-[0_1px_0_0_rgb(226_232_240)]">
                <tr className="border-b border-slate-200 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  <th className="whitespace-nowrap px-4 py-3">발생 일시</th>
                  <th className="px-4 py-3">사용자 질문</th>
                  <th className="px-4 py-3">AI 답변</th>
                  <th className="px-4 py-3">참조 문서</th>
                  <th className="whitespace-normal px-2 py-3 text-[0.65rem] leading-tight" title="문서 검색 품질">
                    Relevance
                  </th>
                  <th className="whitespace-normal px-2 py-3 text-[0.65rem] leading-tight" title="답변의 문서 근거성">
                    Groundedness
                  </th>
                  <th className="whitespace-nowrap px-2 py-3" title="질문 적합성">
                    적절성
                  </th>
                  <th className="whitespace-nowrap px-3 py-3">상태</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {filtered.map((row) => (
                  <tr key={row.id} className="hover:bg-slate-50/80">
                    <td className="whitespace-nowrap px-4 py-3 text-xs text-slate-500 tabular-nums">
                      {row.at}
                    </td>
                    <td className="min-w-0 px-4 py-3 align-top text-xs">
                      <p
                        className="line-clamp-2 break-words text-slate-800"
                        title={row.question}
                      >
                        {row.question}
                      </p>
                    </td>
                    <td
                      className="min-w-0 truncate px-4 py-3 text-xs text-slate-600"
                      title={row.answerSummary}
                    >
                      {row.answerSummary}
                    </td>
                    <td
                      className="min-w-0 truncate px-4 py-3 text-xs text-violet-700"
                      title={row.refDoc}
                    >
                      {row.refDoc}
                    </td>
                    <td className="px-2 py-3">{scoreBadge(row.retrieveScore)}</td>
                    <td className="px-2 py-3">{scoreBadge(row.critiqueScore)}</td>
                    <td className="px-2 py-3">{scoreBadge(row.appropriateness)}</td>
                    <td className="px-3 py-3">{statusBadge(row.status)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filtered.length === 0 && (
              <p className="py-12 text-center text-sm text-slate-500">조건에 맞는 로그가 없습니다.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default ValidationLogs
