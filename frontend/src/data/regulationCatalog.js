/**
 * Student-facing regulation documents per school (demo paths align with public PDFs).
 */
export const STUDENT_REGULATION_CATALOG = [
  {
    schoolId: 'konkuk',
    name: '건국대학교 글로컬캠퍼스',
    shortName: '건국대 글로컬',
    documents: [
      { id: 'k-h1', title: '2026학년도 학사요람', category: '학사', file: '/guide.pdf' },
      { id: 'k-h2', title: '장학금 규정집', category: '장학', file: '/guide.pdf' },
      { id: 'k-h3', title: '졸업·학위 요건 안내', category: '졸업', file: '/guide.pdf' },
      { id: 'k-h4', title: '수강·성적 처리 지침', category: '수강', file: '/guide.pdf' },
    ],
  },
  {
    schoolId: 'yonsei',
    name: '연세대학교',
    shortName: '연세대',
    documents: [
      { id: 'y-h1', title: '학칙·학사요람 통합', category: '학사', file: '/guide2.pdf' },
      { id: 'y-h2', title: '등록금·분납 안내', category: '등록', file: '/guide2.pdf' },
      { id: 'y-h3', title: '교환학생·복수전공 규정', category: '학사', file: '/guide2.pdf' },
    ],
  },
]
