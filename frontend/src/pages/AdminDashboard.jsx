import {
  BadgeCheck,
  BookOpen,
  Brain,
  FileText,
  LayoutDashboard,
  Receipt,
  ScrollText,
  Settings,
  Users,
} from 'lucide-react'
import { useState } from 'react'
import { LINE_ICON } from '../constants/iconProps'
import DocumentManagement from './DocumentManagement'
import KnowledgeBase from './KnowledgeBase'
import PromptPolicy from './PromptPolicy'
import ReliabilityAnalysis from './ReliabilityAnalysis'
import SystemSettings from './SystemSettings'
import UserPermissions from './UserPermissions'
import ValidationLogs from './ValidationLogs'

function DashboardHome() {
  return (
    <div className="flex h-full min-h-0 w-full flex-col overflow-hidden bg-slate-100">
      <div className="shrink-0 border-b border-slate-200 bg-white px-8 py-6">
        <h1 className="text-xl font-bold text-slate-800">대시보드</h1>
        <p className="mt-1 text-sm text-slate-500">
          학사 규정 RAG 파이프라인 상태를 한눈에 확인합니다.
        </p>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-8 py-6">
        <div className="grid grid-cols-4 gap-4">
          <article className="rounded-xl bg-white p-5 shadow-sm">
            <p className="text-sm text-slate-500">등록된 문서</p>
            <p className="mt-2 text-3xl font-bold text-slate-800">147</p>
          </article>
          <article className="rounded-xl bg-white p-5 shadow-sm">
            <p className="text-sm text-slate-500">임베딩된 청크</p>
            <p className="mt-2 text-3xl font-bold text-slate-800">12,847</p>
          </article>
          <article className="rounded-xl bg-white p-5 shadow-sm">
            <p className="text-sm text-slate-500">이번 달 질문</p>
            <p className="mt-2 text-3xl font-bold text-slate-800">3,421</p>
          </article>
          <article className="rounded-xl bg-white p-5 shadow-sm">
            <p className="text-sm text-slate-500">Self-RAG 검증 통과율</p>
            <p className="mt-2 text-3xl font-bold text-emerald-600">94.2%</p>
          </article>
        </div>

        <div className="mt-6 grid grid-cols-2 gap-4">
          <div className="space-y-4">
            <section className="rounded-xl border-2 border-dashed border-slate-300 bg-white p-8 text-center shadow-sm">
              <p className="text-sm font-medium text-slate-700">문서 업로드 (Drag & Drop)</p>
              <p className="mt-2 text-xs text-slate-400">PDF 파일을 드래그해 업로드하세요.</p>
            </section>

            <section className="rounded-xl bg-white p-5 shadow-sm">
              <h3 className="mb-4 text-sm font-semibold text-slate-700">처리 진행 현황</h3>
              <div className="space-y-4">
                <div>
                  <p className="mb-1 text-sm text-slate-600">Upstage OCR 처리중...</p>
                  <div className="h-2 rounded-full bg-slate-100">
                    <div className="h-2 w-2/3 rounded-full bg-violet-500" />
                  </div>
                </div>
                <div>
                  <p className="mb-1 text-sm text-slate-600">Vector DB 임베딩 완료</p>
                  <div className="h-2 rounded-full bg-slate-100">
                    <div className="h-2 w-full rounded-full bg-emerald-500" />
                  </div>
                </div>
              </div>
            </section>
          </div>

          <section className="rounded-xl bg-white p-5 shadow-sm">
            <h3 className="mb-4 text-sm font-semibold text-slate-700">학습된 문서 목록</h3>
            <ul className="space-y-3 text-sm text-slate-700">
              <li className="flex items-center justify-between gap-3 rounded-lg bg-slate-50 px-3 py-2">
                <span className="flex min-w-0 items-center gap-2">
                  <FileText size={16} className="shrink-0 text-slate-400" {...LINE_ICON} aria-hidden />
                  <span className="truncate">2026학년도 학사요람.pdf</span>
                </span>
                <span className="shrink-0 text-slate-500">4,201 chunks</span>
              </li>
              <li className="flex items-center justify-between gap-3 rounded-lg bg-slate-50 px-3 py-2">
                <span className="flex min-w-0 items-center gap-2">
                  <FileText size={16} className="shrink-0 text-slate-400" {...LINE_ICON} aria-hidden />
                  <span className="truncate">장학금 규정집.pdf</span>
                </span>
                <span className="shrink-0 text-slate-500">2,188 chunks</span>
              </li>
              <li className="flex items-center justify-between gap-3 rounded-lg bg-slate-50 px-3 py-2">
                <span className="flex min-w-0 items-center gap-2">
                  <FileText size={16} className="shrink-0 text-slate-400" {...LINE_ICON} aria-hidden />
                  <span className="truncate">졸업 요건 안내.pdf</span>
                </span>
                <span className="shrink-0 text-slate-500">1,062 chunks</span>
              </li>
            </ul>
          </section>
        </div>
      </div>
    </div>
  )
}

