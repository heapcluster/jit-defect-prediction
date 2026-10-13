# 缺陷处置记录（仓库侧索引）

> 权威在 **GitHub Issue**（`.github/ISSUE_TEMPLATE/bug.md` 五项字段）；本文件是**仓库侧索引**，供周报 / 结题材料快速取用，不另造第三套缺陷清单。
> 规则见 `repo/defect-management.md`：缺陷须记**现象 / 复现条件 / 优先级 / 处理状态 / 关联提交或 change** 五项。
> 快照：2026-10-13 ｜ 维护：蒋励（SM）｜ 每条均附**仓库内可核验证据**，无证据不登记。

## 1. 已闭环

| 编号 | 现象 | 复现条件 | 优先级 | 处理状态 | 关联提交 / change | 仓库证据 |
|---|---|---|---|---|---|---|
| D-01（#46） | 用标准 `pickle.load` 加载 `lr_v1.pkl` / `rf_v1.pkl` 报 `invalid load key`，模型起不来 | `pickle.load(open("data_model/models/lr_v1.pkl","rb"))` | P1 | ✅ 已修复 | change `model-training-and-delivery` | `backend/app/model_registry.py`（统一 `joblib.load` + 特征数自检）；`backend/tests/test_model_registry.py::test_wrong_feature_count_skipped` |
| D-02（#50） | `explain()` 对线性模型重复折算 `scaler.scale_`、对随机森林遇 shap 三维数组，解释链失效 | 对 `Pipeline(StandardScaler→LogisticRegression)` 与 `RandomForestClassifier` 调 `explain()` | P1 | ✅ 已修复 | PR #52 已合入 main | `backend/app/model_registry.py` 解释分支；`test_model_registry.py::test_explain_linear_pipeline_shap_additivity`（残差归零断言） |
| D-03（#56） | 分支保护设置读不到（API 404 / 权限不足），且缺一份可自助核验说明，他人无法自查 | 无令牌调 GitHub branch-protection API | P2 | ✅ 已修复 | PR #57 已合入 main | `infra/README.md`（核验步骤与命令） |
| D-04（#33 前端脚手架） | 前端无工程基线，三页面无处落地 | `ls frontend/` 只有 `README.md`，无 `src/`、无 `package.json` | P1 | ✅ 已修复 | PR #33 已合入 main | `frontend/package.json`、`vite.config.js`（`/api` 代理） |
| D-12（飞书侧，2026-10-13 登记） | 飞书《产品设计文档》与《产品需求文档》的**变更日志表格被砸碎**：表体各行（11 / 13 行 × 4 格）降级为表格外的散落段落，文档中不再渲染为表格 | 用 `docs +update --command block_replace` 回写整表时，`--content` 片段**缺少 `<table …>` 开标签**（从 `IndexOf(<id>)` 起切而非从 `<table id="` 起切）→ CLI 把 `<tr>/<td>` 当作普通内容降级为独立 `<p>` | P1 | ✅ 已修复（2026-10-13） | 无代码变更（**飞书交付物运维缺陷**，非产品代码路径） | 修复后两份文档变更日志恢复为完整表格：设计文档 `table id=doxcnEBMCo3YfonccdzPFlLo44g`（12 行，末行 v0.10）、PRD `table id=doxcni0qxT1aXxePSfUGbSufy3f`（14 行，末行 v1.2）；均为 `<colgroup>+<thead>+<tbody>` 完整结构，垃圾文本残留 0。重建方法 = 从改坏前的文档快照取完整 `<table>…</table>`，`block_replace` 首个残留段落，再批量 `block_delete` 其余散落段落 |

## 2. 处理中 / 待提案

