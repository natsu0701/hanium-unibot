import { useMemo, useRef, useState } from 'react'

const ROLE_OPTIONS = [
  { value: 'super', label: '최고 관리자' },
  { value: 'school', label: '학교 관리자' },
  { value: 'staff', label: '일반 담당자' },
]

const INITIAL_ADMINS = [
  {
    id: 'a1',
    name: '김운영',
    affiliation: '시스템 총괄 · 유니봇 본사',
    email: 'ops@unibot.example',
    role: 'super',
    active: true,
    lastLogin: '2026-05-06 08:12',
  },
  {
    id: 'a2',
    name: '이학사',
    affiliation: '건국대 글로컬캠퍼스 · 학사지원팀',
    email: 'registrar.konkuk@example.com',
    role: 'school',
    active: true,
    lastLogin: '2026-05-05 17:40',
  },
  {
    id: 'a3',
    name: '박행정',
    affiliation: '연세대(미래) · 행정지원처',
    email: 'affairs.yonsei@example.com',
    role: 'school',
    active: true,
    lastLogin: '2026-05-06 06:58',
  },
  {
    id: 'a4',
    name: '최문서',
    affiliation: '건국대 글로컬 · 도서관/전자문서실',
    email: 'docs.konkuk@example.com',
    role: 'staff',
    active: false,
    lastLogin: '2026-04-28 11:03',
  },
  {
    id: 'a5',
    name: '정민지',
    affiliation: '연세대(미래) · IT지원실',
    email: 'support.yonsei@example.com',
    role: 'staff',
    active: true,
    lastLogin: '2026-05-04 09:21',
  },
]

