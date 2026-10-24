# 三端联调实测记录 2026-10-24（建库 → 4×ingest → 起服务 → 四接口 → 幂等 → 压测，一条命令链）

- 目的：`test-plan.md` §4.2 T-IT-01~03 与 `docs/backend/acceptance.md` 三端联调条款的**正式执行记录**。此前仓库里只有套件内 SQLite 级联调（`backend/tests/test_integration_api.py` 6 条，夹具模型 + 合成 CSV）与 2026-10-16 的种子库真服务记录（`predict-real-models-2026-10-16.md`，3 行数据），都**不等于**「真实全量数据 + 真交付权重 + 真服务」的联调；本文件补上这一层。
- 基线：main `0773a49`（`backend/app` 与被测树逐字一致）
- 执行方式：**一条驱动脚本顺序跑完全部步骤**（`it_20261024_driver.py`，本机临时目录，不入库），任一步 rc≠0 立即停、不产出半成品；全部 stdout 逐字进 `it_run.log`，接口响应逐字进 `transcripts.md`。
- 环境：Windows 11 / Python 3.12.7（仓库根 `.venv`）/ fastapi 0.141.1 / uvicorn 0.53.0 / SQLAlchemy 2.0.54 / scikit-learn 1.9.1 / xgboost 3.4.1 / shap 0.52.0；服务 `http://127.0.0.1:8024`（PID 55812）
- 数据库：**SQLite 隔离文件库** `it.db`（从空文件建库）。**本轮不用 MySQL**：本机 `jit` 账号只有 `GRANT ALL ON jit_defect.*` 与全局 `USAGE`、无 `CREATE DATABASE`，而 `jit_defect` 已有四表与演示占位数据、不是隔离空库；MySQL 侧待苏哲勋授权隔离库后补跑，补跑前本文件数字不代表 MySQL。
- 模型：真交付权重目录（8 个 `.pkl` + `feature_order.txt`，`[models]` = lr/rf/xgb，md5 与 2026-10-24 交付包一致）
- 测量时间：2026-10-24 14:26–14:31（+08:00）

## 1. 建库：空文件 → 四表 0 行

```text
$ DATABASE_URL="sqlite:///<tmp>/it.db" python -m app.db init
四张表建表完成：commit / commit_label / commit_feature / prediction
[14:26:43] 建库后行数: {'commit': 0, 'commit_label': 0, 'commit_feature': 0, 'prediction': 0}
```

`init_db()` 在 `create_all` 后跑 `_assert_indexes()`（`INDEX_ASSERTIONS`）：`prediction(commit_hash, model_name)` 与 `commit_label(commit_hash, label_method)` 唯一、`commit.committed_at` / `commit_label.commit_hash` / `prediction.commit_hash` 普通索引在位；自检不过会抛 `RuntimeError`，本轮通过。MySQL 方言的同一套断言由 `backend/tests/test_schema_sql.py`（25 条）对 `infra/schema.sql` 静态校验覆盖。

## 2. 灌库：四类 CSV 各灌两遍，行数不变（幂等）

| 步骤 | 命令 | 行数 | 第 1 遍耗时 | 第 2 遍后行数 | 幂等 |
|---|---|---|---|---|---|
| commits | `python -m app.ingest commits <commits.csv>` | 84,461 | 31.2s | `commit`=84,461 | ✅ |
| labels | `python -m app.ingest labels <labels.csv>` | 83,943 | 33.5s | `commit_label`=83,943 | ✅ |
| features | `python -m app.ingest features <features.csv>` | 83,943 | 32.6s | `commit_feature`=83,943 | ✅ |
| predictions | `python -m app.ingest predictions <predictions.csv>` | 83,943 | 33.5s | `prediction`=83,943 | ✅ |

每遍都打印 `灌入完成（<kind>）：N 行`；第二遍跑完与第一遍的行数逐表相同（upsert 按业务键更新、不产生重复行）。灌完合计：

```text
[14:31:03] 灌库完成: {'commit': 84461, 'commit_label': 83943, 'commit_feature': 83943, 'prediction': 83943}
```

**predictions 恰为 83,943 行**（交办口径），`model_name` 全为 `xgb_v1`、`feature_version` 全为 `v1`。

