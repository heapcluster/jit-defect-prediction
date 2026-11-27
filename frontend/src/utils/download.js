// 下载只定义一处：部分浏览器要求 <a> 在文档内才触发下载，
// 也不能在 click() 后立刻 revokeObjectURL（会被取消）。
export function saveBlob(blob, name) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = name
  link.style.display = 'none'
  document.body.appendChild(link)
  try { link.click() } finally {
    setTimeout(() => {
      link.remove()
      URL.revokeObjectURL(url)
    }, 1000)
  }
}
