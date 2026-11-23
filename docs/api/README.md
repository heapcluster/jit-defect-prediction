# API 目标契约索引

一句话：本目录以 17 篇文件定义八个独立工具的 API、公共鉴权与错误包络、统一运行/下载、存储导入导出及展示管理端点，任何工具都可直接凭输入文件独立验收。

实现状态：部分　期次：一期

交换文件单一权威为 [../file-contracts.md](../file-contracts.md) §3.1–§3.9；本文只规定公共 HTTP 口径，各篇是具体端点契约。

## 1. 职责与不负责范围

- 负责导航、公共鉴权、响应包络、业务码、时间格式、统一 run/job/输出目录、安全与配置原则。
- 八个工具分别为 storage、collect、clean、train、predict、evaluate、explain、localization；在线组合演示只是可选调用方式。
- 展示读端点只读已导入数据，模型/配置/job 管理端点只承担各自管理职责，均不代替文件运行。
- 本文不重复定义交换列，不增加第七种 job kind，不把数据库、页面或其他模块在线状态作为业务运行前置。

## 2. 端点契约：17 组索引

| # | 文档 | 分组 | 目标端点 | 实现状态 |
|---|---|---|---|---|
| 1 | [README.md](README.md) | 公共契约 | 鉴权、包络、错误码、run/job/输出公共规则 | 部分 |
| 2 | [storage.md](storage.md) | 工具 1：存储 | `POST /api/storage/import`；`GET /api/storage/export?table=&format=`；`GET /api/storage/outputs/{job_id}/{name}` | 部分 |
| 3 | [collect.md](collect.md) | 工具 2：收集 | `POST /api/collect/run`；`GET /api/collect/preview/{job_id}`；`GET /api/collect/outputs/{job_id}/{name}` | 已实现 |
| 4 | [clean.md](clean.md) | 工具 3：清洗 | `POST /api/clean/run`；`GET /api/clean/operations`；`GET /api/clean/preview/{job_id}`；`GET /api/clean/outputs/{job_id}/{name}` | 已实现 |
| 5 | [train.md](train.md) | 工具 4：训练 | `POST /api/train/run`；`GET /api/algorithms`；`GET /api/train/compare`；`GET /api/train/outputs/{job_id}/{name}` | 已实现 |
| 6 | [predict.md](predict.md) | 工具 5：预测 | `POST /api/predict/run`；`POST /api/predict`；`GET /api/predict/outputs/{job_id}/{name}` | 已实现 |
| 7 | [models.md](models.md) | 模型管理 | `GET /api/models`；`GET /api/models/status`；`POST /api/models/{name}/load`、`unload`、`reload`；`PUT /api/models/default` | 已实现 |
| 8 | [evaluate.md](evaluate.md) | 工具 6：评估 | `POST /api/evaluate/run`；`GET /api/evaluate/metrics`；`GET /api/evaluate/outputs/{job_id}/{name}` | 已实现 |
| 9 | [figures.md](figures.md) | 图件读取 | `GET /api/figures`；鉴权 `/static/**` 或受控输出 URL | 部分 |
| 10 | [explain.md](explain.md) | 工具 7：解释 | `POST /api/explain/run`；`POST /api/explain`；`GET /api/explain/techniques`；`GET /api/explain/outputs/{job_id}/{name}` | 已实现 |
| 11 | [source.md](source.md) | 工具 8：定位与源码 | `POST /api/localize/run`；`GET /api/localize/outputs/{job_id}/{name}`；`GET /api/source/tree`、`GET /api/source/file` | 已实现（无可靠修复补丁时只交付建议） |
| 12 | [commits.md](commits.md) | 提交读取 | `GET /api/commits`；`GET /api/commits/{commit_hash}` | 部分 |
| 13 | [trends.md](trends.md) | 趋势读取 | `GET /api/trends` | 部分 |
| 14 | [datasets.md](datasets.md) | 数据集读取与导出 | `GET /api/datasets`、`/{id}`、`/{id}/commits`、`/{id}/export`；`GET /api/datasets/outputs/{job_id}/{name}` | 未实现 |
| 15 | [config.md](config.md) | 配置管理 | `GET/PUT /api/config`；`PUT/DELETE /api/config/{key}` | 部分 |
| 16 | [jobs.md](jobs.md) | 任务管理 | `GET /api/jobs`；`GET /api/jobs/{id}`；`POST /api/jobs/{id}/retry`、`cancel` | 部分 |
| 17 | [health.md](health.md) | 健康探针 | `GET /api/health`、`/api/health/live`、`/api/health/ready` | 部分 |

