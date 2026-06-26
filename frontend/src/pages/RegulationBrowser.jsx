import { useEffect, useMemo, useState } from 'react'
import { BookOpen, Building2, FileText, X } from 'lucide-react'
import { LINE_ICON } from '../constants/iconProps'
import { STUDENT_REGULATION_CATALOG } from '../data/regulationCatalog'

function RegulationBrowser({ open, onClose, currentUser, onSelectDocument }) {
  const initialSchoolId = useMemo(() => {
    const match = STUDENT_REGULATION_CATALOG.find((s) => s.schoolId === currentUser)
    return match?.schoolId ?? STUDENT_REGULATION_CATALOG[0]?.schoolId
  }, [currentUser])

  const [selectedSchoolId, setSelectedSchoolId] = useState(initialSchoolId)

  useEffect(() => {
    if (!open) return
    setSelectedSchoolId(initialSchoolId)
  }, [open, initialSchoolId])

  useEffect(() => {
    if (!open) return
    const onKey = (e) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  const selectedSchool = useMemo(
    () =>
      STUDENT_REGULATION_CATALOG.find((s) => s.schoolId === selectedSchoolId) ??
      STUDENT_REGULATION_CATALOG[0],
    [selectedSchoolId],
  )

  if (!open) return null

  const handlePickDoc = (doc) => {
    onSelectDocument({ file: doc.file, title: doc.title, schoolId: selectedSchool.schoolId })
    onClose()
  }

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/45 p-4 backdrop-blur-[2px]"
      role="dialog"
      aria-modal="true"
      aria-labelledby="reg-browser-title"
      onClick={onClose}
    >
      <div
        className="flex h-[min(640px,90vh)] w-full max-w-4xl overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <aside className="flex w-[38%] min-w-[200px] flex-col border-r border-slate-200 bg-slate-50">
          <div className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3">
            <p
              id="reg-browser-title"
              className="text-sm font-semibold text-slate-800"
            >
              학교 선택
            </p>
            <Building2 className="text-slate-400" size={18} {...LINE_ICON} aria-hidden />
          </div>
          <ul className="flex-1 overflow-y-auto p-2">
            {STUDENT_REGULATION_CATALOG.map((school) => {
              const active = school.schoolId === selectedSchoolId
              return (
                <li key={school.schoolId}>
                  <button
                    type="button"
                    onClick={() => setSelectedSchoolId(school.schoolId)}
                    className={`mb-1 flex w-full flex-col rounded-xl px-3 py-3 text-left text-sm transition ${
                      active
                        ? 'bg-violet-50 font-semibold text-violet-900 ring-1 ring-violet-200'
                        : 'text-slate-700 hover:bg-white'
                    }`}
                  >
                    <span className="truncate">{school.name}</span>
                    <span className="mt-0.5 text-xs font-normal text-slate-500">
                      규정 {school.documents.length}건
                    </span>
                  </button>
                </li>
              )
            })}
          </ul>
        </aside>

        <section className="flex min-w-0 flex-1 flex-col bg-white">
          <div className="flex items-start justify-between gap-3 border-b border-slate-200 px-5 py-4">
            <div className="min-w-0">
              <h2 className="text-base font-bold text-slate-800">{selectedSchool?.name}</h2>
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

          <div className="flex-1 overflow-y-auto p-4">
            <div className="mb-3 flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-slate-400">
              <BookOpen size={14} {...LINE_ICON} />
              규정·요람 목록
            </div>
            <ul className="space-y-2">
              {selectedSchool?.documents.map((doc) => (
                <li key={doc.id}>
                  <button
                    type="button"
                    onClick={() => handlePickDoc(doc)}
                    className="flex w-full items-center gap-3 rounded-xl border border-slate-200 bg-slate-50/80 px-4 py-3 text-left text-sm transition hover:border-violet-300 hover:bg-violet-50/60"
                  >
                    <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-white text-violet-600">
                      <FileText size={20} {...LINE_ICON} />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block font-medium text-slate-800">{doc.title}</span>
                      <span className="mt-0.5 block text-xs text-slate-500">{doc.category}</span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </section>
      </div>
    </div>
  )
}

export default RegulationBrowser
