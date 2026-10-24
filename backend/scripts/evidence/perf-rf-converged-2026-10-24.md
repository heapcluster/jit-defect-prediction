# D-14 复测：收敛后 `rf_v1` 的端到端分位数

- 日期：2026-10-24
- 对应裁定：`docs/repo/defect-records.md` **D-14** 选 ③「优化 rf 在线推理，不改契约枚举、不改 500ms 靶子」
- 前一份证据：[`perf-2026-10-24.md`](perf-2026-10-24.md)（收敛前：`rf_v1` p50 653.0 / p95 713.8 / p99 751.0ms，未达标）
- 根因证据：`docs/model/evidence/rf-shap-2026-10-24.md`（慢在 SHAP 遍历 366 万节点，不是 `predict_proba`）

## 1. 改动

**只动 `rf` 一棵树，不动特征、不动切分、不动其他 7 个模型。**

| 项 | 收敛前 | 收敛后 |
|---|---|---|
| `n_estimators` | 300 | 300（不变） |
| `min_samples_leaf` | 2 | **100** |
| `max_depth` | `None`（实际平均 34.4） | **15**（实际平均 14.9） |
| 节点总数 | 3,660,998 | **157,420**（降 23.3 倍） |
| `rf_v1.pkl` | 279.4 MB | **12.1 MB** |

## 2. 效果（`POST /api/predict`，`model_name=rf_v1`，同哈希重复请求）

预热 5 次后连续 30 次：

| 分位 | 收敛前 | 收敛后 |
|---|---|---|
| p50 | 653.0 ms | **95.0 ms** |
| p95 | 713.8 ms | **127.7 ms** |
| p99 | 751.0 ms | **130.6 ms** |
| max | 1638.6 ms | **130.6 ms** |

**p95 127.7ms < 500ms 靶子，达标。**

## 3. 精度代价（验收条件：AUC 降 ≤ 0.01）

| 模型 | AUC | F1 | Precision | Recall |
|---|---|---|---|---|
| `rf_v1` 收敛前 | 0.8190 | 0.4083 | 0.5215 | 0.3355 |
| `rf_v1` 收敛后 | **0.8169** | 0.3659 | 0.5321 | 0.2789 |
| 差 | **−0.0021**（≤0.01 ✅） | −0.0424 | +0.0106 | −0.0566 |

Effort-aware 侧反而略好（`P_norm` 由 −0.1955 升到 **−0.0627**，`Recall@20%` 0.1789→0.1543 略降，20% 预算审到的条数 1033→958）。

> F1 与 Recall 下降是模板：`min_samples_leaf=100` 把概率推向中间区，阈值 0.5 附近的正例被压到线下。裁定只约束 AUC（≤0.01），未约束 F1；若后续要求 F1 回到 0.40 以上，应重标阈值（走 change）而不是回退模型规模。

## 4. 复现

```bash
# 1) 重训（只训 rf，其余权重不动）
cd data_model && python -m pipelines.expert.train --models rf

# 2) 重建清单 md5
python -m pipelines.verify_all_weights --write-manifest

# 3) 起服务（MODEL_DIR 留空即用 repo 内权重）
cd ../backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 4) 压测：预热 5 次 + 连续 30 次 POST /api/predict（body 见下），取 p50/p95/p99
#    {"commit_hash":"0000000000000000000000000000000000000001","model_name":"rf_v1"}
```

环境：Windows 11 / Python 3.12.15 / scikit-learn 与 shap 按 `data_model/environment.yml`；联调库按 `docs/frontend/integration-log.md` §0（SQLite + `seed_dev_data.py`）。
