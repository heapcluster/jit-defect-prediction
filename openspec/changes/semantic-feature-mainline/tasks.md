# semantic-feature-mainline — 任务清单

> 提案：`proposal.md` ｜ 设计决策：`design.md` ｜ 规格：`specs/semantic-features/spec.md`
> 负责人：model 蒋励 ｜ 创建：2026-10-13 ｜ 状态：进行中（Sprint 2 启动，Sprint 1 收口后立即开工）
> 用户故事：C1-1（特征工程）/ C2-1（模型训练）/ A2-3（两类评估指标）—— 语义特征为 C1-1 的新增特征路线
> 统一格式见 `docs/common/openspec-task-template.md`；**本文件末的「测试与验证」为强制板块，缺失视为提案不完整。**

## 1. 立项与规格同步（跨线：苏哲勋看板 / 蒋励统稿）
- [ ] 1.1 本 change 进 `openspec/changes/semantic-feature-mainline/`（propose → apply），看板「规格变更或任务」列可点回
- [ ] 1.2 `docs/design/sprint0-scope.md` 边界表述改写：「代码语义特征提取（可选）」→「已提升为模型线主线，Kamei 14 降为基线对照组」（范围变更，须显式留痕）
- [ ] 1.3 `feature-addons-sprint3` 的 G1-4 条目移出，proposal/tasks/design 同步注明「已由 `semantic-feature-mainline` 顶替」，不留双入口
- [ ] 1.4 看板新增 Sprint 2 两行：语义特征全量（MiniLM）/ 抽样增强（CodeBERT），迭代=Sprint 2、关联本 change

## 2. 契约与数据边界（蒋励）
- [ ] 2.1 `docs/model/feature-columns.md` 登记 `feature_version = v2`（语义列），**契约二既有 14 项列名与顺序一字不动**；口径变更走契约变更流程
- [ ] 2.2 明确语义向量**不入库、不进交付链**，只落 `data_model/data/semantic_*.csv`；在 `docs/model/data-pipeline.md` 第 7 节登记该口径

## 3. 环境隔离（蒋励）
- [ ] 3.1 建独立 conda 环境 `jit-sematic`（**实际名以创建结果为准，若改名须回写本行**），装 `torch` + `sentence-transformers`；`jit-defect` **一个包都不加**
- [ ] 3.2 复核 `jit-defect` 仍可跑：`cd backend && python -m pytest -q` → 87 passed；`cd data_model && python -m pytest -q` → 59 passed（环境隔离的验收证据）

## 4. 变更文本构造（蒋励，质量关键）
- [ ] 4.1 新增 `data_model/10_semantic_text.py`：按**文件**生成变更文本（路径 + 变更类型 + 增删行 + 提交信息首行），单文件超模型上限按行截断并统计截断文件数/行数
- [ ] 4.2 输出 `semantic_text_<feature_version>.csv`（一行一个 `commit_hash` + 文件路径 + 文本），供 5/6 两步共用；**同一份文本供两条路线**，避免双份构造漂移

## 5. 打底路线：MiniLM 全量（蒋励）
- [ ] 5.1 新增 `data_model/11_semantic_minilm.py`：`all-MiniLM-L6-v2` 对全部 11,050 条提交提特征，按提交聚合（多文件取均值）
- [ ] 5.2 产出 `data_model/data/semantic_minilm_v2.csv`（`commit_hash` + `sem_0 … sem_383`）；记录设备、耗时、是否全量、截断统计
- [ ] 5.3 交付给：`12_compare_settings.py`（第 8 步），形式为上述 CSV

## 6. 增强路线：CodeBERT 抽样（蒋励）
- [ ] 6.1 新增 `data_model/12_semantic_codebert.py`：CodeBERT / GraphCodeBERT 在 1,000–2,000 条**按时间序分层抽样**的子集上提特征（禁随机抽，保证与切分口径一致）
- [ ] 6.2 产出 `data_model/data/semantic_codebert_v2_sample.csv` + 抽样说明（抽样方法、样本量、设备、是否全量）
- [ ] 6.3 若算力不足无法完成，**如实登记为缺口并写明原因**，不得用 MiniLM 结果冒充代码模型结果

## 7. 融合样本构建（蒋励）
- [ ] 7.1 新增 `data_model/13_build_fused.py`：按 `commit_hash` 左连接专家特征（14 项）与语义向量，产出三类设置各自的样本集；缺失语义向量的提交**显式标注并单列数量**，不用 0 填充冒充
- [ ] 7.2 切分沿用 `05_split_dataset.py` 的时间序切分与 `validate_split` 断言，**三套样本集用同一切分下标**

## 8. 三类设置对比实验（蒋励）
- [ ] 8.1 新增 `data_model/14_compare_settings.py`：仅专家 / 仅语义 / 融合 三类各自跑同一套 8 模型，输出 Effort-unaware（AUC/F1/P/R/Acc）+ Effort-aware（`P_norm`、同预算重排召回）
- [ ] 8.2 产出 `data_model/reports/three_way_comparison.md`（三类 × 8 模型 × 两类指标），标注每组所用特征版本与模型清单
- [ ] 8.3 交付给：`docs/model/training-eval.md` §4 增补一节；后端**不接**新模型（见第 10 步）

## 9. 论文方法论补做（蒋励）
- [ ] 9.1 新增 `data_model/15_feature_ablation.py`：Kamei 14 留一法消融 + 检验集置换重要性，输出特征效力排序（两个口径交叉验证）
- [ ] 9.2 产出 `data_model/reports/feature_ablation.md`（Top-K 特征 + 两项口径对照）
- [ ] 9.3 在模型线报告中显式登记「跨项目 JIT 不可迁移」结论（Kamei et al. 2013）与单仓库设计依据

