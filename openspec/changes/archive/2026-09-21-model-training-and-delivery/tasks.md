# 模型训练与交付 — 任务清单

> 骨架版：按 spec-driven 依赖序生成，任务粒度以「可跑通、有证据」为准。
> 每组任务的验证方式写在该任务行内；跨线交付在任务行尾标注「交付给：后端线」。

## 1. 依赖与环境

- [x] 1.1 `requirements.txt` 新增 `scikit-learn` / `xgboost` / `shap` 并钉死版本，在 conda 环境 `jit-defect`（Python 3.12）实测装通 —— 验证：`conda run -n jit-defect python -c "import sklearn, xgboost, shap"` 正常返回
      —— 已钉 `scikit-learn==1.9.1` / `xgboost==3.4.1` / `shap==0.52.0` / `pandas==3.0.5` / `numpy==2.5.3`，
         与 `models/feature_order.txt` 的 `[dependencies]` 段同源（05–07 已在该环境实跑并产出报告，即装通证据）
      —— **补记（原先漏登记）**：`shap` 此前不在清单里，而后端线按旧清单装环境会缺它，
         预测接口的 `explanation` 正由 SHAP 产出（契约三第三节）—— 已补齐，非可选项

## 2. 特征计算补登记（不写新代码）

- [x] 2.1 核对 `03_extract_features.py` 与既有产物 `reports/feature_stats.md` 是否与 specs/feature-extraction 四条 Requirement 逐条相符，列出任何不一致项 —— 验证：核对清单落本 change 内，不一致项全部结清或登记
      —— 核对清单（四条 Requirement 逐条）：
      —— **R1 列名与取值口径遵循契约二** —— 相符。特征表 17 列 = 契约二第二/三节逐字一致；
         `rexp` 按 `Σ count(n)/(n+1)`、`nuc` 按文件计数求和、六项 DECIMAL，均与契约第四节一致
      —— **R2 历史类特征使用完整历史** —— 相符。`--since` 只决定「给哪些提交算特征」，
         历史仍取全量（`03_extract_features.py:105` 的 help 已写死「不传=全量。历史特征仍用完整历史」）
      —— **R3 全量产物与统计报告可入库可复现** —— 相符。特征表落 `data/`（不入库）；
         `reports/feature_stats.md` 含 14 项取值外沿（变换后与原值两张表）与契约缺口登记结论
      —— **R4 无法计算特征的提交显式处理并计数** —— 相符，口径钉死为「记 0」，与 `log_v1` 实现一致
         （特征表 11050 行 = 提交清单全量；若走「排除」，行数会少于全量）
      —— **不一致项 1 条（已登记，未擅自改规格）**：R4 的**标题**写「MUST 显式**排除**并计数」，
         与其**正文**钉死的「记 0」相冲突。已按正文执行，规格原文也已在注里声明钉死为「记 0」；
         建议后续把标题改为「记 0 并计数」，消除标题与正文的矛盾
      —— `reports/feature_stats.md` 另登记「契约里没写清、由本脚本作主的四处」：其中
         `rexp` 公式、六项类型改 DECIMAL、`nuc` 聚合方式三项已随契约二 v1.0 冻结结清；
         余一项（`ln(x)` 与 0 值处不连续）保留为 `feature_version` v2 的建议，不在本 change 改
- [x] 2.2 特征表 `feature_version` 列值确认为 `v1`（契约二（冻结版，冻结日期 2026-09-18）），列名与契约二第三节逐字比对 —— 验证：比对输出「缺列 0 / 多列 0 / 改名 0」
      —— 实测比对输出：**缺列 0 / 多列 0 / 改名 0**，列序亦与契约二第二、三节一致
      —— 特征表 `commit_features.csv` 17 列 = 3 个标识列（`commit_hash` / `committed_at` /
         `feature_version`）+ 14 项特征列；`feature_version` 取值集合 = {`v1`}，11050 行全部为 `v1`
      —— 注：样本集 `dataset_szz.csv` 是 20 列，比特征表多 `is_bug_inducing` / `label_method` /
         `bug_fix_hash` 三列 —— 那三列来自契约一表三的标签侧，04 步按 `commit_hash` 汇总时带入，
         不属于「自造列」；逐字比对应以**特征表**为对象，结论同上

## 3. 时间序切分与训练

