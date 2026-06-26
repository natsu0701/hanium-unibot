// 백엔드 API 연동 전, UI 테스트를 위한 Mock API 모듈입니다.
// 실제 백엔드가 준비되면 이 파일의 함수만 axios 호출로 교체하면 됩니다.

const MOCK_DELAY_MS = 1000

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

/**
 * 채팅 메시지를 전송하고 봇의 답변을 받아오는 Mock 함수.
 * 실제 백엔드 응답 규격과 동일한 형태로 데이터를 반환합니다.
 *
 * @param {string} message 사용자가 입력한 질문
 * @returns {Promise<{ answer: string, sources: { page: number, text: string }[] }>}
 */
export async function sendChatMessage(message) {
  // 실제 네트워크 지연을 흉내 내기 위한 1초 딜레이
  await delay(MOCK_DELAY_MS)

  return {
    answer: '학점 3.5 이상이어야 합니다.',
    sources: [{ page: 3, text: '제3조 2항' }],
  }
}

export default { sendChatMessage }
