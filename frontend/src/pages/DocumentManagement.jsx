import { useMemo, useState } from 'react'
import { FileText, FileUp, PencilLine, Plus, Search, Trash2, X } from 'lucide-react'
import { LINE_ICON } from '../constants/iconProps'

const SUB_CATEGORY_OPTIONS = [
  '졸업 요람',
  '학과 요람',
  '장학 규정',
  '학사 규정',
  '수강 편람',
]

const INITIAL_SCHOOLS = [
  {
    id: 'kku-gl',
    name: '건국대학교 글로컬캠퍼스',
    documents: [
      {
        id: 'kku-d1',
        name: '2026학년도 졸업요람.pdf',
        subCategory: '졸업 요람',
        uploadedAt: '2026-01-08',
        pipelineStatus: 'completed',
      },
      {
        id: 'kku-d2',
        name: '경영학과_학과안내.pdf',
        subCategory: '학과 요람',
        uploadedAt: '2026-01-15',
        pipelineStatus: 'ocr',
      },
      {
        id: 'kku-d3',
        name: '성적 장학 규정집.pdf',
        subCategory: '장학 규정',
        uploadedAt: '2026-01-22',
        pipelineStatus: 'embedding',
      },
      {
        id: 'kku-d4',
        name: '2026-1학기 수강편람.pdf',
        subCategory: '수강 편람',
        uploadedAt: '2026-02-01',
        pipelineStatus: 'error',
      },
    ],
  },
  {
    id: 'yonsei',
    name: '연세대학교',
    documents: [
      {
        id: 'ys-d1',
        name: '연세 학사 규정 총괄.pdf',
        subCategory: '학사 규정',
        uploadedAt: '2026-01-05',
        pipelineStatus: 'completed',
      },
      {
        id: 'ys-d2',
        name: '등록금 납부 안내.pdf',
        subCategory: '학사 규정',
        uploadedAt: '2026-01-19',
        pipelineStatus: 'ocr',
      },
    ],
  },
  {
    id: 'hanyang-er',
    name: '한양대학교 ERICA 캠퍼스',
    documents: [
      {
        id: 'hy-d1',
        name: 'ERICACampus 장학FAQ.pdf',
        subCategory: '장학 규정',
        uploadedAt: '2025-12-20',
        pipelineStatus: 'completed',
      },
    ],
  },
]

function pipelineBadge(status) {
  switch (status) {
    case 'completed':
      return (
        <span className="inline-flex rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-semibold text-emerald-700">
          OCR · 임베딩 완료
        </span>
      )
    case 'ocr':
      return (
        <span className="inline-flex rounded-full bg-violet-100 px-2.5 py-0.5 text-xs font-semibold text-violet-700">
          OCR 처리중
        </span>
      )
    case 'embedding':
      return (
        <span className="inline-flex rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-semibold text-amber-800">
          임베딩 처리중
        </span>
      )
    case 'error':
      return (
        <span className="inline-flex rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-semibold text-red-700">
          처리 오류
        </span>
      )
    default:
      return null
  }
}