### 2.1 四份 CSV 的来源（不造数，逐份可追）

| CSV | 来源 | 说明 |
|---|---|---|
| commits（84,461） | `python -m preparation.01_extract_commits` 于 2026-10-24 12:33 重跑产出 | 列 = `repo_name, commit_hash, author_name, author_email, committed_at, message, parent_hash`，与 `_upsert_commits` 要求逐字对齐；行数与登记基线 84,461 一致 |
| labels（83,943） | 由**已登记**的 `data_model/data/dataset_szz.csv` 投影 `commit_hash, is_bug_inducing, label_method, bug_fix_hash`，`labeled_at` 钉为派生时间 `2026-10-24 06:24:31`（UTC） | `dataset_szz.csv` 不带 `labeled_at`（02 脚本的元数据列，重跑取当前时间、可用 `--labeled-at` 钉住），故派生时显式钉值并在本行注明；正样本 18,662（= 训练 15,040 + 检验 3,622），`label_method` 全为 `szz` |
| features（83,943） | 同一份 `dataset_szz.csv` 投影 `commit_hash, committed_at, feature_version` + 契约二 14 列 | 不重算特征，直接用已登记数据 |
| predictions（83,943） | `python -m pipelines.expert.predict`（模型线官方入口，`--model` 默认 `xgb_v1.pkl`）于 14:25 实跑 | 脚本自校验「字段 = 契约一表三且顺序一致」通过；`risk_score` 范围 3e-05–0.9993，≥0.5 的 14,596 条（17.39%） |

**复现性交叉校验（补记，2026-10-24 15:26 完成）**：`preparation.02_szz_labeling --method szz` 的独立重跑已结束（7,787 条修复提交全跑完，耗时 10,372.2s）：正样本 **18,662** / 负样本 65,281 / 比例 22.23% / 未命中 742，产出 `data/commit_labels_szz.csv` **83,943 行**。与本记录灌库所用派生 labels 取交集 = 83,943 行，且 `is_bug_inducing` **逐行一致 ✅** —— 派生口径与独立重跑口径零差异，本记录 §2.1 的 labels 来源成立。重跑同批复产 predictions（expert 官方入口、83,943 行、`model_name=xgb_v1`），与本记录灌库所用 predictions 同脚本同口径（`predicted_at` 时间戳不同，属元数据）。该校验是模型线复现性口径（±0）的又一实例，不改变本记录既有数字。

**三线产物灌库兼容性（补记，2026-10-24 17:5x）**：会进 `app.ingest predictions` 的只有 expert 与 e2e 两条线的 `prediction_result.csv`（semantic / fused 的产物是 `*_v1.pkl` + `manifest.txt` + 报告 + 图，不产预测 CSV，见 `config-and-output-spec.md` §3.4 产物表）。expert 那份即本记录 §2 灌入的 83,943 行；**e2e 那份（10-23 重跑产出，`model_name=codebert_e2e_v1`、`feature_version=codebert`）已在新空库上实测灌入：`app.db init` → ingest commits 84,461 → ingest predictions 83,943，rc=0、列序与契约一表三逐字一致**。故 semantic/fused 重跑（占位判定口径已由 #118 修回裁定口径并合入 main `afb2fa1`）不引入新的灌库面；若将来 e2e 重训改字段，脚本自带的表头自校验（多/缺字段 → 退出码 1）会先拦下。

**联调口径指针（补记）**：本记录只覆盖**后端侧**链路（建库 / 灌库 / 服务 / 四接口 / 幂等 / 压测）。前端三页面与后端的联调口径**唯一权威 = `docs/frontend/integration-log.md` §0 联调基线**（2026-10-24 蒋励定；`docs/repo/collaboration.md` §0 第 2 条「联调只认 §0」。§0 由 PR #117 入库，#117 合入前对应该文件文首「环境与启动」段）。本记录不另立口径、不代替前端实测。

