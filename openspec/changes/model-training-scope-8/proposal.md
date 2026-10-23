# 训练口径收敛为 8 个分类器（12 → 8），并新增「预算感知」effort 对照口径

> 起草 2026-10-23 ｜ 起草人 蒋励（模型线）｜ 触发：PR #88 评审意见 #2 / #3
> 关联契约：`docs/model/feature-columns.md`（契约二）、`docs/backend/api-spec.md`（契约三）
> 关联 PR：`feat/model/expert-figs-and-from-saved`（#88）

## Why

1. **训练口径与文档脱节**：`docs/model/model-line-plan.md` §2.1、`docs/model/pipelines/*.md` 一直写「2 类 8 种」，但 `expert` / `semantic` / `fused` 的 `config.DEFAULT_MODELS` 残留 12 个（多 `nb` `dt` `knn` `mlp`）。后果是实测发生的：队友按 README 直接跑 `python -m pipelines.fused.train`，默认训了 12 个模型，报告标题也跟着写「12 分类器」。
2. **跨线对比失真**：四线对比的前提是「同切分、同模型集合，只差特征模态」。默认集合不一致时，横向差异里混入了模型集合差异。
3. **effort-aware 的负 `P_norm` 无法解释**：`risk_score` 与提交规模高度相关（Spearman ρ 中位数 0.862），按 `risk_score` 降序等于先审最大的提交，20% LOC 预算只够 276~1033 条，召回低于随机基线。需要一条「预算感知」对照口径把「排序问题」与「模型问题」分开，但**不改契约三主口径**。

## What Changes

- `expert` / `semantic` / `fused` 的 `config.DEFAULT_MODELS` 收敛为 8 个：`lr rf xgb lgbm et svm mlp_deep tabnet`；`model.py::MODEL_NAMES` 保留 12 个注册项（`nb dt knn mlp` 仅兼容旧产物，默认不训练、不进四线对比）。
- `tests/test_model_registry_parity.py` 拆成两条断言：注册表 = 12、训练口径 = 8，且三线一致。
- `semantic` / `fused` 报告标题的分类器数量改为按本次实际训练模型数动态生成，杜绝「配置 8、标题 12」的漂移。
- 新增 effort 对照口径 `budget`：先按该口径的评审下限过滤（LOC → `MIN_REVIEW_LOC=10` 行，nf → `MIN_REVIEW_FILES=2` 文件），其余按风险密度降序；**单位随口径走，不再共用 10**。
- 报告新增「20% 预算审到的条数」列与由结果计算的读法段；`--from-saved` 的输出改落到 `model_metrics_from_saved.md`，并在文首标注「探索性、非权威指标」。
- 训练入口加泄漏闸门：训练集与检验集 `commit_hash` 有交集时直接拒绝出报告。

## 不在本次范围

- 不切换契约三的排序主口径（`risk_score` 降序保持不变），口径切换另立提案（Issue #37）。
- 不补 semantic / fused / e2e 的产物，它们按 `semantic-feature-mainline` 的 SF-5 推进。

## 影响面

| 受影响 | 变化 |
|---|---|
| `python -m pipelines.<line>.train` 默认行为 | 训 8 个而不是 12 个（复现时间约减半） |
| 已用 12 个训过的报告 | 与四线对比口径不一致，需按 8 个重跑覆盖 |
| 后端 | 不受影响：`model_registry` 加载 `MODEL_DIR` 下全部 `.pkl`，与训练口径解耦 |
| 交付清单 | 不变：`feature_order.txt [models]` 仍是 `lr_v1 / rf_v1 / xgb_v1` |
