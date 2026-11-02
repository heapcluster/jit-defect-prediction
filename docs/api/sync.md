# sync

**一句话**：数据同步接口——从 Git 源仓库取提交并现算预测入库，**是全系统唯一会触发计算的入口**；查询类接口一律只读，补算全走这里。

## 被谁调用
| 调用方 | 场景 |
|---|---|
| 前端风险列表「刷新」按钮 | 按风险列表「同步范围行」的架构 / 模型 / 时间调 `POST /api/sync`，异步补算；轮 `/api/sync/status` |
| 服务启动 | `SYNC_ON_STARTUP=1` 时后台增量/补齐到 HEAD（内部服务，不走前端） |
| 运维 / 演示 | 手动调 `POST /api/sync`（按架构 / 模型 / 时间区间） |

## 处理功能
| 接口 | 方法 | 用途 |
|---|---|---|
| `/api/sync` | POST | 异步补算入库（幂等）：按架构、模型、commit 时间区间；**前端「刷新」走这条** |
| `/api/sync/status` | GET | 同步状态快照（字段见下） |

- **权限**：沿用后端统一鉴权（内部/运维调用）。
- **已下线**：`POST /api/sync/catchup` 不再暴露 HTTP 契约；catchup 逻辑保留为服务启动内部同步（不对外），进度统一轮 `/api/sync/status`。

## 参数（`POST /api/sync`）
| 参数 | 状态 | 含义 |
|---|---|---|
| `line` | **待实现** | 只补该架构（`expert` / `semantic` / `fused` / `e2e`） |
| `model_name` | **待实现** | 只补该模型；省略 = 全部在线模型 |
| `start_time` / `end_time` | **待实现** | 只补该 commit 时间区间（两端闭区间） |

- 「待补齐」判据：该提交**缺目标模型的预测行**；未指定模型时缺「任一在线模型」即算缺口。
- **前端「刷新」= 把同步范围行的架构 / 模型与时间范围作为 `line` / `model_name` / `start_time` / `end_time` 调 `/api/sync`**；时间范围为空时不传 `start_time` / `end_time`，按服务端内部默认批次兜底。
- 启动同步内部使用 catchup 逻辑（补齐 DB→HEAD），不暴露 HTTP 端点，也不由前端「刷新」调用。

## 交互契约（前端口径，强制）
- **模型标识统一用 `model_name`**：`line` / `model_name` 参数对外都是字符串标识，与库表 `prediction.model_name` 直接对应。
- 现算一条实测 **P50 ≈ 108 秒**，补算**必须走异步**：前端提交后立即返回，靠 `/api/sync/status` 轮进度，MUST NOT 同步等结果、MUST NOT 把超时设成 10 秒。
- 「刷新」只负责按当前筛选触发同步；完成后前端再按同一组筛选条件重新查询列表，MUST NOT 把同步结果当查询结果直接拼进表格。
- 同一时刻只允许一个同步任务（服务端串行锁），并发请求返回「已在同步中」而不是排队重试。

## 响应 `data`（`/api/sync/status`）
| 字段 | 含义 |
|---|---|
| `running` | 是否同步中 |
| `mode` | `startup` / `manual`；空闲为 `null` |
| `scope` | `baseline` / `latest` / `catchup-to-head`；空闲为 `null`（`catchup-to-head` 由启动同步产生） |
| `total` / `done` | 本批总量 / 已完成（刚开始 `total` 仍为 0，计划算出后才回填） |
| `current_hash` | 当前处理提交 |
| `started_at` | 本批开始时间 |
| `last_error` | 最近错误（如有） |

**状态只在内存**（`services/sync_state.py`）：进程重启即清零，`/api/health` 的 `last_sync_at` 同步变 `null`。MUST NOT 拿它当历史同步记录查询。

## 错误
| 业务码 | HTTP | 含义 |
|---|---|---|
| 40001 | 400 | 参数非法（`line` / `model_name` / 时间格式错误等） |
| 40100 | 401 | 缺 / 错 token |
| 50000 | 500 | 同步中重复触发 / git 源不可达 / 内部错误 |
