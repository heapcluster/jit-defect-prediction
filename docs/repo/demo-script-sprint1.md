# Sprint 1 端到端演示脚本（10/23 课上验收主证据）

> 负责人：蒋励 ｜ 用途：证明一条提交走完「风险列表 → 详情归因 → 趋势看板」完整链路
> 配套产物：本脚本 + 录屏，二者入库 `docs/` 或附 Issue 链接。
> 接口与错误码口径：`backend/api-spec.md`；页面口径：`docs/frontend/pages.md`。

## 0. 起服务与录屏准备（录屏前按序执行，2026-10-16 补 / 2026-10-24 按 #96/#97/#99 订正 / 2026-10-25 补实时同步口径）

### 0.0 建库与灌数（一次性；首次演示前）

```bash
cd backend
# 建表二选一：DDL 快照，或 ORM 初始化（两条路径都过索引自检）
# ⚠️ 库名固定为 jit_demo（演示库），不要写成 jit_defect —— 那份是占位脏数据，不能上台
mysql -u<user> -p jit_demo < ../infra/schema.sql
# python -m app.db init

# backend/.env 里把连接指向演示库
# DATABASE_URL=mysql+pymysql://jit:<pwd>@127.0.0.1:3306/jit_demo?charset=utf8mb4

# 依次灌四类数据，打印并留档每类入库行数
python -m app.ingest commits     ../data_model/data/commits.csv
python -m app.ingest labels      ../data_model/data/commit_labels_szz.csv
python -m app.ingest features    ../data_model/data/commit_features.csv
python -m app.ingest predictions ../data_model/pipelines/expert/data/prediction_result.csv
```

- 期望：`predictions` 入库 **83,943** 行（`xgb_v1`，`feature_version=v1`）。
- 权重目录：默认即 `data_model/pipelines/expert/models/`，不改 `MODEL_DIR` 也能加载（#99 自动插 `sys.path`）。
- **`backend/.env` 的 `API_TOKEN` 必须等于 `frontend/.env.local` 的 `VITE_API_KEY`**，否则前端全部 40100。
- **实时同步（新入口，随 PR #149 合入生效）**：起后端后 `POST /api/sync?limit=50` —— fetch SOURCE_REPO 最新提交 → 逐条现算特征 → 预测入库（口径见 `docs/common/local-runbook.md` §3.1）。#149 未合入前，本节灌数是唯一数据路径。

### 0.0.1 联调库与演示库统一为 MySQL（2026-10-25 裁定：废除双库，全项目一套 MySQL）

**联调、演示、录屏、T-ST-01~05 与系统层验收统一走 MySQL `jit_demo`。** 不再保留 SQLite 联调库（`dev.db`）；双库策略已废除，所有人 clone 后配好 `backend/.env` 的 `DATABASE_URL` 指向本机 `jit_demo` 即可。

| 库 | 连接 | 生成方式 | 数据规模 | 用在哪 |
|---|---|---|---|---|
| **`jit_demo`**（联调 / 演示 / 验收共用） | **MySQL `jit_demo`** | `python infra/setup_mysql.py` 一键建库建表（或 `mysql -u<user> -p jit_demo < ../infra/schema.sql` + `python -m app.db init`）→ 上面 4× `python -m app.ingest`；#149 合入后改用 `POST /api/sync` | 灌数口径：commits **84,461** / labels **83,943** / features **83,943** / predictions **83,943**，其中 `risk_score ≥ 0.5` 有 **14,596** 条（17.39%）；同步口径：窗口内 Camel 最新提交逐条现场预测 | 联调、演示、录屏、T-ST-01~05、系统层验收 |

