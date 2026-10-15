# 代码项目开工手册（common 包权威）

> 合并自原 `docs/dev-handbook.md`（已并入本文件）v1.2 ｜ 负责人：蒋励 ｜ 审核：苏哲勋
> 新人按本文能在自己机器跑通整条链路。改了口径/依赖，所有下游产物重跑（见 `model/data-pipeline.md` 坑）。

## 1. 找到代码

`git clone <repo>` → 根目录即项目；`python --version` 3.11+；能连 GitHub（直连困难走 `127.0.0.1:7890`）。

## 2. 跑通数据线（蒋励线）

```bash
cd data_model
pip install -r requirements.txt
git -C data/camel rev-parse HEAD   # 必须等于 b2329103df8f5d1edfca2ad262be09e3be95ee68
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

## 3. 接/跑模型（吕建江线）

- 不直接 `pickle.load` 拿 xgb：用 `joblib.load`（lr/rf 是 joblib 格式、xgb 是标准 pickle，后者不兼容前者）。
- 特征顺序以 `feature-columns.md` 为准，不另发清单；特征取值口径照 `02_szz_labeling.py` 与 `03_*`。

## 4. 前端（刘帅华线）

技术栈 Vue3+ElementPlus+ECharts；`X-API-Key` 经 `import.meta.env` 注入，不硬编码；字段名照 `docs/frontend/pages.md` 不驼峰转换。

## 5. 后端（吕建江线）

FastAPI+SQLAlchemy+MySQL（开发期可 SQLite）；`create_all()` 建四表；四接口照 `docs/backend/api-spec.md`；`50000` 不回显内部。

## 6. 文档

- 写文档照 `docs/common/writing-norms.md`；改契约走 `docs/common/openspec-rules.md`。
- 看板状态/PR/周报照 `docs/repo/` 各文件。

## 7. 库表与接口落地（吕建江线，落库即实现）

| 表 | 字段 | 落库形式 |
|---|---|---|
| `commit` | `commit_hash`(PK) `repo_name` `author_name` `committed_at` `message` | 抽取脚本入库 |
| `commit_label` | `commit_hash`+`label_method`(复合 PK) `is_bug_inducing` | SZZ 入库 |
| `commit_feature` | `commit_hash`(PK)+`ns…sexp`(14) | 特征脚本入库 |
| `prediction` | `commit_hash`+`model_name`(复合 PK) `risk_score` `predicted_at` | A+C 共用 |

> 完整字段见 `docs/design/database.md`（契约一）。

## 8. 收尾

改完跑该线自检（lint/test）；开 PR 描述四件事（改什么/为什么/怎么验证/关联）；等非作者审阅；Squash 合入后删分支。
