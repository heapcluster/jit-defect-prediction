# sync

数据同步接口（模块 `sync.py`）：从 Git 源仓库取提交并现算全模型预测入库。**这是唯一会触发计算的接口**，查询类接口一律只读。

## 处理功能
| 接口 | 方法 | 用途 |
|---|---|---|
| `/api/sync` | POST | 补算并提交入库（幂等）：按条数取最新的未预测提交 |
| `/api/sync/catchup` | POST | 补齐到当前 HEAD：git 有、库里缺的提交全部算完入库 |
| `/api/sync/status` | GET | 同步状态快照（字段见下） |
| `/api/sync/stream` | GET | SSE 进度推送。**当前无消费方**：前端只轮 `/sync/status`（`api/index.js:56`），随下一刀决定是否删 |

- **权限**：沿用后端统一鉴权（内部/运维调用）。

## 关键参数（`POST /api/sync`）
| 参数 | 含义 |
|---|---|
| `limit` | 单次批大小，默认 10，上限 `MAX_LIMIT`；取**最新** N 条「在线模型覆盖不全」的提交 |

- **只算全部在线模型，不能指定单模型**：接口无 `model_name` 参数（`sync.py:266` 只收 `limit`）。「待补齐」的判据是**该提交缺任一在线模型的预测行**（`_unpredicted` 的 `_AUTO` 语义，`sync.py:75-90`），所以一轮 sync 会把 8 个模型都算齐。
- **无时间区间参数**：`start_time` / `end_time` 目前不存在，多余 query 被静默忽略。「按 commit 时间区间补算」是待实现能力，落地前前端不得依赖它。
- 注册表为空（模型全部加载失败）时退回「默认模型单模型判据」，避免把整批候选当缺口反复重试。

## 交互契约（前端口径）
- 现算一条实测 **P50 ≈ 108 秒**，所以补算**必须走后台任务**：前端提交后立即返回，靠 `/api/sync/status` 看进度，MUST NOT 同步等结果、MUST NOT 把超时设成 10 秒。
- 查询与补算分两个动作：列表/明细接口只读已入库分数（未预测表现为少一行或 `risk_score = null`），补算只由本模块发起。
- 同一时刻只允许一个同步任务（服务端串行锁），并发请求返回「已在同步中」而不是排队重试。

## 传输模型
### `/api/sync/status` 响应 `data`
| 字段 | 含义 |
|---|---|
| `running` | 是否同步中 |
| `mode` | `startup` / `manual` / `catchup`；空闲为 `null` |
| `scope` | `baseline` / `latest` / `catchup-to-head`；空闲为 `null` |
| `total` / `done` | 本批总量 / 已完成（**刚开始时 `total` 仍为 0**，计划算出后才回填） |
| `current_hash` | 当前处理提交 |
| `started_at` | 本批开始时间 |
| `last_error` | 最近错误（如有） |

**状态只在内存**（`services/sync_state.py` 的模块级字典）：进程重启即清零，`/api/health` 的 `last_sync_at` 同步变 `null`。MUST NOT 拿它当历史同步记录查询。

### `/api/sync/stream` 响应
`text/event-stream`，逐行推送进度事件（百分比 / 当前 hash / 错误）。
