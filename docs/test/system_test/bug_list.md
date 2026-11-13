# Bug 清单

> 依据：[`../../common/test-assessment-guide.md`](../../common/test-assessment-guide.md) §4.1 缺陷管理要求、§4.2「Bug 发现与记录」、§7 红线。
>
> **状态**：字段已按课程要求补齐；**当前计入 4 条可追溯缺陷，距「≥8 个得满分」还差 4 条**。另有 5 条有证据的候选观察列于 §3，**未经人工确认可复现前不计入个数**。严禁编造 Bug 或伪造截图（红线：数据造假该类型计 0 分；无法复现每个扣 2 分）。
>
> 权威动态状态以 **GitHub Issues / 飞书缺陷看板** 为唯一真源；按仓库根 `README.md` 口径，仓库不另存动态记录副本，本表只登记可核验的现象与证据链接。来源标注统一写「待核」——条目原始来源无法确认时不得倒填成 `[手写]`（AI-R1）。

## 1 · 已登记缺陷

| Bug ID | 标题 | 严重级别 | 复现步骤 | 预期结果 | 实际结果 | 截图 / 证据 | 状态 | 来源 | 闭环（回归验证） |
|---|---|---|---|---|---|---|---|---|---|
| #222 | `tabnet_semantic_v1` / `tabnet_fused_v1` 权重绑定 CUDA，CPU 加载抛 `RuntimeError` | 严重 | 在 CPU 机器对有特征落库的提交执行 `POST /api/predict`，`model_name` 分别取这两个模型 | 正常返回 0~1 风险分，或给出明确降级文案 | `Attempting to deserialize object on a CUDA device`，模型不可用；25 模型在线矩阵为 23/25 | `backend/scripts/evidence/2026-11-12-online-25.md`（逐模型矩阵）；暂无人工采集截图 | 待修复 | 待核 | 未闭环：修权重后跑 `online_models_matrix.py` 达 25/25 并回归 |
| #217 | semantic 语义表 / e2e 文本表未按约定布局生成 | 严重 | 干净检出后分别调用 semantic / fused / e2e 预测 | 补齐全套产物后 25 模型均可在线预测 | 返回「该提交暂无预计算语义向量」等降级；补齐两张输入表后 23/25 可用 | `backend/scripts/evidence/2026-11-12-online-25.md`；[`../integration_test/report.md`](../integration_test/report.md) §8 | 待处理（原 #218 已合并） | 待核 | 未闭环：干净检出复现 + 补齐生成步骤后回归 |
| #219 | `backend/Dockerfile` 未装 `transformers`，容器内 e2e 必然降级 | 一般 | 用 `docker-compose` 构建后端镜像后调用 e2e 预测 | 容器行为与本机一致 | 缺依赖导致 e2e 降级 | [`../integration_test/endpoint_inventory.md`](../integration_test/endpoint_inventory.md) §3.1；**容器构建日志与截图待补** | 待处理 | 待核 | 未闭环：容器构建实测并留存日志截图 |
| #220 | 接口文档与实现 6 处口径偏差（D-02~D-07） | 轻微 | 逐条对照 `docs/api/*.md` 与运行时 `/openapi.json` / 实际响应 | 文档与实现一致 | 错误码语义、时间格式、参数描述等 6 处不符；其中 D-06 已实测确认 | [`../integration_test/endpoint_inventory.md`](../integration_test/endpoint_inventory.md) §3；[`../integration_test/report.md`](../integration_test/report.md) §6 | 待裁定 | 待核 | 未闭环：逐条裁定「改文档 / 改代码」并回归 |

**级别分布**：严重 2 / 一般 1 / 轻微 1 / 致命 0。课程要求致命与严重缺陷必须全部修复并回归验证通过，故 #222、#217 会直接阻断验收通过，见 [`../acceptance_test/defect_residual.md`](../acceptance_test/defect_residual.md)。

## 2 · 字段完整性与扣分风险

| 课程要求字段 | 本表状态 |
|---|---|
| Bug ID / 标题 / 严重级别 / 复现步骤 / 预期结果 / 实际结果 / 状态 / 来源 | 4 条均已补齐 |
| 截图 | **缺**：#222、#217、#219 现有的是脚本证据文件与日志说明，不是人工采集截图；课程「Bug 描述规范（含复现步骤、截图）加 2 分」当前不满足 |
| 复现步骤经人工验证 | **待办**：#219 的容器路径未实跑，#220 需逐条裁定；未经人工验证不得计入 |
| 跟踪到关闭形成闭环 | **未闭环**：4 条全部处于待修复 / 待处理，无关闭记录 |
| 数量 ≥8 | **不满足**（当前 4 条） |