## 10. 交付边界确认（蒋励，硬约束）
- [ ] 10.1 确认 `backend/app/model_registry.py` 与 `data_model/models/[models]` 段**未被本 change 改动**；交付模型仍为现有 `xgb_v1` 等
- [ ] 10.2 若三类对比显示语义/融合更优，**另开「模型切换」提案**（spec `model-coverage` R6），本 change 不切换

## 11. 文档与周报（蒋励统稿）
- [ ] 11.1 `docs/design/addons.md` §4 G1-4 定位改写为「已提升为模型线主线，见 `openspec/changes/semantic-feature-mainline`」
- [ ] 11.2 `docs/model/methodology-references.md` §3 补「语义特征路线」决策行与文献依据
- [ ] 11.3 `docs/model/training-eval.md` §4 增补三类对比结果；周报记录已完成/下一步/存在问题

## 测试与验证（强制板块）

> 分层口径见 `docs/common/test-strategy.md`；模板见 `docs/common/openspec-task-template.md`。
> 铁律：勾了 tasks ≠ 功能合格，必须有可复现命令与证据路径。

### 1. 单元测试（蒋励，写代码的人自己写）
| 项 | 内容 |
|---|---|
| 覆盖对象 | 变更文本构造（`10_semantic_text.py`：文件切分、截断统计、增删行剥离）、按提交聚合（均值、单文件直取）、融合左连接与缺失标注、留一法消融的样本数守恒 |
| 测试文件 | `data_model/tests/test_semantic_text.py`、`data_model/tests/test_feature_ablation.py` |
| 用例数与结果 | 计划 ≥ 20 条；环境 `jit-semantic`，跑法 `conda activate jit-semantic && cd data_model && python -m pytest tests/test_semantic_text.py tests/test_feature_ablation.py -q` |
| 复现命令 | 同上 |
| 正向用例 | 多文件提交的语义向量 = 各文件向量均值；专家 14 项与语义列左连接后行数守恒、无重复 `commit_hash` |
| 异常 / 边界用例 | 单文件文本超上限 → 按行截断且**记录**截断文件数与行数（不静默丢）；提交无任何改动文件 → 显式报错而非产出空向量；融合时某提交缺语义向量 → 单列计数，**不用 0 填充** |

### 2. 集成测试（大版本合并后，吕建江组织的跨线契约）
| 项 | 内容 |
|---|---|
| 集成范围 | 语义特征样本集 → 时间序切分 → 8 模型训练 → 评估汇总，与既有 `05`/`06`/`08` 脚本的衔接 |
| 测试文件 | `data_model/tests/test_compare_settings_pipeline.py`（新增，计划） |
| 用例数与结果 | 计划 ≥ 6 条 |
| 复现命令 | `conda activate jit-semantic && cd data_model && python -m pytest tests/test_compare_settings_pipeline.py -q` |
| 关键断言 | 三类设置用**同一切分下标**（train/test 的 `commit_hash` 集合逐字相同）；契约二 14 项列名与顺序未被改动；`feature_version` 正确标为 v2 |

### 3. 验收测试（交付时，按 spec 的 SHALL/MUST 逐条走）
| 项 | 内容 |
|---|---|
| 验收依据 | `specs/semantic-features/spec.md` 的 7 条 Requirement 与全部 Scenario |
| 用例数与结果 | 计划 7 条（每条 Requirement 至少 1 条） |
| 复现命令 / 步骤 | 按 `docs/model/data-pipeline.md` 增补后的 10→14 步顺序执行，比对 `data_model/reports/three_way_comparison.md` |
| 证据归档 | `data_model/reports/three_way_comparison.md`、`feature_ablation.md`；设备/样本量/截断统计随报告附 |

### 4. 非功能验证
| 维度 | 是否触及 | 证据 |
|---|---|---|
| 性能 | 是 | MiniLM 全量耗时与吞吐记录（提交数/分钟）；CodeBERT 抽样耗时；作为「能否全量」的判据 |
| 安全 | 否 | 语义特征为离线实验产物，不碰接口与密钥 |
| 可靠 | 是 | 切分可复现（同种子、同下标）；缺失语义向量显式计数不冒充；环境隔离后 `jit-defect` 87+59 条仍全绿 |
| 易用 | 否 | 本 change 不涉及界面 |

### 5. 已知缺口与后续计划
| 缺口 | 原因 | 归属 | 计划时间 |
|---|---|---|---|
| `torch` 未安装、`jit-semantic` 未建 | Sprint 1 收口前不动环境（避免影响 10/23 验收） | 蒋励 | Sprint 2 第 1 天 |
| CodeBERT 抽样可能因算力无法完成 | 无 GPU，CPU 抽样耗时待实测 | 蒋励 | Sprint 2 末，完不成则如实登记 |
| 语义向量维度（MiniLM 384 维）与 14 项专家特征量纲差异大，融合前是否需标准化待定 | 需先看三类对比的未标准化结果再定 | 蒋励 | Sprint 2 |
| 交付模型切换未做（硬约束，不静默切换） | 须另开「模型切换」提案 | 蒋励 | Sprint 3（若指标支持） |
| 集成测试套件由后端线组织，本 change 只提供被测对象 | 跨线集成属吕建江职责 | 吕建江 | Sprint 2 |