### 公共请求与响应

- **鉴权**：所有 `/api/**`、`/static/**`、图片与输出下载都要求 `X-API-Key`；服务端未配置令牌时 fail closed。前端取图使用带鉴权 fetch 转 ObjectURL。
- **JSON 包络**：成功 `{code:0,message:"ok",data:{...}}`；失败 `{code,message,data:null}`。文件流不走 JSON 包络，但流开始前的校验错误仍走包络。
- **业务码**：仅 `40001`（HTTP 400）、`40100`（401）、`40400`（404）、`50000`（500）；成功 code=0。50000 message 固定 `internal error`，不回显堆栈、SQL、连接串或绝对路径。
- **时间**：响应 UTC ISO 8601 `Z`；时间范围两端闭区间，start 纯日期为当天起点，end 纯日期扩展至当天终点。
- **默认模型**：user_config.default_model；未配置时回退已加载 expert 中 version_key 最大者。模型包加载前必须校验 checksum 与特征列宽。

### 统一 run 与下载

七个计算型 run 均为 `POST /api/{collect,clean,train,predict,evaluate,explain,localize}/run`：

- 请求 `multipart/form-data`，文件字段 `files[]`，配置字段 `config`（JSON part）；collect 可只传仓库配置。
- 表格接受 CSV/XLSX；上传校验大小、扩展名与魔数、列 schema、CSV 公式注入，ZIP 还校验路径穿越与解压大小。路径限定允许根目录，文件名不得拼接 shell。
- 小文件同步执行并返回 `{job_id,status:"success",outputs[],...}`；大文件返回 `{job_id,status:"queued"}`。除 localize 外，同步也落 job 终态，异步落五态。
- 输出统一下载 `GET /api/{module}/outputs/{job_id}/{name}`；name 只能是 manifest 登记的基础文件名，禁止路径穿越。
- localize 同步为主、不新增 kind，超大输入返回 40001 并要求分批；其 job_id 仅作输出批次标识。

### 产物库选择与上传等价

产物库索引已交付的文件，不等同于 `dataset` 展示台账，也不要求文件先经 storage 导入。clean/train/predict/evaluate/explain/localize 的文件选择遵循同一流程：

1. 通过 `GET /api/jobs?kind=<kind>` 分页查询来源任务，从 `output_ref_json` 读取已登记产物；仅显示符合本模块输入类型且已完成交付的文件。部分失败任务中已成功交付的子项仍可选择，不能只凭任务总状态判定文件可用。
2. 选择结果在页面内保存 `{module,job_id,name,sha256,size_bytes}`；`job_id` 使用输出引用中的批次标识，`name` 使用已登记基础文件名，不拼接服务器路径或猜测文件名。
3. 经 `GET /api/{module}/outputs/{job_id}/{name}` 下载所选文件及其已登记 manifest，全部携带 `X-API-Key`。manifest 的 `outputs[]` 必须包含该文件名及相同 SHA256；文件不可下载或 checksum 不符时禁用运行并提示重新选择。
4. 把下载内容构造成 File/Blob，以 `files[]` 提交给目标 `run`，配置仍放 `config` JSON part；已有伴随 manifest 一并作为辅助文件提交。run 不新增文件引用参数，不接受服务器绝对路径，也不通过 `dataset_id` 读取这些产物。
5. 服务端重新校验文件、manifest 与 checksum；manifest 辅助文件不计入模块规定的主表或模型包数量。直接上传没有来源 manifest 的外部文件仍按模块输入契约校验；选择产物库文件与直接上传相同文件应得到等价业务输出。

| 待选输入 | 来源 job kind | 下载端点的 module |
|---|---|---|
| commits | `collect` | `collect` |
| cleaned | `clean` | `clean` |
| model_package | `train` | `train` |
| predictions | `predict_batch` | `predict` |
| explanations | `explain` | `explain` |

`kind=predict` 不合法，预测任务使用 `predict_batch`。外部 labels 或没有对应历史产物的文件可直接上传。`dataset_id` 和已登记 `model_name` 保留为独立便利选项：前者选择已导入数据，后者选择登记模型；它们不是产物文件引用，走 `files[]` 的产物选择路径不同时提交 `dataset_id`。

## 3. 输入契约