function AdminDashboard() {
  const [activeTab, setActiveTab] = useState('dashboard')

  const navBtn = (id, Icon, label) => {
    const active = activeTab === id
    return (
      <li>
        <button
          type="button"
          onClick={() => setActiveTab(id)}
          className={`flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm transition ${
            active
              ? 'bg-violet-50 font-medium text-violet-700'
              : 'text-slate-700 hover:bg-slate-50'
          }`}
        >
          <Icon
            size={17}
            className={`shrink-0 ${active ? 'text-violet-600' : 'text-slate-400'}`}
            {...LINE_ICON}
            aria-hidden
          />
          {label}
        </button>
      </li>
    )
  }

  return (
    <div className="flex h-full min-h-0 w-full overflow-hidden bg-slate-100">
      <aside className="w-64 shrink-0 border-r border-slate-200 bg-white p-5">
        <h2 className="mb-6 text-lg font-bold text-slate-800">Admin Console</h2>

        <div className="mb-6">
          <p className="mb-2 text-xs font-semibold uppercase text-slate-400">메인 메뉴</p>
          <ul className="space-y-2">
            {navBtn('dashboard', LayoutDashboard, '대시보드')}
            {navBtn('knowledge', BookOpen, '지식 베이스')}
            {navBtn('documents', Receipt, '문서 관리')}
          </ul>
        </div>

        <div className="mb-6">
          <p className="mb-2 text-xs font-semibold uppercase text-slate-400">SELF-RAG 관리</p>
          <ul className="space-y-2">
            {navBtn('reliability', BadgeCheck, '신뢰도 분석')}
            {navBtn('validationLogs', ScrollText, '검증 로그')}
            {navBtn('promptPolicy', Brain, '프롬프트 정책')}
          </ul>
        </div>

        <div>
          <p className="mb-2 text-xs font-semibold uppercase text-slate-400">설정</p>
          <ul className="space-y-2">
            {navBtn('userPermissions', Users, '사용자 권한')}
            {navBtn('systemSettings', Settings, '시스템 설정')}
          </ul>
        </div>
      </aside>

      <section className="flex h-full min-h-0 w-full min-w-0 flex-1 flex-col overflow-hidden bg-slate-100">
        {activeTab === 'dashboard' && <DashboardHome />}
        {activeTab === 'knowledge' && <KnowledgeBase />}
        {activeTab === 'documents' && <DocumentManagement />}
        {activeTab === 'reliability' && <ReliabilityAnalysis />}
        {activeTab === 'validationLogs' && <ValidationLogs />}
        {activeTab === 'promptPolicy' && <PromptPolicy />}
        {activeTab === 'userPermissions' && <UserPermissions />}
        {activeTab === 'systemSettings' && <SystemSettings />}
      </section>
    </div>
  )
}

export default AdminDashboard
