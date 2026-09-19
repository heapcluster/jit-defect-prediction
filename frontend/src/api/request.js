import axios from 'axios'

// 统一请求实例：baseURL 走 vite 代理的 /api
const request = axios.create({
  baseURL: '/api',
  timeout: 10000
})

// 响应拦截：统一处理 { code, message, data } 包络
// 只判 code === 0；错误码（40001/40100/40400/50000）交给调用方按契约处理
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
