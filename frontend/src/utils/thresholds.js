import { reactive } from 'vue'
import { getConfig } from '../api'

// 唯一运行时配置源为 /api/config；首次读取成功前不得进行风险分档。
export const thresholds = reactive({ high: null, mid: null })
export const configuration = reactive({
  items: [],
  schema: {},
  ready: false,
  loading: false,
  error: ''
})

// 仅接受服务端确认的生效项，不根据草稿、.env 或本地常量推算回退值。
// 视觉主题只由 ui.css 设计令牌决定，配置中心不再覆盖背景色与主题色。
export async function applyConfiguration(data) {
  if (!Array.isArray(data?.items)) throw new Error('配置响应不完整，请重试')
  const merged = new Map((data.schema ? [] : configuration.items).map(item => [item.config_key, item]))
  for (const item of data.items) merged.set(item.config_key, item)
  const schema = data.schema ?? configuration.schema
  const high = merged.get('risk_high_threshold')?.value
  const mid = merged.get('risk_mid_threshold')?.value
  if (!schema || !Object.keys(schema).length ||
      Object.keys(schema).some(key => !merged.has(key)) ||
      typeof high !== 'number' || typeof mid !== 'number' ||
      !(0 < mid && mid < high && high < 1)) {
    throw new Error('配置响应不完整或风险阈值无效，请重试')
  }
  configuration.items = Array.from(merged.values())
  configuration.schema = schema
  Object.assign(thresholds, { high, mid })
  configuration.ready = true
  return data
}

export async function loadConfiguration() {
  configuration.loading = true
  configuration.error = ''
  try {
    const data = await getConfig()
    if (!data?.schema) throw new Error('配置响应缺少字段元数据，请重试')
    await applyConfiguration(data)
    return data
  } catch (error) {
    configuration.error = error.detail || error.message || '配置读取失败'
    throw error
  } finally {
    configuration.loading = false
  }
}
