# path-references-alignment — 路径扫描证据

> 产出时间：2026-10-23 ｜ 执行者：model 蒋励 ｜ 基线：`main` @ `3a9b7b0`
> 复现环境：conda `jit-defect-prediction`（Python 3.12.x，仓库根执行）

## 1. 修订后路径存在性（5/5 必须为 True）

| # | 路径 | `Test-Path` |
|---|---|---|
| 1 | `data_model/preparation/reports/` | True |
| 2 | `data_model/preparation/reports/feature_stats.md` | True |
| 3 | `data_model/pipelines/expert/reports/` | True |
| 4 | `data_model/pipelines/expert/models/feature_order.txt` | True |
| 5 | `python -m pipelines.expert.predict` → `data_model/pipelines/expert/predict.py` | True |

附带核对（本 change 引用的切分入口已随四包迁移搬家）：

| # | 路径 | `Test-Path` |
|---|---|---|
| 6 | `data_model/preparation/05_split_dataset.py` | True |

复现命令：

```powershell
foreach ($p in @(
  "data_model/preparation/reports",
  "data_model/preparation/reports/feature_stats.md",
  "data_model/pipelines/expert/reports",
  "data_model/pipelines/expert/models/feature_order.txt",
  "data_model/pipelines/expert/predict.py",
  "data_model/preparation/05_split_dataset.py"
)) { "{0,-60} {1}" -f $p, (Test-Path $p) }
```

## 2. 活规格残留旧路径扫描（合入本 change 前）

对 `openspec/specs/*/spec.md` 扫描 `data_model/reports/`、`data_model/0X_*.py`、`06_train_model`、
`07_predict_all`、`08_model_matrix`、`09_calibration`、`16_statistical` 七个旧路径模式：

| 规格 | 行 | 旧引用 | 本 change 覆盖 |
|---|---|---|---|
| `commit-collection/spec.md` | 57 | `data_model/reports/` | §1.1 MODIFIED |
| `feature-extraction/spec.md` | 38 | `data_model/reports/feature_stats.md` | §1.3 MODIFIED |
| `labeled-dataset/spec.md` | 29 | `data_model/reports/` | §1.2 MODIFIED |
| `model-coverage/spec.md` | 10 | `data_model/reports/` | §1.5 MODIFIED |
| `model-coverage/spec.md` | 70 | `07_predict_all.py`、`models/feature_order.txt` | §1.5 MODIFIED |
| `model-training/spec.md` | 50 | `data_model/reports/` | §1.4 MODIFIED |

6 处命中全部落在 5 份 MODIFIED delta 的覆盖范围内；归档本 change 后复扫为 0 处。

## 3. 进行中 change 的路径引用同步

| change | 文件 | 修订 |
|---|---|---|
| `semantic-feature-mainline` | `tasks.md` §7.2 | `05_split_dataset.py` → `data_model/preparation/05_split_dataset.py` |
| `semantic-feature-mainline` | `design.md` | 同上 |
| `frontend-integration` | `design.md` | `data_model/06_train_model.py` → `python -m pipelines.expert.train`（并写明训练口径 8 个） |
| `public-dataset-quality` | `tasks.md` / `proposal.md` / `specs/public-dataset/spec.md` | 无 `data_model/reports/` 引用，无需修订 |

## 4. 校验与测试证据

| 项 | 命令 | 结果 |
|---|---|---|
| 严格校验（全量） | `openspec validate --all` | 19 passed, 0 failed |
| 严格校验（本 change） | `openspec validate path-references-alignment --strict` | 通过（见任务 3.1） |
| 集成层回归（main 树） | `cd data_model && python -m pytest -q` | 100 collected ｜ 99 passed, 1 skipped, 0 failed（26.5s） |
| 语义未改 | `git diff -- openspec/specs` | 本 change 未直接改 `openspec/specs/**`，改动只经 delta 在归档时应用 |

说明：`model-training/spec.md` 等 6 处的实际替换发生在本 change 归档（`openspec archive`）时由
MODIFIED delta 写入活规格；归档后再跑一次 §2 的扫描作为验收。

## 5. 已知缺口

| 缺口 | 状态 |
|---|---|
| 归档后复扫活规格（应为 0 处旧路径） | 归档同一 PR 内执行，见 PR 描述的第 3 步输出 |
| `data_model` 用例数随分支不同（本条基线 99 passed / 1 skipped） | 已按「逐分支实测」口径记录，不用单一数字冒充三线一致 |
