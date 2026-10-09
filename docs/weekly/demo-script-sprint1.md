# Sprint 1 端到端演示脚本（10/23 课上验收主证据）

> 负责人：蒋励 ｜ 用途：证明一条提交走完「风险列表 → 详情归因 → 趋势看板」完整链路
> 配套产物：本脚本 + 录屏，二者入库 `docs/` 或附 Issue 链接。
> 接口与错误码口径：`docs/contracts/api-format.md`；页面口径：`docs/pages.md`。

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
GET /api/commits?order_by=risk_score&order=desc
Header: X-API-Key: <KEY>
```

- 预期：`code=0`，`data.list` 按 `risk_score` 降序。
- 页面动作：打开「风险列表」页，取**第 1 条**高风险提交，记下其 `commit_hash`（下称 `$HASH`）。

### 步骤 2 — 详情归因（被解释）

```
GET /api/commits/$HASH
```

- 预期：返回 `risk_score` 与 `explanation`（每项含 `feature` / `contribution` / `direction`）。
- 页面动作：点进「提交详情」页，确认展示风险分 + SHAP 归因排序。

### 步骤 3 — 趋势看板（被观察）

```
GET /api/trends
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