| 编号 | 现象 | 复现条件 | 优先级 | 处理状态 | 关联提交 / change | 仓库证据 |
|---|---|---|---|---|---|---|
| D-05（#37） | 契约三规定风险列表按 `risk_score` 降序；在 LOC 工作量代理下三个模型 `P_norm` 为负（-0.67 / -0.25 / -0.42），**不如随机排序** | 跑 `data_model/09_calibration_threshold.py` 看第四节 | P1 | 🔶 待契约变更提案 | 证据已产：`data_model/reports/calibration_threshold.md`（同预算召回 +31.72 pp） | `docs/model/training-eval.md` §4 |
| D-06（#38） | `p >= 0.50` 被判高风险的提交里真实缺陷率仅 **29.6%**（Isotonic 校准后 29.1%），阈值语义与数值含义不符，会误导评审员 | 同上报告第三节 | P1 | 🔶 待契约变更提案 | 同上 | `docs/model/training-eval.md` §5 |
| D-07（#59） | A2-4 验收判据方向相反：PRD「正样本比例落在 40%–60% 之外时告警」vs `data-pipeline.md`「落在 40%–60% 就先查打标逻辑」 | 对读 PRD 与 `docs/model/data-pipeline.md` 第 6 节 | P2 | 🔶 仓库侧稿已出，待贴飞书 | `docs/model/a2-4-correction.md` | Issue #59（2026-10-06 登记） |
| D-08（#60） | 用户故事与 OpenSpec 未逐条挂接（核心 22/27 未封口），看板「规格变更或任务」列点不回去 | 打开看板看该列 | P1 | 🔶 进行中 | `docs/repo/user-story-traceability.md`（Epic G 已拆分：G1-1/G1-2→`feature-addons-sprint3`、G1-3→`public-dataset-quality`、G1-4→`semantic-feature-mainline`） | Sprint 1 收口前置 |
| D-09（2026-10-13 新登记） | **大写 `commit_hash` 通过校验却查不到**：`_check_hash` 先 `lower()` 放行大写，详情查询按原样匹配库内小写哈希 → 返回 `40400`「该提交不存在」，对用户是误导性提示 | `GET /api/commits/<40 位大写十六进制>` | P3 | 🔶 新登记，待 OpenSpec change（查询前统一 `lower()` 或校验阶段归一化） | 已用测试钉住当前行为：`backend/tests/test_security_boundaries.py::test_detail_uppercase_hash_passes_validation_but_not_found` | 87 passed 全绿套件内 |
| D-10（2026-10-13 新登记） | 前端三页面已实现但**未过 lint / build 实跑**（`frontend/node_modules` 未安装），也无联调记录 | `cd frontend && npm ci && npm run lint && npm run build` | P2 | 🔶 新登记，属 Sprint 1 验收前置 | change `frontend-integration` tasks 4.1–4.3 | `openspec/changes/frontend-integration/tasks.md` |
| D-11（#50 残留） | Issue #50 的「复现条件」「优先级」两栏补齐情况待确认（代码已修，Issue 字段未闭环） | 打开 Issue #50 | P3 | 🔶 待确认 | PR #52 | `docs/repo/catchup-ledger.md` L1 |

## 3. 暂不处置（有理由，不是遗漏）

| 编号 | 事项 | 理由 |
|---|---|---|
| N-01 | 8 个模型中 5 个仅作评估、不进 `[models]` 段 | 交付边界由 `specs/model-coverage` R6 规定，非缺陷 |
| N-02 | `mlp` 迭代上限内未收敛 | 已如实登记在 `data_model/reports/model_matrix.md`，指标按实际训练结果记录，不重跑调参 |
| N-03 | CI 未落地（`.github/workflows` 为空） | 属待办 E1，不是缺陷；已消除 `collaboration.md` §7 与 `engineering.md` §3 的口径矛盾 |

## 4. Sprint 3 结题导出口径

1. 在 GitHub 按标签 `defect` 导出 Issue 列表，与本表逐条核对（编号 / 状态 / 关联提交）。
2. 导出字段即 `defect-management.md` 五项：现象 / 复现条件 / 优先级 / 处理状态 / 关联提交或 change。
3. 本表新增条目须同步开 GitHub Issue，**不允许只落在本文件**（否则又是一处「写了却没地方可点」）。