- 模块主输入是文件和显式 config；`dataset_id` 只用于选择已导入文件的便利输入，显式上传优先。
- 文件 schema 必须逐篇引用 file-contracts §3.1–§3.8，不在 API 文档另造列名、别名或私有宽表。
- 所有表格解析后归一记录结构；缺列、错类型、非法 hash/时间/概率、公式注入、超限或伪造格式返回 40001，不产半成品。
- `is_bug_inducing` 未打标保持空值；Kamei 14 维列序与 log 变换（fix 除外）、SZZ 词首边界 `\b(fix|bug|patch)` 和 szz/szz_lite、时间序 70/30 禁随机均为不变量。

## 4. 输出契约

- 文件命名统一 `<module>_<artifact>_<job_id>.<ext>`；主产物同名 manifest 为 `<module>_<artifact>_<job_id>.manifest.json`，所有输出登记名称、大小和 checksum。
- 表格默认 CSV（UTF-8 BOM），可配 `format=xlsx`；XLSX 单 sheet，manifest 不进入 sheet。空标签与缺预测保持空值。
- manifest 必伴并严格采用 [../file-contracts.md](../file-contracts.md) §3.9：

```json
{
  "schema_version": "1.0",
  "module": "train",
  "job_id": "j-8f21",
  "inputs": [{"name": "cleaned.csv", "sha256": "…", "rows": 25183}],
  "config": {"algos": ["rf", "xgb"], "seed": 42, "split_ratio": 0.7},
  "outputs": [{"name": "model_package.zip", "sha256": "…"}],
  "code_version": "3e72854",
  "created_at": "2026-11-21T12:00:00Z"
}
```

- 只读查询和管理端点若不生成文件，明确不产 manifest；export/run 产生的文件不得缺少 manifest。

## 5. 可配置项

- 全局单源 user_config：`decision_threshold / risk_high_threshold / risk_mid_threshold / default_model / default_dataset / default_xai / metrics_selected / primary_metric / effort_enabled / page_prefs`。
- 模块命名空间：`collect.allow_roots`、`collect.protocol_whitelist`、`clean.chain_templates`、`train.templates`、`predict.batch_size/cache_ttl/retry_max`、`explain.cache_ttl/compare_enabled`、`localization.weights/top_n/file_size_max/suggestion_sources`。
- `.env` 仅提供出厂默认和部署敏感项；密钥不入库。用户配置写入立即生效，进程或容器重启后恢复。
- 12 表为 `commit / commit_feature / model / prediction / model_figure / user / user_config / job / algorithm / model_artifact / dataset / dataset_commit`，职责是展示导入、配置、任务状态与资产登记。

## 6. 状态持久化

- job kind 仅 `collect / clean / train / predict_batch / evaluate / explain`；状态仅 `queued / running / success / failed / cancelled`。
- 同 kind 互斥通过 job 表条件更新；重启遗留 running 置 failed，保留进度与脱敏日志，可 retry/cancel。
- 所有 run/export 文件落 `backend/var/outputs/<job_id>/`，该目录必须 gitignore；manifest 与文件 checksum 是下载和复现依据。
- 模型交付为 §3.3 model_package.zip；model_artifact 是可选登记展示路径，model 行由工件派生，文件加载不要求先入库。

## 7. 验收

各篇 fixtures 位于 `tests/fixtures/files/<module>/`，均含正常、边界、非法三类，并同时验证 CLI/API 等价（模块提供 CLI 时）。

- **正常**：只上传该模块输入即得到权威 schema 输出、manifest 和可鉴权下载，不要求其他工具或数据库先有数据。
- **边界**：空态、空标签、版本/阈值/缓存变化、任务重启、缺图、部分失败均有明确语义，不填造 0 或静默空结果。
- **非法**：schema、魔数、checksum、路径、配置和鉴权错误只使用公共业务码，且不产半成品。
- 跨模块测试只验证文件 schema 兼容；评估默认 0.5 与历史 `model_metrics.csv` 对应值逐值一致（容差 1e-6），effort-aware/effort-unaware 两类图均验收。

## 8. 边界

模块间依赖仅为交换文件 schema 与版本兼容，而非上游服务或数据库前置。predict 不调用 explain/localize，详情展示可并行编排；SZZ 判据单源在 collect，指标公式单源在 `data_model/evaluation/metrics.py`。storage、commits、trends、figures、datasets 提供可选展示面，不能反向成为独立运行的必要条件。
