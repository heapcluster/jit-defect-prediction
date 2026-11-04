// 风险等级阈值常量：与后端 .env 的 HIGH_RISK_THRESHOLD / MID_RISK_THRESHOLD 同值。
// runtime_setting 与 /api/config 已下线，高/中/低判定由前端按常量算（docs/api/predict.md）。
export const thresholds = { high: 0.5, mid: 0.2 }
