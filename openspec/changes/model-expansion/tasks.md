# 模型覆盖补齐 — 任务清单

> 每组任务的验证方式写在该任务行内。本 change **不新增依赖、不改交付模型、不改契约**。
> 实跑环境：conda env `jit-defect`（Python 3.12.14，依赖版本与 `requirements.txt` 逐项一致）。
> 数据集：`szz` 主标签，训练 7,625 / 检验 3,268 条，随机种子 42。

## 1. 扩展训练脚本（`06_train_model.py`）

- [x] 1.1 `build_model` 支持 5 个新增模型：`nb`（高斯朴素贝叶斯）/ `dt`（决策树）/ `knn`（k 近邻，k=25，标准化后计算）/ `mlp`（1 隐藏层 32 单元）/ `mlp_deep`（3 隐藏层 64/32/16 + 早停），并登记进 `MODEL_NAMES` —— 验证：`--models` 逐个传参可训练、不抛异常；**默认值 `lr,rf,xgb` 保持不变**，默认命令产出的 `reports/model_metrics.md` 与合入前逐行一致（SHAP 计时节除外）
      —— 8 个模型全部实跑成功（`08` 的控制台输出 8 行，见 `reports/model_matrix.md`）
      —— **回归验证（默认命令）**：`python 06_train_model.py --report reports/_tmp_default.md --no-export`
         后与已入库的 `reports/model_metrics.md` 逐行比对，**差异 6 行，全部是 SHAP 计时节那 3 行模型记录**
         （该节本就是实测耗时、随负载波动，`docs/data-pipeline.md` 已写明比对时排除）—— 指标表与其他文字**逐字节一致**
- [x] 1.2 SHAP 解释耗时按模型类型分派解释器；不支持精确解释器的模型**显式登记「未实测 + 原因」**，不静默跳过 —— 验证：报告中出现明确的未实测原因，而非空白行
      —— 已实现 `SHAP_TREE_MODELS = {rf, xgb, dt}` / `SHAP_LINEAR_MODELS = {lr}`；`nb` / `knn` /
         `mlp` / `mlp_deep` 返回 `skipped` 并带原因（`TreeExplainer` 只适用树模型、`DeepExplainer`
         需 PyTorch/TensorFlow 而本项目未引入），报告渲染为「未实测（原因）」

## 2. 覆盖矩阵（8 种 × 类别 × 两类指标）

- [x] 2.1 以单一口径跑 8 个模型，产出 `reports/model_matrix.md`（含类别标注与每类最优）—— 验证：8 行模型 + 每类最优行齐全
      —— 报告含：覆盖达标声明（**2 类 / 8 种 = ✅ 达标**）、8 行 Effort-unaware、两个工作量代理各 8 行
         Effort-aware、每类最优 ⭐ 标注、**神经网络收敛登记**（`mlp` 500/500 轮未收敛，如实登记）
- [x] 2.2 复核「口径没被动过」：既有 3 个模型（`lr_v1` / `rf_v1` / `xgb_v1`）的两类指标与 `reports/model_metrics.md` 逐项一致 —— 验证：逐项比对输出「差异 0」
      —— `08` 内置比对并把结果写进报告第二节：**差异 0 项**（比对 `lr_v1` / `rf_v1` / `xgb_v1`
         的 AUC / F1 / Precision / Recall / Accuracy 共 15 个数字）
      —— 该自证同时锁住三件事：切分文件未换、特征未重算、种子未变

## 3. 校准与阈值证据（支撑契约三提案 Issue #37 / #38）

- [x] 3.1 新增 `09_calibration_threshold.py`：时间序 CV 下的 isotonic / Platt 校准，产出 Brier / 对数损失 / 分箱可靠性表 —— 验证：报告写明折划分方式为时间序；随机 `KFold` 出现在代码里即视为不合格
      —— 折划分用 `TimeSeriesSplit(n_splits=3)` 并**显式落表**：三折的「拟合集最后时间 / 校准集最早时间」
         逐折成立（2006-11-13 / 2009-07-20 / 2012-03-20），全码无 `KFold` / `ShuffleSplit`
      —— 实测：`xgb` Brier 0.2209 → isotonic 0.2145；但**ECE 反而变差**（0.2466 → 0.2870）
