import axios from 'axios'

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
// 成功（code === 0）返回 data；失败把 { code, message } 原样 reject，由页面按 docs/pages.md 第 5 节三态口径处理：
//   40001 参数非法 → 指出是哪个参数
//   40100 未通过鉴权 → 提示令牌失效/重新登录，不给「重试」按钮
//   40400 目标不存在 → 「该提交不存在」+ 返回列表
//   50000 服务内部错误 → 「服务异常，请稍后重试」+ 重试（不回显堆栈/SQL/路径）
request.interceptors.response.use(
  (response) => {
    const res = response.data
    if (res.code === 0) {
      return res.data
    }
    return Promise.reject(res)
  },
  (error) => Promise.reject(error)
)

export default request
