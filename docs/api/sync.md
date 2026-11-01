# sync

**一句话**：数据同步接口——从 Git 源仓库取提交并现算预测入库，**是全系统唯一会触发计算的入口**；查询类接口一律只读，补算全走这里。

## 被谁调用
| 调用方 | 场景 |
|---|---|
| 前端风险列表「补齐」按钮 | 选线 → 选模型 → 选时间 → 确认，异步补算该范围 |
| 前端风险列表「补齐缺口」按钮 | 按条数追最新 |
| 运维 / 演示 | 手动触发增量或补齐到 HEAD |

## 处理功能
| 接口 | 方法 | 用途 |
|---|---|---|
| `/api/sync` | POST | 异步补算入库（幂等）：按线 → 模型 → commit 时间区间，或按条数 |
| `/api/sync/catchup` | POST | 补齐到当前 HEAD：git 有、库里缺的提交全部算完入库 |
| `/api/sync/status` | GET | 同步状态快照（字段见下） |
| `/api/sync/stream` | GET | SSE 进度推送。**当前无消费方**：前端只轮 `/sync/status` |

- **权限**：沿用后端统一鉴权（内部/运维调用）。

## 参数（`POST /api/sync`）
| 参数 | 状态 | 含义 |
|---|---|---|
| `limit` | 已实现 | 单次批大小，默认 10，上限 `MAX_LIMIT`；取最新 N 条「覆盖不全」的提交 |
| `line` | **待实现** | 只补该线（`expert` / `semantic` / `fused` / `e2e`） |
| `model_name` | **待实现** | 只补该模型；省略 = 全部在线模型 |
| `start_time` / `end_time` | **待实现** | 只补该 commit 时间区间（两端闭区间）；与 `limit` 二选一 |

- 「待补齐」判据：该提交**缺目标模型的预测行**；`limit` 模式缺「任一在线模型」即算缺口。
- 前端「补齐」弹窗（选线 → 选模型 → 选时间 → 确认）对应 `line + model_name + start_time/end_time` 四参组合。

## 交互契约（前端口径，强制）
- **模型标识统一用 `model_name`**：`line` / `model_name` 参数对外都是字符串标识，与库表 `prediction.model_name` 直接对应。
- 现算一条实测 **P50 ≈ 108 秒**，补算**必须走异步**：前端提交后立即返回，靠 `/api/sync/status` 轮进度，MUST NOT 同步等结果、MUST NOT 把超时设成 10 秒。
- 同一时刻只允许一个同步任务（服务端串行锁），并发请求返回「已在同步中」而不是排队重试。

## 响应 `data`（`/api/sync/status`）
| 字段 | 含义 |
|---|---|
| `running` | 是否同步中 |
| `mode` | `startup` / `manual` / `catchup`；空闲为 `null` |
| `scope` | `baseline` / `latest` / `catchup-to-head`；空闲为 `null` |
| `total` / `done` | 本批总量 / 已完成（刚开始 `total` 仍为 0，计划算出后才回填） |
| `current_hash` | 当前处理提交 |
| `started_at` | 本批开始时间 |
| `last_error` | 最近错误（如有） |

**状态只在内存**（`services/sync_state.py`）：进程重启即清零，`/api/health` 的 `last_sync_at` 同步变 `null`。MUST NOT 拿它当历史同步记录查询。

## 错误
| 业务码 | HTTP | 含义 |
|---|---|---|
| 40001 | 400 | 参数非法（`limit` 越界等） |
| 40100 | 401 | 缺 / 错 token |
| 50000 | 500 | 同步中重复触发 / git 源不可达 / 内部错误 |
