import { reactive } from 'vue'
import { getConfig } from '../api'

// 风险等级阈值的唯一前端数据源：后端运行时配置（/api/config）。
// 阈值是运营参数，质量看板改完立即影响等级与门禁；前端若继续硬编码 0.5/0.2，
// 就会出现「后端说中风险、列表仍标高风险」的双源漂移。
// 初值只作首屏兜底，与 backend/app/config.py 的默认值保持一致。
export const thresholds = reactive({ high: 0.5, mid: 0.2, loaded: false })

let inflight = null

export async function loadThresholds(force = false) {
  if (thresholds.loaded && !force) return thresholds
  if (!inflight) {
    // 用 Promise 包一层：api 模块缺失导出时是同步抛错，直接写 getConfig() 会绕过下面的 catch
    inflight = Promise.resolve()
      .then(() => getConfig())
      .then((cfg) => {
        applyThresholds(
          cfg?.high_risk_threshold ?? thresholds.high,
          cfg?.mid_risk_threshold ?? thresholds.mid
        )
        return thresholds
      })
      // 配置拉不到就按当前值渲染：阈值只影响配色，不该阻断整页
      .catch(() => thresholds)
      .finally(() => {
        inflight = null
      })
  }
  return inflight
}

export function applyThresholds(high, mid) {
  thresholds.high = high
  thresholds.mid = mid
  thresholds.loaded = true
}
