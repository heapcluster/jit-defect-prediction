# model-training-scope-8 — 任务清单

> 提案：`proposal.md` ｜ 设计决策：无独立 `design.md`（口径收敛与取舍已在 `proposal.md` §Why / §不在本次范围 写明） ｜ 规格：`specs/model-training-scope/spec.md`
> 负责人：model 蒋励 ｜ 创建：2026-10-23 ｜ 状态：进行中
> 关联需求：C1-1（特征工程）/ C2-1（模型训练）/ A2-3（两类评估指标）—— 训练口径收敛与 effort 预算感知对照
> 统一格式见 `docs/common/openspec-task-template.md`；**本文件末的「测试与验证」为强制板块，缺失视为提案不完整。**

## 1. 训练口径收敛

- [x] 1.1 `expert/config.py`、`semantic/config.py`、`fused/config.py` 的 `DEFAULT_MODELS` 改为 8 个（`lr rf xgb lgbm et svm mlp_deep tabnet`）
      · 验证：`grep -A2 "DEFAULT_MODELS" data_model/pipelines/*/config.py` 三处逐字相同
- [x] 1.2 `MODEL_NAMES` 保留 12 项并加注释「默认不训练，兼容旧产物」
      · 验证：`data_model/tests/test_model_registry_parity.py::test_all_three_lines_share_the_same_default_model_set`（注册表 12 / 训练口径 8 双断言）
- [x] 1.3 `semantic` / `fused` 报告标题的分类器数量改为 `len(results)`
      · 验证：`data_model/tests/test_fused_report_coverage.py::test_report_title_states_trained_classifier_count`
