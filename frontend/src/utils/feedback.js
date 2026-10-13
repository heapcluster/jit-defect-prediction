import { ElMessage } from 'element-plus'

// 错误码 → 页面提示，三页共用（口径见 docs/frontend/pages.md 第 5 节，只定义一处）。
// 50000 只给通用文案，不回显堆栈 / SQL / 路径（backend/api-spec.md §二）。
export function handleError(err) {
  const code = err && err.code
  if (code === 40100) {
    ElMessage.error('登录已失效，请重新登录')
  } else if (code === 40400) {
    ElMessage.error('该提交不存在')
  } else if (code === 40001) {
    ElMessage.error((err && err.detail) || '请求参数有误')
  } else if (code === 50000) {
    ElMessage.error('服务异常，请稍后重试')
  } else {
    ElMessage.error((err && err.message) || '请求失败')
  }
}
