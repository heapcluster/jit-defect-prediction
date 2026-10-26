# 页面 ↔ 接口 ↔ 字段 映射

> 来源：原 `docs/pages.md`（已并入本文件）v1.5（已裁定）｜ 维护：刘帅华 ｜ 审核：吕建江、蒋励
> **核心三页（风险列表 / 提交详情 / 趋势看板）之外，2026-10-25 起增补 PR 两页与 404 兜底页
> （对应 openspec change `realtime-pr-prediction`）。**

## 1. 三页共用约定

1. 字段名与契约完全一致，前端不改名、不驼峰转换（`risk_score` 就叫 `risk_score`）。
2. 概率一律前端转百分比；后端返回 `0.0`~`1.0` 小数。
3. 时间：ISO 8601 带时区 → 前端转本地时区（实现：`src/utils/datetime.js`，**只此一处**）。
4. 响应包络 `{code,message,data}`，前端只判 `code===0`。
5. 技术栈：Vue 3 + Element Plus + ECharts。
6. 每请求带 `X-API-Key`（构建期环境变量注入，不硬编码）；收到 `40100` 按三态处理。
7. 时间范围筛选为闭区间：`end_time` 送纯日期串 `YYYY-MM-DD`，服务端含结束日全天；前端不自行拼接时间收尾（契约三 1.5 口径）。
8. 错误文案只有一处实现（`src/utils/errors.js` 的 `errText`）：响应拦截器已把后端包络转成带 `code`/`detail`/`message` 的普通 Error，**页面不得再读 `e.response.data.message`**（那个字段不存在，读它等于三态分支全失效）。超时/网络异常统一显示「请求超时，请稍后重试」，不把 axios 技术文案甩给用户。
9. 同步类端点（`POST /api/sync`、`POST /api/sync-prs`）走长超时（`SYNC_TIMEOUT = 300s`）：实测单条提交 × 8 模型约 4.1s，一条 PR 常有 20+ 提交，默认 10s 必然超时。
10. 组件库文案走中文（Element Plus `zh-cn` locale），与 `index.html` 的 `lang="zh-CN"` 一致。

| 页面 | 接口 |
|---|---|
| 风险列表 | `GET /api/commits` |
| 提交详情 | `GET /api/commits/{commit_hash}` |
| 缺陷引入趋势看板 | `GET /api/trends` |

## 2. 页面一：风险列表

| 页面元素 | 来源 | 说明 |
|---|---|---|
| 模型下拉 | `model_name` | 前端维护清单（见 §6） |
| 最低风险输入 | `min_risk` | 0.0~1.0 |
| 时间范围 | `start_time`/`end_time` | 转 ISO 8601 |
| **风险** | `items[].risk_score` | 前端 ×100 转百分比，保留一位 |
| 提交哈希 | `items[].commit_hash` | 显前 8 位，悬停全量，点击复制 |
| 作者 / 时间 / 信息 | `author_name`/`committed_at`/`message` | 时间转本地；信息单行截断悬停全文 |
| 总数 / 分页 | `total`/`page`/`size` | 默认 20 上限 100 |

排序固定按 `risk_score` 降序；点击整行跳详情（路由带 `commit_hash`）。接口没有的字段不画。

## 3. 页面二：提交详情

| 页面元素 | 来源 |
|---|---|
| 风险值 / 模型版本 / 哈希 / 作者 / 时间 / 信息 | 同名字段 |
| 风险等级标签 | 前端按阈值判定（§5 一处定义） |
| 风险解释条 | `explanation[].feature/.contribution/.direction`：`increase` 向右、`decrease` 向左；按 `|contribution|` 降序，只显前 8 |
| 特征值 | `features.*` 按五维度分组（代码分布/规模/目的/历史/开发者经验）全显示 |