function UserPermissions() {
  const [admins, setAdmins] = useState(INITIAL_ADMINS)
  const [query, setQuery] = useState('')
  const [inviteOpen, setInviteOpen] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState('staff')
  const [inviteSchool, setInviteSchool] = useState('건국대 글로컬캠퍼스')
  const [toast, setToast] = useState(null)
  const toastTimerRef = useRef(null)

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return admins
    return admins.filter(
      (a) =>
        a.name.toLowerCase().includes(q) ||
        a.email.toLowerCase().includes(q) ||
        a.affiliation.toLowerCase().includes(q),
    )
  }, [admins, query])

  const showToast = (msg) => {
    setToast(msg)
    if (toastTimerRef.current) window.clearTimeout(toastTimerRef.current)
    toastTimerRef.current = window.setTimeout(() => setToast(null), 2800)
  }

  const updateRole = (id, role) => {
    setAdmins((prev) => prev.map((a) => (a.id === id ? { ...a, role } : a)))
  }

  const toggleActive = (id) => {
    setAdmins((prev) => prev.map((a) => (a.id === id ? { ...a, active: !a.active } : a)))
  }

  const removeAdmin = (id) => {
    if (!window.confirm('이 관리자 계정을 목록에서 제거할까요?')) return
    setAdmins((prev) => prev.filter((a) => a.id !== id))
    showToast('계정이 제거되었습니다. (목업)')
  }

  const sendInvite = () => {
    const email = inviteEmail.trim()
    if (!email) {
      showToast('이메일을 입력해 주세요.')
      return
    }
    setInviteOpen(false)
    setInviteEmail('')
    showToast(`초대장을 ${email} 로 발송했습니다. (목업)`)
  }

  return (
    <div className="flex h-full min-h-0 w-full flex-col overflow-hidden bg-slate-100">
      <div className="shrink-0 border-b border-slate-200 bg-white px-8 py-6">
        <h1 className="text-lg font-bold text-slate-800">사용자 권한</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          멀티 테넌트 환경에서 관리자 계정·역할·활성 상태를 관리합니다.
        </p>
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-hidden px-8 py-6">
        <div className="flex shrink-0 flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="relative min-w-0 flex-1 sm:max-w-md">
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="이름 또는 이메일 검색…"
              className="w-full rounded-xl border border-slate-200 bg-white py-2.5 pl-4 pr-4 text-sm text-slate-800 shadow-sm outline-none transition focus:border-violet-300 focus:ring-2 focus:ring-violet-100"
            />
          </div>
          <button
            type="button"
            onClick={() => setInviteOpen(true)}
            className="inline-flex shrink-0 items-center justify-center rounded-xl bg-violet-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-violet-700"
          >
            새 관리자 초대
          </button>
        </div>

        {toast && (
          <p className="shrink-0 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm text-emerald-800">
            {toast}
          </p>
        )}

        <div className="min-h-0 flex-1 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="h-full overflow-auto">
            <table className="min-w-[900px] w-full border-collapse text-left text-sm">
              <thead className="sticky top-0 z-10 bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="border-b border-slate-200 px-4 py-3">이름</th>
                  <th className="border-b border-slate-200 px-4 py-3">소속</th>
                  <th className="border-b border-slate-200 px-4 py-3">이메일</th>
                  <th className="border-b border-slate-200 px-4 py-3">권한 등급</th>
                  <th className="border-b border-slate-200 px-4 py-3">계정 상태</th>
                  <th className="border-b border-slate-200 px-4 py-3">최근 로그인</th>
                  <th className="border-b border-slate-200 px-4 py-3 text-right">관리</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-800">
                {filtered.map((a) => (
                  <tr key={a.id} className="hover:bg-slate-50/80">
                    <td className="whitespace-nowrap px-4 py-3 font-medium">{a.name}</td>
                    <td className="max-w-[220px] px-4 py-3 text-slate-600">
                      <span className="line-clamp-2">{a.affiliation}</span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-violet-700">{a.email}</td>
                    <td className="px-4 py-3">
                      <select
                        value={a.role}
                        onChange={(e) => updateRole(a.id, e.target.value)}
                        className="rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-sm text-slate-800 outline-none focus:border-violet-300 focus:ring-2 focus:ring-violet-100"
                      >
                        {ROLE_OPTIONS.map((o) => (
                          <option key={o.value} value={o.value}>
                            {o.label}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        role="switch"
                        aria-checked={a.active}
                        onClick={() => toggleActive(a.id)}
                        className={`relative inline-flex h-7 w-12 shrink-0 cursor-pointer rounded-full border border-transparent transition focus:outline-none focus:ring-2 focus:ring-violet-400 focus:ring-offset-2 ${
                          a.active ? 'bg-emerald-500' : 'bg-slate-300'
                        }`}
                      >
                        <span
                          className={`pointer-events-none inline-block h-6 w-6 translate-y-px rounded-full bg-white shadow-sm ring-1 ring-slate-900/10 transition ${
                            a.active ? 'translate-x-5' : 'translate-x-0.5'
                          }`}
                        />
                      </button>
                      <span className="ml-2 text-xs text-slate-500">
                        {a.active ? '활성' : '비활성'}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-xs text-slate-500">{a.lastLogin}</td>
                    <td className="px-4 py-3 text-right">
                      <button
                        type="button"
                        onClick={() => removeAdmin(a.id)}
                        className="rounded-lg px-3 py-1 text-xs font-medium text-rose-600 transition hover:bg-rose-50"
                      >
                        삭제
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filtered.length === 0 && (
              <p className="p-10 text-center text-sm text-slate-500">검색 결과가 없습니다.</p>
            )}
          </div>
        </div>
      </div>

      {inviteOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
          <div
            role="dialog"
            aria-labelledby="invite-title"
            className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-6 shadow-lg"
          >
            <h2 id="invite-title" className="text-base font-bold text-slate-800">
              새 관리자 초대
            </h2>
            <p className="mt-1 text-xs text-slate-500">
              테넌트(학교)별 접근 범위는 권한 등급과 함께 적용됩니다.
            </p>
            <label className="mt-5 block text-xs font-medium text-slate-600">이메일</label>
            <input
              type="email"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              placeholder="name@univ.ac.kr"
              className="mt-1 w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm outline-none focus:border-violet-300 focus:ring-2 focus:ring-violet-100"
            />
            <label className="mt-4 block text-xs font-medium text-slate-600">권한 등급</label>
            <select
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value)}
              className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm outline-none focus:border-violet-300 focus:ring-2 focus:ring-violet-100"
            >
              {ROLE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
            <label className="mt-4 block text-xs font-medium text-slate-600">소속 학교 (테넌트)</label>
            <select
              value={inviteSchool}
              onChange={(e) => setInviteSchool(e.target.value)}
              className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm outline-none focus:border-violet-300 focus:ring-2 focus:ring-violet-100"
            >
              <option>건국대 글로컬캠퍼스</option>
              <option>연세대학교(미래)</option>
              <option>전체 플랫폼 (최고 관리자 전용)</option>
            </select>
            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setInviteOpen(false)}
                className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                취소
              </button>
              <button
                type="button"
                onClick={sendInvite}
                className="rounded-xl bg-violet-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-violet-700"
              >
                초대장 발송
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default UserPermissions
