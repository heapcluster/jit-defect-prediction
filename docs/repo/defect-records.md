# 缺陷处置记录（仓库侧索引）

> 权威在 **GitHub Issue**（`.github/ISSUE_TEMPLATE/bug.md` 五项字段）；本文件是**仓库侧索引**，供周报 / 结题材料快速取用，不另造第三套缺陷清单。
> 规则见 `repo/defect-management.md`：缺陷须记**现象 / 复现条件 / 优先级 / 处理状态 / 关联提交或 change** 五项。
> 快照：2026-10-24 ｜ 维护：蒋励（SM）｜ 每条均附**仓库内可核验证据**，无证据不登记。

## 1. 已闭环

| 编号 | 现象 | 复现条件 | 优先级 | 处理状态 | 关联提交 / change | 仓库证据 |
|---|---|---|---|---|---|---|
| D-01（#46） | 用标准 `pickle.load` 加载 `lr_v1.pkl` / `rf_v1.pkl` 报 `invalid load key`，模型起不来 | `pickle.load(open("data_model/models/lr_v1.pkl","rb"))` | P1 | ✅ 已修复 | change `model-training-and-delivery` | `backend/app/model_registry.py`（统一 `joblib.load` + 特征数自检）；`backend/tests/test_model_registry.py::test_wrong_feature_count_skipped` |
| D-02（#50） | `explain()` 对线性模型重复折算 `scaler.scale_`、对随机森林遇 shap 三维数组，解释链失效 | 对 `Pipeline(StandardScaler→LogisticRegression)` 与 `RandomForestClassifier` 调 `explain()` | P1 | ✅ 已修复 | PR #52 已合入 main | `backend/app/model_registry.py` 解释分支；`test_model_registry.py::test_explain_linear_pipeline_shap_additivity`（残差归零断言） |
| D-03（#56） | 分支保护设置读不到（API 404 / 权限不足），且缺一份可自助核验说明，他人无法自查 | 无令牌调 GitHub branch-protection API | P2 | ✅ 已修复 | PR #57 已合入 main | `infra/README.md`（核验步骤与命令） |
| D-04（#33 前端脚手架） | 前端无工程基线，三页面无处落地 | `ls frontend/` 只有 `README.md`，无 `src/`、无 `package.json` | P1 | ✅ 已修复 | PR #33 已合入 main | `frontend/package.json`、`vite.config.js`（`/api` 代理） |
| D-09（2026-10-13 登记，2026-10-24 闭环） | **大写 `commit_hash` 通过校验却查不到**：`_check_hash` 先 `lower()` 放行大写，详情查询按原样匹配库内小写哈希 → 返回 `40400`「该提交不存在」，对用户是误导性提示 | `GET /api/commits/<40 位大写十六进制>`（SQLite 等大小写敏感 collation 必现；MySQL 8 默认 `utf8mb4_0900_ai_ci` 可能复现不到，见 change design D2） | P3 | ✅ 已修复（PR #101 合入 main `c011463`；change 已归档 `2026-10-24-backend-hash-case-normalization`） | PR #101；change `backend-hash-case-normalization`：`_check_hash()` 改为「校验并返回小写哈希」，`commit_detail()` 用返回值查四张表；`POST /api/predict` 原本已归一化，未改 | `backend/tests/test_security_boundaries.py::test_detail_uppercase_hash_is_normalized_to_the_stored_commit`、`::test_detail_unknown_hash_stays_40400_after_normalization`、`::test_detail_hash_boundaries_return_40001`（含 `G`×40 参数）；`backend/tests/test_predict_api.py::test_predict_uppercase_hash_uses_normalized_key`（大小写同键只留一行）；cwd=backend `python -m pytest tests/` → **145 passed**（main `0773a49`，junitxml 计数）。遗留：Open Question 1（契约三 §2 是否补大小写口径）仍待 PO 裁定，裁定若为「补」则另立 change，不影响本行闭环 |
| D-12（飞书侧，2026-10-13 登记） | 飞书《产品设计文档》与《产品需求文档》的**变更日志表格被砸碎**：表体各行（11 / 13 行 × 4 格）降级为表格外的散落段落，文档中不再渲染为表格 | 用 `docs +update --command block_replace` 回写整表时，`--content` 片段**缺少 `<table …>` 开标签**（从 `IndexOf(<id>)` 起切而非从 `<table id="` 起切）→ CLI 把 `<tr>/<td>` 当作普通内容降级为独立 `<p>` | P1 | ✅ 已修复（2026-10-13） | 无代码变更（**飞书交付物运维缺陷**，非产品代码路径） | 修复后两份文档变更日志恢复为完整表格：设计文档 `table id=doxcnEBMCo3YfonccdzPFlLo44g`（12 行，末行 v0.10）、PRD `table id=doxcni0qxT1aXxePSfUGbSufy3f`（14 行，末行 v1.2）；均为 `<colgroup>+<thead>+<tbody>` 完整结构，垃圾文本残留 0。重建方法 = 从改坏前的文档快照取完整 `<table>…</table>`，`block_replace` 首个残留段落，再批量 `block_delete` 其余散落段落 |

