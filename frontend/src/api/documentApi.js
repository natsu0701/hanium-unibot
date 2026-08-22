import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000'
const EMPTY_MESSAGE =
  '등록된 규정 문서가 없습니다. 관리자 대시보드에서 PDF를 업로드해 주세요.'

export function getDocumentDownloadUrl(documentId, downloadUrl) {
  if (typeof downloadUrl === 'string' && downloadUrl.trim()) {
    const trimmed = downloadUrl.trim()

    if (/^https?:\/\//i.test(trimmed)) {
      return trimmed
    }

    const path = trimmed.startsWith('/') ? trimmed : `/${trimmed}`
    return `${API_BASE_URL}${path}`
  }

  if (!documentId) {
    return ''
  }

  return `${API_BASE_URL}/api/documents/${documentId}`
}

function normalizeDocument(item) {
  if (!item || typeof item !== 'object') {
    return null
  }

  const id = item.id == null ? '' : String(item.id)

  if (!id) {
    return null
  }

  const filename =
    typeof item.filename === 'string' && item.filename.trim()
      ? item.filename.trim()
      : '문서.pdf'

  return {
    id,
    filename,
    status: item.status ?? '',
    chunks_count: Number.isFinite(Number(item.chunks_count))
      ? Number(item.chunks_count)
      : 0,
    upload_time: item.upload_time ?? null,
    download_url: getDocumentDownloadUrl(id, item.download_url),
  }
}

/**
 * 업로드된 문서 목록을 조회하고, 처리가 끝난 항목만 반환합니다.
 * 응답 규격: { data: { items: [{ id, filename, status, download_url, ... }] } }
 *
 * @param {string | null} [schoolId] 선택된 학교 id. 있으면 query로 전달합니다.
 * @returns {Promise<{ id: string, filename: string, status: string, download_url: string }[]>}
 */
export async function fetchDocuments(schoolId) {
  try {
    const params = {}

    if (schoolId != null && schoolId !== '') {
      params.school_id = schoolId
    }

    const response = await axios.get(`${API_BASE_URL}/api/documents`, {
      params,
    })

    const items = response?.data?.data?.items

    if (!Array.isArray(items)) {
      return []
    }

    return items
      .filter((item) => item?.status === 'completed')
      .map(normalizeDocument)
      .filter(Boolean)
  } catch (error) {
    const serverMessage = error?.response?.data?.error?.message
    throw new Error(serverMessage ?? EMPTY_MESSAGE, { cause: error })
  }
}

export default { fetchDocuments, getDocumentDownloadUrl }
