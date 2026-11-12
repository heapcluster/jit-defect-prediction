# TODO 总览（任务分配与追踪）

> 依据：`docs/common/project-requirements.md`、`docs/common/test-assessment-guide.md`，以及 `openspec/config.yaml` 的契约与目录约定。
> 本目录只做"按人、按能力分配未完成任务"，每份文档统一包含：一句话任务 / 为什么做 / 你要做什么 / 交付物 / 什么算合格 / 不要做什么 / 依赖协作。
> 编号规则：按人前缀 + 序号，**每人序号从 1 连续递增、不跳号**。
> 状态边界：本目录只是临时任务拆解；负责人、截止与完成状态以飞书工作周报和项目看板为准。

## 评分结构（项目总分 100）

| 维度 | 分值 | 关联任务 |
|---|---:|---|
| 产品价值与范围控制（需求分析） | 10 | 蛋神的蛋-1、lsh-1 |
| 生成式软件开发（工具使用） | 10 | sober-1（OpenSpec 归档与一致性） |
| 软件开发过程实践 | 40 | 蛋神的蛋-1、sober-1、lsh-1、lsh-2、neon-5 |
| 软件测试实践 | 40 | 蛋神的蛋-2、neon-1/2/3、sober-1 |

## 任务分配

| 编号 | 负责人 | 任务 | 优先级 | 状态（2026-11-12） |
|---|---|---|---|---|
| 蛋神的蛋-1 | 蛋神的蛋 | 在线预测能力对齐（25 模型全部接入 + 详情/进度 bug） | P1 | 代码已合入（PR #216 / `afdee84`），**产物侧未闭环**：#217 #218 未修复前 semantic/fused/e2e 无法在干净检出下预测 |
| 蛋神的蛋-2 | 蛋神的蛋 | 单元测试（三例 + 覆盖率，自测通过即可） | P0 | 测试代码已补（PR #215/#216），覆盖率以 CI 报告为准（归档见 PR #212），待 sober 核对归档 |
| neon-1 | neon | 集成测试 | P0 | 清单与用例设计已交付；44 条用例未执行（无后端运行时） |
| neon-2 | neon | 系统测试 | P0 | 未执行（环境阻断，见 `docs/common/neon-test-execution.md`） |
| neon-3 | neon | 验收测试 | P0 | 未执行（需真实环境演示 + 本人签字文档） |
| neon-4 | neon | 缺陷与 PR 管理 | P1 | 进行中：PR #216 已审阅合入并留痕，缺陷 #217~#220 已登记；飞书缺陷看板未建 |
| neon-5 | neon | 项目看板与周报 | P1 | 进行中：看板 / 周报在飞书维护，仓库侧只留索引 |
| sober-1 | sober | 测试文档（含 OpenSpec 规范化） | P0 | 未开始（依赖 neon-1/2/3 结果） |
| lsh-1 | lsh | 飞书《产品需求文档》维护与同步 | P1 | 未开始 |
| lsh-2 | lsh | 飞书《产品设计文档》维护与同步 | P1 | 未开始 |
| lsh-3 | lsh | 答辩 PPT 初稿（骨架 + 图 + 文字） | P1 | 未开始 |

> **状态口径**：本表的「状态」只反映仓库内可核对的证据（PR / 提交 / 文档）。任务是否算完成以飞书看板与负责人确认为准；未闭环项不写成已完成。

## 编号变更记录

- **2026-11-10 分工确认**：蛋神的蛋=全栈开发（25 模型接入 + bug）+ 单元测试；neon=集成/系统/验收测试 + 缺陷与 PR + 项目看板/周报；sober=测试文档（+ OpenSpec 规范化）；lsh=产品需求文档 + 产品设计文档 + 答辩 PPT 初稿。
- 每人编号从 1 连续：蛋神的蛋 1–2、neon 1–5、sober 1、lsh 1–3。
- 已完成的旧任务文档（S-1~S-4、DS-1、DS-2 等）已删除；公开数据集暂不做。
- **2026-11-12 合入同步**：PR #215（DS-1 容器化插件化 + DS-2 缺陷定位/修复参考 + 三线单测补齐，`2e1896a`）与 PR #216（25 模型在线预测接通 + 详情/进度两 bug + 单测 AI 标注，`afdee84`）已合入 main。据此更新蛋神的蛋-1/-2 状态；同时登记审阅发现的产物缺口 [#217](https://github.com/heapcluster/jit-defect-prediction/issues/217)、[#218](https://github.com/heapcluster/jit-defect-prediction/issues/218)、[#219](https://github.com/heapcluster/jit-defect-prediction/issues/219) 与接口口径偏差 [#220](https://github.com/heapcluster/jit-defect-prediction/issues/220)。

## 课程要求 vs 增强