- [x] 3.2 等工作量对照「固定阈值 0.50」与「配额取前 1% / 5% / 10%」（LOC 与改动文件数两种代理）—— 验证：报告给出同工作量下的召回/精确率对照与代价说明；结论写明「交提案决策」
      —— 两种代理各 6 行策略对照，另加一节**脚本自动算的「同一预算下谁更好」**：
         ④ 密度排序相对 ① 的召回 **+31.72 pp（LOC）/ +22.01 pp（nf）**
      —— 结论段写明「证据交提案」，并给出三条可执行结论（含「① 本身就是一个没写出来的工作量配额」）

## 4. 文档与规格同步

- [x] 4.1 `data_model/README.md`：补模型覆盖与类别口径（哪 8 种、分两类、交付模型不变）—— 验证：README 与 `MODEL_NAMES` 一致
      —— 新增「模型覆盖（8 种 / 2 类）」一节；链路表由五步扩到九步（补 ⑥⑦⑧⑨ 的脚本入口与产出）
- [x] 4.2 `docs/data-pipeline.md`：链路表与复现命令补评估扩展与校准证据两步 —— 验证：按文档命令可从干净 clone 重放
      —— §4 由「链路七步」改为「**链路九步**」并写明 ⑧⑨ 属本 change；§5 复现命令补 ⑧⑨ 两条；
         新增「⑧–⑨ 的口径」（⑧ 差异必须为 0、⑨ 折必须时间序且对照同工作量口径）；变更日志记 1.0
- [x] 4.3 `openspec validate --all --strict` 通过 —— 验证：命令输出全绿
      —— 实测：6 项全通过（含本 change 的 `model-coverage`），`validate` 输出无 error / warning
- [ ] 4.4 提交 PR 并在描述里写明关联 change id `model-expansion`，由非作者审阅后合入 —— 验证：PR 链接与审阅记录
      —— 已提交 **PR #42**（`feat/model/expansion-batch2`）：描述写明关联 change id、四条复跑验证方式、
         两条给 Issue #37/#38 的实测结论、以及「不新增依赖 / 不改交付模型 / 不做序列模型」的边界
      —— **本项仍未完成**：等非作者审阅后合入。未合入前不勾选（与首 change tasks 5.3 的口径一致）

## 5. 交付边界确认（跨线）

- [x] 5.1 确认交付模型与交付清单未变：`models/feature_order.txt` 的 `[models]` 段、`07_predict_all.py` 与 `prediction_result.csv` 口径均不变 —— 验证：`git diff` 不出现 `07_predict_all.py`；清单内容与首 change 交付一致
      —— 本 change 的改动只落在 `06` / `08` / `09` / 两份报告 / 两份文档；`07_predict_all.py`
         与 `models/feature_order.txt` 的 `[models]` 段（仍是 `lr_v1` / `rf_v1` / `xgb_v1`）未动
- [x] 5.2 若矩阵显示新模型显著更优 → 登记「模型切换」提案（另开 change），不在本 change 静默切换 —— 验证：PR 描述或 Issue 里有登记记录
      —— 实测：`rf_v1` 的 AUC（0.7463）略高于交付模型 `xgb_v1`（0.7397），但 Effort-aware 上两者
         **互有胜负**（LOC 代理 `P_norm` −0.2476 vs −0.4195 偏向 `rf`；文件数代理 0.2415 vs 0.2525
         偏向 `xgb`），差距在噪声量级。**不切换**，在 PR 描述里登记为观察项
      —— 另记一条更重要的发现：LOC 代理下**全部 8 个模型**的 `P_norm` 都在 0 附近或为负
         （最好的是 `mlp_v1` 0.0246），说明瓶颈在**排序口径**（Issue #37）而不在模型选择