- [x] 3.1 写 `05_split_dataset.py`：按 `committed_at` 升序排前 70% / 后 30%，内置断言「检验集最早 > 训练集最晚」，破坏即非零退出 —— 验证：正常切分通过；人为构造乱序输入时断言拦截（边界场景留输出）
      —— 已产出 `reports/split_stats_szz.md`：训练 7625 / 检验 3268，行数守恒（7625+3268=10893）
      —— 边界场景已留输出：`python 05_split_dataset.py --selfcheck` 打乱输入后被断言拦下
         （第一版自检写的是「不排序直接切」，**没拦住** —— 样本集本身已按时间升序；
         已改为先 `shuffle` 再切。自检本身也要能失败，否则等于没检）
- [x] 3.2 写 `06_train_model.py`：仅用 `szz` 标签训练 LR / RF / XGBoost（2–3 个，按 Sprint 0 余量定），随机种子显式固定 —— 验证：同参数连跑两次评估指标逐项一致
      —— 已产出 `reports/model_metrics.md`：`lr_v1` / `rf_v1` / `xgb_v1` 三个模型，随机种子 `42` 显式固定并写进报告
- [x] 3.3 两类指标落 `reports/`：Effort-unaware（AUC / F1 / 精确率 / 召回率）+ Effort-aware（P_opt，Kamei 原文口径），报告注明检验集时间范围、样本数与全集/检验集正样本比例 —— 验证：指标表两类齐全，检验集为空时不出指标（边界场景留输出）
      —— 两类齐全：Effort-unaware（AUC / F1 / Precision / Recall / Accuracy）+ Effort-aware
         （**LOC 与 nf 两种工作量代理各一张表**，并含随机排序基线的自我校验）
      —— 已注明检验集时间范围 2014-02-10 ~ 2025-03-13、样本数 3268、训练/检验正样本比例 48.66% / 16.40%

## 4. 导出与交付物（交付给：后端线）

- [x] 4.1 模型导出 `.pkl` 至 `data_model/models/`（不入库），随包产出特征顺序清单（契约二第三节（冻结版） 列序）—— 验证：`git status --short` 不出现 models/ 项；后端按清单组装向量推理一条提交，结果与训练侧离线预测一致
      —— `models/` 与 `*.pkl` 均在 `.gitignore` 内，`git status --short` 不出现该目录
      —— `models/feature_order.txt` 为交付清单：`.pkl` 路径 + 14 项特征顺序 + 依赖版本 pin + 风险阈值，
         并注明「本清单是契约二第三节的**副本**，不是独立来源，不一致时以契约为准」
- [x] 4.2 写 `07_predict_all.py`：对全部样本（含检验集）推理，产出 `prediction_result.csv`，字段与契约一表三逐字对齐（`commit_hash` / `model_name` / `risk_score` / `predicted_at` UTC / `feature_version`），`model_name` 按 `<算法>_v<序号>` 命名 —— 验证：与契约一表三逐字段比对通过；文件中无契约外字段；**数据线脚本与依赖中无任何数据库连接**（边界场景）
      —— 已产出 `reports/prediction_stats.md`：10893 条全量推理，模型 `xgb_v1`
      —— 三条断言全部通过：字段与契约一表三逐字一致（无契约外字段）/ 列顺序一致 /
         源码扫描 `sqlalchemy` / `pymysql` / `mysql.connector` / `sqlite3` / `psycopg2` 零命中（不直连数据库）
- [x] 4.3 向后端线出具 A 方案交付清单：`.pkl` 路径 + 特征顺序清单 + SHAP 依赖版本 pin（与 `requirements.txt` 同源），外加推理环境依赖版本表 —— 验证：后端线签收确认（Issue 或 PR 评论留痕）
      —— 交付物本身已备好：`models/feature_order.txt`（含依赖 pin 与阈值）与 `requirements.txt` 已同源
      —— **2026-09-21 后端线已签收**：吕建江在 Issue #39 回「**三项全签**」，并给出他自己的复核口径 ——
         按 `06_train_model.py:257-259` 逐项核对交付 `rf_v1.pkl` 的
         `min_samples_leaf=2 / random_state=42 / n_estimators=300`，与代码一致。签收评论留痕在 Issue #39
      —— 签收前本项一直不勾（跨线交付不能由数据线自己宣布完成）；签收后按审阅意见补齐了清单的两处缺口，见 **4.5**
