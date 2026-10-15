# public-dataset-quality — 任务清单

> 提案：`proposal.md` ｜ 设计决策：`design.md` ｜ 规格：`specs/public-dataset/spec.md`
> 负责人：model 蒋励 ｜ 创建：2026-10-13 ｜ 状态：进行中（Sprint 2 启动）
> 用户故事：C1-2（数据集加载）/ C1-3（数据质量治理）—— 回应课程附加功能 (3) 三条问题
> 统一格式见 `docs/common/openspec-task-template.md`；**本文件末的「测试与验证」为强制板块，缺失视为提案不完整。**

## 0. 阻塞前置：可下载性验证（第 1 号任务，不过则整体降级）
- [ ] 0.1 逐个验证候选公开 JIT 数据集的可下载性（网络、链接、体积、许可证），输出 `data_model/reports/public_dataset_probe.md`：候选清单 / 可达性 / 体积 / 许可证 / 字段完备性
- [ ] 0.2 **若全部不可达**：本 change 降级为「加载器 + 质量评价框架 + 用 Camel 数据自验」，并在 0.1 报告与周报中**如实写明「未能获取公开数据集及原因」**，**不虚构数据**
- [ ] 0.3 若部分可达：按「字段完备性优先、语种多样性优先」选定 1–2 个入change，其余记入候选清单备查

## 1. 加载器（蒋励）
- [ ] 1.1 新增 `data_model/20_load_public_dataset.py`：解析公开数据集为与契约一 `commit` / `commit_label` 对齐的记录；**缺必需字段报错终止，不产半成品**
- [ ] 1.2 字段映射表输出（公开数据集字段 ↔ 契约字段）；口径冲突显式登记，不静默对齐
- [ ] 1.3 元数据落盘：来源、许可证、获取日期、原始体积、抽样方法（若抽样）
- [ ] 1.4 落盘位置 `data_model/data/public/<name>/`；**不入库、不进交付链**

## 2. 三维度质量治理（蒋励，逐条回应课程 (3)）
- [ ] 2.1 **① 标签粒度**：标注每个数据集「有无缺陷类型」；有类型则保留类型字段并输出类型分布；无类型则元数据明确写「无缺陷类型」，**不伪造**
- [ ] 2.2 **② 语种分布**：统计「数据集 × 语言 × 提交数 × 占比」；含非 Java 项目（如 OpenStack/Python、Qt/C++）时明确标注为对「主要针对 Java」的回应证据
- [ ] 2.3 **③ 数据质量**：新增 `data_model/21_public_dataset_quality.py`，输出缺失率、重复率、字段一致性、时间序一致性四项指标 + 异常样本清单（可点回具体记录）
- [ ] 2.4 重复记录的「标签冲突」子项单列，**不静默去重保留其一**
- [ ] 2.5 产出 `data_model/reports/public_dataset_quality.md`

## 3. 变更文本统一表示（与语义特征线共用，蒋励）
- [ ] 3.1 公开数据集的代码变更统一表示为「变更文本」（文件路径 + 变更类型 + 增删行 + 提交信息首行），与 `semantic-feature-mainline` D3 同一套构造，保证两条线可对比
- [ ] 3.2 超模型上限按行截断并记录截断统计，不静默丢数据

## 4. 与 Camel 基线并列（蒋励）
- [ ] 4.1 确认 Camel 基线未被改动：`data_model/models/[models]` 段、契约三接口、契约二 14 项列名与顺序均无变化
- [ ] 4.2 任何基于公开数据集的结论**必须标注**「基于公开数据集 X，与 Camel 基线并列对照」，不得表述为替换了交付数据

## 5. 抽样纪律（蒋励）
- [ ] 5.1 数据集体积过大时按 `committed_at` **分层等距抽样**，禁随机；抽样方法、样本量、层级边界写入报告

## 5bis. 与文献数字对照（蒋励，可选目标）
- [ ] 5b.1 若获取到标准 benchmark（DeepJIT / CC2Vec 用过的项目），在同一评测口径下训练并评估，产出「本组结果 vs 文献报告值」对照表，标注文献出处
- [ ] 5b.2 对照表**必须标注口径差异**（工作量代理、划分方式、特征集、模型），口径不同不得直接并列数字
- [ ] 5b.3 未获取到标准 benchmark 时，报告中写明「未获取标准 benchmark，故不与文献数字对照」及原因，**不为凑对照而选用非标准数据集**