- [x] 1.4 [历史版 `data_model/ENVIRONMENT.md`](https://github.com/heapcluster/jit-defect-prediction/blob/100008e787c8902c35760c9cef6d61d279d921b7/data_model/ENVIRONMENT.md) §5 的「均为 12 个」改为「训练口径 8 个、注册表 12 个」
      · 验证：`data_model/ENVIRONMENT.md` §5 与三处 `config.py` 口径一致（人工核对 + 本 change 引用）
- [ ] 1.5 用 12 个训过的 semantic / fused 报告，按 8 个重跑覆盖
      · 验证：两份报告标题分别显示「8 分类器」，表格模型行数 = 8

## 2. 预算感知对照口径

- [x] 2.1 `metrics.budget_order(proba, effort, floor)` 的 `floor` 由调用方按口径传入
      · 验证：`data_model/tests/test_effort_scope_and_narrative.py::test_floor_unit_follows_effort_unit`（LOC 用行、nf 用文件，误用 10 个文件会退化）
- [x] 2.2 `metrics.effort_aware_metrics(..., review_floor=None)`：不给 floor 就不产出 `budget` 项
      · 验证：`data_model/tests/test_effort_scope_and_narrative.py::test_metrics_skip_budget_when_no_floor`
- [x] 2.3 `config.EFFORT_REVIEW_FLOORS` 提供 LOC / nf 两份下限，`train.py` 两处调用点按口径取值
      · 验证：`grep -n "EFFORT_REVIEW_FLOORS" data_model/pipelines/expert/train.py` 两处调用
- [x] 2.4 报告表格新增「20% 预算审到的条数」列，预算感知与无下限密度并列
      · 验证：`data_model/pipelines/expert/reports/model_metrics.md` §2 每个模型 3 行（模型排序 / 预算感知 / 对照密度）

## 3. 报告结论由结果生成（评审意见 #4）

- [x] 3.1 删除「全为负 / 最低出自 svm / 其余 0.85 上下 / 两万多条 8 行」等硬编码断言
      · 验证：`data_model/tests/test_effort_scope_and_narrative.py::test_narrative_does_not_claim_all_negative_when_results_are_positive` 与 `::test_narrative_scales_to_model_subset`
- [x] 3.2 负 P_norm 的计数、最差模型名、ρ 区间、条数区间、中位 LOC 全部来自本轮 `results`
      · 验证：`--models lr` 子集重跑，报告里只出现 `lr`，且结论措辞随结果变化

## 4. 权重来源与泄漏（评审意见 #1）

- [x] 4.1 在当前 `split_szz_train.csv`（58,760）/ `split_szz_test.csv`（25,183）上**重训** 8 个模型，报告由本次训练直接产出
      · 验证：`data_model/pipelines/expert/reports/model_metrics.md` 的「数据与参数」段条数与切分统计一致；权重文件 mtime 与新报告同批
- [x] 4.2 训练入口加泄漏闸门：训练/检验 `commit_hash` 交集非空时拒绝出报告
      · 验证：`data_model/pipelines/expert/train.py::main` 的 `overlap` 分支（交集非空打印条数、退出码 2、不写报告）
- [x] 4.3 `--from-saved` 不再覆盖权威报告：默认输出 `model_metrics_from_saved.md`，文首标注「探索性、非权威指标」
      · 验证：`python -m pipelines.expert.train --from-saved` 后 `reports/model_metrics.md` 未被改动（mtime 不变，git status 干净）
- [x] 4.4 `--from-saved` 的图表落 `figs_from_saved/` 独立目录，不触碰权威 `reports/figs/`（复审阻断项 2）
      · 验证：`data_model/tests/test_from_saved_isolation.py::test_from_saved_charts_isolated_from_authoritative_figs`（权威 figs/ 哨兵文件逐字节不变）+ CLI 复跑后 `git status` 中 `figs/` 零改动

## 5. 收尾

- [x] 5.1 `data_model/tests` 全量通过（107 条，2026-10-23，Python 3.12.14，exit 0）
- [x] 5.2 PR #88 标题与描述更新为「重训产出权威报告」，并核对 #87（已 merged）带入的 ENVIRONMENT 改动无重复
      · 验证：PR #88 页面当前标题/描述（2026-10-23T08:41Z 更新）与代码一致 —— 权威报告 = 重训（58,760/25,183）、`--from-saved` 仅写 `model_metrics_from_saved.md` + `figs_from_saved/`、默认训练口径 8；#87 已 merged，本分支仅剩 ENVIRONMENT §5 一行差异（任务 1.4），无重复带入
- [ ] 5.3 本 change 归档（`openspec archive`），规格与实现一致性抽查

---

## 测试与验证（强制板块）

> 分层口径见 `docs/common/test-strategy.md`：**单元测试**由写代码的人自己做、
> **集成测试**在大版本合并后做、**验收测试**在交付时做，非功能验证并行。
> 铁律：**勾了 tasks ≠ 功能合格，必须有可复现的运行证据。**

### 1. 单元测试
| 项 | 内容 |
|---|---|
| 覆盖对象 | ① `budget_order`/`effort_aware_metrics` 的评审下限按口径取值与无下限跳过；② 报告结论由本轮 `results` 计算（非负、子集两形态）；③ 三线 `DEFAULT_MODELS`=8 且 `MODEL_NAMES`=12；④ `semantic`/`fused` 报告标题取实际训练数；⑤ `--from-saved` 报告与图表双隔离 |
| 测试文件 | `data_model/tests/test_effort_scope_and_narrative.py`、`data_model/tests/test_model_registry_parity.py`、`data_model/tests/test_fused_report_coverage.py`、`data_model/tests/test_from_saved_isolation.py` |
| 用例数与结果 | `cd data_model && python -m pytest -q` 全量 **107 条 passed**（2026-10-23，Python 3.12.14，exit 0） |
| 复现命令 | `conda activate jit-defect-prediction && cd data_model && python -m pytest -q` |
| 正向用例 | LOC 口径 floor=10 按行挡、nf 口径 floor=2 按文件挡（`test_floor_unit_follows_effort_unit`）；`--from-saved` 图表落 `figs_from_saved/` 且权威 `figs/` 哨兵文件逐字节不变（`test_from_saved_isolation.py`） |
| 异常 / 边界用例 | nf 口径误用 floor=10 → 全部被判「太小」、排序退化为按分数（`test_floor_unit_follows_effort_unit` 末段断言）；P_norm 全非负 → 报告不出现「全为负」且不写死模型名（`test_narrative_does_not_claim_all_negative_when_results_are_positive`）；`--models lr` 子集 → 报告只含 `lr`（`test_narrative_scales_to_model_subset`） |

### 2. 集成测试
| 项 | 内容 |
|---|---|
| 集成范围 | 训练入口 ↔ 05 时间序切分产物 ↔ 03 原始特征表（effort 列）↔ 交付清单 `models/feature_order.txt` |
| 测试文件 | 无独立套件：单元层以 tmp 构造数据覆盖，集成层以 CLI 复现 + 报告自证承担 |
| 用例数与结果 | 3 项 CLI 检查 ｜ 通过（2026-10-23，见下） |
| 复现命令 | `cd data_model && python -m pipelines.expert.train --from-saved --models lr`（隔离验证）；`python -m pipelines.expert.matrix`（与基线报告逐项比对） |
| 关键断言 | ① 训练/检验 `commit_hash` 交集为空，人为构造交集时退出码 2 且不写任何报告（泄漏闸门）；② `--from-saved` 运行后 `reports/model_metrics.md` mtime 不变、`reports/figs/` 在 `git status` 中零改动；③ `models/feature_order.txt` 的 `[models]` 段仍为 `lr/rf/xgb`（交付清单不随训练口径变化） |

### 3. 验收测试
| 项 | 内容 |
|---|---|
| 验收依据 | `specs/model-training-scope/spec.md` 的 4 条 Requirement + 6 个 Scenario |
| 用例数与结果 | 4 条（每条 Requirement 一项）｜ 通过，证据如下 |
| 复现命令 / 步骤 | ① 8 分类器：`grep -A2 "DEFAULT_MODELS" data_model/pipelines/{expert,semantic,fused}/config.py` 三处逐字相同；② 预算口径：`reports/model_metrics.md` §2 每模型 3 行且「20% 预算审到的条数」有值；③ 结论计算：`--models lr` 子集重跑报告只含 `lr`；④ 权威指标：`reports/model_metrics.md`「数据与参数」段 58,760 / 25,183 与 `preparation/reports/split_stats.md` 一致 |
| 证据归档 | `data_model/pipelines/expert/reports/model_metrics.md`、`data_model/pipelines/expert/reports/model_matrix.md`、`data_model/ENVIRONMENT.md` §5、`data_model/pipelines/expert/models/feature_order.txt` |

### 4. 非功能验证
| 维度 | 是否触及 | 证据 |
|---|---|---|
| 性能 | 否 | 训练为离线批处理，不触及接口 SLA |
| 安全 | 否 | 不涉及接口与密钥 |
| 可靠 | 是 | 泄漏闸门（交集拒绝出报告）+ `--from-saved` 报告与图表双隔离（不覆盖权威产物），证据见板块 1/2 |
| 易用 | 否 | 无界面改动；报告可读性属产物质量，随验收板块核对 |

### 5. 已知缺口与后续计划
| 缺口 | 原因 | 归属 | 计划时间 |
|---|---|---|---|
| semantic / fused 用 12 分类器训过的报告未按 8 个重跑（1.5 未勾） | 语义特征样本集尚未产出（依赖 `semantic-feature-mainline`），现在单独重跑无意义 | model 蒋励 | 随 `semantic-feature-mainline` SF-5 |
| `--from-saved` 报告的 SHAP 一节显示「未实测」 | 设计如此：旧权重复算不算 SHAP 实测，不倒填 | model 蒋励 | 如需补，重训时按 `--shap-rows` 实测 |
| 本 change 归档（5.3） | 待 PR #88 复审通过合入后执行 `openspec archive` | model 蒋励 | #88 合入后 |