两处不要混淆：① 本记录为**后端验收跑**，库是一次性隔离空库 + 83,943 行真实数据（命令里的 `sqlite:///<tmp>/it.db`），跑完即弃；② §0 的**联调库**只有 `backend/dev.db` 一份，由 `scripts.seed_dev_data` 生成（3 提交 / 3 特征 / 3 预测）。前后端联调、截图取证一律用 ②，不要拿 ① 当联调库；本记录已实测 §0 的后端三行——`cd backend` 后 `python -m scripts.seed_dev_data` 可不带 `PYTHONPATH` 直接跑通（rc=0）、重跑幂等、库内 3/0/3/3 行且 `commit_hash` = `000…001`~`000…003`，与 §0 表逐字一致。

## 3. 起服务：三个交付模型全部加载、无失败行

```text
INFO:     Started server process [55812]
INFO:     Waiting for application startup.
INFO:backend.model_registry:loaded models: ['lr_v1', 'rf_v1', 'xgb_v1']
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8024 (Press CTRL+C to quit)
```

`MODEL_DIR` 指向含 **8 个** `.pkl` 的目录，注册表按 `feature_order.txt` 的 `[models]` 段只载入交付清单三个（#96 口径）；日志**没有** `failed models:` / `model load failed` 行（#99 的失败汇总钩子未触发）。

## 4. 四个接口各一发（真服务、真数据、带令牌）

| # | 请求 | 结果 | 关键断言 |
|---|---|---|---|
| 1 | `GET /api/commits?size=3` | HTTP 200，3,803 字节 | `data.total` = **83,943**（与灌入的 prediction 行数一致）；`items` 按 `risk_score` 降序（0.9993 / 0.99905 / 0.99905）；首条 `commit_hash=3f166232023e04689bfa3814a569920e30fef42b`、`model_name=xgb_v1` |
| 2 | `GET /api/commits/3f166232…` | HTTP 200，2,331 字节 | `features` 恰为契约二 14 键（`ns…sexp`，逐字）；`explanation` 14 条、键为 `feature/contribution/direction`；`risk_score=0.9993` 与列表首条同源 |
| 3 | `GET /api/trends?granularity=month` | HTTP 200，18,735 字节 | `series` **236 期**（2007-03 → 2026-10），各期 `commit_count` 之和 = **83,943**（每条预测恰被聚合一次，无重无漏）；`model_name=xgb_v1` |
| 4 | `POST /api/predict`（不传 `model_name`） | HTTP 200，1,336 字节 | 默认模型 `xgb_v1`；`predicted_at` 为本次调用时间（ISO-8601 Z）；`features` 回显 14 项与库内一致 |

响应全文在 `transcripts.md`（列表与详情的 `message` 含真实提交信息原文、趋势含 236 期全量，故单条最大 18.7 kB；本表只摘录断言字段，不截断原始文件）。

## 5. 三个交付模型逐个 `model_name` + 非法枚举（T9 / #99 tasks 3.3）

| 请求 | 结果 | `risk_score` | `explanation` 条数 |
|---|---|---|---|
| `model_name=lr_v1` | HTTP 200 | 0.91203 | 10（零贡献项被线性解释器省略，非空 ✅） |
| `model_name=rf_v1` | HTTP 200 | 0.90499 | 14 ✅ |
| `model_name=xgb_v1` | HTTP 200 | 0.99930 | 14 ✅ |
| `model_name=not_a_model_v9` | HTTP 400 `code=40001` | — | message「参数非法：model_name 不在已加载模型清单」 |

三个模型的 `explanation` 键名都能回溯到契约二 14 项特征；同一提交上三模型给出不同分数（0.912 / 0.905 / 0.999），说明切换真实生效而非回退默认。

实拍截图 `integration-shot-predict.png`：无头 Edge 对本服务发起**真实** `POST /api/predict`（默认模型）后渲染 —— 状态行 `HTTP/1.1 200 OK`、`code==0`、`model_name==xgb_v1`、`risk_score=0.9993`、`features` 14 键、`explanation` 14 条非空，响应体节选与截断字节数都在图内；抓取时间 2026-10-24 14:42:14（+08:00）。该图同时充当 `delivery-model-allowlist` tasks 2.1 要的「真实加载与预测截图」的预测半张（加载半张是 §3 的启动日志）。

## 6. 幂等：同一哈希 POST 两次，`prediction` 只留一行

