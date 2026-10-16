# Tasks — path-references-alignment

## 1. 规格修订（5 个能力的 MODIFIED delta）

- [ ] 1.1 `specs/commit-collection/spec.md`：「报出采集统计」的统计报告路径改为 `data_model/preparation/reports/`
- [ ] 1.2 `specs/labeled-dataset/spec.md`：「报出七项统计」的统计表路径改为 `data_model/preparation/reports/`
- [ ] 1.3 `specs/feature-extraction/spec.md`：「全量产物与统计报告 MUST 可入库可复现」的报告路径改为 `data_model/preparation/reports/feature_stats.md`
- [ ] 1.4 `specs/model-training/spec.md`：「MUST 产出两类评估指标」的报告路径改为 `data_model/pipelines/expert/reports/`
- [ ] 1.5 `specs/model-coverage/spec.md`：登记报告路径改为 `data_model/pipelines/expert/reports/`；「交付模型 MUST 保持不变」的清单路径改为 `data_model/pipelines/expert/models/feature_order.txt`，推理入口改为 `python -m pipelines.expert.predict`

## 2. 进行中 change 的路径引用同步

- [ ] 2.1 `semantic-feature-mainline`：`tasks.md` / `design.md` 中 `data_model/reports/`、`16_statistical_test.py`、`06_train_model.py`、`08_model_matrix.py` 引用改为新路径（`data_model/pipelines/<线>/reports/`、`python -m pipelines.expert.significance` 等）
- [ ] 2.2 `public-dataset-quality`：`tasks.md` / `proposal.md` / `specs/public-dataset/spec.md` 中 `data_model/reports/` 引用改为新归属路径
- [ ] 2.3 `feature-addons-sprint3`：`tasks.md` / `design.md` 中旧路径引用改为新归属路径

## 3. 校验

- [ ] 3.1 `openspec validate --all --strict` 全绿（15+1 项）
- [ ] 3.2 `git diff` 确认本 change 只动路径字符串，规格语义（阈值 / 判定 / 交付边界）逐字未改
