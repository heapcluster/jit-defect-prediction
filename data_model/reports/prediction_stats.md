# 全量预测结果统计（07_predict_all.py 产出）

> 本文件可入库。字段口径见 `docs/contracts/data-fields.md` 表三 `prediction`。
> **产出文件本身不入库**（`data/` 在 `.gitignore` 里）—— 它随包交付后端线，由后端导入。

## 产出

| 项 | 值 |
|---|---|
| 模型 | `xgb_v1`（`D:\workspace\code\course\jit-defect-prediction\data_model\models\xgb_v1.pkl`） |
| 推理条数 | 10893（全量，含检验集） |
| `feature_version` | `v1` |
| `predicted_at` | 2026-09-18 06:38:03（UTC） |
| 输出文件 | `D:\workspace\code\course\jit-defect-prediction\data_model\data\prediction_result.csv` |

## 风险分数分布

| 统计量 | 值 |
|---|---|
| 均值 | 0.46382 |
| 中位数 | 0.37709 |
| p95 | 0.98227 |
| `risk_score >= 0.5` 的条数 | 4900（44.98%） |

## 三条断言（tasks.md 4.2）

| 检查项 | 结果 |
|---|---|
| 字段与契约一表三**逐字一致**，无契约外字段 | ✅ 通过 |
| 列顺序与契约一表三一致 | ✅ 通过 |
| 脚本与依赖中**无任何数据库连接** | ✅ 通过（源码扫描 `sqlalchemy` / `pymysql` / `mysql.connector` / `sqlite3` / `psycopg2`，零命中） |

## 一个要一起看的数：高分占比 vs 真实正样本比例

`risk_score >= 0.5` 的占比（**44.98%**）是**模型输出侧**的「高风险」比例。
把它和 `reports/model_metrics.md` 里**检验集的真实正样本比例**并排看：

- 两者差得越远，说明模型**校准越偏**（高分判得过多），风险列表的 triage 区分度越弱 ——
  如果把「`>= 0.5`」直接当成「值得优先审」的门槛，等于没筛。
- 偏高的来源是两个已知事实叠加，都不是算错：
  ① **时间序切分**让训练集正样本比例显著高于检验集（见 `model_metrics.md` 的表头）；
  ② 契约三把判定阈值钉死为**服务端常量 `0.5`**，不能按检验集分布调。
- **两条都不在本 change 的范围内改。** 可选方向（都要走契约变更，不在实现里静默调）：
  ① 阈值语义改为「按高风险**配额**取前 N%」；② 训练侧加概率校准（Platt / isotonic）。

## 交付方式（A + C）

- **C（本文件）**：数据线产出 `prediction_result.csv`，**由后端线灌入 `prediction` 表**。
  数据线**不直连数据库、不写库**。
- **A（模型文件）**：`xgb_v1.pkl` + `models/feature_order.txt`（14 项特征顺序、
  依赖版本 pin、风险判定阈值）。该清单是契约二第三节的**副本**，不一致时以契约为准。