function DocumentManagement() {
  const [schools, setSchools] = useState(INITIAL_SCHOOLS)
  const [selectedSchoolId, setSelectedSchoolId] = useState(INITIAL_SCHOOLS[0].id)
  const [schoolSearch, setSchoolSearch] = useState('')
  const [docSearch, setDocSearch] = useState('')
  const [uploadOpen, setUploadOpen] = useState(false)

  const filteredSchools = useMemo(() => {
    const q = schoolSearch.trim().toLowerCase()
    if (!q) return schools
    return schools.filter((s) => s.name.toLowerCase().includes(q))
  }, [schools, schoolSearch])

  const selectedSchool = useMemo(
    () => schools.find((s) => s.id === selectedSchoolId) ?? schools[0],
    [schools, selectedSchoolId],
  )

  const filteredDocuments = useMemo(() => {
    if (!selectedSchool) return []
    const q = docSearch.trim().toLowerCase()
    if (!q) return selectedSchool.documents
    return selectedSchool.documents.filter((d) => d.name.toLowerCase().includes(q))
  }, [selectedSchool, docSearch])

  const handleSubCategoryChange = (docId, value) => {
    setSchools((prev) =>
      prev.map((school) =>
        school.id !== selectedSchoolId
          ? school
          : {
              ...school,
              documents: school.documents.map((d) =>
                d.id === docId ? { ...d, subCategory: value } : d,
              ),
            },
      ),
    )
  }

  const handleAddSchool = () => {
    const name = window.prompt('추가할 대학교 이름을 입력하세요.')
    if (!name?.trim()) return
    const id = `school-${Date.now()}`
    setSchools((prev) => [...prev, { id, name: name.trim(), documents: [] }])
    setSelectedSchoolId(id)
  }

  return (
    <div className="flex h-full min-h-0 w-full flex-col overflow-hidden bg-slate-100">
      <div className="shrink-0 border-b border-slate-200 bg-white px-8 py-6">
        <h1 className="text-lg font-bold text-slate-800">문서 관리</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          기관별로 문서를 그룹화해 등록·OCR·임베딩 상태를 관리합니다.
        </p>
      </div>

      <div className="flex min-h-0 flex-1 flex-row gap-6 overflow-hidden px-8 py-6">
        {/* 좌측: 학교 목록 (~1/3) */}
        <aside className="flex min-h-0 w-full shrink-0 flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm lg:w-[32%]">
          <div className="space-y-3 border-b border-slate-100 p-4">
            <button
              type="button"
              onClick={handleAddSchool}
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-violet-200 bg-violet-50 py-2.5 text-sm font-semibold text-violet-700 transition hover:bg-violet-100"
            >
              <Plus size={18} {...LINE_ICON} />
              학교 추가
            </button>
            <div className="relative">
              <Search
                className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
                {...LINE_ICON}
                aria-hidden
              />
              <input
                type="search"
                value={schoolSearch}
                onChange={(e) => setSchoolSearch(e.target.value)}
                placeholder="학교 검색..."
                className="w-full rounded-xl border border-slate-200 py-2.5 pl-10 pr-3 text-sm text-slate-800 shadow-sm outline-none focus:border-violet-300 focus:ring-2 focus:ring-violet-100"
              />
            </div>
          </div>
          <ul className="flex-1 overflow-y-auto p-2">
            {filteredSchools.map((school) => {
              const count = school.documents.length
              const active = school.id === selectedSchoolId
              return (
                <li key={school.id}>
                  <button
                    type="button"
                    onClick={() => setSelectedSchoolId(school.id)}
                    className={`mb-1 flex w-full items-center justify-between rounded-xl px-3 py-3 text-left text-sm transition ${
                      active
                        ? 'bg-violet-50 font-semibold text-violet-800 ring-1 ring-violet-200'
                        : 'text-slate-700 hover:bg-slate-50'
                    }`}
                  >
                    <span className="min-w-0 truncate pr-2">{school.name}</span>
                    <span className="flex shrink-0 items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                      <FileText size={12} {...LINE_ICON} aria-hidden />
                      {count}개
                    </span>
                  </button>
                </li>
              )
            })}
            {filteredSchools.length === 0 && (
              <p className="px-2 py-6 text-center text-sm text-slate-500">검색 결과 없음</p>
            )}
          </ul>
        </aside>

        {/* 우측: 선택 학교 문서 */}
        <section className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="shrink-0 flex flex-wrap items-start justify-between gap-4 border-b border-slate-100 p-5">
            <div className="min-w-0 flex-1">
              <h2 className="text-xl font-bold text-slate-800">
                {selectedSchool?.name ?? '학교 선택'}
                <span className="font-semibold text-slate-600"> 문서 관리</span>
              </h2>
              <div className="relative mt-3 max-w-md">
                <Search
                  className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
                  {...LINE_ICON}
                  aria-hidden
                />
                <input
                  type="search"
                  value={docSearch}
                  onChange={(e) => setDocSearch(e.target.value)}
                  placeholder="이 학교 문서 검색..."
                  className="w-full rounded-xl border border-slate-200 py-2 pl-10 pr-3 text-sm text-slate-800 shadow-sm outline-none focus:border-violet-300 focus:ring-2 focus:ring-violet-100"
                />
              </div>
            </div>
            <button
              type="button"
              onClick={() => setUploadOpen(true)}
              disabled={!selectedSchool}
              className="inline-flex shrink-0 items-center gap-2 rounded-xl bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-violet-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <FileUp size={18} {...LINE_ICON} />
              이 학교에 문서 업로드
            </button>
          </div>

          <div className="flex-1 overflow-auto p-5">
            <div className="overflow-hidden rounded-xl border border-slate-200">
              <div className="overflow-x-auto">
                <table className="w-full min-w-[720px] text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-500">
                      <th className="px-4 py-3">문서명</th>
                      <th className="px-4 py-3">세부 분류</th>
                      <th className="px-4 py-3">업로드 날짜</th>
                      <th className="px-4 py-3">OCR / 임베딩</th>
                      <th className="px-4 py-3 text-right">액션</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-700">
                    {filteredDocuments.map((doc) => (
                      <tr key={doc.id} className="hover:bg-slate-50/90">
                        <td className="max-w-[220px] truncate px-4 py-3 font-medium text-slate-800">
                          {doc.name}
                        </td>
                        <td className="px-4 py-3">
                          <select
                            value={doc.subCategory}
                            onChange={(e) =>
                              handleSubCategoryChange(doc.id, e.target.value)
                            }
                            className="w-full max-w-[160px] cursor-pointer rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700 shadow-sm outline-none focus:border-violet-300 focus:ring-2 focus:ring-violet-100"
                          >
                            {SUB_CATEGORY_OPTIONS.map((opt) => (
                              <option key={opt} value={opt}>
                                {opt}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td className="whitespace-nowrap px-4 py-3 text-slate-600">
                          {doc.uploadedAt}
                        </td>
                        <td className="px-4 py-3">{pipelineBadge(doc.pipelineStatus)}</td>
                        <td className="px-4 py-3">
                          <div className="flex items-center justify-end gap-1">
                            <button
                              type="button"
                              title="수정"
                              className="rounded-lg p-2 text-slate-500 transition hover:bg-violet-50 hover:text-violet-700"
                            >
                              <PencilLine size={18} {...LINE_ICON} />
                            </button>
                            <button
                              type="button"
                              title="삭제"
                              className="rounded-lg p-2 text-slate-500 transition hover:bg-red-50 hover:text-red-600"
                            >
                              <Trash2 size={18} {...LINE_ICON} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {filteredDocuments.length === 0 && (
                <p className="px-4 py-10 text-center text-sm text-slate-500">
                  등록된 문서가 없거나 검색 결과가 없습니다.
                </p>
              )}
            </div>
          </div>
        </section>
      </div>

      {uploadOpen && selectedSchool && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          role="dialog"
          aria-modal="true"
        >
          <div className="relative w-full max-w-lg rounded-xl bg-white p-6 shadow-xl">
            <button
              type="button"
              onClick={() => setUploadOpen(false)}
              className="absolute right-4 top-4 rounded-lg p-1 text-slate-500 hover:bg-slate-100"
              aria-label="닫기"
            >
              <X size={20} {...LINE_ICON} />
            </button>
            <h2 className="text-lg font-bold text-slate-800">문서 업로드</h2>
            <p className="mt-2 text-sm text-violet-700">
              대상 기관: <span className="font-semibold">{selectedSchool.name}</span>
            </p>
            <p className="mt-2 text-sm text-slate-500">
              PDF를 선택하면 해당 학교 지식 베이스용으로 OCR 및 임베딩이 진행됩니다. (데모 UI)
            </p>
            <div className="mt-6 rounded-xl border-2 border-dashed border-slate-200 bg-slate-50 p-8 text-center text-sm text-slate-600">
              파일 선택 또는 드래그 앤 드롭
            </div>
            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setUploadOpen(false)}
                className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                취소
              </button>
              <button
                type="button"
                onClick={() => setUploadOpen(false)}
                className="rounded-xl bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-700"
              >
                업로드 시작
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default DocumentManagement
