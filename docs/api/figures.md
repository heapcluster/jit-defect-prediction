# 模型图件查询 API（figures）

一句话：只读列出评估运行产生并经 storage 登记的模型图件及可用状态，按鉴权 URL 供页面取图，不在查询时计算指标或绘图。

实现状态：部分　期次：一期

W2 已支持已登记输出图件的鉴权下载 URL 与 checksum 可用性验证；新批次不嫁接旧静态指标。完整评估指标的同批次投影随 W7 接入，尚未实现部分不作通过证据。

图文件 schema 与类型引用 [../file-contracts.md](../file-contracts.md) §3.6，manifest 引用 §3.9；评估产物见 [evaluate.md](evaluate.md)。

## 1. 职责与不负责范围

- 负责按 model_name 返回 model_figure 中登记的图类型、标题、鉴权 URL、checksum 和缺图状态。
- 支持 roc/pr/confusion/calibration/effort/feat_importance；effort-aware 与 effort-unaware 两类图均可登记。
- 不负责读取静态指标表充当评估，不负责重算指标、预测、训练或生成新图；指标数值由 evaluate 输出提供。

## 2. 端点契约

### GET /api/figures

| 参数 | 必填 | 契约 |
|---|---|---|
| `model_name` | 是 | 已登记模型 |
| `figure_type` | 否 | `roc` / `pr` / `confusion` / `calibration` / `effort` / `feat_importance` |
| `job_id` | 否 | 选择已登记的 evaluate 输出批次；缺省取该模型最新登记且 manifest 完整的批次 |

响应 `data`：

| 字段 | 含义 |
|---|---|
| `model_name` / `line` / `source_job_id` | 模型、模型线与选定的 evaluate 批次 |
| `metrics[]` | 只读该批次 evaluate_metrics 中此模型的 §3.6 长表行；文件不可用则为空并由 metrics_unavailable 说明 |
| `metrics_unavailable` | 指标文件缺失、checksum 不符或批次无此模型时的原因，无问题为 null |
| `figures[]` | 磁盘校验存在的图，按上述类型固定顺序 |
| `figures[].figure_type` | 六类之一；effort 项另含 effort_kind |
| `figures[].effort_kind` | `aware` / `unaware`，非 effort 为 null |
| `figures[].title` / `file_path` / `checksum_sha256` | 标题、鉴权 URL 与校验值 |
| `figures[].source_job_id` | 产生该图的 evaluate job |
| `missing[]` | 有登记但文件或 checksum 校验失败的项及原因 |

`file_path` 可为 `/static/figures/...` 或受控输出下载 URL；两种路径都要求 X-API-Key。metrics 的逐字段结构只能是 §3.6 的 `model_name,line,metric,value,threshold,n,pos_rate,dataset_version,model_version,computed_at`，从同一批次已生成文件只读投影，本接口不重算。混淆数据从对应 evaluate 输出取得。

### 错误码

| 业务码 | HTTP | 场景 |
|---|---|---|
| 40001 | 400 | 缺 model_name、figure_type 非法或未知参数 |
| 40100 | 401 | 缺失或错误的 `X-API-Key`，包括 `/static` 取图 |
| 40400 | 404 | 模型不存在或没有任何图件登记 |
| 50000 | 500 | 未预期读取错误；可预期缺图进入 missing，不作为 50000 |

## 3. 输入契约

无上传文件。查询只接受模型、图类型和可选 evaluate job_id；图与 metrics 必须来自 §3.6 evaluate 输出及 §3.9 manifest，经 storage 校验登记。登记路径限定在允许静态根或 `backend/var/outputs` 内，拒绝绝对任意外部路径与 `..`。

§3.6 对图的逐字定义为：**“图 png：roc/pr/confusion/calibration/effort/feat_importance（effort 两类课程硬要求）。”** 文件格式需校验 PNG 魔数、大小和 checksum，SVG 或伪造 PNG 不得冒充。

## 4. 输出契约

GET 仅输出 JSON 图件索引与已生成 metrics 的只读投影，不生成新图、CSV 或 manifest，不创建输出目录。图、metrics 与其原 evaluate manifest 仍由产生它们的输出目录提供；本接口不复制、重命名或修改文件。

缺图时 figures 不包含不可用 URL，missing 给出原因；checksum 改变视为不可用。页面使用带 X-API-Key 的 fetch 获取二进制并转 ObjectURL，不能为 img 标签关闭鉴权。

## 5. 可配置项

- model_name、figure_type 与 job_id 为查询选项；effort_enabled 控制评估是否产生 effort-aware 结果，但 figures 不隐藏已登记历史图。
- 静态根、输出根和大小限制属于部署安全策略；阈值与指标配置由 evaluate 使用，figures 不另设计算配置。
- `.env` 仅提供出厂路径默认，不允许通过查询指定任意文件系统路径。

## 6. 状态持久化

- model_figure 持久登记模型、图类型、路径和来源；源文件位于 `backend/var/outputs/<job_id>/`（gitignore）或受控静态根。
- 只读查询不创建 job、不改图、不改指标；服务重启后登记仍在，文件缺失据实进入 missing。
- 新 evaluate 产物经 storage 登记后可无需重启查询；旧登记不覆盖不同来源 job 的审计信息。

## 7. 验收

fixtures：`tests/fixtures/files/figures/`，包含合法 PNG、缺失文件、checksum 改变和伪造格式，以及对应 §3.9 manifest。

- **正常**：各图类型与 effort 两类按固定顺序返回，URL 带鉴权可取，source_job_id/checksum 与登记一致。
- **边界**：某模型只有部分图、无 effort-aware、feat_importance 不可用、文件被删除均通过 figures/missing 明确表达。
- **非法**：缺模型参数、非法类型、伪造 PNG、路径越界、无/错 API Key 返回 40001/40100/40400；不触发评估计算。
- 响应无私有指标来源；改用户阈值不会导致本接口绘图，新的图只能来自 evaluate run。

## 8. 边界

figures 是评估产物的展示索引，不是评估计算入口。evaluate 只依 §3.4 文件（含透传真标签）独立运行，storage 登记为可选展示路径；数据库或 figures 服务均不是评估和其他模块运行前置。
