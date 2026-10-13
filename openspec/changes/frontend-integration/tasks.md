# frontend-integration — 任务清单

## 1. 立项（F2）
- [x] 1.1 本 change 进 `openspec/changes/frontend-integration/`（propose → apply），看板「规格变更或任务」列可点回
- [x] 1.2 飞书 PRD 第五章增补前端三页面 User Story（**F Epic**，非 C —— PRD 第五章分层为 A–F + G，见 `repo/user-story-traceability.md`），状态写实

## 2. 脚手架与接口层（F3 前置）
- [x] 2.1 `npm create vue@latest` + 装 `element-plus`/`echarts`/`axios`；配 `/api` 代理 → PR #33 已合入 main：`frontend/package.json` 四依赖齐、`vite.config.js` 将 `/api` 代理到 `localhost:8000`、`.env.example` 给出密钥示例（真实密钥走 `.env.local`，不入库）
- [x] 2.2 `src/api/request.js`（**实际为 `.js` 而非 `.ts`**：本组前端不使用 TypeScript，已在 tasks 中订正口径）：axios 实例 + `X-API-Key` 拦截器 + 统一解包 `code===0` + 错误码分发三态

## 3. 三页面（F3）
- [x] 3.1 风险列表 `views/RiskList.vue`（**实际文件名为 `RiskList.vue`，非 `CommitList.vue`**）：排序固定 `risk_score` 降序、筛选、分页、点击整行跳详情；字段与 `docs/frontend/pages.md` §2 逐条对应
- [x] 3.2 提交详情 `views/CommitDetail.vue`：风险值 / 模型版本 / SHAP 解释条（`increase` 右、`decrease` 左，按 `|contribution|` 降序取前 8）/ 特征值五维度分组
- [x] 3.3 趋势看板 `views/TrendBoard.vue`：ECharts 折线（`avg_risk`）+ 三项汇总（总数 / 高风险数求和、平均风险按 `commit_count` 加权）；数据点 < 2 不画折线

> ⚠️ 3.1–3.3 于 2026-10-13 实现，**尚未过 lint/build 实跑校验**（本机 `frontend/node_modules` 未安装，需 `npm ci` 后执行 `npm run lint` 与 `npm run build`），也**未与后端联调**。按课程「只勾 tasks ≠ 功能合格」，此三条标「已实现」而非「已验收」，联调通过后才可在周报记完成。

## 4. 联调（F4）
- [ ] 4.1 起后端 `:8000`，按 `repo/demo-script-sprint1.md` 跑通 API-01~04
- [ ] 4.2 联调记录入库 `docs/frontend/frontend-integration-log.md`（原写 `docs/implementation/...`，该目录在六包重构后不存在）
- [ ] 4.3 PR 合入 main，看板行指向本 change
---

## 测试与验证（强制板块）

> 分层口径见 `docs/common/test-strategy.md`；模板见 `docs/common/openspec-task-template.md`。
> 铁律：勾了 tasks ≠ 功能合格，必须有可复现运行证据。**本 change 的代码已实现但尚未跑过任何测试命令**，如实记入 §5。

### 1. 单元测试（刘帅华，写代码的人自己写）
| 项 | 内容 |
|---|---|
| 覆盖对象 | 前端纯口径函数：风险阈值分档（`riskClass`）、百分比/哈希/时间格式化（`formatPct` / `shortHash` / `formatTime`）、特征值展示（`formatFeature`）、模型下拉清单（`MODEL_OPTIONS`）、特征五维度分组（`FEATURE_GROUPS`）、解释条上限、默认分页 |
| 测试文件 | `frontend/src/__tests__/contract.test.js` |
| 用例数与结果 | **13 个 it / 30 条断言已写**；**尚未执行**（`frontend/node_modules` 未安装） |
| 复现命令 | `cd frontend && npm ci && npm run test:unit` |
| 正向用例 | `riskClass(0.83) === 'high'`、`riskClass(0.3) === 'mid'`、`riskClass(0.29) === 'low'`；`MODEL_OPTIONS` 长度 8 且含经典 6 + 神经 2、无重复；`FEATURE_GROUPS` 展平后恰 14 项且五维度分组齐全 |
| 异常 / 边界用例 | `riskClass(null)` / `riskClass(undefined)` → `'none'`（**不得当 0 处理**）；`formatTime('not-a-date')` 原样返回、`formatTime(null)` → `'—'`（不静默吞掉）；`shortHash('short')` 原样返回 |