## 2. 处理中 / 待提案

| 编号 | 现象 | 复现条件 | 优先级 | 处理状态 | 关联提交 / change | 仓库证据 |
|---|---|---|---|---|---|---|
| D-05（#37） | 契约三规定风险列表按 `risk_score` 降序；在 LOC 工作量代理下三个模型 `P_norm` 为负（-0.67 / -0.25 / -0.42），**不如随机排序**（旧仓库实测，已随 2026-10-14 换库清理） | 跑 `pipelines/expert/calibrate.py` 看第四节 | P1 | 🔶 待契约变更提案 | 证据已产：`pipelines/expert/reports/calibration_threshold.md`（同预算召回 +31.72 pp，旧仓库实测） | `docs/model/model-line-plan.md` §4.3 |
| D-06（#38） | `p >= 0.50` 被判高风险的提交里真实缺陷率仅 **29.6%**（Isotonic 校准后 29.1%），阈值语义与数值含义不符，会误导评审员（旧仓库实测，已随换库清理） | 同上报告第三节 | P1 | 🔶 待契约变更提案 | 同上 | `docs/model/model-line-plan.md` §4.4 |
| D-07（#59） | A2-4 验收判据方向相反：PRD「正样本比例落在 40%–60% 之外时告警」vs `data-pipeline.md`「落在 40%–60% 就先查打标逻辑」 | 对读 PRD 与 `docs/model/data-pipeline.md` 第 6 节 | P2 | 🔶 仓库侧稿已出，待贴飞书 | `docs/model/data-pipeline.md` §6（原 a2-4-correction.md 已并入） | Issue #59（2026-10-06 登记） |
| D-08（#60） | 用户故事与 OpenSpec 未逐条挂接（核心 22/27 未封口），看板「规格变更或任务」列点不回去 | 打开看板看该列 | P1 | 🔶 进行中 | `docs/repo/user-story-traceability.md`（Epic G 已拆分：G1-1/G1-2→`feature-addons-sprint3`、G1-3→`public-dataset-quality`、G1-4→`semantic-feature-mainline`） | Sprint 1 收口前置 |
| D-10（2026-10-13 新登记） | 前端三页面已实现但**未过 lint / build 实跑**（`frontend/node_modules` 未安装），也无联调记录 | `cd frontend && npm ci && npm run lint && npm run build` | P2 | 🔶 新登记，属 Sprint 1 验收前置 | change `frontend-integration` tasks 4.1–4.3 | `openspec/changes/frontend-integration/tasks.md` |
| D-11（#50 残留） | Issue #50 的「复现条件」「优先级」两栏补齐情况待确认（代码已修，Issue 字段未闭环） | 打开 Issue #50 | P3 | 🔶 待确认 | PR #52 | `docs/repo/catchup-ledger.md` L1 |
| D-13（2026-10-24 登记，蒋励交办） | **main 上 e2e 线训练/报告入口不可运行**：`pipelines/e2e/report.py` 从 `.metrics` 导入 `cumulative_curve`，而 `pipelines/e2e/metrics.py` 没有该函数 → 训练前 ImportError，e2e 线无法出报告 | 在具备 `data_model/environment.yml` 依赖的环境中，`cd data_model && python -c "import pipelines.e2e.train"` → `ImportError: cannot import name 'cumulative_curve' from 'pipelines.e2e.metrics'`（main `0773a49` 已复现） | P1 | 🔧 修复在 PR #88 当前 head `c0649cb`，CI 已绿、审阅已通过；**分支与 main 仍有 `e2e/report.py` 冲突，合入前 main 仍有缺陷**，合入后再迁 §1 | PR #88 / change `model-training-scope-8` | `data_model/tests/test_e2e_effort_curve.py`（与 fused 逐点一致）；[PR #88](https://github.com/heapcluster/jit-defect-prediction/pull/88) |
| D-14（2026-10-24 新登记；D-13 已由 PR #106 占用） | **交付清单三模型「可在线切换」与性能靶子 p95<500ms 冲突**：`POST /api/predict` 显式传 `model_name=rf_v1` 时 p50=653.0 / p95=713.8 / p99=751.0 / max=1638.6 ms，**p95 超靶子 43%**；不传 `model_name` 的默认路径（版本序最新 = `xgb_v1`）p95=15.5ms、`lr_v1` p95=9.0ms 均达标。即达标与否取决于调用方选哪个模型，而契约三 §4 把三个都列为可切换枚举 | 单模型 `MODEL_DIR`（目录只含 `rf_v1.pkl` + 声明它的 `feature_order.txt`）起真 uvicorn，`python scripts/perf_loop.py --n 100` 打 `POST /api/predict`（SQLite 库、真权重、真 HTTP）；2026-10-24 实测，非函数级探测 | P1 | 🔧 已裁定 ③（2026-10-24，蒋励/模型线；待苏哲勋（契约/infra）共签后转 ✅）：**优化 rf 在线推理，不改契约三 §4 枚举、不改 500ms 靶子**。不选 ① 是不愿缩小已承诺的可切换能力；不选 ② 是按模型分档等于靶子随实现漂移。根因已实测（`docs/model/evidence/rf-shap-2026-10-24.md`）：p95 713.8ms 里 `predict_proba` 只占 53–86ms，`shap.TreeExplainer.shap_values` 单次 782ms，explainer 已缓存（非构造开销），慢在模型体量——rf_v1.pkl 279.4MB、300 棵、平均深 34.4、**366 万节点**、`max_depth=None`。做法：重训收敛 rf 规模（收紧 `max_depth` / `min_samples_leaf`，目标节点数降一个量级），验收 **rf p95 < 500ms 且 AUC 相对现状下降 ≤ 0.01**；未达标即自动降级为 ①（rf 移出 `[models]`、留 `[evaluated]`，同步契约三 §4 枚举与 `specs/model-coverage` R6，走 change） | 证据 `backend/scripts/evidence/perf-2026-10-24.md`（PR #107）；先前函数级旁证 `backend/scripts/evidence/on-demand-commit-2026-10-23.md`（rf_v1 五次 605–947ms，当时已提示冲突） | `docs/design/non-functional.md` §2 与 D2 验证章节 |
| D-15（#103，2026-10-24 登记） | **TabNet 权重跨机器分发后不可回读**：本地工作目录的 `tabnet_v1.pkl` 是 `pipelines.expert.model.TabNetWithEarlyStop`，旧交付包同名文件却指向 `__main__.TabNetWithEarlyStop`；“8/8 本地已验证”不能在收包方复现 | 从 `expert_models_20261021.zip` 解压旧权重，在干净进程中 `joblib.load`；该文件 300,421 B、内层类为 `__main__`，与新包内 300,437 B、md5 `201a002b78c61a9589bec9b14496533c` 的权重不同 | P1 | 🔧 已重打 `expert_models_20261024.zip`；校验脚本、md5 清单在 PR #88，**待 PR 合入及收包方复核后再判闭环**（Issue #103 已关闭不等于交付验收完成） | Issue #103；PR #88 `c0649cb`；PR #98（仅评估，不扩大在线三模型清单） | [Issue #103](https://github.com/heapcluster/jit-defect-prediction/issues/103)；PR #88 的 `data_model/pipelines/verify_all_weights.py`、`models/manifest.txt`、`reports/weight_manifest_2026-10-24.md`（待合入后可在 main 点开） |

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
