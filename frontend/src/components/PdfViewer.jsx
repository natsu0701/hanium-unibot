import {
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import {
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Download,
  Printer,
} from 'lucide-react'
import { Document, Page, pdfjs } from 'react-pdf'
import 'react-pdf/dist/Page/AnnotationLayer.css'
import 'react-pdf/dist/Page/TextLayer.css'
import { LINE_ICON } from '../constants/iconProps'

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString()

const SCHOOL_OPTIONS = [
  {
    label: '건국대학교 글로컬캠퍼스',
    file: '/guide.pdf',
  },
  {
    label: '연세대학교',
    file: '/guide2.pdf',
  },
]

function normalizeText(value = '') {
  return String(value)
    .replace(/\s+/g, '')
    .replace(/[.,:;·ㆍ•()[\]{}"'“”‘’\-_/]/g, '')
    .trim()
}

function PdfViewer({
  targetPage = 1,
  highlightText = '',
  currentUser = 'konkuk',
  activePdfFile = null,
  onPdfFileChange,
}) {
  const selectedSchool = useMemo(() => {
    if (activePdfFile) {
      const matchedSchool = SCHOOL_OPTIONS.find(
        (school) => school.file === activePdfFile,
      )

      if (matchedSchool) {
        return matchedSchool
      }
    }

    return currentUser === 'yonsei'
      ? SCHOOL_OPTIONS[1]
      : SCHOOL_OPTIONS[0]
  }, [currentUser, activePdfFile])

  const fileUrl = activePdfFile ?? selectedSchool.file

  const [numPages, setNumPages] = useState(null)
  const [pageNumber, setPageNumber] = useState(1)
  const [pageInput, setPageInput] = useState('1')
  const [containerWidth, setContainerWidth] = useState(0)

  const containerRef = useRef(null)
  const pageRef = useRef(null)

  useEffect(() => {
    setPageInput(String(pageNumber))
  }, [pageNumber])

  useEffect(() => {
    const parsedPage = Number(targetPage)

    if (
      !Number.isFinite(parsedPage) ||
      !Number.isInteger(parsedPage) ||
      parsedPage < 1
    ) {
      return
    }

    const nextPage = numPages
      ? Math.min(parsedPage, numPages)
      : parsedPage

    setPageNumber(nextPage)
  }, [targetPage, numPages, highlightText])

  useEffect(() => {
    setNumPages(null)
    setPageNumber(1)
    setPageInput('1')
  }, [fileUrl])

  useLayoutEffect(() => {
    const container = containerRef.current

    if (!container) {
      return undefined
    }

    const updateContainerWidth = () => {
      setContainerWidth(container.clientWidth)
    }

    updateContainerWidth()

    const resizeObserver = new ResizeObserver(
      updateContainerWidth,
    )

    resizeObserver.observe(container)

    return () => {
      resizeObserver.disconnect()
    }
  }, [])

  const clearHighlights = () => {
    const pageElement = pageRef.current

    if (!pageElement) {
      return
    }

    const textSpans = pageElement.querySelectorAll(
      '.react-pdf__Page__textContent span',
    )

    textSpans.forEach((span) => {
      span.style.backgroundColor = ''
      span.style.borderRadius = ''
      span.style.boxShadow = ''
    })
  }

  const applyHighlightStyle = (span) => {
    span.style.backgroundColor =
      'rgba(250, 204, 21, 0.75)'
    span.style.borderRadius = '2px'
    span.style.boxShadow =
      '0 0 0 1px rgba(234, 179, 8, 0.28)'
  }

  const highlightEvidence = () => {
    const pageElement = pageRef.current

    if (!pageElement) {
      return
    }

    const spans = Array.from(
      pageElement.querySelectorAll(
        '.react-pdf__Page__textContent span',
      ),
    )

    if (spans.length === 0) {
      return
    }

    clearHighlights()

    const normalizedEvidence = normalizeText(highlightText)

    if (!normalizedEvidence) {
      return
    }

    let fullPageText = ''
    const spanRanges = []

    spans.forEach((span) => {
      const spanText = normalizeText(span.textContent)
      const start = fullPageText.length

      fullPageText += spanText

      spanRanges.push({
        span,
        start,
        end: fullPageText.length,
      })
    })

    if (!fullPageText) {
      return
    }

    let matchStart = fullPageText.indexOf(normalizedEvidence)
    let matchLength = normalizedEvidence.length

    if (matchStart === -1) {
      const maximumCandidateLength = Math.min(
        normalizedEvidence.length,
        120,
      )

      for (
        let candidateLength = maximumCandidateLength;
        candidateLength >= 8;
        candidateLength -= 1
      ) {
        let found = false

        for (
          let evidenceStart = 0;
          evidenceStart + candidateLength <= normalizedEvidence.length;
          evidenceStart += 1
        ) {
          const candidate = normalizedEvidence.slice(
            evidenceStart,
            evidenceStart + candidateLength,
          )

          const foundIndex = fullPageText.indexOf(candidate)

          if (foundIndex !== -1) {
            matchStart = foundIndex
            matchLength = candidateLength
            found = true
            break
          }
        }

        if (found) {
          break
        }
      }
    }

    if (matchStart === -1) {
      return
    }

    const matchEnd = matchStart + matchLength
    let firstHighlightedSpan = null

    spanRanges.forEach(({ span, start, end }) => {
      const overlaps =
        end > matchStart &&
        start < matchEnd

      if (!overlaps) {
        return
      }

      applyHighlightStyle(span)

      if (!firstHighlightedSpan) {
        firstHighlightedSpan = span
      }
    })

    firstHighlightedSpan?.scrollIntoView({
      behavior: 'smooth',
      block: 'center',
    })
  }

  const handleSchoolChange = (event) => {
    const nextSchool = SCHOOL_OPTIONS.find(
      (school) => school.file === event.target.value,
    )

    if (!nextSchool) {
      return
    }

    setNumPages(null)
    setPageNumber(1)
    setPageInput('1')
    onPdfFileChange?.(nextSchool.file)
  }

  const handleLoadSuccess = ({
    numPages: loadedNumPages,
  }) => {
    setNumPages(loadedNumPages)

    setPageNumber((previousPage) =>
      Math.min(
        Math.max(previousPage, 1),
        loadedNumPages,
      ),
    )
  }

  const goPrevPage = () => {
    clearHighlights()

    setPageNumber((previousPage) =>
      Math.max(previousPage - 1, 1),
    )
  }

  const goNextPage = () => {
    clearHighlights()

    setPageNumber((previousPage) =>
      numPages
        ? Math.min(previousPage + 1, numPages)
        : previousPage + 1,
    )
  }

  const handlePageInputSubmit = () => {
    const nextPage = Number(pageInput)

    if (
      !Number.isFinite(nextPage) ||
      !Number.isInteger(nextPage) ||
      nextPage < 1 ||
      (numPages && nextPage > numPages)
    ) {
      setPageInput(String(pageNumber))
      return
    }

    clearHighlights()
    setPageNumber(nextPage)
  }

  const handlePrint = () => {
    window.open(
      fileUrl,
      '_blank',
      'noopener,noreferrer',
    )
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
                  <option
                    key={school.file}
                    value={school.file}
                  >
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
            <div ref={pageRef}>
              <Page
                key={`${pageNumber}-${highlightText}`}
                pageNumber={pageNumber}
                width={
                  containerWidth
                    ? Math.min(containerWidth - 32, 800)
                    : undefined
                }
                className="overflow-hidden rounded-lg shadow-lg"
                renderAnnotationLayer
                renderTextLayer
                onRenderTextLayerSuccess={highlightEvidence}
              />
            </div>
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
              onChange={(event) =>
                setPageInput(event.target.value)
              }
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
            disabled={
              numPages
                ? pageNumber >= numPages
                : false
            }
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