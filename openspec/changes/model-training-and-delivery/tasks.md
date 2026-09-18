# 模型训练与交付 — 任务清单

> 骨架版：按 spec-driven 依赖序生成，任务粒度以「可跑通、有证据」为准。
> 每组任务的验证方式写在该任务行内；跨线交付在任务行尾标注「交付给：后端线」。

## 1. 依赖与环境

- [ ] 1.1 `requirements.txt` 新增 `scikit-learn` / `xgboost` / `shap` 并钉死版本，在 conda 环境 `jit-defect`（Python 3.12）实测装通 —— 验证：`conda run -n jit-defect python -c "import sklearn, xgboost, shap"` 正常返回

## 2. 特征计算补登记（不写新代码）

- [ ] 2.1 核对 `03_extract_features.py` 与既有产物 `reports/feature_stats.md` 是否与 specs/feature-extraction 四条 Requirement 逐条相符，列出任何不一致项 —— 验证：核对清单落本 change 内，不一致项全部结清或登记
- [ ] 2.2 特征表 `feature_version` 列值确认为 `v1`（契约二（冻结版，冻结日期 2026-09-18）），列名与契约二第三节逐字比对 —— 验证：比对输出「缺列 0 / 多列 0 / 改名 0」

## 3. 时间序切分与训练

- [ ] 3.1 写 `05_split_dataset.py`：按 `committed_at` 升序排前 70% / 后 30%，内置断言「检验集最早 > 训练集最晚」，破坏即非零退出 —— 验证：正常切分通过；人为构造乱序输入时断言拦截（边界场景留输出）
- [ ] 3.2 写 `06_train_model.py`：仅用 `szz` 标签训练 LR / RF / XGBoost（2–3 个，按 Sprint 0 余量定），随机种子显式固定 —— 验证：同参数连跑两次评估指标逐项一致
- [ ] 3.3 两类指标落 `reports/`：Effort-unaware（AUC / F1 / 精确率 / 召回率）+ Effort-aware（P_opt，Kamei 原文口径），报告注明检验集时间范围、样本数与全集/检验集正样本比例 —— 验证：指标表两类齐全，检验集为空时不出指标（边界场景留输出）

## 4. 导出与交付物（交付给：后端线）

- [ ] 4.1 模型导出 `.pkl` 至 `data_model/models/`（不入库），随包产出特征顺序清单（契约二第三节（冻结版） 列序）—— 验证：`git status --short` 不出现 models/ 项；后端按清单组装向量推理一条提交，结果与训练侧离线预测一致
- [ ] 4.2 写 `07_predict_all.py`：对全部样本（含检验集）推理，产出 `prediction_result.csv`，字段与契约一表三逐字对齐（`commit_hash` / `model_name` / `risk_score` / `predicted_at` UTC / `feature_version`），`model_name` 按 `<算法>_v<序号>` 命名 —— 验证：与契约一表三逐字段比对通过；文件中无契约外字段；**数据线脚本与依赖中无任何数据库连接**（边界场景）
- [ ] 4.3 向后端线出具 A 方案交付清单：`.pkl` 路径 + 特征顺序清单 + SHAP 依赖版本 pin（与 `requirements.txt` 同源），外加推理环境依赖版本表 —— 验证：后端线签收确认（Issue 或 PR 评论留痕）
- [ ] 4.4 实测 SHAP 单条推理耗时并记录，评估是否满足 95% 请求 < 500ms —— 验证：实测数据进报告；若不达标，契约三变更提案已提（不静默降级）。**原条目里「SHAP 定稿后回填契约三『待确认』项」已删除** —— 契约三已由 PR #6 结清、`explanation` 定为 SHAP，该回填已无对象

## 5. 文档回填与规格同步

- [ ] 5.1 `data_model/README.md` 末节「三个候选待定」改为已定 A+C，修正「模型线批量预测写 prediction 表」为「数据线产出 `prediction_result.csv`，后端灌库」—— 验证：文中不再有与铁规矩 4 冲突的表述
- [ ] 5.2 `docs/data-pipeline.md` 链路表补 ⑥⑦ 步（训练 / 导出与全量预测），复现命令补随机种子参数 —— 验证：按文档命令从干净 clone 重放可得一致结果
- [ ] 5.3 提交 PR 并在描述里写明关联 change id `model-training-and-delivery`，由非作者审阅合入 —— 验证：PR 链接与审阅记录
