import axios from 'axios'

export class ApiError extends Error {
  constructor(code, message, detail = null, status = 0) {
    super(message || '请求失败')
    this.name = 'ApiError'
    this.code = code
    this.detail = detail
    this.status = status
  }
}

let unauthorizedHandler = null

export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = handler
}

const http = axios.create({
  baseURL: '/api',
  withCredentials: true,
  timeout: 0
})

function parseBlobError(blob) {
  return blob.text().then((text) => {
    try {
      return JSON.parse(text)
    } catch (error) {
      return null
    }
  })
}

http.interceptors.response.use(
  (response) => {
    if (response.config.responseType === 'blob') return response
    const body = response.data
    if (body && body.code === 0) return body.data
    throw new ApiError(body?.code ?? 50001, body?.message || '请求失败', body?.data ?? null, response.status)
  },
  async (error) => {
    if (error instanceof ApiError) throw error
    let body = error.response?.data
    if (body instanceof Blob) body = await parseBlobError(body)
    const status = error.response?.status || 0
    if (status === 401) {
      if (unauthorizedHandler) unauthorizedHandler()
      throw new ApiError(40101, body?.message || '登录已失效，请重新登录', null, 401)
    }
    if (status === 0) {
      throw new ApiError(50001, '无法连接服务器，请重试', null, 0)
    }
    throw new ApiError(body?.code ?? 50001, body?.message || '请求失败', body?.data ?? null, status)
  }
)

export default http
