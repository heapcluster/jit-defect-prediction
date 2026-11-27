# 数据同步 API（sync）

一句话：按架构 / 模型 / commit 时间区间把最新提交补算入库，是系统**唯一会触发计算**的入口；查询类接口一律只读。

实现状态：已实现　期次：一期

## 1. 职责与不负责范围

- 负责拉取最新提交、现算特征、在线预测并写入 `commit` / `commit_feature` / `prediction`。
- 负责同步互斥与进度状态快照。
- 不负责训练、清洗、评估；不负责历史回填之外的业务编排。
- `POST /api/sync/catchup` 与 `POST /api/sync/stream` 已下线：启动同步走内部 `catchup`，进度统一轮询 `/api/sync/status`。

## 2. 端点契约

### POST /api/sync

异步补算：提交后立即返回，进度通过 `GET /api/sync/status` 轮询。同一时刻只允许一个同步任务。

| 参数 | 必填 | 契约 |
|---|---|---|
| `line` | 否 | `expert` / `semantic`；指定时补算该线交付模型 |
| `model_name` | 否 | 指定模型；不存在返回 40001 |
| `start_time` / `end_time` | 否 | commit 时间区间（UTC，ISO 8601）；为空时取服务端默认批次（`SYNC_BATCH_LIMIT`） |

未指定 `line` / `model_name` 时只补算当前已加载模型的缺口，保持普通「刷新」轻量。

响应：

```json
{"code": 0, "message": "ok", "data": {"accepted": true}}
```

并发冲突：已有同步在跑时返回 40001 +「同步进行中，请稍候」，不排队；前端接上轮询而不是报服务异常。

### GET /api/sync/status

同步状态快照：

| 字段 | 类型 | 含义 |
|---|---|---|
| `running` | bool | 是否有同步在跑 |
| `mode` | string | `manual` / `startup` 等 |
| `scope` | string | `latest` / `range` 等 |
| `line` / `model_name` | string\|null | 本次范围 |
| `phase` | string | `fetch` / `plan` / `predict` 等阶段 |
| `total` / `done` | int | 进度总量与已完成量 |
| `current_hash` | string\|null | 当前处理的提交 |
| `started_at` | string\|null | 开始时间（UTC，`Z` 结尾） |
| `last_error` | string\|null | 最近错误（脱敏） |

## 3. 状态与边界

- 无数据首启：`prediction` 表为空时，同步按「现算特征 → 预测 → 逐条落库」建立基线，不预先批量灌库。
- 单条提交失败计入 `skipped` 并记录原因，不影响其余提交。
- 上传/日志中不出现 API Key、口令或连接串。
- `SYNC_ON_STARTUP=1` 时启动后后台同步一次；状态同样通过 `/api/sync/status` 读取。

## 4. 错误码

| 业务码 | HTTP | 场景 |
|---|---|---|
| 40001 | 400 | `line` 非法、`model_name` 不存在、时间参数非法、同步进行中 |
| 40100 | 401 | 鉴权失败 |
| 50000 | 500 | 未预期异常 |

## 5. 验收

- 带 `X-API-Key` 调用 `POST /api/sync` 返回 `accepted=true`，随后轮询 `GET /api/sync/status` 至 `running=false`、`last_error` 为空。
- 同步进行中再次提交返回 40001 +「同步进行中，请稍候」。
- 对同一提交重复同步，`prediction` 表按幂等键不产生重复行。
- 未配置 `SOURCE_REPO` 且任务未指定仓库时，`/api/sync` 无法现算新提交特征并给出可读原因。
