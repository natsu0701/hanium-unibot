import { useEffect, useState } from 'react'
import { BookOpen, FileText, X } from 'lucide-react'
import { LINE_ICON } from '../constants/iconProps'
import { fetchDocuments } from '../api/documentApi'

const EMPTY_MESSAGE =
  '등록된 규정 문서가 없습니다. 관리자 대시보드에서 PDF를 업로드해 주세요.'

const HANDBOOK_TITLE = '건국대학교 글로컬캠퍼스 학사 요람'

const DOCUMENT_DISPLAY_NAMES = {
  'guide.pdf': HANDBOOK_TITLE,
  'guide2.pdf': '연세대학교 요람',
}

const DEFAULT_YORAM = {
  id: 'local-guide',
  file: '/guide.pdf',
  filename: 'guide.pdf',
  title: HANDBOOK_TITLE,
}

function getFilenameBase(filename) {
  const raw = String(filename || '').trim()
  return raw.split(/[/\\]/).pop() || raw
}

function getDocumentDisplayName(filename) {
  const base = getFilenameBase(filename)

  if (DOCUMENT_DISPLAY_NAMES[base]) {
    return DOCUMENT_DISPLAY_NAMES[base]
  }

  const mappedByLower = DOCUMENT_DISPLAY_NAMES[base.toLowerCase()]
  if (mappedByLower) {
    return mappedByLower
  }

  return base.replace(/\.[^/.]+$/, '') || base || '문서'
}

function RegulationBrowser({
  open,
  onClose,
  currentSchoolId = null,
  currentSchoolName = '',
  currentPdfFile = '/guide.pdf',
  currentPdfTitle = HANDBOOK_TITLE,
  onSelectDocument,
}) {
  const [documents, setDocuments] = useState([])
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (!open) {
      return undefined
    }

    const onKey = (event) => {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  useEffect(() => {
    let cancelled = false

    const loadDocuments = async () => {
      setIsLoading(true)

      try {
        const items = await fetchDocuments(currentSchoolId)

        if (!cancelled) {
          setDocuments(items)
        }
      } catch {
        if (!cancelled) {
          setDocuments([])
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }

    loadDocuments()

    return () => {
      cancelled = true
    }
  }, [currentSchoolId])

  if (!open) {
    return null
  }

  const handlePickDoc = (doc) => {
    onSelectDocument?.({
      id: doc.id,
      title: getDocumentDisplayName(doc.filename),
      file: doc.download_url,
    })
    onClose()
  }

  const handlePickDefault = () => {
    onSelectDocument?.({
      ...DEFAULT_YORAM,
      file: currentPdfFile || DEFAULT_YORAM.file,
      title: currentPdfTitle || DEFAULT_YORAM.title,
    })
    onClose()
  }

  const schoolLabel = currentSchoolName || '선택된 학교'
  const openPdf = {
    id: 'current-open-pdf',
    filename: getFilenameBase(currentPdfFile) || DEFAULT_YORAM.filename,
    download_url: currentPdfFile || DEFAULT_YORAM.file,
    displayName: currentPdfTitle || HANDBOOK_TITLE,
  }
  const listedDocuments = [
    openPdf,
    ...documents.filter(
      (doc) =>
        getFilenameBase(doc.filename) !== getFilenameBase(openPdf.filename),
    ),
  ]
  const isEmpty = !isLoading && listedDocuments.length === 0

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/45 p-4 backdrop-blur-[2px]"
      role="dialog"
      aria-modal="true"
      aria-labelledby="reg-browser-title"
      onClick={onClose}
    >
      <div
        className="flex h-[min(640px,90vh)] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3 border-b border-slate-200 px-5 py-4">
          <div className="min-w-0">
            <h2
              id="reg-browser-title"
              className="text-base font-bold text-slate-800"
            >
              {schoolLabel}
            </h2>
            <p className="mt-1 text-xs text-slate-500">
              열람할 문서를 선택하면 우측 PDF 뷰어에 표시됩니다.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 rounded-lg p-2 text-slate-500 transition hover:bg-slate-100"
            aria-label="닫기"
          >
            <X size={20} {...LINE_ICON} />
          </button>
        </div>

        <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto p-4">
            <div className="mb-3 flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-slate-400">
              <BookOpen size={14} {...LINE_ICON} />
              규정·요람 목록
            </div>

            {isEmpty ? (
              <div className="flex min-h-[12rem] items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50 px-6 py-10">
                <p className="max-w-sm text-center text-sm leading-relaxed text-slate-500">
                  {EMPTY_MESSAGE}
                </p>
              </div>
            ) : (
              <ul className="space-y-2">
                {listedDocuments.map((doc, index) => {
                  const isCurrent = index === 0

                  return (
                    <li key={doc.id}>
                      <button
                        type="button"
                        onClick={() =>
                          isCurrent
                            ? handlePickDefault()
                            : handlePickDoc(doc)
                        }
                        className={`flex w-full items-center gap-3 rounded-xl border px-4 py-3 text-left text-sm transition ${
                          isCurrent
                            ? 'border-violet-300 bg-violet-50/70'
                            : 'border-slate-200 bg-slate-50/80 hover:border-violet-300 hover:bg-violet-50/60'
                        }`}
                      >
                        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-white text-violet-600">
                          <FileText size={20} {...LINE_ICON} />
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="block truncate font-medium text-slate-800">
                            {doc.displayName ||
                              getDocumentDisplayName(doc.filename)}
                          </span>
                          <span className="mt-0.5 block text-xs text-slate-500">
                            {isCurrent ? '지금 열려 있는 PDF' : 'PDF 문서'}
                          </span>
                        </span>
                      </button>
                    </li>
                  )
                })}
              </ul>
            )}
          </div>

          <div className="border-t border-slate-200 bg-slate-50 px-4 py-3">
            <button
              type="button"
              onClick={handlePickDefault}
              className="flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-600 transition hover:border-slate-300 hover:bg-slate-100"
            >
              <FileText size={16} {...LINE_ICON} />
              기본 요람 뷰어
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default RegulationBrowser
