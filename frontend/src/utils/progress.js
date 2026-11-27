// 任务进度换算：数据收集 / 数据清洗 / 模型训练 / 模型预测共用同一口径。
// 终态（成功 / 失败 / 取消）统一收口到 100%，运行中按 done/total 取整，
// 避免同一次任务在不同工具页出现「进度条不满格」的差异。
const TERMINAL = new Set(['success', 'failed', 'cancelled'])

export function jobPercentage(job) {
  if (!job) return 0
  if (TERMINAL.has(job.status)) return 100
  const total = Number(job.total) || 0
  if (!total) return 0
  const done = Number(job.done) || 0
  return Math.max(0, Math.min(100, Math.floor(done / total * 100)))
}
