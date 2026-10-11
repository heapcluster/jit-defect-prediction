# 数据链路与版本固定（模型包权威）

> 合并自原 `docs/data-pipeline.md`（已并入本文件）v1.1 ｜ 负责人：蒋励 ｜ 冻结：Sprint 0 末（10-02）
> Sprint 0 第 2 号交付物验收依据：可复现脚本 + 样本总数与正负样本比例。

## 0. 解决什么问题

Sprint 0 第 2 号交付物验收依据就是本文。权威边界：任务在飞书、代码在仓库。本文只写三件事：数据从哪来且固定在哪个版本、落在哪、每步脚本入口与复现命令。

## 1. 数据源

| 项 | 值 |
|---|---|
| 仓库 | `https://github.com/apache/activemq.git` |
| 仓库名（入库 `commit.repo_name`） | `activemq` |
| 本期范围 | 只用这一个仓库，不跨仓库训练对比 |

## 2. 版本固定（最重要）

**必须固定到某个 tag/commit，不用 `main`**（main 每天变，两个月后无法解释 F1 波动）。

固定信息登记（2026-09-16）：tag `activemq-5.18.7`（附注标签，对象哈希 `3d1f921d…`）｜ **完整 commit 哈希 `7c03f67d46ae290ca49d549215277ab384c2bb8a`** ｜ 抽取提交总数 **11,050**（过滤合并提交）｜ 跨度 2005-12-12~2025-03-13 ｜ 体积 139 MB / 5,334 文件。

为什么选 5.18.7：6.x 包名迁 `jakarta.*` 引入噪声；5.18 是 5.x 最后稳定线且历史连续。

## 3. 数据落盘路径

| 路径 | 内容 | 入库？ |
|---|---|---|
| `data_model/data/` | 仓库副本/中间数据 | ❌ 被 `.gitignore` 排除 |
| `data_model/models/` | 模型文件 | ❌ 排除 |
| `data_model/reports/` | 统计结果（样本数/比例/指标） | ✅ 可入库当证据 |
| `data_model/artifacts/` | 中间产物/缓存 | ❌ 排除 |

**不改 `.gitignore`、不用 `git add -f`** —— 数据集/模型不入库是课程硬要求。

## 4. 链路九步

```
① 克隆固定版本 → ② 抽取提交 → ③ SZZ 打标 → ④ Kamei14 特征 → ⑤ 样本集
                                                     ↓
                          ⑦ 全量预测出交付文件 ← ⑥ 时间序切分/训练/评估
                                                     ↓
                          ⑨ 校准与阈值证据 ← ⑧ 覆盖矩阵(8种/2类)
```

| 步 | 脚本 | 输出 |
|---|---|---|
| ① | 手工（§2 命令） | `data/activemq/` |
| ② | `01_extract_commits.py` | `commits.csv` + 统计 |
| ③ | `02_szz_labeling.py --method both` | `commit_labels_{szz,szz_lite}.csv` |
| ④ | `03_extract_features.py` | `commit_features.csv` |
| ⑤ | `04_build_dataset.py` | `dataset_{szz,szz_lite}.csv` + 七项统计 |
| ⑥ | `05_split_dataset.py` `06_train_model.py` | 切分文件/模型/指标报告 |
| ⑦ | `07_predict_all.py` | `prediction_result.csv` |
| ⑧ | `08_model_matrix.py` | `model_matrix.md`（8 种×2 类×两类指标） |
| ⑨ | `09_calibration_threshold.py` | `calibration_threshold.md` |

**⑥ 两条铁规矩**：只能时间序切分（禁随机，防时序泄漏）；两类指标都要报。
**⑦ 三条边界**：字段与契约一表三逐字一致；不直连数据库；全量推理（含检验集）。
**①–⑤** 属 change `data-collection-and-szz-labeling`；**⑥⑦** 属 `model-training-and-delivery`；**⑧⑨** 属 `model-expansion`。

## 5. 复现命令（从干净 clone）

```bash
cd data_model
git -C data/activemq rev-parse HEAD     # 必须等于 7c03f67d...
python 01_extract_commits.py
python 02_szz_labeling.py --method both
python 03_extract_features.py
python 04_build_dataset.py --labels data/commit_labels_szz.csv --labels data/commit_labels_szz_lite.csv
python 05_split_dataset.py --tag szz
python 06_train_model.py --train data/split_szz_train.csv --test data/split_szz_test.csv
python 07_predict_all.py --model models/xgb_v1.pkl
python 08_model_matrix.py
python 09_calibration_threshold.py
```

**⑥ 核对命令**：`python 05_split_dataset.py --selfcheck`（打乱输入断言必须拦住）；连跑两次 `06` 指标报告应逐行一致（仅 SHAP 计时行不同）。

**两条实测坑**：① 子集运行会覆盖全量四份统计报告（`--tag` 只改数据文件名不改报告名），跑完 `git checkout -- data_model/reports/` 恢复；② 改了 D4 判据必须重跑窗口对照，否则对照产物是旧口径。

## 6. 必须报出的统计

| 指标 | szz | szz_lite |
|---|---|---|
| 总提交数 | 11,050 | 11,050 |
| 打标成功数 | 10,893 | 10,880 |
| 正样本数 | 4,246 | 3,018 |
| 负样本数 | 6,647 | 7,862 |
| **正样本比例** | **38.98%** | **27.74%** |

**正样本比例判据**：实现里 `ABNORMAL_LOW,HIGH = 0.40,0.60` —— **落在 40%–60% 之间就停下来先查打标逻辑**，不要带可疑标签往下走。实测 38.98% 在区间外通过，但贴近 40% 下沿（正样本数 4,246 > 修复提交 2,417 正常，因 SZZ 一条修复可指控多个引入方；标准行级 SZZ 不做二次过滤，故意与 Kamei 可比）。

## 7. 关键裁定（待定项已结清）

- PySZZ 不在 PyPI → 两套均为自研实现（标准行级 + 文件级简化版）。
- 不裁剪时间窗口（全链路 24.5 分钟，在 Sprint 0 预算内）。
- 打标判据 D4：`AMQ-\d+` **且** `\b(fix|bug|patch)`（词首边界，排除 dispatch/debug/prefix 122 条假阳性）。

## 8. 变更日志（精简）

| 日期 | 版本 | 变更 |
|---|---|---|
| 2026-10-09 | 1.1 | 补权威边界指针；复现命令去 onboarding 引用 |
| 2026-09-19 | 1.0 | 链路扩到九步（补⑧⑨ 覆盖矩阵/校准阈值） |
| 2026-09-18 | 0.97~0.99 | 七步→九步、子集坑修正、Sprint 周期口径 |
| 2026-09-16 | 0.9~0.96 | 初版→全链路跑通→正样本比例判据统一 40%~60% |
