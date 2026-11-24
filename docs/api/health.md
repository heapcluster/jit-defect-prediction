# 健康检查 API（health）

一句话：以三个均鉴权的探针分别报告进程存活、数据库与模型就绪状态，以及持久化任务和资产的只读快照。

实现状态：部分　期次：一期

模型状态见 [models.md](models.md)，任务状态见 [jobs.md](jobs.md)，公共鉴权见 [README.md](README.md)。

## 1. 职责与不负责范围

- `/api/health/live` 只证明进程可响应，不访问数据库或模型。
- `/api/health/ready` 检查数据库可用且至少一个模型已加载。
- `/api/health` 提供数据库、模型、提交/预测/数据集和 job 的综合快照。
- 不执行业务计算、模型加载、任务恢复或数据修复；健康状态不得暴露连接串、密钥、堆栈或绝对路径。

## 2. 端点契约

### GET /api/health/live

无参数。响应 `data:{status:"ok",server_time}`；只要进程能处理请求即为 ok，数据库故障不影响该探针。

### GET /api/health/ready

无参数。响应：

| 字段 | 含义 |
|---|---|
| `status` | `ok` / `degraded` |
| `db` | `up` / `down` |
| `models_loaded` | 当前已加载模型数 |
| `server_time` | UTC ISO 8601 `Z` |

db=up 且 models_loaded>0 为 ok，否则 degraded。degraded 仍 HTTP 200、code=0，调用方读取 data.status。

### GET /api/health

无参数。响应：

| 字段 | 含义 |
|---|---|
| `status` / `db` | 综合状态与数据库状态 |
| `models_loaded` / `model_names` / `catalog_count` | 已加载数、名单与登记数，三者语义不同 |
| `commit_count` / `prediction_count` / `dataset_count` | 展示表行数 |
| `jobs_running` | job 表 running 数，仅六类 kind |
| `last_collect_at` / `last_predict_batch_at` | 对应 kind 最近 started_at，无记录为 null |
| `server_time` | 服务端时间 |

数据库故障时状态 degraded、可读取字段保持 null/0 并标明 db=down，不抛内部异常；模型全部卸载时 ready degraded，catalog_count 不因此改变。

### 错误码

| 业务码 | HTTP | 场景 |
|---|---|---|
| 40100 | 401 | 三探针缺失或错误的 `X-API-Key` |
| 40001 | 400 | 出现未定义业务参数 |
| 40400 | 404 | 仅用于错误路径，不是健康降级的表达 |
| 50000 | 500 | 仅鉴权/框架外未预期故障；可预期 DB/模型不可用必须返回 degraded |

## 3. 输入契约

无文件、无业务参数。三探针都要求 X-API-Key，监控路径也不例外。健康检查不得接受模型名、仓库路径或修复指令，防止探针变成管理端点。

## 4. 输出契约

仅输出上述 JSON，不生成 CSV、图、报告或 manifest，不创建输出目录。所有时间使用 UTC `Z`，错误细节只写服务端脱敏日志。

live/ready/综合快照的 status 都在 data 内；degraded 不使用错误包络替代。model_names 只代表进程内已加载实例，catalog_count 只代表登记资产，不能互相推导。

## 5. 可配置项

- 无请求级配置；就绪条件固定为数据库可用且至少一个模型加载。
- 默认模型与模型加载由 config/models 管理，health 不提供覆盖项。
- 超时、连接信息等部署值只在服务端使用，不通过响应暴露；`.env` 仅提供部署与出厂默认。

## 6. 状态持久化

- 三探针只读，不创建 job、不写业务行、不写文件。
- last_collect_at、last_predict_batch_at、jobs_running 读取 job 表，重启后可恢复；live 不访问这些表。
- 模型加载态来自模型注册表，资产计数来自 model_artifact/model；health 不维护第二份状态。

## 7. 验收

fixtures：`tests/fixtures/files/health/`，以数据库、模型和 job 状态的正常/边界/非法 JSON 样例及鉴权用例驱动测试。

- **正常**：三探针 ok 字段完整，综合快照计数与表一致，最近任务时间重启后仍可读。
- **边界**：停 DB 时 live=ok、ready/综合=degraded 且 HTTP 200；模型全卸载时 ready degraded，catalog_count 不变；无任务时间为 null。
- **非法**：无/错/篡改 API Key 均 40100，额外业务参数 40001；响应不包含连接串、口令、堆栈和敏感路径。
- 健康请求不触发加载、收集、预测或任务状态修复；localize/storage 输出批次不计入 jobs_running。

## 8. 边界

health 是运维读面，不是任何业务模块运行前置。模块独立运行依输入文件与配置；数据库 down 只影响展示和持久化能力的健康状态，不应被解释为交换文件 schema 依赖。
