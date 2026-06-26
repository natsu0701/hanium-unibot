import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000'

/**
 * 백엔드 채팅 API와 통신하는 함수.
 *
 * 요청 Body: { message, user_id }
 * 응답 형식: { data: { answer, sources, confidence } }
 *
 * @param {string} message 사용자가 입력한 텍스트
 * @returns {Promise<{ answer: string, sources: { page: number, text: string }[], confidence: number }>}
 */
export async function sendChatMessage(message) {
  try {
    const response = await axios.post(`${API_BASE_URL}/api/chat`, {
      message,
      user_id: 'tester',
    })

    // 백엔드 응답은 { data: { answer, sources, confidence } } 형태이므로 내부 data를 반환
    return response.data.data
  } catch (error) {
    const serverMessage = error?.response?.data?.error?.message
    throw new Error(
      serverMessage ?? '채팅 요청 중 오류가 발생했습니다.',
      { cause: error },
    )
  }
}

export default { sendChatMessage }
