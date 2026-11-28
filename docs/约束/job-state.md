# 任务状态机

本文件是异步任务状态、取消、重试与轮询的唯一真源。

## 1 状态流转

```text
queued ──► running ──► success
                │
                ├──► failed ──► 新任务（重试）
                └──► cancelled
```

- `queued`：已创建，等待执行。
- `running`：执行中，持续更新 `done` / `total` / `current_stage`。
- `success`：正常结束，产物可预览、导出、保存。
- `failed`：异常结束，记录 `error_message`，允许重试。
- `cancelled`：用户取消，不产生可保存结果。

## 2 归属与可见性

- 每个任务必须绑定 `owner_user_id`。
- 非本人任务查询、取消、下载一律返回 `40401`。
- 后台执行不因用户登出而中断；任务结果只对归属用户可见。

## 3 并发

- 同一用户同一时刻只允许 1 条 `running` 任务，重复提交返回 `42901`。
- 不保证跨用户并发，也不做跨用户排队与抢占；这是使用假设，不是系统强制。

## 4 进度与轮询

- `GET /api/jobs/{job_id}` 返回 `status`、`done`、`total`、`current_stage`、`error_message`。

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "job_id": "job_...",
    "kind": "collect",
    "status": "running",
    "params": { "repo_url": "https://github.com/owner/repo", "branch": "main", "mode": "expert" },
    "done": 320,
    "total": 1200,
    "current_stage": "SZZ 回溯",
    "error_message": null,
    "created_at": "2026-11-27T10:00:00+08:00",
    "started_at": "2026-11-27T10:00:02+08:00",
    "finished_at": null
  }
}
```

- 非本人任务返回 `40401`；任务不存在返回 `40401`。
- `params` 返回启动参数原文，失败任务据此重试。
- `total` / `done` 口径按任务类型固定：

| `kind` | `total` | `done` |
|---|---|---|
| `collect` | 预检的提交数 | 已处理提交数 |
| `clean` | 操作数 | 已完成操作数 |
| `train` | 算法数 | 已完成算法数 |
| `predict` | 待预测行数 | 已预测行数 |
| `evaluate` | 计划生成的图数 | 已生成图数 |

- 前端轮询间隔 3 秒；进入终态后停止轮询。
- 取消成功返回 `data: { "status": "cancelled" }`；任务已进入 `success` / `failed` / `cancelled` 时返回 `40901`。
- 进度数字必须来自后端真实计数，不允许前端自行估算。

## 5 取消

- 仅 `queued` 与 `running` 可取消。
- 取消后任务置 `cancelled`，清理其未入库产物；已保存的数据集不受影响。
- 取消后再次提交新任务不自动重试旧任务。

## 6 重试

- 仅 `failed` 可重试；重试复用原参数，生成新任务记录，原任务保持 `failed`，不覆盖原任务。
- 重试由前端读取失败任务的参数，调用对应模块的启动端点重新提交；不单独提供重试端点。
- 原任务记录保留，便于查看失败原因。

## 7 服务重启

- 服务启动时，残留的 `running` 任务统一置为 `failed`，原因写“服务重启导致中断”，可由用户重试。
- `queued` 任务保持等待，重新调度。
