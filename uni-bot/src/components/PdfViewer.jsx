import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { ChevronDown, ChevronLeft, ChevronRight, Download, Printer } from 'lucide-react'
import { Document, Page, pdfjs } from 'react-pdf'
import 'react-pdf/dist/Page/AnnotationLayer.css'
import 'react-pdf/dist/Page/TextLayer.css'
import { LINE_ICON } from '../constants/iconProps'

// PDF.js 워커는 react-pdf 컴포넌트를 렌더링하는 모듈과 동일한 파일에서 설정해야 합니다.
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString()

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

  // 실제로 렌더링·다운로드·인쇄할 파일은 부모가 내려준 activePdfFile을 우선합니다.
  // (학교별로 서로 다른 규정 PDF URL을 추가해도 그대로 표시됩니다.)
  const fileUrl = activePdfFile ?? selectedSchool.file

  const [numPages, setNumPages] = useState(null)
  const [pageNumber, setPageNumber] = useState(targetPage)
  const [pageInput, setPageInput] = useState(String(targetPage))
  const [containerWidth, setContainerWidth] = useState(0)
  const containerRef = useRef(null)

  // 현재 페이지가 바뀌면 입력창 표시값도 동기화합니다.
  useEffect(() => {
    setPageInput(String(pageNumber))
  }, [pageNumber])

  // 부모로부터 전달된 targetPage가 "실제로 바뀔 때만" 해당 페이지로 이동합니다.
  // (numPages 변경 등 다른 이유로 효과가 재실행될 때 페이지가 되돌아가는 것을 방지)
  const appliedTargetRef = useRef(targetPage)
  useEffect(() => {
    if (!targetPage || targetPage === appliedTargetRef.current) return
    appliedTargetRef.current = targetPage
    setPageNumber(
      numPages ? Math.min(Math.max(targetPage, 1), numPages) : targetPage,
    )
  }, [targetPage, numPages])

  // 다른 규정 파일로 교체되면 페이지 정보를 초기화하고 1페이지부터 다시 시작합니다.
  useEffect(() => {
    setNumPages(null)
    setPageNumber(1)
  }, [fileUrl])

  // 뷰어 컨테이너 너비에 맞춰 PDF 페이지 폭을 반응형으로 조정합니다.
  useLayoutEffect(() => {
    const node = containerRef.current
    if (!node) return
    const update = () => setContainerWidth(node.clientWidth)
    update()
    const observer = new ResizeObserver(update)
    observer.observe(node)
    return () => observer.disconnect()
  }, [])

  const handleSchoolChange = (event) => {
    const nextSchool = SCHOOL_OPTIONS.find((option) => option.file === event.target.value)
    if (!nextSchool) return
    setNumPages(null)
    setPageNumber(1)
    onPdfFileChange?.(nextSchool.file)
  }

  const handleLoadSuccess = ({ numPages: nextNumPages }) => {
    setNumPages(nextNumPages)
    setPageNumber((prev) => Math.min(Math.max(prev, 1), nextNumPages))
  }

  const goPrevPage = () => setPageNumber((prev) => Math.max(prev - 1, 1))
  const goNextPage = () =>
    setPageNumber((prev) => (numPages ? Math.min(prev + 1, numPages) : prev + 1))

  // 입력창에 숫자를 넣고 Enter를 누르면 해당 페이지로 이동합니다.
  // 1보다 작거나 전체 페이지 수를 초과하는 값은 무시하고 현재 페이지로 되돌립니다.
  const handlePageInputSubmit = () => {
    const next = Number(pageInput)
    if (!Number.isInteger(next) || next < 1 || (numPages && next > numPages)) {
      setPageInput(String(pageNumber))
      return
    }
    setPageNumber(next)
  }

  // 새 탭에서 PDF를 열어 브라우저 기본 뷰어의 인쇄 기능을 사용합니다.
  const handlePrint = () => {
    window.open(fileUrl, '_blank', 'noopener,noreferrer')
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
            <a
              href={fileUrl}
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
      </header>

      <section
        ref={containerRef}
        className="flex-1 overflow-auto bg-slate-200/60 px-4 py-6"
      >
        <div className="mx-auto flex w-full max-w-3xl justify-center">
          <Document
            file={fileUrl}
            onLoadSuccess={handleLoadSuccess}
            loading={
              <div className="py-20 text-center text-sm text-slate-500">
                PDF를 불러오는 중입니다...
              </div>
            }
            error={
              <div className="py-20 text-center text-sm text-red-500">
                PDF를 불러오지 못했습니다.
              </div>
            }
            className="flex justify-center"
          >
            <Page
              pageNumber={pageNumber}
              width={containerWidth ? Math.min(containerWidth - 32, 800) : undefined}
              className="overflow-hidden rounded-lg shadow-lg"
              renderAnnotationLayer
              renderTextLayer
            />
          </Document>
        </div>
      </section>

      <footer className="shrink-0 border-t border-slate-200 bg-white px-4 py-3">
        <div className="mx-auto flex w-full max-w-3xl items-center justify-center gap-4">
          <button
            type="button"
            onClick={goPrevPage}
            disabled={pageNumber <= 1}
            className="inline-flex items-center gap-1 rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <ChevronLeft size={16} {...LINE_ICON} />
            이전
          </button>
          <div className="flex items-center gap-1.5 text-sm font-medium text-slate-600">
            <input
              type="number"
              min={1}
              max={numPages ?? undefined}
              value={pageInput}
              onChange={(event) => setPageInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  event.preventDefault()
                  handlePageInputSubmit()
                }
              }}
              onBlur={handlePageInputSubmit}
              aria-label="페이지 번호 입력"
              className="w-14 rounded-md border border-slate-300 px-2 py-1 text-center text-sm outline-none focus:border-[#654AEC] focus:ring-2 focus:ring-[#654AEC]/20"
            />
            <span>/ {numPages ?? '-'}</span>
          </div>
          <button
            type="button"
            onClick={goNextPage}
            disabled={numPages ? pageNumber >= numPages : false}
            className="inline-flex items-center gap-1 rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
          >
            다음
            <ChevronRight size={16} {...LINE_ICON} />
          </button>
        </div>
      </footer>
    </aside>
  )
}

export default PdfViewer