- 解释条只说「推高/降低」，不解释数值含义。
- `features` 键名必须与 `feature-columns.md` 一致，否则解释条取不到值、静默空白。
- 特征值为 0 照常显示；字段缺失显示 `—`（链路出问题信号，要让它可见）。
- **重新预测**：`POST /api/predict`，传 `commit_hash`（可选 `model_name`），返回后刷新 `risk_score`/`model_name`/`explanation`；模型下拉列实际交付模型（`lr_v1`/`rf_v1`/`xgb_v1`）。**预测结果是一次性展示**：刷新页面（重新 GET 详情）后回到 `prediction` 表默认模型记录，不持久化所选模型。

## 4. 页面三：缺陷引入趋势看板

| 页面元素 | 来源 |
|---|---|
| 粒度 / 模型选择 | `granularity`/`model_name` |
| 折线 y | `series[].avg_risk`（0~1 画轴，不必转百分比） |
| 折线 x | `series[].period`（如 `2026-W30`） |
| 汇总：提交总数 | `series[].commit_count` 求和 |
| 汇总：高风险提交 | `series[].high_risk_count` 求和 |
| 汇总：平均风险 | 按 `commit_count` 加权平均（非算术平均） |

- 「高风险」口径只有一处：后端 `high_risk_count`（阈值 `≥0.5`），前端不重算。
- 单模型单维度趋势：不做分组、不做同图多模型叠加。
- 数据点 < 2 个：不画折线，只显明细表 + 提示「数据点不足」。

## 5. 三态与错误码（三页共用）

| 情形 | 页面表现 |
|---|---|
| 加载中 | 骨架屏/loading，容器高度不变 |
| 空数据 | 列表：「当前筛选条件下没有提交」+清空；趋势：「所选时间范围内没有数据」+重置。**空数据不是错误** |
| `40001` | 指出哪个参数非法 |
| `40100` | 令牌失效/需重登，不给重试按钮 |
| `40400` | 「该提交不存在」+返回列表，不显服务端 message |
| `50000` | 「服务异常，请稍后重试」+重试，不显堆栈/SQL/路径 |
| `explanation` 空 | 「该模型未提供特征解释」+保留特征值区 |

**风险着色阈值只在这一处定义**：`≥0.5` 高（深色警示）/ `≥0.3` 中 / 其余常规。

## 5.1 页面四 / 五：PR 列表与 PR 详情（2026-10-25 增补）

对应接口与字段口径见 `docs/backend/api-spec.md` v1.7 §6~§8 与 openspec change `realtime-pr-prediction`。

| 页面 | 接口 | 关键字段 |
|---|---|---|
| PR 列表 | `GET /api/prs` | `items[].number/title/author/state/risk_score/commit_count/predicted_count/updated_at` |
| PR 详情 | `GET /api/prs/{number}` | `commits[].sha/message/author/risk_score/predicted_at` |
| 同步动作 | `POST /api/sync-prs` | 长耗时端点，超时按 §1.9 |

- **未预测的 PR/提交一律显「未预测」**（`risk_score === null`），**不用 `0.0` 冒充**。
- 「已预测/总提交」用 `predicted_count`/`commit_count` 两个字段表达，不在前端推算。
- 同步按钮：点了以后无论同步成功与否都重新拉一次列表（同步可能只完成一部分，单 PR 失败进 `skipped`）。
- 表格不随错误提示卸载：出错时保留上一次拉到的数据。
- PR 列表的模型下拉切换后立即重查（`@change`）。

## 5.2 页面六：404 兜底

- 未知路径走 `/:pathMatch(.*)*` 路由 → 「页面不存在」+ 回风险列表按钮（不留白屏）。
- 路由切换后滚动位置回到顶部（`scrollBehavior`）。

## 6. 已裁定（牵动接口的项）

| 项 | 结论 | 页面影响 |
|---|---|---|
| 模型下拉选项来源 | MVP 前端维护清单，不新增接口 | 静态清单 |
| 趋势看板分组 | 不做 | 单一维度 |
| 多模型同图对比 | 不做 | `series` 单模型一组，`model_name` 切换 |
| 详情页显示「判对没」 | 不显示 | 无此元素 |
| `explanation` 算法 | SHAP | 页面只说推高/降低 |

> 接口冻结后（契约三 v1.7）推翻任一条走契约变更流程，不在群里口头改。
