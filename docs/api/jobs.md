# 统一任务 API（jobs）

一句话：统一查询六类异步或同步落库任务的状态、进度、日志与输出引用，并提供受限重试和取消，所有生命周期以 job 表为准。

实现状态：部分　期次：一期

W2 已实现六类五态管理、同 kind 数据库互斥、重启中断恢复和持久进度。W3 collect/run、W4 clean/run、W5 train/run、W6 predict/run、W7 evaluate/run、W8 explain/run 任务重试后由各自执行器消费队列；其余尚未接入执行器的 kind 仍只排队，不宣称自动执行。执行器携带 retry_count 令牌并协作检查取消状态；clean/train 在发布文件与写 success 期间持有同 kind 锁，阻止旧 attempt 发布。

任务与输出公共口径见 [README.md](README.md)；存储职责见 [storage.md](storage.md)。

## 1. 职责与不负责范围

- 负责 `collect / clean / train / predict_batch / evaluate / explain` 六类 kind 的列表、详情、retry、cancel。
- 五态固定为 `queued / running / success / failed / cancelled`；同步 run 也写 success/failed 终态供审计。
- 不负责执行模块业务算法、修改输出文件内容或管理 localize/storage 批次；后两者不新增 kind。
- 不依赖进程内字典推断状态，不在响应中泄漏凭证、堆栈、SQL 或本机敏感路径。

## 2. 端点契约

### GET /api/jobs

查询参数：`kind`、`status` 可选，`page=1`、`size=20` 可选，1≤size≤100。响应 `{total,page,size,items[]}`，items 为详情摘要，按 created_at DESC、job_id ASC 排序。

### GET /api/jobs/{job_id}

响应 `data`：

| 字段 | 含义 |
|---|---|
| `job_id` / `kind` / `status` | 标识、六类之一、五态之一 |
| `params_json` | 脱敏入参与配置快照 |
| `total` / `done` / `current_item` | 进度与当前对象 |
| `created_at` / `started_at` / `finished_at` | UTC ISO 8601 `Z` 时间 |
| `error_log` | 脱敏可读错误，成功可为 null |
| `retry_count` | 已重试次数 |
| `output_ref_json` | 输出目录相对文件名、checksum、子项状态和统计，不含绝对路径 |

### POST /api/jobs/{job_id}/retry

无请求体，仅 failed 可重试；复用 params_json 新建排队上下文，状态转 queued、retry_count+1。响应 `{job_id,status:"queued",retry_count}`。已完成输出不删除，重试产生的新文件必须避免被误认为旧成功批次。

### POST /api/jobs/{job_id}/cancel

无请求体，仅 queued/running 可取消；响应 `{job_id,status:"cancelled",retry_count}`。执行器须协作停止，不能取消后继续写 success。

### 错误码

| 业务码 | HTTP | 场景 |
|---|---|---|
| 40001 | 400 | kind/status/分页非法、非法状态流转、retry 同 kind 互斥冲突 |
| 40100 | 401 | 缺失或错误的 `X-API-Key` |
| 40400 | 404 | job_id 不存在；localize/storage 输出批次 id 不属于本接口 |
| 50000 | 500 | 未预期存储错误，不回显内部细节 |

## 3. 输入契约

输入仅为 kind/status、分页和 job_id，无文件输入。kind 与 status 必须逐字匹配六类五态，id 必须为已登记标识；retry/cancel 不接收覆盖参数，防止重试时配置被悄悄改变。

输出目录中的文件下载仍走各模块 `/api/{module}/outputs/{job_id}/{name}`，jobs 不提供任意路径读取。params_json 中的 repo URL、模板和超参可保留，API Key、口令、LLM Key 必须在写入前剔除。

## 4. 输出契约

仅输出 JSON 任务记录，不生成 CSV/XLSX、报告或 manifest。实际业务输出及 §3.9 manifest 由各 run 模块负责，jobs 只保存引用、checksum 和状态。

- 文件型 run 的 `output_ref_json` 包含 `{module,job_id,outputs[],manifest_name}`；outputs 项含 `{name,sha256,size_bytes}`，可另带统计和子项状态。module 是下载端点标识，预测使用 `predict` 而非 job kind `predict_batch`；job_id 是产物批次标识。产物选择与再提交遵循 [API 公共契约](README.md#产物库选择与上传等价)，不得暴露任意文件系统路径。
- 训练等多子项任务在 output_ref_json 中保存逐算法成功/失败与产物；总体状态汇总规则必须明确，部分成功不得掩盖失败子项。
- 时间字段统一 UTC `Z`，error_log 有长度上限并脱敏。

## 5. 可配置项

- jobs API 无独立业务配置；列表分页、重试次数等来自请求和原任务快照。
- 各模块的 predict.retry_max、模板和资源参数由 [config.md](config.md) 管理，jobs 不提供额外配置副本。
- 同 kind 互斥、重启中断置 failed、日志脱敏是固定系统不变量，不能由单次请求关闭。

## 6. 状态持久化

- 合法流转：`queued→running→success/failed`，`queued/running→cancelled`，`failed→queued`；条件更新必须检查当前状态。
- 同 kind 同时最多一个 running，以 job 表条件更新实现，冲突返回 40001；进程内锁只可作优化，不能替代表约束。
- 服务启动把遗留 running 置 failed，error_log 标记进程重启中断，保留 done 供支持续跑的模块重试。
- 业务文件落 `backend/var/outputs/<job_id>/`（gitignore）；jobs 自身不新增输出目录，重启后列表与详情完整可读。

## 7. 验收

fixtures：`tests/fixtures/files/jobs/`，以六类任务的参数、状态与输出引用 JSON 样例驱动测试。

- **正常**：六类五态列表/详情、进度、日志、输出引用可见；failed retry 与 queued/running cancel 状态正确，前端和 CLI 读取一致。
- **边界**：同步终态、训练部分子项失败、重复 cancel、重启遗留 running、续跑幂等、空输出成功均有明确结果。
- **非法**：未知 kind/status、分页越界、retry 非 failed、cancel 终态、同 kind 冲突、不存在的 id 返回 40001/40400，不发生非法流转。
- 六类之外不出现第七种 kind；日志和 params_json 无凭证；输出文件仍只能通过所属模块鉴权下载。

## 8. 边界

jobs 是状态管理面，不是模块间数据通道。每个业务模块仅依自己的文件 schema 独立运行；job 表用于状态和审计，数据库任务记录不是上游服务数据前置，localize/storage 的同步批次也不被强行纳入任务体系。
