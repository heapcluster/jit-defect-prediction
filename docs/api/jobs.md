# 任务 API（jobs）

一句话：统一管理六个模块的异步任务状态、进度、产物引用、重试与取消，是页面轮询的唯一入口。

## 1. 职责与不负责范围

- 负责任务列表/详情、五态流转、进度字段、产物引用与错误日志的读取。
- 负责 retry（仅失败）与 cancel（排队/运行中）。
- 不负责执行任务本身：重试由各模块 service 重新派发；不做业务校验，不做产物重写。

## 2. 端点契约

### GET /api/jobs

| 参数 | 必填 | 契约 |
|---|---|---|
| `kind` | 否 | `collect/clean/train/predict_batch/evaluate/explain` |
| `status` | 否 | `queued/running/success/failed/cancelled` |
| `chain_id` | 否 | 按数据链路根任务过滤，用于产物库链路视图 |
| `page` | 否 | ≥1，默认 1 |
| `size` | 否 | 1..100，默认 20 |

响应 `data:{total,page,size,items[]}`，按创建时间倒序。

任务记录字段：

```text
job_id, chain_id, parent_job_ids, kind, status, params_json, total, done, current_item,
created_at, started_at, finished_at, error_log, retry_count, output_ref_json
```

- `chain_id` 为链路根任务；`parent_job_ids` 为直接父任务 JSON 数组，由提交阶段显式写入。

- `params_json` 为归一化后的请求快照（含 `input_ref` / `input_sha256` / `config`），不是原始请求文本。
- `output_ref_json` 成功时含 `module`、`outputs[{name,sha256,size_bytes}]`、`manifest_name`、`summary`，clean/collect 另含 `columns`、`mode`。
- `error_log` 为脱敏文本，≤2000 字符，不含内部路径与堆栈。

### GET /api/jobs/{job_id}

单条记录；不存在返回 `40400`。

### POST /api/jobs/{job_id}/retry

- 不接受任何 query 或 body（否则 40001）。
- 前置：同 kind 无 `running`；目标状态为 `failed`（CAS，冲突返回 40001）。
- 效果：置 `queued`、`retry_count+1`、清空 `started_at/finished_at/error_log/current_item`，由模块 service 重新派发。
- 响应 `data:{job_id,status,retry_count}`。

### POST /api/jobs/{job_id}/cancel

- 不接受任何 query 或 body。
- 仅 `queued`/`running` 可取消，否则 40001。
- 响应 `data:{job_id,status,retry_count}`。

### 错误码

| 业务码 | HTTP | 场景 |
|---|---|---|
| 40001 | 400 | kind/status/分页非法、同类任务运行中、状态冲突、携带 body/query |
| 40100 | 401 | 鉴权失败 |
| 40400 | 404 | 任务不存在 |
| 50000 | 500 | 未预期异常（死锁/锁等待转 40001 提示稍后重试） |

## 3. 输入契约

- 任务由各模块 run 端点创建，客户端不能直接创建任务。
- `job_id` 不透明，客户端只做透传，不解析其内部结构。

## 4. 输出契约

- 只输出 JSON，不产生文件；产物通过各模块 `outputs` 端点下载。
- 时间统一 UTC `Z`；`finished_at` 未结束为 null。
- 进程重启时遗留 `running` 会被置为 `failed`，`error_log="进程重启中断"`。

## 5. 可配置项

无独立配置。默认分页大小来自 `page_prefs.page_size`，接口入参可覆盖。

## 6. 状态持久化

- 写 `job` 表；状态变化以 CAS 保证并发安全。
- retry 复用原 job 行，递增 `retry_count`；不新建任务记录。

## 7. 验收

- 六类任务的状态推进、进度、终态与产物引用可查询。
- 失败任务可重试并重新进入队列；运行中可取消；重复 retry 或跨状态操作返回 40001。
- 同 kind 并发启动被拒绝。
- 列表分页稳定，不重不漏。

## 8. 边界

jobs 只是状态台账，不承载业务数据；任务成功与否以 `status` 为准，产物以 `output_ref_json.outputs` 为准，客户端不得用文件系统状态推断任务结果。
