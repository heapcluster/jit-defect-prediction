import axios from 'axios'

// 错误码 → 用户友好提示（页面错误三态由 docs/web_page/ 各页面设计统一约定）
const ERROR_MESSAGES = {
  40001: '请求参数有误',
  40100: '登录已失效，请重新登录',
  40400: '该提交不存在',
  50000: '服务异常，请稍后重试'
}

function apiError(res) {
  const err = new Error(ERROR_MESSAGES[res.code] || res.message || '请求失败')
  err.code = res.code
  err.detail = res.message
  return err
}

// 统一请求实例：baseURL 走 vite 代理的 /api
const request = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    // 契约三第一节：鉴权请求头，字段名 X-API-Key（取值走构建期环境变量，真实密钥不入库）
    'X-API-Key': import.meta.env.VITE_API_KEY
  }
})

// 同步类端点（/api/sync）的超时：实测单条提交 × 8 模型约 4.1s，
// 一条 PR 动辄 20+ 提交，再加上从 GitHub 拉 PR 头与提交清单，默认的 10s 必然超时
// （2026-10-25 修复：同步按钮此前 100% 报 "timeout of 10000ms exceeded"）。
export const SYNC_TIMEOUT = 300000

// 响应拦截：统一处理 { code, message, data } 包络
// 成功（code === 0）返回 data；失败 reject 一个带 code 的错误，页面按 code 区分三态：
//   40001 参数非法 → 指出是哪个参数（参数名取 err.detail，message 是通用文案）
//   40100 未通过鉴权 → 提示重新登录，不给「重试」
//   40400 目标不存在 → 「该提交不存在」+ 返回列表
//   50000 服务内部错误 → 「服务异常，请稍后重试」+ 重试（不回显堆栈/SQL/路径）
request.interceptors.response.use(
  (response) => {
    const res = response.data
    if (res.code === 0) {
      return res.data
    }
    return Promise.reject(apiError(res))
  },
  (error) => {
    // 后端错误统一使用非 2xx HTTP 状态，Axios 会直接进入此分支。
    const res = error.response?.data
    if (res && typeof res.code === 'number') {
      return Promise.reject(apiError(res))
    }
    return Promise.reject(error)
  }
)

// Storage/datasets 响应保留结构化安全校验细节，不改动 W1 响应拦截器，
// 也不让二进制文件经过该拦截器。
export const storageOptions = {
  transformResponse: [...request.defaults.transformResponse, data => {
    const detail = data?.error?.detail
    if (data?.code === 40001 && typeof detail === 'string') return { ...data, message: detail }
    return data
  }]
}

// 所有产物/图片下载统一走带 X-API-Key 的 fetch：<img> 和浏览器直接打开都带不了鉴权头。
export async function fetchBinary(path, { label = '下载', serverError = '下载服务异常，请稍后重试', includeStatus = false } = {}) {
  const response = await fetch(path, { headers: { 'X-API-Key': import.meta.env.VITE_API_KEY } })
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    const code = payload?.code ?? (response.status === 401 ? 40100 : undefined)
    const detail = payload?.error?.detail ?? payload?.message
    const message = code === 40100
      ? '登录已失效，请重新登录'
      : code === 50000 || response.status >= 500
        ? serverError
        : (typeof detail === 'string' && detail) || (includeStatus ? `${label}失败：${response.status}` : `${label}失败`)
    throw Object.assign(new Error(message), { code })
  }
  return response.blob()
}

export default request
