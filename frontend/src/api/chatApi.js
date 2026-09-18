import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000'

function normalizeSource(source) {
  if (!source || typeof source !== 'object') {
    return {
      page: 0,
      text: '',
      evidence: '',
      is_table: false,
      table_headers: [],
    }
  }

  return {
    ...source,
    page: Number.isFinite(Number(source.page)) ? Number(source.page) : 0,
    text: typeof source.text === 'string' ? source.text : '',
    evidence: typeof source.evidence === 'string' ? source.evidence : '',
    is_table: source.is_table === true,
    table_headers: Array.isArray(source.table_headers)
      ? source.table_headers
      : [],
  }
}

function normalizeSources(sources) {
  if (!Array.isArray(sources)) {
    return []
  }

  return sources.filter(Boolean).map(normalizeSource)
}

/**
 * 백엔드 채팅 API와 통신하는 함수.
 *
 * 요청 Body: { message, user_id, school_id? }
 * 응답 형식: { data: { answer, sources, confidence } }
 *
 * @param {string} message 사용자가 입력한 텍스트
 * @param {string | null} [schoolId] 선택된 학교 id. 관리자 모드면 null
 * @returns {Promise<{ answer: string, sources: object[], confidence?: number }>}
 */
export async function sendChatMessage(message, schoolId) {
  try {
    const payload = {
      message,
      user_id: 'tester',
    }

    if (schoolId != null && schoolId !== '') {
      payload.school_id = schoolId
    }

    const response = await axios.post(`${API_BASE_URL}/api/chat`, payload)
    const data = response?.data?.data ?? {}

    return {
      ...data,
      answer: typeof data.answer === 'string' ? data.answer : '',
      sources: normalizeSources(data.sources),
    }
  } catch (error) {
    const detail = error?.response?.data?.detail
    const serverMessage =
      error?.response?.data?.error?.message ||
      (typeof detail === 'string' ? detail : null)
    throw new Error(
      serverMessage ?? '채팅 요청 중 오류가 발생했습니다.',
      { cause: error },
    )
  }
}

export default { sendChatMessage }
