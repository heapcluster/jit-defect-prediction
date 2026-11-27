// 任务提交后把视口带到结果卡片，省去用户手动向下滚动查找结果。
export function scrollToResults() {
  if (typeof document === 'undefined') return
  document.getElementById('tool-results')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