- **数据库敲定为 MySQL**：`DATABASE_URL=mysql+pymysql://jit:<pwd>@127.0.0.1:3306/jit_demo?charset=utf8mb4`。不用 SQLite —— 演示要的是「真库 + 真实规模」，MySQL 也是课程验收与 Issue #121 的既定方向。
- **为什么废除 SQLite 联调库**：原 `integration-log.md` §0 定 SQLite 是为了零外部依赖，且 #117 的 9 张三态截图曾在该口径下取证；现统一 MySQL 后，新联调直接走 `jit_demo`，避免两套库带来的口径分裂。
- **历史说明（不影响现口径）**：早期 seed 三行 `risk_score` 最高 0.3，若用极小 seed 库跑 `min_risk=0.5&size=5` 自检会为空；联调与演示现都用 `jit_demo` 的真实规模数据，不踩此坑。
- **前置（先解，否则跑不起来）**：每人本机 MySQL，配好 `jit` 账号与库（一键脚本 `infra/setup_mysql.py` 会建 `jit_demo` 与测试库 `jit_test` 并授权；`jit` 通常无 `CREATE DATABASE`，脚本支持 `--root-password` 由 root 代建）。现有 `jit_defect` 里的 2 提交 / 4 预测是**占位脏数据**（假哈希 `1111…`/`2222…`、`repo_name=activemq`、`smoke_v1`/`tree_placeholder_v0`），按 §5 第 4 条「演示 `commit_hash` 必须与库中真实数据一致」**不能上台**；用新建的干净库 `jit_demo`，`jit_defect` 的存量由 infra 处置，不在演示路径上。
- 灌数只走 `app.ingest`，**不许手工改库**。#149 合入后切到 `/api/sync` 时，同样只走接口、不手工改库。
- 录屏前跑一次 `backend/scripts/demo_preflight.py`（Issue #138，后端线；PR #151 起支持 `--init-db --ingest` 一条命令建库+灌数）：按本节口径逐项自检，任一不满足退出码 1 并打印实际值。注意其六条判据**不比对 `commit_feature` 的值**——灌错特征表（raw 那份）也会全绿，判别方法见 `docs/backend/mysql-setup.md` §4。

### 0.1 起后端（终端 A）

```bash
# 依赖统一在 data_model/environment.yml（backend 不再有 requirements.txt）
conda env create -f data_model/environment.yml   # 首次
conda activate jit-defect-prediction
cd backend
uvicorn app.main:app --reload --port 8000
```

自检：`curl -s -o /dev/null -w "%{http_code}" -H "X-API-Key: $KEY" http://localhost:8000/api/commits` → `200`。

### 0.2 起前端（终端 B）

```bash
cd frontend
npm ci
npm run dev          # Vite 默认 http://localhost:5173
```

### 0.3 录屏前数据自检（终端 C）

```bash
# 演示步骤 1 需要「至少 1 条 risk_score >= 0.5」的高风险提交
curl -s -H "X-API-Key: $KEY" "http://localhost:8000/api/commits?min_risk=0.5&size=5" | head -c 400
```

- 返回为空 → 先由后端线把 `data_model/pipelines/expert/predict.py` 产出的 `prediction_result.csv` 灌库（#149 合入后改为 `POST /api/sync?limit=50`）；
  **不要在演示现场临时造数据**（演示所用 `commit_hash` 必须与库中真实数据一致，见 §5 第 4 条）。

### 0.4 录屏设置

| 项 | 要求 |
|---|---|
| 分辨率 / 帧率 | 1920×1080 / 30fps（代码与数字可辨） |
| 画面 | 全屏浏览器 + 终端同屏，或分段剪辑（列表/详情/趋势各一段） |
| 音频 | 需口播（按 §2 / §3 的「口播」行） |
| 命名 | `demo-sprint1-YYYYMMDD.mp4` |

> 本节的启动命令取自 `backend/README.md` 与 `frontend/package.json`；命令若变更，以那两处为准。

## 1. 前置（演示前逐项确认）

| 项 | 确认方式 | 通过标准 |
|---|---|---|
| 后端已起 | `curl -s -o /dev/null -w "%{http_code}" -H "X-API-Key: $KEY" http://localhost:8000/api/commits` | 返回 `200` |
| 交付模型已加载 | 启动日志搜 `model_name` / 搜 `failed models` | 出现 `lr_v1` / `rf_v1` / `xgb_v1` **三个**，且无 `model load failed`（#96 定：在线模型集 = `feature_order.txt` 的 `[models]` 段） |
| 预测结果已入库 | `SELECT COUNT(*) FROM prediction;` | 83,943（只少不多即为灌数未完成；`0` 时不要临场造数）；#149 合入后改为「同步后 `new` 递减至 0」 |
| 前端三页面可访问 | 浏览器打开列表 / 详情 / 趋势三页 | 三页均渲染，非白屏 |

## 2. 正向演示（主链路，一条提交走完三段）

### 步骤 1 — 风险列表（被预警）

```
GET /api/commits?min_risk=0.5&size=20
Header: X-API-Key: <KEY>
```

- 预期：`code=0`，`data.items` 按 `risk_score` 降序；因 `min_risk=0.5`，返回首行 `risk_score` ≥ 0.5，确属高风险。
- 页面动作：打开「风险列表」页，取**第 1 条**高风险提交（已 ≥ 0.5），记下其 `commit_hash`（下称 `$HASH`）。

