import axios from 'axios'

// 错误码 → 用户友好提示（docs/pages.md 第 5 节三态口径，只定义一处）
const ERROR_MESSAGES = {
  40001: '请求参数有误',
  40100: '登录已失效，请重新登录',
  40400: '该提交不存在',
  50000: '服务异常，请稍后重试'
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

// 响应拦截：统一处理 { code, message, data } 包络
// 成功（code === 0）返回 data；失败 reject 一个带 code 的错误，页面按 code 区分三态：
//   40001 参数非法 → 指出是哪个参数
//   40100 未通过鉴权 → 提示重新登录，不给「重试」
//   40400 目标不存在 → 「该提交不存在」+ 返回列表
//   50000 服务内部错误 → 「服务异常，请稍后重试」（不回显堆栈/SQL/路径）
request.interceptors.response.use(
  (response) => {
    const res = response.data
    if (res.code === 0) {
      return res.data
    }
    const err = new Error(ERROR_MESSAGES[res.code] || res.message || '请求失败')
    err.code = res.code
    err.detail = res.message
    return Promise.reject(err)
  },
  (error) => Promise.reject(error)
)

export default request