- [x] 4.4 实测 SHAP 单条推理耗时并记录，评估是否满足 95% 请求 < 500ms —— 验证：实测数据进报告；若不达标，契约三变更提案已提（不静默降级）。**原条目里「SHAP 定稿后回填契约三『待确认』项」已删除** —— 契约三已由 PR #6 结清、`explanation` 定为 SHAP，该回填已无对象
      —— 已实测并落 `reports/model_metrics.md` 第三节：`lr` p95 **0.6 ms** / `rf` p95 **127.7 ms** /
         `xgb` p95 **5.0 ms**，三条均满足「95% 请求 < 500ms」，**无需提契约变更**
      —— 注：该节是实测耗时，随机器负载波动，连跑两次会变；核对可复现性时不要比对计时表
- [x] 4.5 交付清单补两处缺口（审阅发现，2026-09-21）：`[dependencies]` 段补 `joblib`、`[contract]` 段补契约二版本号 —— 验证：重跑 `06_train_model.py` 后清单含两项，且三个 `.pkl` 的 md5 与重跑前**逐一致**
      —— **① `joblib` 是运行时会踩的坑**：交付的 `.pkl` 是 `joblib.dump` 产物（内含 numpy 缓冲
         `numpy_array_alignment_bytes`），**标准 `pickle.load` 会报 invalid load key**，只有
         `joblib.load` 能读；而它此前只是 `scikit-learn` 的传递依赖、**不受 pin 约束**（装到哪个版本看 sklearn），
         清单自己的规则却是「按 `[dependencies]` 段钉版本建环境」→ 已补 `joblib==1.6.0`，
         `requirements.txt` 同步显式钉死（两处同源）
      —— **② `[contract]` 段原先只写路径、没写版本号**（自称「契约二第三节的副本」却不可追溯）→
         补为「**契约二 v1.2** 第三节」。判据：契约二文件头当前版本即 1.2（冻结 2026-09-18，冻结人蒋励）
      —— **③ 另补 `[how_to_load]` 段**：写明用 `joblib.load` 读取、依赖见 `[dependencies]` 段；
         并写明 `lr_v1.pkl` 是 `Pipeline`（`StandardScaler → LogisticRegression`）——
         取系数或特征重要度**须经 `named_steps`**（如 `model.named_steps["lr"].coef_`），
         直接 `model.coef_` 会 `AttributeError`（横向比 LR 时最容易踩）
      —— 同源自证（更硬的那条）：重跑前后 `lr_v1.pkl` `789d57c1a1ad492fa3204a44695e89ce`、
         `rf_v1.pkl` `71731a270b679dc74b4006ba68c7856f`、`xgb_v1.pkl` `c436197daa4bccda9a08a60748e0107b`
         **完全一致** → 三个交付模型确由当前代码 + pin 环境逐字节可复现，无需重新签收
      —— 规格无需同步：`specs/model-delivery` 的 Requirement 本就要求「SHAP 依赖及其版本 pin（写入
         `requirements.txt`）」、Scenario 要求「按清单安装后加载与推理可跑通」—— 补 `joblib` 是**满足**它，
         不是改口径

## 5. 文档回填与规格同步

- [x] 5.1 `data_model/README.md` 末节「三个候选待定」改为已定 A+C，修正「模型线批量预测写 prediction 表」为「数据线产出 `prediction_result.csv`，后端灌库」—— 验证：文中不再有与铁规矩 4 冲突的表述
      —— 已完成：末节改为已裁定 A+C，并写明两条交付链的分工（数据线出文件、后端线灌库），
         与铁规矩 4「不建库表」不再冲突
- [x] 5.2 `docs/data-pipeline.md` 链路表补 ⑥⑦ 步（训练 / 导出与全量预测），复现命令补随机种子参数 —— 验证：按文档命令从干净 clone 重放可得一致结果
      —— 已完成：链路表补 ⑥ 时间序切分与训练、⑦ 全量预测两步，各步脚本与产物一一对应；
         复现命令段含 `--train/--test` 与随机种子参数；另注明 ⑥ 的两条口径与 ⑦ 的三条边界
- [x] 5.3 提交 PR 并在描述里写明关联 change id `model-training-and-delivery`，由非作者审阅合入 —— 验证：PR 链接与审阅记录
      —— PR #28 已提交，描述中写明关联 change id 与合并顺序
      —— **2026-09-19 已合入**：PR #28 合入 main（`31cd4b6`）；审阅人苏哲勋先 `CHANGES_REQUESTED`、
         复核后 **`APPROVED`** —— 非作者审阅留痕在 PR 上（含 four 处意见的修改记录）
