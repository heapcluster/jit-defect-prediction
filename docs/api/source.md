# 缺陷定位、修复建议与源码 API（localize / source）

一句话：独立消费 predictions、可选 explanations 与指定仓库版本，输出可疑行、完整证据与四段式修复建议，并提供同版本源码树与文件读取；当前不生成修复补丁。

实现状态：已实现（定位、源码读取、建议与文件交付；无可靠修改，当前不生成修复补丁）　期次：一期

验证口径：2026-11-23 本轮后端全量 809 项、前端全量 253 项测试通过；1200/375px 浏览器自动化覆盖源码浏览、高亮、真实 SHAP 文件匹配、版本拒绝、提交级回退、下载校验及八 tab 旧链接兼容，CLI/API 同输入结果一致。测试为 AI 生成、未经人工审阅，不代表人工验收。

文件契约唯一权威：[../file-contracts.md](../file-contracts.md) §3.4、§3.7、§3.8、§3.9；公共口径见 [README.md](README.md)。

## 1. 职责与不负责范围

- 负责提交版本源码目录/文件按限额读取、行级可疑度排序、完整证据和四段式修复建议；原始 Git diff 仅为只读证据。当前无可靠修改，不生成修复补丁；`patch_preview=true` 记录 `summary.patch_reason="no_reliable_patch"`。
- 提交级 risk_score 与行级 suspicion 是不同数值；后者为可配置启发式可疑度，不宣称为独立训练的行级概率。
- 不负责提交级预测、XAI 计算、训练或评估；只消费其文件，不调用 predict/explain 服务。
- 不自动应用补丁、修改工作区、创建提交或 PR；无源码或建议服务失败不影响已交付预测文件。

## 2. 端点契约

### POST /api/localize/run

