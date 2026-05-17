import { useMemo, useState } from 'react'
import { Search, X } from 'lucide-react'
import { SiAppstore, SiGoogleplay } from 'react-icons/si'
import { LINE_ICON } from '../constants/iconProps'

const SCHOOLS = [
  { id: 'konkuk', name: '건국대학교 글로컬캠퍼스', region: '충주' },
  { id: 'yonsei', name: '연세대학교', region: '서울' },
]

const APP_STORE_URL = 'https://apps.apple.com/'
const PLAY_STORE_URL = 'https://play.google.com/store'

function Home({ onSelectSchool }) {
  const [isSchoolOpen, setIsSchoolOpen] = useState(false)
  const [schoolQuery, setSchoolQuery] = useState('')

  const filteredSchools = useMemo(() => {
    const q = schoolQuery.trim().toLowerCase()
    if (!q) return SCHOOLS
    return SCHOOLS.filter(
      (school) =>
        school.name.toLowerCase().includes(q) ||
        school.region.toLowerCase().includes(q),
    )
  }, [schoolQuery])

  const openSchoolModal = () => {
    setSchoolQuery('')
    setIsSchoolOpen(true)
  }

  const closeSchoolModal = () => {
    setSchoolQuery('')
    setIsSchoolOpen(false)
  }

  const handlePickSchool = (schoolId) => {
    onSelectSchool(schoolId)
    closeSchoolModal()
  }

  return (
    <div className="flex min-h-screen w-full flex-col bg-[#654AEC] font-sans">
      <main className="relative z-10 mx-auto flex w-full max-w-6xl flex-1 flex-col items-center justify-between px-8 lg:flex-row lg:px-12">
        <div className="z-20 flex min-w-[100px] w-full max-w-xl flex-col items-start pt-20 lg:max-w-none lg:pt-0">
          <p className="mb-2 text-lg font-medium text-white/80 md:text-xl">
            학사 행정 AI 비서
          </p>

          <h1
            className="mb-6 text-6xl font-black tracking-tight text-white md:text-8xl"
            style={{ fontFamily: 'Arial Black, sans-serif' }}
          >
            Uni-Bot
          </h1>

          <h2 className="mb-10 break-keep text-3xl font-normal leading-snug text-white md:text-4xl">
            캠퍼스의 모든 정보,
            <br />
            찾지 말고 물어보세요!
          </h2>

          <div className="mb-10 w-full max-w-lg">
            <button
              type="button"
              onClick={openSchoolModal}
              className="group flex w-full items-center gap-3 rounded-full border border-white/25 bg-white px-4 py-3.5 text-left shadow-xl ring-1 ring-black/5 transition hover:border-white/40 hover:bg-white hover:shadow-2xl"
            >
              <Search
                size={22}
                className="shrink-0 text-slate-400 transition group-hover:text-[#654AEC]"
                {...LINE_ICON}
              />
              <span className="min-w-0 flex-1 select-none truncate text-base text-slate-400 transition group-hover:text-slate-500">
                학교 이름을 검색해 보세요...
              </span>
            </button>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <a
              href={APP_STORE_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-3 rounded-full border border-white/15 bg-white/15 px-5 py-2.5 font-medium text-white shadow-sm backdrop-blur-sm transition hover:bg-white/25"
            >
              <span
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[10px] bg-black text-white shadow-inner"
                aria-hidden
              >
                <SiAppstore className="size-[1.35rem]" title="" />
              </span>
              App Store
            </a>
            <a
              href={PLAY_STORE_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-3 rounded-full border border-white/15 bg-white/15 px-5 py-2.5 font-medium text-white shadow-sm backdrop-blur-sm transition hover:bg-white/25"
            >
              <span
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[10px] bg-white text-slate-900 shadow-inner"
                aria-hidden
              >
                <SiGoogleplay className="size-[1.35rem]" title="" />
              </span>
              Google Play
            </a>
          </div>
        </div>

        <div className="relative mt-12 flex w-full justify-center lg:mt-0 lg:w-1/2 lg:justify-end">
          <div className="pointer-events-none absolute left-1/2 top-1/2 h-96 w-96 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white/10 blur-3xl" />

          <img
            src="/bot1.png"
            alt="Uni-Bot Mascot"
            className="relative z-10 flex w-[500px] max-w-full flex-wrap object-contain drop-shadow-2xl"
          />
        </div>
      </main>

      <footer className="w-full bg-[#5A6268] py-4 text-center">
        <p className="text-center text-xs font-light text-white/70">
          CompanyName @ 202X. All rights reserved.
        </p>
      </footer>

      {isSchoolOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="school-modal-title"
        >
          <div className="relative w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
            <button
              type="button"
              onClick={closeSchoolModal}
              className="absolute right-4 top-4 rounded-lg p-1 text-slate-500 hover:bg-slate-100"
              aria-label="닫기"
            >
              <X size={20} {...LINE_ICON} />
            </button>
            <h3 id="school-modal-title" className="mb-2 text-lg font-bold text-slate-800">
              학교 선택
            </h3>
            <p className="mb-4 text-sm text-slate-600">
              이용할 학교를 선택하면 채팅 화면으로 이동합니다.
            </p>

            <div className="relative mb-4">
              <Search
                className="pointer-events-none absolute left-3 top-1/2 size-[18px] -translate-y-1/2 text-slate-400"
                aria-hidden
                {...LINE_ICON}
              />
              <input
                type="search"
                value={schoolQuery}
                onChange={(event) => setSchoolQuery(event.target.value)}
                placeholder="학교 이름으로 검색..."
                className="w-full rounded-xl border border-slate-200 bg-white py-2.5 pl-10 pr-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-[#654AEC] focus:ring-2 focus:ring-[#654AEC]/25"
                autoComplete="off"
                autoFocus
              />
            </div>

            {filteredSchools.length === 0 ? (
              <p className="py-8 text-center text-sm text-slate-500">
                검색 결과가 없습니다.
              </p>
            ) : (
              <ul className="max-h-[min(50vh,20rem)] space-y-2 overflow-y-auto pr-1">
                {filteredSchools.map((school) => (
                  <li key={school.id}>
                    <button
                      type="button"
                      onClick={() => handlePickSchool(school.id)}
                      className="flex w-full items-center justify-between rounded-xl border border-slate-200 px-4 py-3 text-left text-sm font-medium text-slate-800 transition hover:border-[#654AEC] hover:bg-violet-50"
                    >
                      <span>{school.name}</span>
                      <span className="text-xs text-slate-500">{school.region}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default Home
