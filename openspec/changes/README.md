# 活跃 change 核对状态

活跃目录表示**尚未归档**，不代表本次设计仍要实施，也不代表勾选项有当前证据。2026-11 文档重组后，旧 `docs/backend/` 等路径已改为现行导航入口；正文里残留的“契约三 §4”“旧三页”等章节号是历史说明，**不能据此找到新文档中的同一节**。复审时从 `docs/README.md` 进入对应接口、库表或页面文件，并按当前提交重新取证。

| change | 与当前 `docs/overview.md` 的关系 | 归档前动作 |
|---|---|---|
| `default-model-resolution` | 含已删除的 `runtime_setting.champion_model`，与当前 `version_key` 缺省规则冲突 | 作者提出撤销/重写 delta，不得直接 apply |
| `delivery-model-allowlist` | 旧三模型在线限制已被 expert 八模型交付口径取代 | 核对权重实测后以“被取代”结案，不能再把三项写回活规格 |
| `backend-mysql-schema-sql` | 提案与 delta 仍规定旧四表，当前 ORM/SQL 为五表 | 核实原 PR 是否已完成历史验收；归档时保留原证据，不把旧四表 delta 应用到现行活规格 |
| `realtime-pr-prediction` | PR 入口已从当前范围下线 | 核对未遗留运行路由后以“范围取消”结案 |
| `feedback-observability`、`quality-loop` | 反馈、质量独立页及相关接口已下线 | 分开核对仍有效的可观测能力；不得整体当作现行功能归档 |
| `ops-hardening` | 仍要求已删除的 `runtime_setting`、`/api/config` 和 webhook | 将已下线 delta 撤销，若需新的运维能力另提 change |
| `feature-addons-sprint3` | G1-3/G1-4 已移出；G1-2 delta 仍依赖已删除的 `commit_label` | 仅保留 G1-1/G1-2 的提案范围，先裁定修复提交来源与接口，再更新 delta |
| `public-dataset-quality` | 提案仍将新数据对齐已删除的 `commit_label` | 先改为现行五表及离线标签产物口径，再实施加载器 |
| `startup-baseline-sync` | 当前保留启动同步和状态轮询，PR 同步/SSE 已下线 | 收缩 delta 到现行 `docs/api/sync.md`，再验收 |
| `lean-jit-prediction` | “只由实时同步入库”与当前测试集离线初始化并存 | 区分运行时同步与测试数据导入，再核对未完成项 |
| `frontend-integration` | 记录旧三页的历史联调；当前为四页 | 在 `docs/common/integration-log.md` 补现行四页截图与异常场景 |
| `pr-review-automation-prototype` | 旧工作流已删除 | 标为历史原型；不要把它算作当前自动审阅能力 |
| `model-training-scope-8`、`online-eight-model-selection`、`test-set-eval-figures` | 八分类器、expert 在线八模型、五表图集与当前设计方向一致 | 补未勾选任务、真实权重/数据库/页面证据后再归档 |
| `neon-test-baseline` | 已新增测试脚本、取证清单和执行记录；PR #221 已合入。运行时十一端点和部分系统用例已有作者证据，但 25 模型矩阵仍为 23/25 | 复核并发与强杀恢复用例的有效性；补 124 条现场判定、系统/验收正式签字文档及 #222 复测，再按 `tasks.md` 逐项结案 |

其他 change 也必须逐条核对 Requirement 标题、实际代码与证据路径。未复核不能直接勾选或归档。历史归档目录保留当时的路径和结论，不回写历史。

## 2026-11-13 结构与归档复核

旧任务要求见 [`todo/sober-2-OpenSpec归档.md`](../../todo/sober-2-OpenSpec归档.md)：归档前要确认活规格、代码、文档和测试证据一致，已勾选任务可复现。旧任务编号只作历史验收线索；现行文件格式仍以 [`../TASKS_TEMPLATE.md`](../TASKS_TEMPLATE.md) 与 [`../config.yaml`](../config.yaml) 为准。

- 已核对 25 个活跃 change：`proposal.md` 均含 Why / What Changes / Capabilities / Impact，`tasks.md` 均有四项文件头和末尾「测试与验证」五节。`neon-test-baseline` 第 2 章的任务已按 2.1–2.8 顺序重排，4.2 的验收语句已改为「未执行项不写通过」。
- 活跃 delta 中 9 条 `MODIFIED` Requirement 的标题均能在对应活规格中精确找到，当前没有同一 capability、同一标题被多个活跃 change 同时 `MODIFIED` 的情况。这只是静态标题检查，不能证明几个 change 的语义互不冲突。
- 活规格 `db-schema`、`environment`、`predict-api` 的三个已删除路径已改成仓库现有运行说明与实际默认模型目录。`data_model/data/` 和 `data_model/preparation/reports/` 是运行时生成目录，干净 clone 中不存在时不得当成已交付证据。
- `architecture-refactor`、`feedback-observability`、`frontend-redesign`、`ops-hardening`、`quality-loop` 虽然任务已全勾选，仍须逐项核对当前代码与证据。尤其反馈/质量页面和部分运维接口已下线，不能将旧 delta 直接应用到活规格；本次没有凭勾选状态自动归档。
- `backend-mysql-schema-sql`、`model-training-scope-8` 等活跃 change 仍含 `backend/README.md`、`data_model/ENVIRONMENT.md` 等历史交付路径。它们是待复核的旧任务证据，不等于这些文件当前存在。负责人须提供现行可打开的证据链接或在结案时明确说明被取代的部分。

本节是结构与路径复核，不是 25 个 change 的产品验收结论。OpenSpec CLI 在本次本机环境中不可用；`openspec validate --specs --strict` 和逐 change 校验仍需在装有 CLI 的环境补跑，并把输出附在后续归档 PR。