## 3 · 候选观察（有证据，未计入缺陷数）

以下现象有真实证据，但**是否构成 Bug、级别如何、能否稳定复现须由人工逐条确认**；确认前不计入 §1 个数，确认后须补复现步骤、截图与 Issue 编号。

| # | 观察 | 证据 | 待人工确认点 |
|---|---|---|---|
| C-01 | 10 并发 × 10 请求时 `POST /api/predict` p95 = 694.0ms，超出 500ms 判据（错误率仍 0%） | `backend/scripts/evidence/2026-11-13-load-test.md`；[`performance/performance_report.md`](performance/performance_report.md) §2.1 | 波动原因未定位，是否稳定复现；属性能缺陷还是同机资源争用 |
| C-02 | `sync/status.started_at` 输出 `2026-11-12T09:04:02.303942`（无 `Z`），与规格「时间统一 UTC + `Z`」不符（D-06） | [`../integration_test/report.md`](../integration_test/report.md) §6 | 按文档口径修正还是修改实现 |
| C-03 | `POST /api/predict` 传多余字段仍返回 200（Pydantic 忽略），与 `docs/api/predict.md`「非法请求体 40001」不符（D-03） | 同上 §6 | 是否加 `extra="forbid"`；已并入 #220 还是单列 |
| C-04 | 规格 `openspec/specs/nfr-evidence/spec.md` 要求模型缺失返回 `50000`，实现统一收敛为 `40001` 明确文案 | `backend/scripts/evidence/2026-11-12-security.md` §规格偏差 | 规格订正或代码回改 |
| C-05 | `openspec/specs/` 下 `feedback`、`observability`、`ops`、`quality`、`ui` 五个能力目录无 `spec.md`，影响验收逐 Scenario 对照 | [`../integration_test/endpoint_inventory.md`](../integration_test/endpoint_inventory.md) §3.1 补充 | 属规格交付缺口，是否计入缺陷 |

已确认**不成立**的观察（D-01「`features` 条件返回」、语义表「路径写错」、「e2e 无生成脚本」等）复核结论已落在对应 Issue，**不重复登记**（红线：Bug 报告无法复现每个扣 2 分）。

## 4 · 未闭合项与闭环计划

| 项 | 要求 | 处置与完成判据 | 状态 |
|---|---|---|---|
| 复现步骤验证与人工采集截图 | 4 条 + 候选观察 | 在系统测试窗口逐条实跑、采集截图，缺项不得计入「Bug 描述规范」加分 | 未开始 |
| 补齐 ≥4 条真实可复现缺陷 | ≥8 条拿满该维度 | 各模块作者如实登记；如无新缺陷保持 4 条并申报扣分，**不得凑数** | 未开始 |
| #222 / #217 严重缺陷修复与回归 | 验收前置条件 | 模型线修复后跑 `online_models_matrix.py` 至 25/25、干净检出复现，附回归记录 | 未开始 |
| #219 / #220 与候选观察裁定 | 契约与部署一致性 | 逐条给出「改文档 / 改代码 / 不成立」，同步 `docs/api/` 与 `/openapi.json` | 未开始 |
| 缺陷关闭记录 | Bug 闭环 | 状态置已修复、附关联提交与回归用例结果、Issue 关闭 | 0 / 4 关闭 |
| 影响评估与修复计划确认 | 验收通过标准依据 | 见 [`../acceptance_test/defect_residual.md`](../acceptance_test/defect_residual.md) §1；本轮为 AI 代写草案，须人工复核（不要求逐份签字） | 待复核 |
| 单元测试代码整改分派 | §2.1 / §2.2 / §7 红线 | 已创建 [Issue #233](https://github.com/heapcluster/jit-defect-prediction/issues/233) 并指派 `s1mple-less`；#222 / #225 / #226 / #227 / #228 / #230 已追加测试侧反馈评论 | 已分派，待负责人处理 |

> #233 是测试体系整改单（依赖隔离、弱断言、来源注释），**不计入本表产品缺陷数量**；按分工由蛋神（DS-4 单元测试）处理，测试侧不修改代码本体。

> 本清单与 [`../acceptance_test/defect_residual.md`](../acceptance_test/defect_residual.md)、[`../summary_report.md`](summary_report.md) §3 口径一致；按红线，未修复项不得写成已闭环。
