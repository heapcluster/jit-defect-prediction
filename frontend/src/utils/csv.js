// CSV 解析只定义一处：后端 csv 模块会为含逗号/引号/换行的字段加引号，
// 直接用 split(',') 会让列错位（预览、提交详情深链都依赖这张表）。
export function parseCsv(text) {
  if (typeof text !== 'string' || !text.length) return { columns: [], rows: [] }
  const source = text.charCodeAt(0) === 0xfeff ? text.slice(1) : text
  const rows = []
  let row = [], field = '', quoted = false
  for (let i = 0; i < source.length; i += 1) {
    const char = source[i]
    if (quoted) {
      if (char === '"') {
        if (source[i + 1] === '"') { field += '"'; i += 1 } else quoted = false
      } else field += char
    } else if (char === '"') quoted = true
    else if (char === ',') { row.push(field); field = '' }
    else if (char === '\n') { row.push(field); rows.push(row); row = []; field = '' }
    else if (char !== '\r') field += char
  }
  if (field.length || row.length) { row.push(field); rows.push(row) }
  if (!rows.length) return { columns: [], rows: [] }
  const columns = rows.shift()
  return {
    columns,
    rows: rows.filter(cells => cells.some(cell => cell !== '')).map(cells =>
      Object.fromEntries(columns.map((name, index) => [name, cells[index] ?? '']))
    )
  }
}