- **核心必做（§1）**：数据采集/SZZ、Kamei 14 维 + 语义特征（可选）、≥2 类 ≥8 模型 + 两类指标 + 划分、预测与解释（缺陷概率 + 缺陷归因/解释）、风险列表与趋势看板、工程化（分支/评审/CI/CD/插件化）——**现有代码已符合**。
- **可选附加（§2）**：(1) 高亮可疑代码行（当前提交级着色，未做增强）；(2) 修复建议（已有 fix_references）；(3) 公开数据集（暂不做）；(4) 语义特征（已做）。
- **非功能需求（§3）**：至少 2 项——安全已实现（API Key），其余在系统测试中实测。

## 文档归属（飞书 vs 仓库）

> 飞书文档均在「想到什么取什么」文件夹（token `HDVdf3vbHlj1iUd00XrcNagpnWc`）下。

| 文档 | 位置 | 负责人 / 任务 |
|---|---|---|
| 工作周报（9 篇 docx：20260911～20261106） | 飞书 | neon（neon-5） |
| 讨论纪要（3 篇 docx：20260915 / 20261030 / 20261031） | 飞书 | neon |
| 项目看板（bitable `SilBbJZFPaDct1slrIVcN2Nonsc`） | 飞书 | neon（neon-5） |
| 产品需求文档（docx `PgG0dvODooN1clxgV65ctC6JnQg`） | 飞书 | lsh-1 |
| 产品设计文档（docx `YdgBdOjm5otdvxx6P8nceSY2n1f`） | 飞书 | lsh-2 |
| PPT-20261002（slides `HSUCsBp3wlqHQ1d7v5FcHFBonRd`） | 飞书 | lsh-3（初稿） |
| 软件开发与测试综合实训 项目要求 | 飞书 docx（只读参考） | — |
| 软件缺陷预测系统测试考核说明.md | 飞书 file（owner 非本组，待确认） | 待定 |
| 仓库契约：docs/api、docs/database、docs/model | 仓库 | 各线 |
| docs/common/project-requirements.md、test-assessment-guide.md | 仓库 | 公共（蒋励统稿） |

> 两文档边界：`lsh-1` 写「要做什么、用户怎么用」，`lsh-2` 写「系统怎么实现」；各自维护版本号与变更日志，不互相复制正文。

## 依赖关系

- `蛋神的蛋-2` → `sober-1`（单元测试文档依赖测试结果）
- `neon-1/2/3` → `sober-1`（集成/系统/验收文档）
- `neon-1/2/3` → `neon-5`（测试进展进看板与周报）
- `lsh-3` ← `neon-1/2/3`（PPT 初稿依赖测试结论）
- `lsh-1` ↔ `lsh-2`（两文档边界与口径对齐）

## 分配原则

- 蛋神的蛋：全栈开发 + 单元测试；neon：集成/系统/验收测试 + 缺陷与 PR + 项目看板/周报；sober：测试文档（+ OpenSpec 规范化）；lsh：产品需求文档、产品设计文档、答辩 PPT 初稿。
- 一份文档一个任务、一个负责人；`lsh-1` 与 `lsh-2` 按文档边界拆分。
- OpenSpec 的 tasks 勾选与规范化统一由 **sober** 负责，开发任务不写 openspec。

## 完成定义（DoD）

- 每项任务有交付物与可核对的验收标准。
- `openspec/changes/*/tasks.md` 勾选必须有证据支撑。
- 归档 change 后 `openspec/specs/` 与当前产品一致。

## 现状快照

- **已具备**：5 张表、11 个 API、25 模型（四线清单全部登记在线）、SZZ 时间序切分、Effort-aware 指标、四个前端页面、CI（四线全测 + build）、OpenSpec 体系、容器化与插件化（#215）、localization 与 fix_references（#215）、详情按 `model_name` 与列表对齐、同步进度全局化（#216）。
- **缺口**：
  - semantic/fused 在线默认路径失效（[#217](https://github.com/heapcluster/jit-defect-prediction/issues/217)）、e2e 缺文本表与生成脚本（[#218](https://github.com/heapcluster/jit-defect-prediction/issues/218)）——「25 模型可预测」当前只在作者环境成立。
  - 契约与部署未随 #216 同步（[#219](https://github.com/heapcluster/jit-defect-prediction/issues/219)）；接口文档 6 处偏差待裁定（[#220](https://github.com/heapcluster/jit-defect-prediction/issues/220)）。
  - 测试执行与证据：集成 44 条用例、系统与验收测试均未执行（无可用后端运行时）；系统测试计划/总结与验收方案/报告待 neon 本人撰写签字。
  - AI 来源标注已在测试文件补齐（#215/#216），Prompt 归档仍只有集成用例一份（`docs/common/ai-prompts/`）。
