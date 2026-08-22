import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000'

/**
 * 등록된 학교 목록을 조회합니다.
 * 응답 규격: { data: { schools: [{ id, name, doc_count }] } }
 *
 * @returns {Promise<{ id: string, name: string, doc_count: number }[]>}
 */
export async function fetchSchools() {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/schools`)
    const schools = response?.data?.data?.schools

    if (!Array.isArray(schools)) {
      return []
    }

    return schools
  } catch (error) {
    const serverMessage = error?.response?.data?.error?.message
    throw new Error(
      serverMessage ?? '학교 목록을 불러오는 중 오류가 발생했습니다.',
      { cause: error },
    )
  }
}

export default { fetchSchools }
