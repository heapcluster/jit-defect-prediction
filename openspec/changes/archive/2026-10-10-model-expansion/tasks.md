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
- [x] 4.4 提交 PR 并在描述里写明关联 change id `model-expansion`，由非作者审阅后合入 —— 验证：PR 链接与审阅记录
      —— 已提交 **PR #42**（`feat/model/expansion-batch2`）：描述写明关联 change id、四条复跑验证方式、
         两条给 Issue #37/#38 的实测结论、以及「不新增依赖 / 不改交付模型 / 不做序列模型」的边界
      —— **审阅与合入记录**：PR #42 已由非作者（苏哲勋 / PO，审阅职责见 `docs/team-charter.md` §1.1）
         审阅后 Squash 合入 `main`，合入提交 `388415e`（author 为作者、committer 为 GitHub，
         即经 GitHub 合并队列合入）。PR 链接：https://github.com/heapcluster/jit-defect-prediction/pull/42
      —— 代码已进 `main` 且 `openspec validate --all --strict` 全绿，本项闭环

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

---

## 测试与验证（强制板块 · 2026-10-13 回溯补录）

> 本节由 2026-10-13 课堂反馈后统一补录，**按实际已发生的验证写实**，未做的一律进 §5 缺口，不倒填。
> 分层口径见 `docs/common/test-strategy.md`；模板见 `docs/common/openspec-task-template.md`。

### 1. 单元测试（蒋励）
| 项 | 内容 |
|---|---|
| 覆盖对象 | `06_train_model.py` 扩展的模型分支、`08_model_matrix.py` 汇总逻辑 |
| 测试文件 | 无新增单测；沿用 `data_model/tests/test_feature_contract.py` 的 8 条口径断言守住回归 |
| 用例数与结果 | 8 条全通过 |
| 复现命令 | `cd data_model && python -m pytest -q` |
| 异常 / 边界用例 | 特征口径未变（契约二 14 项），故以契约测试保证扩展不破坏既有列名与顺序 |

### 2. 集成测试
| 项 | 内容 |
|---|---|
| 集成范围 | 8 个模型在同一时间序切分上训练 → 同一测试集评估 → 覆盖矩阵汇总 |
| 测试文件 | 无独立集成测试；以覆盖矩阵报告为证据 |
| 用例数与结果 | 8 模型 × 2 类指标齐备 |
| 复现命令 | 按 `docs/model/data-pipeline.md` 跑 06 → 07 → 08，产出 `data_model/reports/model_matrix.md` |
| 关键断言 | 同一划分、同一特征集、同一随机种子；交付模型只进 `[models]` 段且与 `model-coverage` R6 一致 |

### 3. 验收测试（交付时）
| 项 | 内容 |
|---|---|
| 验收依据 | `specs/model-coverage/spec.md` 的 SHALL/MUST 与 Scenario（≥2 类不少于 8 种） |
| 用例数与结果 | 经典 6（`lr_v1` `rf_v1` `xgb_v1` `nb_v1` `dt_v1` `knn_v1`）+ 神经网络 2（`mlp_v1` `mlp_deep_v1`），达标 |
| 证据归档 | `data_model/reports/model_matrix.md`、`calibration_threshold.md` |

### 4. 非功能验证
| 维度 | 是否触及 | 证据 |
|---|---|---|
| 性能 | 否 | —— |
| 安全 | 否 | —— |
| 可靠 | 是 | 训练/检验时间序切分不变；模型文件 md5 记录在 Issue #39 |
| 易用 | 否 | —— |

### 5. 已知缺口与后续计划
| 缺口 | 原因 | 归属 | 计划时间 |
|---|---|---|---|
| 新增模型分支无单测 | 以覆盖矩阵为验收 | 蒋励 | Sprint 2 |
| `mlp_v1` 未收敛、5 个模型仅评估不进交付段 | 已如实登记（`model_matrix.md`、`defect-records.md` N-01/N-02） | 蒋励 | 不处置（有理由） |
