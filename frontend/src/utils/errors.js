// 统一错误文案：**只定义一处**（docs/frontend/pages.md 第 5 节三态口径）。
//
// 2026-10-25 修复要点：
// - 此前 RiskList / TrendBoard / CommitDetail 各写一份 errText（措辞还不一致），
//   而 PrList / PrDetail 读的是 `e?.response?.data?.message` —— 响应拦截器
//   （api/request.js）已经把后端错误包络转成普通 Error（有 code / detail / message，
//   没有 response），所以那个字段永远取不到，三态分支与错误码分支全部失效，
//   连「timeout of 10000ms exceeded」这种技术文案都会直接甩给用户。
// - 本模块是 pages.md §5 的唯一实现，五个视图都从这里取文案。

export function errText(e) {
  const code = e?.code
  // 40001 要指出是哪个参数，参数名在 err.detail（message 是通用文案）
  if (code === 40001) return `参数有误：${e?.detail || e?.message || ''}`
  if (code === 40100) return '登录已失效，请重新登录'
  if (code === 40400) return '该提交不存在'
  if (code === 50000) return '服务异常，请稍后重试'
  // 超时 / 网络中断：axios 的 message 是技术文案，给一句人话
  if (e?.code === 'ECONNABORTED' || /timeout/i.test(e?.message || '')) {
    return '请求超时，请稍后重试'
  }
  return e?.message || '请求失败'
}

// 该错误是否值得给「重试」按钮：只有 50000 给（pages.md §5：40100 不给重试）
export function isRetryable(e) {
  return e?.code === 50000
}