> 只覆盖**不依赖 DOM 与 element-plus 的纯口径函数**，与「前端零测试」的旧状态相比是补齐，但**组件层（三态 / 错误码分发 / 字段映射）尚无测试**，见 §5。

### 2. 集成测试（大版本合并后，本 change 即为与后端的集成点）
| 项 | 内容 |
|---|---|
| 集成范围 | 前端 `src/api/request.js`（axios + `X-API-Key` 拦截器 + `code===0` 解包 + 错误码三态分发）↔ 后端四个接口 |
| 测试文件 | **尚无**（依赖联调，见 §3 与 §5） |
| 用例数与结果 | —— |
| 复现命令 | 起后端 `:8000` 后 `cd frontend && npm run dev`，按 `docs/frontend/pages.md` §2/§3/§4 逐页走 |
| 关键断言 | 40100 → 登提示而非空白页；40001 → 指参数名；40400 →「该提交不存在」；提交存在但无预测记录 → `code=0` + null 字段 →「尚未预测」（不用 0.0 冒充） |

### 3. 验收测试（交付时）
| 项 | 内容 |
|---|---|
| 验收依据 | `specs/frontend-pages/spec.md` 的 SHALL/MUST 与 Scenario + `docs/frontend/acceptance.md` F1–F6 |
| 用例数与结果 | 主链路演示 API-01~04 + 三页面走查，尚未执行 |
| 复现命令 / 步骤 | `docs/repo/demo-script-sprint1.md`（需先起后端） |
| 证据归档 | 联调记录拟入 `docs/frontend/frontend-integration-log.md`（tasks 4.2，未建） |

### 4. 非功能验证
| 维度 | 是否触及 | 证据 |
|---|---|---|
| 性能 | 否 | 由后端接口层实测（`backend/scripts/evidence/perf-real-2026-09-20.md`） |
| 安全 | 是 | `X-API-Key` 只走 `.env.local` 不入库；`request.js` 统一注入；令牌缺失由后端返 40100 |
| 可靠 | 是 | 数据点 < 2 不画折线（空数据不是错误）；接口空列表不当作异常 |
| 易用 | 是 | 三页面三态（加载中 / 空 / 错误）+ `explanation` 为空数组时显示「该模型未提供特征解释」并保留特征值区域 |

### 5. 已知缺口与后续计划（**本 change 的真实状态，不粉饰**）
| 缺口 | 原因 | 归属 | 计划时间 |
|---|---|---|---|
| 13 条单测**未执行** | 本机 `frontend/node_modules` 未安装 | 刘帅华 | Sprint 1 收口前 |
| **未过 lint / build 实跑** | 同上 | 刘帅华 | Sprint 1 收口前 |
| **未与后端联调**，联调记录文件未建 | 依赖后端起服务 + tasks 4.1/4.2 未做 | 刘帅华 | Sprint 1 收口前 |
| 组件层测试为零（三态、错误码分发、字段映射无自动化） | 组件测试需先跑通 vitest + 组件库环境 | 刘帅华 | Sprint 2 |
| 无 `vitest.config.js`，测试入口配置散落在 `package.json` | 脚手架未配测试框架 | 刘帅华 | Sprint 1 |

> 因此 tasks 3.1–3.3 的状态口径是「**已实现**」而非「**已验收**」：联调与测试命令跑通前，不得在周报记为完成。
