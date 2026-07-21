import { useEffect, useState } from 'react'
import {
  FileText,
  GraduationCap,
  Lightbulb,
  Search as SearchIcon,
} from 'lucide-react'
import AdminDashboard from './pages/AdminDashboard'
import ChatScreen from './components/ChatScreen'
import Home from './pages/Home'
import PdfViewer from './components/PdfViewer'
import RegulationBrowser from './pages/RegulationBrowser'
import { LINE_ICON } from './constants/iconProps'

const USERS = [
  { label: '건국대 학생 (konkuk)', value: 'konkuk' },
  { label: '연세대 학생 (yonsei)', value: 'yonsei' },
  { label: '관리자 (admin)', value: 'admin' },
]

function App() {
  const [isChatStarted, setIsChatStarted] = useState(false)
  const [currentUser, setCurrentUser] = useState('konkuk')
  const [regulationBrowserOpen, setRegulationBrowserOpen] = useState(false)
  const [studentPdfFile, setStudentPdfFile] = useState(null)
  const [pdfPage, setPdfPage] = useState(1)
<<<<<<< HEAD
  // RAG 모드 표시용 토글. 아직 Self-RAG가 완전히 연동되지 않아 기본값은 'v1'.
  // 현재는 배지 텍스트만 전환되는 껍데기 상태입니다(실제 동작 미연동).
  const [ragMode, setRagMode] = useState('v1')
=======
  const [pdfHighlightText, setPdfHighlightText] = useState('')
>>>>>>> d2c565d (feat: RAG 검색 및 답변 기능 구현)

  const isStudentView = currentUser !== 'admin'

  useEffect(() => {
    if (currentUser !== 'konkuk' && currentUser !== 'yonsei') {
      return
    }

    setStudentPdfFile(null)
    setPdfPage(1)
    setPdfHighlightText('')
  }, [currentUser])

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

  const handleDocumentSelect = ({ file }) => {
    setStudentPdfFile(file)
    setPdfPage(1)
    setPdfHighlightText('')
  }

  const handleSchoolSelect = (schoolId) => {
    setCurrentUser(schoolId)
    setStudentPdfFile(null)
    setPdfPage(1)
    setPdfHighlightText('')
    setIsChatStarted(true)
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
<<<<<<< HEAD
              <button
                type="button"
                onClick={() => setRagMode((mode) => (mode === 'v1' ? 'self' : 'v1'))}
                title="RAG 모드 전환 (표시용 - 실제 동작 미연동)"
                aria-label={`현재 RAG 모드: ${ragMode === 'v1' ? 'RAG v1' : 'Self-RAG'}. 클릭하여 전환`}
                className="flex shrink-0 items-center gap-1.5 rounded-full bg-white px-2 py-0.5 text-xs font-semibold text-[#8B5CF6] transition hover:bg-white/90"
              >
                <span
                  className={`h-1.5 w-1.5 rounded-full transition-colors ${
                    ragMode === 'self' ? 'bg-emerald-500' : 'bg-slate-300'
                  }`}
                  aria-hidden
                />
                {ragMode === 'v1' ? 'RAG v1' : 'Self-RAG'}
              </button>
=======

              <span className="shrink-0 rounded-full bg-white px-2 py-0.5 text-xs font-semibold text-[#8B5CF6]">
                Self-RAG
              </span>
>>>>>>> d2c565d (feat: RAG 검색 및 답변 기능 구현)
            </div>

            <div className="pointer-events-none absolute left-1/2 hidden -translate-x-1/2 px-4 lg:block">
              <span className="flex items-center gap-2 whitespace-nowrap rounded-full bg-white/15 px-4 py-1.5 text-xs font-medium backdrop-blur-sm">
                <Lightbulb
                  size={14}
                  {...LINE_ICON}
                  className="shrink-0 text-amber-200"
                  aria-hidden
                />

                <span>Self-RAG 기반 학사 규정 AI 검색 플랫폼</span>
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
                    className="inline-flex items-center gap-1.5 rounded-md bg-white/20 px-3 py-1.5 text-sm transition hover:bg-white/30"
                  >
                    <SearchIcon size={16} {...LINE_ICON} />
                    <span className="hidden sm:inline">검색</span>
                  </button>
                </>
              )}

              <select
                value={currentUser}
                onChange={(event) => setCurrentUser(event.target.value)}
                className="max-w-[10rem] rounded-md bg-white/20 py-1.5 pl-2 pr-8 text-xs text-white outline-none ring-1 ring-white/30 sm:max-w-none sm:pr-10 sm:text-sm"
              >
                {USERS.map((user) => (
                  <option
                    key={user.value}
                    value={user.value}
                    className="text-slate-800"
                  >
                    {user.label}
                  </option>
                ))}
              </select>
            </div>
          </header>

          <main className="flex h-full min-h-0 w-full flex-1 overflow-hidden">
            {currentUser === 'admin' ? (
              <AdminDashboard />
            ) : (
              <div className="flex h-full min-h-0 w-full flex-1 flex-row overflow-hidden">
                <div className="flex min-h-0 w-1/2 flex-col overflow-hidden border-r border-slate-200">
                  <ChatScreen onSourceClick={handleSourceClick} />
                </div>

                <div className="flex min-h-0 w-1/2 flex-col overflow-hidden">
                  <PdfViewer
                    targetPage={pdfPage}
                    highlightText={pdfHighlightText}
                    currentUser={currentUser}
                    activePdfFile={studentPdfFile}
                    onPdfFileChange={setStudentPdfFile}
                  />
                </div>
              </div>
            )}
          </main>

          <RegulationBrowser
            open={regulationBrowserOpen && isStudentView}
            currentUser={currentUser}
            onClose={() => setRegulationBrowserOpen(false)}
            onSelectDocument={handleDocumentSelect}
          />
        </>
      ) : (
        <Home onSelectSchool={handleSchoolSelect} />
      )}
    </div>
  )
}

export default App