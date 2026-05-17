import { useMemo, useState } from 'react'
import { Pencil, Search, Trash2 } from 'lucide-react'
import { LINE_ICON } from '../constants/iconProps'

const CHUNKS = [
  {
    id: 'c1',
    source: '장학금 규정집',
    page: 12,
    preview:
      '성적우수 장학금 수혜 대상자는 직전 학기 평점 평균 3.5 이상이며, 15학점 이상 이수한 자에 한한다. 다만 징계 이력이 있는 경우 심사에서 제외될 수 있다.',
  },
  {
    id: 'c2',
    source: '2026학년도 학사요람',
    page: 48,
    preview:
      '수강신청 변경 기간은 매 학기 개시일로부터 정해진 일정 내에만 가능하며, 정원 초과 과목은 선착순 또는 추첨에 따른다. 변경 후 이수 신청서는 반드시 지도교수 승인을 받아야 한다.',
  },
  {
    id: 'c3',
    source: '수강편람_2026-1학기',
    page: 5,
    preview:
      '재수강은 동일 과목코드에 한하며, 최초 이수 성적이 C+ 이하인 경우에만 신청할 수 있다. 재수강 시 최종 성적은 최고 성적만 반영된다.',
  },
  {
    id: 'c4',
    source: '졸업 요건 안내',
    page: 3,
    preview:
      '졸업을 위해서는 전공 60학점 이상, 교양 30학점 이상을 이수하고, 졸업 논문 또는 졸업작품 심사에 합격하여야 한다. 연계 전공 과목은 학과별 세부 규정을 따른다.',
  },
]

function KnowledgeBase() {
  const [query, setQuery] = useState('')

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return CHUNKS
    return CHUNKS.filter(
      (c) =>
        c.preview.toLowerCase().includes(q) ||
        c.source.toLowerCase().includes(q) ||
        String(c.page).includes(q),
    )
  }, [query])

  return (
    <div className="flex h-full min-h-0 w-full flex-col overflow-hidden bg-slate-100">
      <div className="shrink-0 border-b border-slate-200 bg-white px-8 py-6">
        <h1 className="text-lg font-bold text-slate-800">지식 베이스</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          Vector DB에 저장된 청크를 검색하고 텍스트를 점검합니다.
        </p>
      </div>

      <div className="shrink-0 border-b border-slate-100 bg-white px-8 py-4">
        <div className="relative">
          <Search
            className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400"
            {...LINE_ICON}
            aria-hidden
          />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="키워드로 청크 검색 (예: 장학금, 수강신청, 졸업)..."
            className="w-full rounded-xl border border-slate-200 bg-slate-50 py-4 pl-12 pr-4 text-base text-slate-800 shadow-sm outline-none ring-violet-100 focus:border-violet-400 focus:bg-white focus:ring-2"
          />
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-8 py-6">
        <div className="flex flex-col gap-4">
          {filtered.map((chunk) => (
            <article
              key={chunk.id}
              className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-violet-200 hover:shadow-md"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-violet-700">
                    {chunk.source}
                    <span className="ml-2 font-normal text-slate-500">· {chunk.page}p</span>
                  </p>
                  <p className="mt-2 line-clamp-3 text-sm leading-relaxed text-slate-600">
                    {chunk.preview}
                  </p>
                </div>
                <div className="flex shrink-0 gap-2">
                  <button
                    type="button"
                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-xs font-medium text-slate-700 transition hover:border-violet-300 hover:bg-violet-50 hover:text-violet-800"
                  >
                    <Pencil size={14} {...LINE_ICON} />
                    수정
                  </button>
                  <button
                    type="button"
                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-xs font-medium text-slate-700 transition hover:border-red-200 hover:bg-red-50 hover:text-red-700"
                  >
                    <Trash2 size={14} {...LINE_ICON} />
                    삭제
                  </button>
                </div>
              </div>
            </article>
          ))}
        </div>
        {filtered.length === 0 && (
          <p className="py-12 text-center text-sm text-slate-500">검색 결과가 없습니다.</p>
        )}
      </div>
    </div>
  )
}

export default KnowledgeBase