## 6. 范围与文档同步（蒋励统稿）
- [ ] 6.1 `docs/design/sprint0-scope.md` 边界表述改写：「公开数据集（可选）」→「已提升为承诺范围（Sprint 2）」
- [ ] 6.2 `feature-addons-sprint3` 的 G1-3 条目移出，proposal/tasks/design 同步注明「已由 `public-dataset-quality` 顶替」，不留双入口
- [ ] 6.3 `docs/design/addons.md` §3 G1-3 定位改写；`docs/model/data-pipeline.md` 增补公开数据集加载步骤
- [ ] 6.4 `docs/model/methodology-references.md` 补「公开数据集与质量评价」文献依据行

## 测试与验证（强制板块）

> 分层口径见 `docs/common/test-strategy.md`；模板见 `docs/common/openspec-task-template.md`。
> 铁律：勾了 tasks ≠ 功能合格，必须有可复现命令与证据路径。

### 1. 单元测试（蒋励，写代码的人自己写）
| 项 | 内容 |
|---|---|
| 覆盖对象 | 字段映射（不一致时显式报冲突）、必需字段校验（缺失即终止）、重复与标签冲突检测、时间序一致性检测、分层抽样的边界与守恒 |
| 测试文件 | `data_model/tests/test_public_dataset.py` |
| 用例数与结果 | 计划 ≥ 18 条 |
| 复现命令 | `cd data_model && python -m pytest tests/test_public_dataset.py -q` |
| 正向用例 | 完整公开数据集 → 记录数与源一致、字段映射表正确、元数据含来源/许可证/日期 |
| 异常 / 边界用例 | 缺 `commit_hash` → 报错终止且**不产出文件**；同一 `commit_hash` 标签冲突 → 计入「标签冲突」子项而非静默去重；`committed_at` 无法解析 → 计入时间序不一致项而非静默剔除；分层抽样后各层样本数守恒 |

### 2. 集成测试（大版本合并后）
| 项 | 内容 |
|---|---|
| 集成范围 | 公开数据集 → 变更文本构造 → 与 Camel 数据并列的特征/样本格式一致性 |
| 测试文件 | `data_model/tests/test_public_pipeline.py`（计划） |
| 用例数与结果 | 计划 ≥ 6 条 |
| 复现命令 | `cd data_model && python -m pytest tests/test_public_pipeline.py -q` |
| 关键断言 | 公开数据集与 Camel 样本集**列名与顺序一致**（除新增元数据列）；同一切分函数可复用；契约二 14 项未被改动 |

### 3. 验收测试（交付时，按 spec 的 SHALL/MUST 逐条走）
| 项 | 内容 |
|---|---|
| 验收依据 | `specs/public-dataset/spec.md` 的 7 条 Requirement 与全部 Scenario |
| 用例数与结果 | 计划 7 条（每条 Requirement 至少 1 条） |
| 复现命令 / 步骤 | 跑 20 → 21，比对 `data_model/reports/public_dataset_quality.md` 四项指标与异常清单 |
| 证据归档 | `data_model/reports/public_dataset_probe.md`、`public_dataset_quality.md` |

### 4. 非功能验证
| 维度 | 是否触及 | 证据 |
|---|---|---|
| 性能 | 是 | 加载与质量报告的耗时、数据集体积、抽样比例记录 |
| 安全 | 否 | 离线数据治理，不碰接口与密钥 |
| 可靠 | 是 | 同一数据集重复加载结果一致；缺字段即终止而非产半成品 |
| 易用 | 是 | 质量报告含异常样本可点回具体记录，便于定位 |

### 5. 已知缺口与后续计划
| 缺口 | 原因 | 归属 | 计划时间 |
|---|---|---|---|
| **公开数据集可下载性未验证**（代理不通，无法访问 GitHub） | 当前网络环境受限 | 蒋励 | Sprint 2 第 1 天（tasks 0.1） |
| 候选数据集清单尚未固化 | 同上 | 蒋励 | Sprint 2 第 1 天 |
| 不获取公开数据集时的降级方案需与老师确认口径 | 避免被误判为「没做附加功能 (3)」 | 蒋励 | Sprint 2 第 1 周 |
| 跨语言模型训练不在本 change | 属 `semantic-feature-mainline` 范围 | 蒋励 | Sprint 2–3 |
| 缺陷类型预测模型不在本 change | 本 change 只做「保留/标注类型字段 + 分布统计」 | 蒋励 | Sprint 3（若数据集有类型标签） |
