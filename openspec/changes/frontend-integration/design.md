# frontend-integration — 设计要点

## 技术栈
Vue 3 + Vite + Element Plus + ECharts + axios。`/api` 走本地代理到 `:8000`。`X-API-Key` 由构建期环境变量 `VITE_API_KEY` 注入，不硬编码。

## 三页面（字段照 docs/frontend/pages.md）
- **风险列表**：表格 + `min_risk`/`model_name`/时间筛选 + 分页；固定 `risk_score` 降序；行点击带 `commit_hash` 跳详情；`risk_score` ×100 转百分比。
- **提交详情**：风险值 + SHAP 解释条（推高/降低，按 `|contribution|` 降序显前 8）+ 14 特征分组；`explanation[].feature` 取值须与 `features` 键名一致；`features=null`/`explanation=[]` 照常显示。
- **趋势看板**：ECharts 折线（`avg_risk`）+ 汇总卡（提交总数 / 高风险数求和 / 平均风险加权平均，权重 `commit_count`）；`high_risk_count` 用后端算好的；数据点 <2 不画折线。

## 三态（三页共用）
加载中骨架屏（容器高度不变）；空数据非错误（文案 + 清空/重置操作）；`40001` 指参数、`40100` 不重试、`40400`/`50000` 不显服务端 message 原文。

## 联调
起后端 `:8000`，按 `docs/weekly/demo-script-sprint1.md` 跑通四接口，记录进 `docs/implementation/frontend-integration-log.md`。
