import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import {
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Columns2,
  Download,
  Printer,
  Search,
  Square,
  X,
  ZoomIn,
  ZoomOut,
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
    id: 'konkuk',
    label: '건국대학교 글로컬캠퍼스',
    file: '/guide.pdf',
  },
]

const MAX_SEARCH_HITS = 200
const FIT_PADDING_X = 24
const FIT_PADDING_Y = 24
const FIT_GAP = 12
const FIT_SHRINK = 0.92
const MIN_ZOOM = 0.5
const MAX_ZOOM = 3
const ZOOM_STEP = 0.1

function normalizeText(value = '') {
  return String(value)
    .replace(/\s+/g, '')
    .replace(/[.,:;·ㆍ•()[\]{}"'“”‘’\-_/]/g, '')
    .trim()
}

function itemString(item) {
  return item && typeof item.str === 'string' ? item.str : ''
}

const PdfViewer = forwardRef(function PdfViewer(
  {
    targetPage = 1,
    highlightText = '',
    currentUser = 'konkuk',
    activePdfFile = null,
    activePdfTitle = '',
    onPdfFileChange,
  },
  ref,
) {
  const selectedSchool = useMemo(() => {
    if (activePdfFile) {
      const matchedSchool = SCHOOL_OPTIONS.find(
        (school) => school.file === activePdfFile,
      )

      if (matchedSchool) {
        return matchedSchool
      }
    }

    return (
      SCHOOL_OPTIONS.find((school) => school.id === currentUser) ??
      SCHOOL_OPTIONS[0]
    )
  }, [currentUser, activePdfFile])

  const fileUrl = activePdfFile ?? selectedSchool?.file
  const isRemotePdf =
    typeof fileUrl === 'string' && /^https?:\/\//i.test(fileUrl)
  const headerTitle =
    activePdfTitle ||
    selectedSchool?.label ||
    '학사 요람'
  const pdfSource = isRemotePdf
    ? { url: fileUrl, withCredentials: false }
    : fileUrl

  const [numPages, setNumPages] = useState(null)
  const [pageNumber, setPageNumber] = useState(1)
  const [pageInput, setPageInput] = useState('1')
  const [containerSize, setContainerSize] = useState({ width: 0, height: 0 })
  const [pageSize, setPageSize] = useState({ width: 595, height: 842 })
  const [zoom, setZoom] = useState(1)
  const [viewMode, setViewMode] = useState('single')
  const [searchQuery, setSearchQuery] = useState('')
  const [searchDraft, setSearchDraft] = useState('')
  const [matches, setMatches] = useState([])
  const [activeMatch, setActiveMatch] = useState(0)
  const [searchStatus, setSearchStatus] = useState('')
  const [isSearching, setIsSearching] = useState(false)

  const containerRef = useRef(null)
  const pageRef = useRef(null)
  const pdfDocRef = useRef(null)
  const searchInputRef = useRef(null)
  const searchRequestRef = useRef(0)

  useImperativeHandle(ref, () => ({
    openSearch() {
      searchInputRef.current?.focus()
      searchInputRef.current?.select()
    },
  }))

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
    setSearchQuery('')
    setSearchDraft('')
    setMatches([])
    setActiveMatch(0)
    setSearchStatus('')
    pdfDocRef.current = null
  }, [fileUrl])

  useLayoutEffect(() => {
    const container = containerRef.current

    if (!container) {
      return undefined
    }

    const updateContainerSize = () => {
      setContainerSize({
        width: container.clientWidth,
        height: container.clientHeight,
      })
    }

    updateContainerSize()

    const resizeObserver = new ResizeObserver(
      updateContainerSize,
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
      span.classList.remove('pdf-evidence-highlight')
      span.style.backgroundColor = ''
      span.style.borderRadius = ''
      span.style.boxShadow = ''
      span.style.mixBlendMode = ''
    })
  }

  const applyHighlightStyle = (span) => {
    span.classList.add('pdf-evidence-highlight')
  }

  const highlightNormalizedNeedle = (needle) => {
    const pageElement = pageRef.current

    if (!pageElement || !needle) {
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

    let firstHighlightedSpan = null
    let from = 0

    while (from < fullPageText.length) {
      const matchStart = fullPageText.indexOf(needle, from)

      if (matchStart === -1) {
        break
      }

      const matchEnd = matchStart + needle.length

      spanRanges.forEach(({ span, start, end }) => {
        const overlaps = end > matchStart && start < matchEnd

        if (!overlaps) {
          return
        }

        applyHighlightStyle(span)

        if (!firstHighlightedSpan) {
          firstHighlightedSpan = span
        }
      })

      from = matchEnd
    }

    firstHighlightedSpan?.scrollIntoView({
      behavior: 'smooth',
      block: 'center',
    })
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

  const handleTextLayerReady = () => {
    const needle = normalizeText(searchQuery)

    if (needle) {
      highlightNormalizedNeedle(needle)
      return
    }

    highlightEvidence()
  }

  const runSearch = async (rawQuery) => {
    const pdf = pdfDocRef.current
    const trimmed = rawQuery.trim()
    const needle = normalizeText(trimmed)

    setSearchQuery(trimmed)

    if (!pdf || !needle) {
      setMatches([])
      setActiveMatch(0)
      setSearchStatus(trimmed ? '검색어를 입력해 주세요.' : '')
      clearHighlights()
      return
    }

    const requestId = searchRequestRef.current + 1
    searchRequestRef.current = requestId
    setIsSearching(true)
    setSearchStatus('검색 중...')

    try {
      const found = []

      for (let page = 1; page <= pdf.numPages; page += 1) {
        if (searchRequestRef.current !== requestId) {
          return
        }

        const pdfPage = await pdf.getPage(page)
        const content = await pdfPage.getTextContent()
        const haystack = normalizeText(
          content.items.map(itemString).join(''),
        )

        let from = 0

        while (from < haystack.length && found.length < MAX_SEARCH_HITS) {
          const index = haystack.indexOf(needle, from)

          if (index === -1) {
            break
          }

          found.push({ page, index })
          from = index + Math.max(needle.length, 1)
        }

        if (found.length >= MAX_SEARCH_HITS) {
          break
        }
      }

      if (searchRequestRef.current !== requestId) {
        return
      }

      setMatches(found)
      setActiveMatch(0)

      if (found.length === 0) {
        setSearchStatus('검색 결과가 없습니다.')
        return
      }

      setSearchStatus('')
      setPageNumber(found[0].page)
    } catch {
      if (searchRequestRef.current !== requestId) {
        return
      }

      setMatches([])
      setSearchStatus('검색에 실패했습니다.')
    } finally {
      if (searchRequestRef.current === requestId) {
        setIsSearching(false)
      }
    }
  }

  const goToMatch = (nextIndex) => {
    if (matches.length === 0) {
      return
    }

    const wrapped =
      ((nextIndex % matches.length) + matches.length) % matches.length

    setActiveMatch(wrapped)
    setPageNumber(matches[wrapped].page)
  }

  const clearSearch = () => {
    searchRequestRef.current += 1
    setSearchDraft('')
    setSearchQuery('')
    setMatches([])
    setActiveMatch(0)
    setSearchStatus('')
    setIsSearching(false)
    clearHighlights()
    highlightEvidence()
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

  const handleLoadSuccess = (pdf) => {
    pdfDocRef.current = pdf
    setNumPages(pdf.numPages)

    setPageNumber((previousPage) =>
      Math.min(
        Math.max(previousPage, 1),
        pdf.numPages,
      ),
    )
  }

  useEffect(() => {
    let cancelled = false
    const pdf = pdfDocRef.current

    if (!pdf || !pageNumber) {
      return undefined
    }

    pdf.getPage(pageNumber).then((page) => {
      if (cancelled) {
        return
      }

      const viewport = page.getViewport({ scale: 1 })
      setPageSize({ width: viewport.width, height: viewport.height })
    })

    return () => {
      cancelled = true
    }
  }, [pageNumber, numPages, fileUrl])

  const showSecondPage =
    viewMode === 'two' &&
    Boolean(numPages) &&
    pageNumber < numPages

  const pageWidth = useMemo(() => {
    const { width: containerWidth, height: containerHeight } = containerSize

    if (!containerWidth || !containerHeight || !pageSize.width) {
      return undefined
    }

    const pageCount = showSecondPage ? 2 : 1
    const gap = pageCount === 2 ? FIT_GAP : 0
    const availableWidth =
      (containerWidth - FIT_PADDING_X - gap) / pageCount
    const availableHeight = containerHeight - FIT_PADDING_Y
    const fit = Math.min(
      availableWidth / pageSize.width,
      availableHeight / pageSize.height,
    )

    return Math.max(120, pageSize.width * fit * FIT_SHRINK * zoom)
  }, [containerSize, pageSize, showSecondPage, zoom])

  const pageStep = viewMode === 'two' ? 2 : 1

  const goPrevPage = () => {
    clearHighlights()

    setPageNumber((previousPage) =>
      Math.max(previousPage - pageStep, 1),
    )
  }

  const goNextPage = () => {
    clearHighlights()

    setPageNumber((previousPage) =>
      numPages
        ? Math.min(previousPage + pageStep, numPages)
        : previousPage + pageStep,
    )
  }

  const zoomOut = () => {
    setZoom((current) =>
      Math.max(MIN_ZOOM, Math.round((current - ZOOM_STEP) * 10) / 10),
    )
  }

  const zoomIn = () => {
    setZoom((current) =>
      Math.min(MAX_ZOOM, Math.round((current + ZOOM_STEP) * 10) / 10),
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

  const handleSearchSubmit = (event) => {
    event.preventDefault()
    runSearch(searchDraft)
  }

  const matchLabel =
    matches.length > 0
      ? `${activeMatch + 1}/${matches.length}`
      : ''

  return (
    <aside className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-slate-50">
      <header className="sticky top-0 z-20 shrink-0 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="flex items-center gap-3 px-4 py-3">
          <div className="min-w-0 flex-1">
            <div className="relative min-w-0 max-w-xs rounded-lg border border-slate-200 bg-white px-3 py-2">
              <p className={`truncate text-sm font-medium text-slate-700 ${isRemotePdf ? '' : 'pr-8'}`}>
                {headerTitle}
              </p>

              {isRemotePdf ? null : (
                <>
                  <ChevronDown
                    className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-slate-400"
                    aria-hidden
                    {...LINE_ICON}
                  />

                  <select
                    value={selectedSchool?.file ?? ''}
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
                </>
              )}
            </div>
          </div>

          <div className="flex min-w-0 shrink-0 items-center gap-2">
            <form
              onSubmit={handleSearchSubmit}
              className="flex min-w-0 items-center gap-1.5"
            >
              <div className="relative min-w-0">
                <Search
                  size={16}
                  {...LINE_ICON}
                  className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400"
                  aria-hidden
                />
                <input
                  ref={searchInputRef}
                  type="text"
                  autoComplete="off"
                  value={searchDraft}
                  onChange={(event) => setSearchDraft(event.target.value)}
                  placeholder="PDF 검색"
                  aria-label="PDF 본문 검색"
                  className="h-8 w-[9.5rem] rounded-md border border-slate-200 bg-white py-1.5 pl-8 pr-8 text-sm text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-slate-400 focus:ring-2 focus:ring-slate-200 sm:w-44"
                />
                {searchDraft ? (
                  <button
                    type="button"
                    onClick={clearSearch}
                    className="absolute right-1.5 top-1/2 inline-flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded-md text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
                    aria-label="검색어 지우기"
                  >
                    <X size={14} {...LINE_ICON} />
                  </button>
                ) : null}
              </div>

              {matches.length > 0 ? (
                <>
                  <span className="hidden whitespace-nowrap text-xs font-medium text-slate-500 sm:inline">
                    {matchLabel}
                  </span>
                  <button
                    type="button"
                    onClick={() => goToMatch(activeMatch - 1)}
                    className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-slate-200 text-slate-600 transition hover:bg-slate-100"
                    aria-label="이전 검색 결과"
                  >
                    <ChevronLeft size={16} {...LINE_ICON} />
                  </button>
                  <button
                    type="button"
                    onClick={() => goToMatch(activeMatch + 1)}
                    className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-slate-200 text-slate-600 transition hover:bg-slate-100"
                    aria-label="다음 검색 결과"
                  >
                    <ChevronRight size={16} {...LINE_ICON} />
                  </button>
                </>
              ) : null}
            </form>

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

        {searchStatus ? (
          <p className="px-4 pb-2 text-xs text-slate-500" role="status">
            {isSearching ? '검색 중...' : searchStatus}
          </p>
        ) : null}
      </header>

      <section
        ref={containerRef}
        className="flex-1 overflow-auto bg-slate-200/60"
      >
        <div className="flex min-h-full min-w-full items-center justify-center p-3">
          <Document
            file={pdfSource}
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
            <div
              ref={pageRef}
              className="flex items-start justify-center gap-3"
            >
              <Page
                key={`${pageNumber}-${highlightText}-${searchQuery}`}
                pageNumber={pageNumber}
                width={pageWidth}
                className="overflow-hidden rounded-lg shadow-lg"
                renderAnnotationLayer
                renderTextLayer
                onRenderTextLayerSuccess={handleTextLayerReady}
              />
              {showSecondPage ? (
                <Page
                  key={`${pageNumber + 1}-${highlightText}-${searchQuery}-b`}
                  pageNumber={pageNumber + 1}
                  width={pageWidth}
                  className="overflow-hidden rounded-lg shadow-lg"
                  renderAnnotationLayer
                  renderTextLayer
                  onRenderTextLayerSuccess={handleTextLayerReady}
                />
              ) : null}
            </div>
          </Document>
        </div>
      </section>

      <footer className="shrink-0 border-t border-slate-200 bg-white px-3 py-2.5">
        <div className="flex w-full items-center gap-2">
          <div className="w-[4.5rem] shrink-0" aria-hidden />
          <div className="flex min-w-0 flex-1 items-center justify-center gap-2">
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
              <button
                type="button"
                onClick={zoomOut}
                disabled={zoom <= MIN_ZOOM}
                className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-slate-300 text-slate-600 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
                aria-label="축소"
                title="축소"
              >
                <ZoomOut size={16} {...LINE_ICON} />
              </button>
              <button
                type="button"
                onClick={zoomIn}
                disabled={zoom >= MAX_ZOOM}
                className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-slate-300 text-slate-600 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
                aria-label="확대"
                title="확대"
              >
                <ZoomIn size={16} {...LINE_ICON} />
              </button>
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

          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setViewMode('single')}
              aria-pressed={viewMode === 'single'}
              className={`inline-flex h-8 w-8 items-center justify-center rounded-md border transition ${
                viewMode === 'single'
                  ? 'border-violet-300 bg-violet-50 text-violet-700'
                  : 'border-slate-300 text-slate-600 hover:bg-slate-100'
              }`}
              aria-label="한 페이지 보기"
              title="한 페이지 보기"
            >
              <Square size={15} {...LINE_ICON} />
            </button>
            <button
              type="button"
              onClick={() => setViewMode('two')}
              aria-pressed={viewMode === 'two'}
              className={`inline-flex h-8 w-8 items-center justify-center rounded-md border transition ${
                viewMode === 'two'
                  ? 'border-violet-300 bg-violet-50 text-violet-700'
                  : 'border-slate-300 text-slate-600 hover:bg-slate-100'
              }`}
              aria-label="두 페이지 보기"
              title="두 페이지 보기"
            >
              <Columns2 size={15} {...LINE_ICON} />
            </button>
          </div>
        </div>
      </footer>
    </aside>
  )
})

export default PdfViewer
