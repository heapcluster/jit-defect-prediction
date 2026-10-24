# Sprint 1 端到端演示脚本（10/23 课上验收主证据）

> 负责人：蒋励 ｜ 用途：证明一条提交走完「风险列表 → 详情归因 → 趋势看板」完整链路
> 配套产物：本脚本 + 录屏，二者入库 `docs/` 或附 Issue 链接。
> 接口与错误码口径：`backend/api-spec.md`；页面口径：`docs/frontend/pages.md`。

## 0. 起服务与录屏准备（录屏前按序执行，2026-10-16 补 / 2026-10-24 按 #96/#97/#99 订正）

### 0.0 建库与灌数（一次性；首次演示前）

```bash
cd backend
# 建表二选一：DDL 快照，或 ORM 初始化（两条路径都过索引自检）
mysql -u<user> -p jit_defect < ../infra/schema.sql
# python -m app.db init

# 依次灌四类数据，打印并留档每类入库行数
python -m app.ingest commits     ../data_model/data/commits.csv
python -m app.ingest labels      ../data_model/data/commit_labels_szz.csv
python -m app.ingest features    ../data_model/data/commit_features.csv
python -m app.ingest predictions ../data_model/pipelines/expert/data/prediction_result.csv
```

- 期望：`predictions` 入库 **83,943** 行（`xgb_v1`，`feature_version=v1`）。
- 权重目录：默认即 `data_model/pipelines/expert/models/`，不改 `MODEL_DIR` 也能加载（#99 自动插 `sys.path`）。
- **`backend/.env` 的 `API_TOKEN` 必须等于 `frontend/.env.local` 的 `VITE_API_KEY`**，否则前端全部 40100。

### 0.0.1 演示库 vs 联调库（2026-10-24 蒋励裁定，Issue #130 一 → A）

**演示与 T-ST-01~05 一律用演示库；联调与截图取证一律用联调库。** 两份都登记在案，不要混用：

| 库 | 文件 | 生成方式 | 数据规模 | 用在哪 |
|---|---|---|---|---|
| **联调库**（唯一） | `backend/dev.db` | `cd backend` → `python -m scripts.seed_dev_data` | 3 提交 / 3 特征 / 3 预测，hash `000…001`~`000…003`，`model_name` 全 `seed_v1`，`risk_score` = 0.1 / 0.2 / 0.3 | 日常联调、T-FE-01 三态截图取证 |
| **演示库**（唯一） | `backend/demo.db` | `cd backend` → `python -m app.db init` → 上面 4× `python -m app.ingest` | 真实产物：commits **84,461** / labels **83,943** / features **83,943** / predictions **83,943**，其中 `risk_score ≥ 0.5` 有 **14,596** 条（17.39%） | **演示与录屏、T-ST-01~05** |

- **为什么不能拿 `dev.db` 上台**：§0.3 的自检 `min_risk=0.5&size=5` 在 `dev.db` 下**必为空**（seed 三行最高 0.3），演示步骤 1 会演成空态，T-ST-01 直接判不过。上述行数与 ≥0.5 条数见 `backend/scripts/evidence/integration-2026-10-24.md`。
- **这不是「另建一套库」**：`docs/frontend/integration-log.md` §0 硬规矩 2 防的是「每人各建一套、口径无法复现」，不是禁止一份**登记在案、生成命令可复现**的演示库。两张表的生成命令都写在本节，仍是单一出处。
- 切库只改 `backend/.env` 的 `DATABASE_URL=sqlite:///./demo.db`，**不要手改库内容**；`*.db` 已被 `.gitignore` 排除，不入库。
- MySQL 路径（Issue #121 授权后）与 `demo.db` 等价，属同一「演示库」槽位，届时只换 `DATABASE_URL`，本脚本的期望值不变。
- 录屏前跑一次 `backend/scripts/demo_preflight.py`（派工中，归后端线）：它按本节口径逐项自检，任一不满足退出码 1 并打印实际值。

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

- 返回为空 → 先由后端线把 `data_model/pipelines/expert/predict.py` 产出的 `prediction_result.csv` 灌库；
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
| 预测结果已入库 | `SELECT COUNT(*) FROM prediction;` | 83,943（只少不多即为灌数未完成；`0` 时不要临场造数） |
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