同步 multipart：`files[]` 必须含 predictions，可含 explanations 及其同 stem manifest；`config` JSON part。最多 4 个文件、合计 64MiB（含 manifest），文件名不可重复。文件可直接上传，也可按 [产物库选择流程](README.md#产物库选择与上传等价)从 `predict_batch` / `explain` 任务下载后提交；`dataset_id` 仅便利解析仓库，不代替预测文件。localize 不新增 job kind；筛选后最多 20 个预测目标（提交/模型/版本预测行），且预估 `targets * top_n.files * top_n.lines <= 5000`，超限返回 40001，由调用方筛选、降低 Top-N 或分批。

| config 字段 | 必填 | 契约 |
|---|---|---|
| `repo_source` | 与 dataset_id 二选一 | 本地路径或 URL；安全规则同 collect，显式值优先 |
| `dataset_id` | 与 repo_source 二选一 | 解析登记仓库的便利项，不代替预测文件 |
| `commit_hash` | 否 | 40 位 hex，筛选预测目标；不传则不按提交筛选 |
| `model_name` | 否 | 非空模型名，筛选预测目标；不传则不按模型筛选 |
| `weights` | 否 | `file_types` / `change` / `hunk` / `line_content` / `line_path` / `mix`；嵌套部分覆盖 `localization.weights`，未提供项保留已保存默认值 |
| `top_n` | 否 | 对象 `{files,lines}`，各为 1..1000 整数；部分覆盖保留 `localization.top_n` 未提供项 |
| `file_size_max` | 否 | 字节数，1..16MiB 的整数；默认取已保存 `localization.file_size_max`（出厂 1MiB） |
| `suggestion_sources` | 否 | `template` / `llm` / `history` 的非空、无重复子集 |
| `patch_preview` | 否 | 默认 true；当前不生成修复补丁，true 时 `summary.patch_reason="no_reliable_patch"`，false 时为 null |
| `format` | 否 | `csv` / `xlsx`，默认 `csv`；当前两种表格均输出，此项决定首选格式和主 manifest |

响应 `data`：`{job_id,module:"localize",status:"success",outputs[],manifest_name,summary,localization,suggestions}`。这里 job_id 为 UUID，仅是输出批次标识，不创建 job 行；`outputs[]` 项为 `{name,sha256,size_bytes}`，`localization` 为前 20 行预览，`suggestions` 为建议全文。完整 rows 从登记的 `localization_evidence_<job_id>.json` 加载，不以预览充当全部结果；页面须完成证据 JSON 结构校验后才确认输出成功。summary 含 `commits,localized_rows,line_rows,commit_rows,insufficient_count,suggestion_sources,truncated,patch_reason`。单批过大返回 40001，不排队、不隐式创建异步任务。

### GET /api/localize/outputs/{job_id}/{name}

下载已登记的 localization CSV/XLSX、完整 evidence JSON、suggestions Markdown 或 manifest；只允许 `outputs[]` 登记的基础文件名。当前没有修复 patch 文件可下载，原始提交 Git diff 位于 evidence JSON 中，仅供只读取证。

### GET /api/source/tree

| 参数 | 必填 | 契约 |
|---|---|---|
| `commit_hash` | 是 | 完整 40 位 hex，不接受分支名、ref 或短哈希 |
| `path` | 否 | 仓库相对目录，默认根目录；禁止绝对路径与 `..` |
| `search` | 否 | 非空路径子串，最多 4096 字符；空搜索必须省略参数，不能传 `search=` |
| `repo_source` / `dataset_id` | 二选一 | 显式仓库或可选登记便利项 |

响应 `data:{commit_hash,path,entries[],truncated,skipped[]}`；entries 每项 `{name,path,type,size,mode}`，type 为 tree/blob，每次最多 1000 项，超出标记 `truncated`。不支持的 gitlink 以 `skipped:[{path,reason:"unsupported_gitlink"}]` 标注（最多 1000 项）；目录浏览不保证单次返回整棵树。

### GET /api/source/file

`commit_hash` 必填且为完整 40 位 hex，`path` 必填且为仓库相对文件路径，`repo_source`/`dataset_id` 同上；另接受 `start_line`（默认 1）、`end_line`（1-based 闭区间）。每次最多返回 2000 行，省略 end 时读自 start 起最多 2000 行；end 超过 EOF 或请求上限时自动夹取，start 超过 EOF 非法（空文件仅允许 start=1）。超过 `file_size_max` 的文件整体返回 `too_large`，缩小行范围不能绕过大小限制。响应：

| 字段 | 含义 |
|---|---|
| `commit_hash` / `path` | 版本与文件 |
| `status` | `ok` / `binary` / `too_large` / `not_found` |
| `content` | ok 时文本，其余为 null |
| `start_line` / `end_line` / `total_lines` | 实际行范围与总行数 |
| `size_bytes` / `encoding` | 字节数与文本编码 |
| `reason` | 非 ok 的明确原因 |

文件 binary/too_large/not_found 在提交可达时以 HTTP 200 + data.status 表达，不当作服务异常。

### 错误码

| 业务码 | HTTP | 场景 |
|---|---|---|
| 40001 | 400 | 路径越界、行范围非法、输入 schema/权重/top_n 非法、单批过大、下载名非法 |
| 40100 | 401 | 缺失或错误的 `X-API-Key`，包括源码和下载 |
| 40400 | 404 | 仓库、提交、可选 dataset、输出批次或文件登记不存在 |
| 50000 | 500 | 未预期 Git/服务错误；建议生成失败应回退模板并标来源 |

## 3. 输入契约

predictions 逐字采用 §3.4：

| 列 | 类型 | 必填 | 含义 |
|---|---|---|---|
| commit_hash | string(40) | 是 | 提交 |
| model_name | string | 是 | 模型 |
| risk_score | float [0,1] | 是 | 概率（5 位小数） |
| predicted_label | int 0/1 | 是 | 按 decision_threshold 的二分类标签 |
| decision_threshold | float | 是 | 本次判定阈值 |
| model_version / feature_version | string | 是 | 版本元信息 |
| predicted_at | datetime | 是 | 预测时间 |
| is_bug_inducing | int 空可 | 否 | 透传真标签（便于 evaluate 单文件输入） |

可选 explanations 逐字采用 §3.7：

> `commit_hash,model_name,technique,feature,raw_value,contribution,direction,rank,label,model_version,feature_version`；不支持组合产 `reason_code` 行（feature 空、contribution 空、reason_code 非空），MUST NOT 静默缺行。

源码来自 repo_source 对应 commit 的 Git 对象，禁止以当前工作区替代。上传执行大小、扩展名魔数、schema、公式注入校验；Git 使用参数数组，仓库路径限定允许根目录，文件路径禁止穿越，文件名不拼接 shell。

缺少 explanations 时可仅依 predictions、diff 与代码上下文定位，但 evidence_json 必须标明证据来源不足；缺 predictions 不允许凭空生成提交风险。

## 4. 输出契约

当前交付采用 §3.8 的定位列与四段式建议：

> localization：`commit_hash,file_path,line_number,suspicion,rank,evidence_json,level(line|commit)`；建议含问题说明/建议修改/风险提示/参考依据。§3.8 的修复 patch 当前不生成：没有可靠修改，不能将原始 Git diff 当作修复补丁交付。

| 文件 | 命名（job_id 为 UUID） | 契约 |
|---|---|---|
| localization | `localization_localization_<job_id>.csv` 和 `.xlsx` | 两种格式均生成，严格使用上述 §3.8 列 |
| evidence | `localization_evidence_<job_id>.json` | `{rows,evidence,summary}`；rows 为完整定位行，evidence 按 commit_hash 收录原始 diff、文件/预测证据与不足原因 |
| suggestions | `localization_suggestions_<job_id>.md` | 四段式，引用实际 file_path/line_number 与证据来源；无可验证文本行时引用提交并注明不足 |
| manifest | 各产物同 stem `.manifest.json` | 表格共用 `localization_localization_<job_id>.manifest.json`；证据和建议各有同 stem manifest，按 §3.9 登记输入、配置快照及全部产物 checksum |

当前不输出修复 `.diff`；`patch_preview=true` 时 `summary.patch_reason="no_reliable_patch"`，false 时为 null。evidence 中的 `diff` 是原始提交的只读 Git 证据，不是建议修改的补丁。

逐行 `evidence_json` 记录预测风险、解释上下文、diff 元数据、代码上下文、历史修复及不足原因；提交级解释不证明某行有缺陷，也不作为可调的解释映射权重。level 只能 line/commit；无法验证行时可给 commit 级结果，file_path/line_number 为 null，禁止编造行号。

suggestions 必须含“问题说明、建议修改、风险提示、参考依据”四段；LLM 不可用回退模板并标来源。CSV UTF-8 BOM、XLSX 单 sheet，证据 JSON 与 md 使用 UTF-8。

源码 GET 只读 Git 对象，不产生交换文件或 manifest；localize run 的上述文件必须全部落盘并可下载。

## 5. 可配置项

- `localization.weights`：仅 `file_types`、`change`、`hunk`、`line_content`、`line_path`、`mix` 六组；权重须为非负有限数，拒绝未知字段。HTTP run 的嵌套部分覆盖保留数据库已保存的未提供项，不退回出厂默认；解释仅为上下文，不存在解释映射权重。
- `localization.top_n`（files/lines 各 1..1000）、`localization.file_size_max`（1..16MiB 字节整数）、`localization.suggestion_sources`，全部落 user_config，重启恢复。
- 单次运行可覆盖权重、Top-N、文件大小上限、建议来源、patch_preview、格式和目标筛选；源码文件超过 file_size_max 整体返回 too_large，行范围不能绕过限制。
- LLM 连接和密钥只走部署环境，不写入 user_config 或 manifest；`.env` 仅提供非敏感出厂默认。

## 6. 状态持久化

- localize 同步执行，不新增 job kind，不写 queued/running；job_id 仅用于输出目录、manifest 与下载关联。
- 输出落 `backend/var/outputs/<job_id>/`（gitignore）；配置写 user_config，重启恢复。任务列表不会把 localize 显示为第七类任务。
- 超大输入以 40001 请求分批，已完成批次文件保留；不得返回部分成功却缺 manifest 的目录。
- 源码 tree/file 为只读请求，不创建输出目录；定位结果复现依输入 checksum、commit、权重与建议来源快照。

## 7. 验收

自动化用例与临时 Git/表格输入见 `backend/tests/test_localization_core.py`、`backend/tests/test_source_api.py` 和 `frontend/tests/Localization.spec.js`，无需 predict/explain 服务在线；均为 AI 生成、未经人工审阅的自动化验证，不作为人工验收结论。

- **正常**：得到 §3.8 可疑行 CSV/XLSX、完整 evidence JSON、四段建议和同 stem manifest；tree/file 读取同一 commit，行号映射一致，下载全部鉴权。当前不生成修复补丁；请求 patch 时明确 `no_reliable_patch`，原始 diff 只作为证据。
- **边界**：无 explanations、commit 级降级、空 diff、二进制、超大文件、LLM 失败、无补丁均明确标注，不伪造行号或修改工作区。
- **非法**：缺 predictions、hash/版本不符、路径 `..`、绝对路径、非法行范围、权重建模错误、单批过大均返回 40001/40400，不产半成品。
- 权重和 Top-N 改动真实影响排序；不新增 job kind；CLI/API 同 fixture 的 localization 数值与建议结构一致。

## 8. 边界

localization 与 predict/explain 仅以 §3.4/§3.7 文件和模型/特征版本衔接，与 collect 仅共享仓库安全约束。`dataset_id` 只便利解析仓库。CLI 文件定位与源码浏览无需数据库或上游服务，但必须显式提供 `--allow-root`；`localize run --config` 的 JSON 仅被显式提供的同名 flag 覆盖。HTTP 使用数据库读取配置和可选数据集，不应将 CLI 的无数据库能力等同为 HTTP 无数据库。
