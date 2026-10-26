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
  Download,
  Printer,
  Search,
  X,
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
  const [containerWidth, setContainerWidth] = useState(0)
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
            <div className="relative min-w-0 max-w-xs rounded-md-sm border border-slate-200 bg-white px-3 py-2">
              <p className={`m3-title truncate text-sm font-medium text-slate-700 ${isRemotePdf ? '' : 'pr-8'}`}>
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
                  className="h-10 w-[9.5rem] rounded-md-xl border border-slate-200 bg-white py-1.5 pl-8 pr-8 text-sm text-slate-800 outline-none transition duration-md-short ease-md-standard placeholder:text-slate-400 focus:border-slate-400 focus:ring-2 focus:ring-slate-200 sm:w-44"
                />
                {searchDraft ? (
                  <button
                    type="button"
                    onClick={clearSearch}
                    className="absolute right-1.5 top-1/2 inline-flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded-full text-slate-400 transition duration-md-short ease-md-standard hover:bg-slate-100 hover:text-slate-600"
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
                    className="inline-flex h-10 w-8 items-center justify-center rounded-md-sm border border-slate-200 text-slate-600 transition duration-md-short ease-md-standard hover:bg-slate-100"
                    aria-label="이전 검색 결과"
                  >
                    <ChevronLeft size={16} {...LINE_ICON} />
                  </button>
                  <button
                    type="button"
                    onClick={() => goToMatch(activeMatch + 1)}
                    className="inline-flex h-10 w-8 items-center justify-center rounded-md-sm border border-slate-200 text-slate-600 transition duration-md-short ease-md-standard hover:bg-slate-100"
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
              className="inline-flex h-10 w-10 items-center justify-center rounded-md-sm border border-slate-200 text-slate-600 transition duration-md-short ease-md-standard hover:bg-slate-100"
              aria-label="다운로드"
            >
              <Download size={16} {...LINE_ICON} />
            </a>

            <button
              type="button"
              onClick={handlePrint}
              className="inline-flex h-10 w-10 items-center justify-center rounded-md-sm border border-slate-200 text-slate-600 transition duration-md-short ease-md-standard hover:bg-slate-100"
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
        className="flex-1 overflow-auto bg-slate-200/60 px-4 py-6"
      >
        <div className="mx-auto flex w-full max-w-3xl justify-center">
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
            <div ref={pageRef}>
              <Page
                key={`${pageNumber}-${highlightText}-${searchQuery}`}
                pageNumber={pageNumber}
                width={
                  containerWidth
                    ? Math.min(containerWidth - 32, 800)
                    : undefined
                }
                className="overflow-hidden rounded-md-sm shadow-md-2"
                renderAnnotationLayer
                renderTextLayer
                onRenderTextLayerSuccess={handleTextLayerReady}
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
            className="inline-flex min-h-10 items-center gap-1 rounded-md-sm border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 transition duration-md-short ease-md-standard hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
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
              className="h-10 w-14 rounded-md-xs border border-slate-300 px-2 py-1 text-center text-sm outline-none focus:border-[#654AEC] focus:ring-2 focus:ring-[#654AEC]/20"
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
            className="inline-flex min-h-10 items-center gap-1 rounded-md-sm border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 transition duration-md-short ease-md-standard hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
          >
            다음
            <ChevronRight size={16} {...LINE_ICON} />
          </button>
        </div>
      </footer>
    </aside>
  )
})

export default PdfViewer
