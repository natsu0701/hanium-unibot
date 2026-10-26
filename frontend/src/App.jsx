import { useEffect, useRef, useState } from 'react'
import {
  FileText,
  GraduationCap,
  Search as SearchIcon,
} from 'lucide-react'

import AdminDashboard from './pages/AdminDashboard'
import ChatScreen from './components/ChatScreen'
import Home from './pages/Home'
import PdfViewer from './components/PdfViewer'
import RegulationBrowser from './pages/RegulationBrowser'
import { fetchSchools } from './api/schoolApi'
import { LINE_ICON } from './constants/iconProps'

const ROLE_OPTIONS = [
  { label: '학생', value: 'student' },
  { label: '관리자', value: 'admin' },
]

function App() {
  const [isChatStarted, setIsChatStarted] = useState(false)
  const [role, setRole] = useState('student')
  const [schools, setSchools] = useState([])
  const [schoolsLoading, setSchoolsLoading] = useState(true)
  const [schoolsError, setSchoolsError] = useState('')
  const [currentSchoolId, setCurrentSchoolId] = useState(null)
  const [regulationBrowserOpen, setRegulationBrowserOpen] = useState(false)
  const [studentPdfFile, setStudentPdfFile] = useState(null)
  const [studentPdfTitle, setStudentPdfTitle] = useState('')
  const [pdfPage, setPdfPage] = useState(1)
  const [pdfHighlightText, setPdfHighlightText] = useState('')

  const lastStudentSchoolIdRef = useRef(null)
  const pdfViewerRef = useRef(null)

  const isStudentView = role !== 'admin'
  const currentSchool = schools.find((school) => school.id === currentSchoolId)
  const currentSchoolName = currentSchool?.name ?? ''

  const loadSchools = async () => {
    setSchoolsLoading(true)
    setSchoolsError('')

    try {
      const list = await fetchSchools()
      setSchools(list)
    } catch (error) {
      setSchools([])
      setSchoolsError(
        error?.message || '학교 목록을 불러오지 못했습니다.',
      )
    } finally {
      setSchoolsLoading(false)
    }
  }

  useEffect(() => {
    loadSchools()
  }, [])

  useEffect(() => {
    if (!isStudentView) {
      return
    }

    setStudentPdfFile(null)
    setStudentPdfTitle('')
    setPdfPage(1)
    setPdfHighlightText('')
  }, [currentSchoolId, isStudentView])

  const handleSourceClick = (source) => {
    const parsedPage = Number(source?.page)

    if (
      !Number.isFinite(parsedPage) ||
      !Number.isInteger(parsedPage) ||
      parsedPage < 1
    ) {
      return
    }

    const evidence =
      typeof source?.evidence === 'string'
        ? source.evidence.trim()
        : ''

    setPdfPage(parsedPage)
    setPdfHighlightText(evidence)
  }

  const handleDocumentSelect = ({ file, title }) => {
    setStudentPdfFile(file)
    setStudentPdfTitle(title || '')
    setPdfPage(1)
    setPdfHighlightText('')
  }

  const handleSchoolSelect = (schoolId) => {
    lastStudentSchoolIdRef.current = schoolId
    setCurrentSchoolId(schoolId)
    setRole('student')
    setStudentPdfFile(null)
    setStudentPdfTitle('')
    setPdfPage(1)
    setPdfHighlightText('')
    setIsChatStarted(true)
  }

  const handleRoleChange = (event) => {
    const nextRole = event.target.value

    setRole(nextRole)
    setRegulationBrowserOpen(false)

    if (nextRole === 'admin') {
      setCurrentSchoolId(null)
      setStudentPdfFile(null)
      setStudentPdfTitle('')
      setPdfPage(1)
      setPdfHighlightText('')
      return
    }

    const restoredId =
      lastStudentSchoolIdRef.current ?? schools[0]?.id ?? null

    setCurrentSchoolId(restoredId)
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      {isChatStarted ? (
        <>
          <header className="relative flex h-14 w-full shrink-0 items-center justify-between gap-3 bg-[#8B5CF6] px-4 text-white">
            <div className="flex min-w-0 items-center gap-2">
              <GraduationCap
                className="hidden shrink-0 sm:block"
                size={22}
                {...LINE_ICON}
              />

              <p className="truncate font-bold">Uni-Bot</p>

              <span className="shrink-0 rounded-full bg-white px-2 py-0.5 text-xs font-semibold text-[#8B5CF6]">
                Self-RAG
              </span>
            </div>

            <div className="pointer-events-none absolute left-1/2 hidden -translate-x-1/2 px-4 lg:block">
              <span className="whitespace-nowrap text-xs font-medium">
                Self-RAG 기반 학사 규정 AI 검색 플랫폼
              </span>
            </div>

            <div className="flex shrink-0 items-center gap-2">
              {isStudentView && (
                <>
                  <button
                    type="button"
                    onClick={() => setRegulationBrowserOpen(true)}
                    title="학교별 규정 목록 보기"
                    className="inline-flex items-center gap-1.5 rounded-md bg-white/20 px-3 py-1.5 text-sm transition hover:bg-white/30"
                  >
                    <FileText size={16} {...LINE_ICON} />
                    <span className="hidden sm:inline">규정 목록</span>
                  </button>

                  <button
                    type="button"
                    title="PDF 뷰어에서 검색"
                    onClick={() => pdfViewerRef.current?.openSearch()}
                    className="inline-flex items-center gap-1.5 rounded-md bg-white/20 px-3 py-1.5 text-sm transition hover:bg-white/30"
                  >
                    <SearchIcon size={16} {...LINE_ICON} />
                    <span className="hidden sm:inline">검색</span>
                  </button>
                </>
              )}

              <select
                value={role}
                onChange={handleRoleChange}
                className="max-w-[10rem] rounded-md bg-white/20 py-1.5 pl-2 pr-8 text-xs text-white outline-none ring-1 ring-white/30 sm:max-w-none sm:pr-10 sm:text-sm"
              >
                {ROLE_OPTIONS.map((option) => (
                  <option
                    key={option.value}
                    value={option.value}
                    className="text-slate-800"
                  >
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
          </header>

          <main className="flex h-full min-h-0 w-full flex-1 overflow-hidden">
            {role === 'admin' ? (
              <AdminDashboard />
            ) : (
              <div className="flex h-full min-h-0 w-full flex-1 flex-row overflow-hidden">
                <div className="flex min-h-0 w-1/2 flex-col overflow-hidden border-r border-slate-200">
                  <ChatScreen
                    onSourceClick={handleSourceClick}
                    currentSchoolId={currentSchoolId}
                    currentSchoolName={currentSchoolName}
                  />
                </div>

                <div className="flex min-h-0 w-1/2 flex-col overflow-hidden">
                  <PdfViewer
                    ref={pdfViewerRef}
                    targetPage={pdfPage}
                    highlightText={pdfHighlightText}
                    currentUser={currentSchoolId}
                    activePdfFile={studentPdfFile}
                    activePdfTitle={studentPdfTitle}
                    onPdfFileChange={(file) => {
                      setStudentPdfFile(file)
                      setStudentPdfTitle('')
                    }}
                  />
                </div>
              </div>
            )}
          </main>

          <RegulationBrowser
            open={regulationBrowserOpen && isStudentView}
            currentSchoolId={currentSchoolId}
            currentSchoolName={currentSchoolName}
            onClose={() => setRegulationBrowserOpen(false)}
            onSelectDocument={handleDocumentSelect}
          />
        </>
      ) : (
        <Home
          onSelectSchool={handleSchoolSelect}
          schools={schools}
          schoolsLoading={schoolsLoading}
          schoolsError={schoolsError}
          onRetrySchools={loadSchools}
        />
      )}
    </div>
  )
}

export default App
