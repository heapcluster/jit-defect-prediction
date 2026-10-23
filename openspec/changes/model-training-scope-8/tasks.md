# 任务清单：训练口径 8 个 + 预算感知对照口径

> 每一项都写「怎么验证」，没有证据不算完成。证据路径写在本文件与 PR 描述里。

## 1. 训练口径收敛

- [x] 1.1 `expert/config.py`、`semantic/config.py`、`fused/config.py` 的 `DEFAULT_MODELS` 改为 8 个（`lr rf xgb lgbm et svm mlp_deep tabnet`）
      · 验证：`grep -A2 "DEFAULT_MODELS" data_model/pipelines/*/config.py` 三处逐字相同
- [x] 1.2 `MODEL_NAMES` 保留 12 项并加注释「默认不训练，兼容旧产物」
      · 验证：`tests/test_model_registry_parity.py::test_all_three_lines_share_the_same_default_model_set`
- [x] 1.3 `semantic` / `fused` 报告标题的分类器数量改为 `len(results)`
      · 验证：`tests/test_fused_report_coverage.py::test_report_title_states_trained_classifier_count`
- [x] 1.4 `data_model/ENVIRONMENT.md` §5 的「均为 12 个」改为「训练口径 8 个、注册表 12 个」
      · 验证：该文件 §5 与三处 `config.py` 口径一致（人工核对 + 本 change 引用）
- [ ] 1.5 用 12 个训过的 semantic / fused 报告，按 8 个重跑覆盖
      · 验证：两份报告标题分别显示「8 分类器」，表格模型行数 = 8

## 2. 预算感知对照口径

- [x] 2.1 `metrics.budget_order(proba, effort, floor)` 的 `floor` 由调用方按口径传入
      · 验证：`tests/test_effort_scope_and_narrative.py::test_floor_unit_follows_effort_unit`（LOC 用行、nf 用文件，误用 10 个文件会退化）
- [x] 2.2 `metrics.effort_aware_metrics(..., review_floor=None)`：不给 floor 就不产出 `budget` 项
      · 验证：`test_metrics_skip_budget_when_no_floor`
- [x] 2.3 `config.EFFORT_REVIEW_FLOORS` 提供 LOC / nf 两份下限，`train.py` 两处调用点按口径取值
      · 验证：`grep "EFFORT_REVIEW_FLOORS" data_model/pipelines/expert/train.py` 两处
- [x] 2.4 报告表格新增「20% 预算审到的条数」列，预算感知与无下限密度并列
      · 验证：`reports/model_metrics.md` §2 每个模型 3 行（模型排序 / 预算感知 / 对照密度）

## 3. 报告结论由结果生成（评审意见 #4）

- [x] 3.1 删除「全为负 / 最低出自 svm / 其余 0.85 上下 / 两万多条 8 行」等硬编码断言
      · 验证：`tests/test_effort_scope_and_narrative.py::test_narrative_does_not_claim_all_negative_when_results_are_positive` 与 `::test_narrative_scales_to_model_subset`
- [x] 3.2 负 P_norm 的计数、最差模型名、ρ 区间、条数区间、中位 LOC 全部来自本轮 `results`
      · 验证：`--models lr` 子集重跑，报告里只出现 `lr`，且结论措辞随结果变化

## 4. 权重来源与泄漏（评审意见 #1）

- [x] 4.1 在当前 `split_szz_train.csv`（58,760）/ `split_szz_test.csv`（25,183）上**重训** 8 个模型，报告由本次训练直接产出
      · 验证：`reports/model_metrics.md` 的「数据与参数」段条数与切分统计一致；权重文件 mtime 与新报告同批
- [x] 4.2 训练入口加泄漏闸门：训练/检验 `commit_hash` 交集非空时拒绝出报告
      · 验证：`train.py::main` 中的 `overlap` 分支；构造重叠切分应返回 2 且不写报告
- [x] 4.3 `--from-saved` 不再覆盖权威报告：默认输出 `model_metrics_from_saved.md`，文首标注「探索性、非权威指标」
      · 验证：`python -m pipelines.expert.train --from-saved` 后 `model_metrics.md` 未被改动

## 5. 收尾

- [x] 5.1 `data_model/tests` 全量通过（105 条）
- [ ] 5.2 PR #88 描述更新为「重训产出权威报告」，并摘掉 #87 带入的 ENVIRONMENT 改动
- [ ] 5.3 本 change 归档（`openspec archive`），规格与实现一致性抽查
