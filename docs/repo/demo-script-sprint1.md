# Sprint 1 端到端演示脚本（10/23 课上验收主证据）

> 负责人：蒋励 ｜ 用途：证明一条提交走完「风险列表 → 详情归因 → 趋势看板」完整链路
> 配套产物：本脚本 + 录屏，二者入库 `docs/` 或附 Issue 链接。
> 接口与错误码口径：`backend/api-spec.md`；页面口径：`docs/frontend/pages.md`。

## 0. 起服务与录屏准备（录屏前按序执行，2026-10-16 补）

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
| 交付模型已加载 | 启动日志搜 `model_name` | 出现 `xgb_v1` |
| 预测结果已入库 | `SELECT COUNT(*) FROM prediction;` | 大于 0 |
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

**口播**：一条提交从"被预警"到"被解释"到"被观察"，闭环成立。

## 3. 异常输入验证（至少演示一项，二者建议都录）

### A. 无效 API Key → 401

```
curl -i -H "X-API-Key: wrong-key" http://localhost:8000/api/commits
```

- 预期：HTTP `401`，`code=40100`；响应体 **不得**出现堆栈、SQL 语句、文件路径。

### B. 非法 commit_hash → 404

```
curl -i -H "X-API-Key: $KEY" http://localhost:8000/api/commits/zzzz
```

- 预期：HTTP `404`，`code=40400`；**页面展示空态而非崩溃**。

> 两者均为契约约定的错误码，不属于自造错误码。

## 4. 录屏要求

| 项 | 要求 |
|---|---|
| 命名 | `demo-sprint1-YYYYMMDD.mp4` |
| 内容顺序 | 列表 → 详情归因 → 趋势看板 → 异常用例（单独一段） |
| 归档 | 入库 `docs/` 或附到 Issue，并在飞书看板本行「关联链接」填写该地址 |

> 说明：录屏需人工实际执行演示录制，脚本本身不产生录屏文件。

## 5. 验收对账（演示后自评）

- [ ] 三段主链路连续走通，无中断
- [ ] 至少一项异常用例返回预期错误码且页面不崩
- [ ] 录屏文件已归档，看板「关联链接」可点开
- [ ] 演示所用 `commit_hash` 与库中真实数据一致（可复现）