### 步骤 2 — 详情归因（被解释）

```
GET /api/commits/$HASH
Header: X-API-Key: <KEY>
```

- 预期：返回 `risk_score` 与 `explanation`（每项含 `feature` / `contribution` / `direction`）。
- 页面动作：点进「提交详情」页，确认展示风险分 + SHAP 归因排序。

### 步骤 3 — 趋势看板（被观察）

```
GET /api/trends
Header: X-API-Key: <KEY>
```

- 预期：返回按时间的风险序列。
- 页面动作：打开「趋势看板」，定位 `$HASH` 所处时段。

### 步骤 4 — 换模型重预测（可选加分项；#90 合并后可用）

> **T-ST-04 计数口径（2026-10-25 组长裁定）**：`prediction` 表按 `(commit_hash, model_name)` 各留一行，演示库基线是 `xgb_v1` 的 **83,943** 行（`risk_score≥0.5` 14,596、`trends` 236 期）。现场再用 `lr_v1` / `rf_v1` 各 POST 一次会**新增 2 行 → 83,945** —— 这是预期行为，不是缺陷。
> - **不写死单一数字**：脚本与判据同时登记三个数「基线 **83,943** / 演后 **83,945** / 恢复 **83,943**」。
> - **演完按备份清一次**（后端同学已执行过一次：恢复 83,943、`risk_score≥0.5` 14,596、非 `xgb` 0 行）。

```
POST /api/predict
Header: X-API-Key: <KEY>
Body: {"commit_hash": "$HASH", "model_name": "rf_v1"}
```

- 预期：`code=0`，返回 `risk_score` + `model_name` + `predicted_at` + `explanation`；同一 hash 连调两次**不产生第二行** prediction（幂等 upsert）。
- 页面动作：详情页「重新预测」下拉切 `xgb_v1` → `rf_v1`，分数就地刷新、不刷新整个页面。
- 注：#90 未合入前前端没有入口，则走 curl 版本，口播说明「接口已通、页面入口随 #90 上」。
- 另一条可选项（更能体现「在线推理」而非只展示历史分数）：换一条**库里没有预测**的提交直接调 `POST /api/predict`，后端会现算 14 维特征（#97）。

**口播**：一条提交从"被预警"到"被解释"到"被观察"，再到"换模型重算"，闭环成立。

## 3. 异常输入验证（A / B 必录，C 建议录）

### A. 无效 API Key → 401

```
curl -i -H "X-API-Key: wrong-key" http://localhost:8000/api/commits
```

- 预期：HTTP `401`，`code=40100`；响应体 **不得**出现堆栈、SQL 语句、文件路径。

### B. 畸形 commit_hash → 400（**不是 404**）

```
curl -i -H "X-API-Key: $KEY" http://localhost:8000/api/commits/zzzz
```

- 预期：HTTP `400`，`code=40001`，`message` = 「参数非法：commit_hash 需为 40 位十六进制」。
- 口径依据：`backend/app/api/commits.py:45-47` —— 长度≠40 或非十六进制先判**参数非法（40001）**。

### C. 合法格式但不存在的 commit_hash → 404

```
curl -i -H "X-API-Key: $KEY" http://localhost:8000/api/commits/0000000000000000000000000000000000000000
```

- 预期：HTTP `404`，`code=40400`；**页面展示空态而非崩溃**。

> A/B/C 三者均为契约约定的错误码，不属于自造错误码。演示时务必区分 B 与 C：拿 `zzzz` 演示 404 会当场被问住。

## 4. 录屏要求

| 项 | 要求 |
|---|---|
| 命名 | `demo-sprint1-YYYYMMDD.mp4` |
| 内容顺序 | 列表 → 详情归因 → 趋势看板 → 换模型重预测（可选）→ 异常用例（单独一段） |
| 归档 | 入库 `docs/` 或附到 Issue，并在飞书看板本行「关联链接」填写该地址 |

> 说明：录屏需人工实际执行演示录制，脚本本身不产生录屏文件。

## 5. 验收对账（演示后自评）

- [ ] 三段主链路连续走通，无中断
- [ ] 至少一项异常用例返回预期错误码且页面不崩
- [ ] 错误码未混用：缺令牌 `40100` / 畸形 hash `40001` / 合法但不存在 `40400`（拿 `zzzz` 演示 404 属口径错误）
- [ ] 录屏文件已归档，看板「关联链接」可点开
- [ ] 演示所用 `commit_hash` 与库中真实数据一致（可复现）
