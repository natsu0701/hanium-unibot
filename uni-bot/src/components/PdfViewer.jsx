import { useMemo, useState } from 'react'
import { ChevronDown, Download, Printer, Search } from 'lucide-react'
import { LINE_ICON } from '../constants/iconProps'

const SCHOOL_OPTIONS = [
  { label: '건국대학교 글로컬캠퍼스', file: '/guide.pdf' },
  { label: '연세대학교', file: '/guide2.pdf' },
]

function PdfViewer({
  targetPage = 1,
  currentUser = 'konkuk',
  activePdfFile = null,
  onPdfFileChange,
}) {
  const selectedSchool = useMemo(() => {
    if (activePdfFile) {
      const match = SCHOOL_OPTIONS.find((o) => o.file === activePdfFile)
      if (match) return match
    }
    return currentUser === 'yonsei' ? SCHOOL_OPTIONS[1] : SCHOOL_OPTIONS[0]
  }, [currentUser, activePdfFile])

  const iframeSrc = `${selectedSchool.file}#page=${targetPage}&zoom=100`
  const [isPdfSearchOpen, setIsPdfSearchOpen] = useState(false)
  const [pdfSearchQuery, setPdfSearchQuery] = useState('')

  const handleSchoolChange = (event) => {
    const nextSchool = SCHOOL_OPTIONS.find((option) => option.file === event.target.value)
    if (!nextSchool) return
    onPdfFileChange?.(nextSchool.file)
  }

  const handlePdfSearchSubmit = () => {
    const q = pdfSearchQuery.trim()
    console.log('[PDF 검색 실행]', q, { file: selectedSchool.file, page: targetPage })
  }

  const handlePdfSearchToggle = () => {
    setIsPdfSearchOpen((open) => !open)
  }

  const handlePrint = () => {
    window.open(selectedSchool.file, '_blank', 'noopener,noreferrer')
  }

  return (
    <aside className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-slate-50">
      <header className="sticky top-0 z-20 shrink-0 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="flex items-center gap-3 px-4 py-3">
          <div className="min-w-0 flex-1">
            <div className="relative min-w-0 max-w-xs rounded-lg border border-slate-200 bg-white px-3 py-2">
              <p className="truncate pr-8 text-sm font-medium text-slate-700">
                {selectedSchool.label}
              </p>
              <ChevronDown
                className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-slate-400"
                aria-hidden
                {...LINE_ICON}
              />
              <select
                value={selectedSchool.file}
                onChange={handleSchoolChange}
                className="absolute inset-0 cursor-pointer opacity-0"
                aria-label="학교 선택"
              >
                {SCHOOL_OPTIONS.map((school) => (
                  <option key={school.file} value={school.file}>
                    {school.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <button
              type="button"
              onClick={handlePdfSearchToggle}
              className={`inline-flex h-8 w-8 items-center justify-center rounded-md border text-slate-600 transition hover:bg-slate-100 ${
                isPdfSearchOpen
                  ? 'border-[#654AEC] bg-violet-50 text-[#654AEC]'
                  : 'border-slate-200'
              }`}
              aria-label="검색"
              aria-expanded={isPdfSearchOpen}
            >
              <Search size={16} {...LINE_ICON} />
            </button>
            <a
              href={selectedSchool.file}
              download
              className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-slate-200 text-slate-600 transition hover:bg-slate-100"
              aria-label="다운로드"
            >
              <Download size={16} {...LINE_ICON} />
            </a>
            <button
              type="button"
              onClick={handlePrint}
              className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-slate-200 text-slate-600 transition hover:bg-slate-100"
              aria-label="인쇄"
            >
              <Printer size={16} {...LINE_ICON} />
            </button>
          </div>
        </div>

        <div
          className={`overflow-hidden border-slate-200 bg-slate-50 transition-[max-height,opacity,border-bottom-width] duration-300 ease-out ${
            isPdfSearchOpen
              ? 'max-h-16 border-b border-slate-200 opacity-100'
              : 'max-h-0 border-b-0 opacity-0'
          }`}
          aria-hidden={!isPdfSearchOpen}
        >
          <div className="flex items-center gap-2 px-4 pb-3 pt-1">
            <label htmlFor="pdf-search-input" className="sr-only">
              PDF 내 검색어
            </label>
            <input
              id="pdf-search-input"
              type="search"
              value={pdfSearchQuery}
              onChange={(event) => setPdfSearchQuery(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  event.preventDefault()
                  handlePdfSearchSubmit()
                }
              }}
              placeholder="PDF에서 검색할 단어 입력..."
              className="min-w-0 flex-1 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none placeholder:text-slate-400 focus:border-[#654AEC] focus:ring-2 focus:ring-[#654AEC]/20"
            />
            <button
              type="button"
              onClick={handlePdfSearchSubmit}
              className="shrink-0 rounded-lg bg-[#654AEC] px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-[#5438cc]"
            >
              검색
            </button>
          </div>
        </div>
      </header>
      <section className="relative h-full w-full flex-1 overflow-hidden">
        <div className="h-full w-full flex-1">
          <iframe
            src={iframeSrc}
            className="h-full w-full border-none"
            title="PDF Viewer"
          />
        </div>
      </section>
    </aside>
  )
}

export default PdfViewer