```text
[14:31:15] 预测 POST /api/predict 第1次: HTTP 200 … "model_name":"xgb_v1","risk_score":0.9993 …
[14:31:15] 预测 POST /api/predict 第2次: HTTP 200 … "model_name":"xgb_v1","risk_score":0.9993 …
[14:31:15] 同哈希两次预测后的 prediction 分组:
           [('3f166232…', 'lr_v1', 1), ('3f166232…', 'rf_v1', 1), ('3f166232…', 'xgb_v1', 1)]
```

默认模型键 `(hash, xgb_v1)` 在两次 POST 后**恰 1 行**（第二次走 update 分支，`predicted_at` 更新、行数不变）；`lr_v1` / `rf_v1` 各 1 行是 §5 显式指定 `model_name` 产生的**不同业务键**，符合契约「按 `(commit_hash, model_name)` 只留最新一行」。结束时全表 83,945 = 83,943 + lr + rf 两行，账目闭合。

## 7. 压测（同一条链内顺手产出，正式证据另见 perf 文件）

```text
[14:31:17] --- perf_loop n=100 rc=0 elapsed=1.9s
p50=9.7ms p95=11.9ms p99=16.9ms max=50.2ms → 达标
```

靶子 `POST /api/predict`、100 次全成功；分位数口径与冷启动对照、分模型结果、`rf_v1` 未达标的处置见 `perf-2026-10-24.md`（本行即其 #2「官方·预热」）。

## 8. 本记录**不**覆盖什么（不冒充）

- **MySQL**：见首段；`infra/schema.sql` 的 MySQL 方言正确性由 `test_schema_sql.py` 25 条静态校验 + 待授权的实机建库补跑覆盖。
- **前端页面层**：本记录止于 HTTP 接口；三页面的渲染与三态属 T-ST/前端线联调（`frontend/implementation.md`），且 T-FE-01/02 组件级用例仍 0 覆盖（`test-report-sprint2.md` §2.4）。
- **录屏**：课程 T-ST 要求的端到端录屏待演示排期，本记录提供的是可复跑的命令链与逐字转录，不代替录屏。
- **02 重跑交叉校验**：见 §2.1，进行中，结论以补记行回填。

## 9. 复现命令（一条链）

```bash
RUN=<临时目录>
export DATABASE_URL="sqlite:///$RUN/it.db" API_TOKEN=*** \
       MODEL_DIR=<含 feature_order.txt 与 8 个 .pkl 的目录>

# ① 建库 + 灌库（两遍验幂等）
python -m app.db init
for k in commits labels features predictions; do
  python -m app.ingest $k <对应 CSV> && python -m app.ingest $k <对应 CSV>
done

# ② 起服务并确认加载日志
python -m uvicorn app.main:app --host 127.0.0.1 --port 8024
#   期望：loaded models: ['lr_v1', 'rf_v1', 'xgb_v1']，无 failed models 行

# ③ 四接口 + 逐模型 + 幂等 + 压测
curl -sS -H "X-API-Key: ***" "http://127.0.0.1:8024/api/commits?size=3"
curl -sS -H "X-API-Key: ***" "http://127.0.0.1:8024/api/commits/<top>"
curl -sS -H "X-API-Key: ***" "http://127.0.0.1:8024/api/trends?granularity=month"
curl -sS -X POST -H "X-API-Key: ***" -H "Content-Type: application/json" \
     -d '{"commit_hash":"<top>"}' http://127.0.0.1:8024/api/predict   # 连发两次验幂等
python scripts/perf_loop.py --base-url http://127.0.0.1:8024 --n 100 --model-source "…" --out <tmp>/perf.md

# ④ 被测树等价性核对（cwd=仓库根）
git merge-base --is-ancestor 0773a49 HEAD && echo ok
git diff --name-only 0773a49 HEAD -- backend/   # 期望：只有本目录新增文件
```

## 10. 口径与引用

- 看板「前后端联调 / 三端联调」行与 `docs/backend/acceptance.md` 的联调条款改引**本文件**；`predict-real-models-2026-10-16.md` 降为「种子库真服务记录」（3 行数据），不再作为全量联调证据。
- 本文件只记已发生的执行；MySQL 补跑、02 交叉校验结论、前端页面层联调分别以补记行或新文件追加，不倒填既有数字。
