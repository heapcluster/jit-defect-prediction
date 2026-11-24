# 缺陷定位及修复（功能 8）

实现状态：已实现（定位、源码读取、建议与文件交付；无可靠修改，当前不生成修复补丁）　期次：一期

验证口径：2026-11-23 本轮后端全量 809 项、前端全量 253 项测试通过；CLI/API 同输入结果一致，浏览器自动化已检查 1200/375px 的源码、高亮、解释匹配和提交级回退。测试为 AI 生成、未经人工审阅，不代表人工验收。

## 一句话概述

独立的定位与修复建议工具：消费 `predictions.csv` 与其提交版本的源码，可选结合 `explanations.csv` 给出行级可疑度、完整证据和四段式建议；源码浏览可单独使用，不自动修改代码。原始提交 Git diff 是只读输入证据，不是修复补丁；当前无可靠修改，不生成 patch。

## 1 职责与不负责范围

**负责**：

- 用 `git ls-tree` / `git cat-file` 原语按限额读取指定提交的目录树、文件全文和行范围，支持路径搜索、分页与行跳转。
- 综合必需预测文件中的提交风险、代码上下文与 diff 计算行级可疑度，输出排序、Top-N 截断和逐行证据说明；可选提交级解释仅补充上下文，不证明某行存在缺陷，也不是可调的解释映射权重。
- 生成引用具体文件和行号的“问题说明 / 建议修改 / 风险提示 / 参考依据”四段式建议，可结合模板、LLM 与真实历史修复。
- 当前无可靠修改，不生成修复补丁；`patch_preview=true` 仅记录 `summary.patch_reason="no_reliable_patch"`。缺少解释时按预测、代码与原始 diff 定位并标注证据不足，缺少预测文件则拒绝定位运行。

**不负责**：

- 自动应用补丁、修改工作区、自动提交、创建 PR 或提供完整 IDE 编辑能力。
- 训练提交级或行级预测模型、重新计算 XAI、定义性能阈值；行级可疑度不得冒充独立训练的行级缺陷概率。
- 在源码读取失败时影响已有提交级预测，或编造文件、行号、API、历史修复和模型证据。

## 2 独立运行入口

```bash
python -m app.cli source tree --repo /path/to/repo --allow-root /path --commit <40hex> --path src
python -m app.cli source file --repo /path/to/repo --allow-root /path --commit <40hex> --path <file> --start-line 1 --end-line 200
python -m app.cli localize run \
  --repo /path/to/repo --allow-root /path --commit <40hex> \
  --predictions predictions.csv --explanations explanations.csv \
  --top-n 10 --patch-preview --out ./out
```

| 入口 | 命令 / 端点 | 契约 |
|---|---|---|
| CLI | `source tree/file`、`localize run` | 无需数据库，但必须显式提供 `--allow-root`（可重复）；source 浏览需仓库与 40 位提交哈希，localize run 必需预测文件与对应源码，解释文件可选 |
| 源码 API | `GET /api/source/tree`、`GET /api/source/file` | 按提交读取目录与文件，使用 ls-tree/cat-file，不读当前工作区替代版本 |
| 定位 API | `POST /api/localize/run` | 同步返回前 20 行定位预览、建议、summary 和输出关联号；完整 rows 从证据 JSON 加载，不新增任务 kind |
| 下载 | `GET /api/localize/outputs/{job_id}/{name}` | 下载已登记 localization CSV/XLSX、evidence JSON、suggestions Markdown 与 manifest；当前没有修复 patch |
| 详情展示 | 提交详情源码/原始 diff 视图 | 仅做展示和外部编排；原始提交 diff 是只读证据，不是修复补丁 |

所有 HTTP 端点（含 source 与文件下载）必须使用 `X-API-Key`。路径禁止绝对路径和 `..` 越界；Git 使用参数数组，仓库根目录复用 collect 的安全边界。CLI `--config` 读取定位配置 JSON；`--commit`、`--file-size-max`、`--top-files`、`--top-n`、`--patch-preview` / `--no-patch-preview`、`--format` 仅在显式提供时覆盖 JSON 对应项，不以未提供的 flag 默认值覆盖配置。CLI 不读取数据库保存的默认值。

## 3 输入契约

- 定位 run 的必填输入为 `predictions.csv`、可读仓库与定位配置；源码版本由预测行中的 40 位提交哈希确定。仓库必须能读取对应 blob，blobless 克隆无法惰性取回时明确失败。
- 必需预测文件遵循 [`../file-contracts.md`](../file-contracts.md) §3.4，可选解释文件遵循 §3.7；两者可直接上传或从产物库下载后按 `files[]` 提交，按提交、模型与版本匹配，不要求 predict/explain 服务在线。
- 独立 `source/tree` 与 `source/file` 浏览只需仓库与完整 40 位提交哈希，不接受 ref 或短哈希，不需要预测文件；tree 接收可选目录与非空路径搜索词，空搜索省略参数；file 接收文件路径与可选 1-based 行范围。
- 定位配置包含行级权重、Top-N、`file_size_max`、建议来源、`patch_preview`、格式，以及可选 `commit_hash` / `model_name` 预测目标筛选；完整输入版本和 checksum 入 manifest。建议来源为 template/llm/history 的非空无重复子集，patch 请求不保证产出补丁，当前一律无可靠 patch。
- 上传最多 4 个文件、合计 64MiB（含 companion manifest）；筛选后最多 20 个预测目标，且预估 `targets * top_n.files * top_n.lines <= 5000`，否则返回 40001，需筛选、降低 Top-N 或分批。
- 缺预测文件或预测与提交、版本不匹配时返回 40001；仅缺解释或解释含 `reason_code` 行时按已有预测、代码和 diff 证据显式降级，不得把空贡献解释成无风险。

## 4 输出契约

### 源码读取

- tree 返回目录/文件条目及路径、类型、大小和模式，每次最多 1000 项，含 `truncated` 与 `skipped`（不支持的 gitlink）；file 返回文本、实际行范围、总行数、大小、编码和状态。
- file 状态仅 `ok / binary / too_large / not_found`；仓库或提交不可达通过业务错误表达。非 ok 不强行解码、不返回伪造正文；超大文件整体拒绝，缩小行范围不能解决。
- file 每次最多返回 2000 行；end 超过 EOF 或请求上限会夹取，start 超过 EOF 非法（空文件仅允许 start=1）。所有内容来自提交哈希对应版本，保证目录、文件、原始 diff、定位和建议版本一致。

### 定位与建议文件

| 输出 | 文件与内容 |
|---|---|
| 行级定位 | `localization_localization_<job_id>.csv` 和 `.xlsx` 均生成（job_id 为 UUID）：严格遵循 §3.8 localization schema，行级与提交级降级均用 `level` 区分 |
| 证据明细 | `localization_evidence_<job_id>.json`：`{rows,evidence,summary}`；rows 为完整行，evidence 按 commit_hash 收录原始 diff、文件/hunk/代码信号、预测/解释上下文、真实历史修复和不足原因 |
| 修复建议 | `localization_suggestions_<job_id>.md`：严格遵循 §3.8 四段式，引用当前提交的具体文件与行号并标明来源；无可验证行时引用提交并注明不足 |
| patch 请求限制 | 当前无可靠修改，不生成修复 `.diff`；`patch_preview=true` 记录 `summary.patch_reason="no_reliable_patch"`，false 时为 null；证据中的原始 Git diff 不是修复补丁 |
| manifest | 各产物伴同 stem `.manifest.json`（CSV/XLSX 共用表格 stem）；满足 §3.9，记录仓库/提交、预测及可选解释输入 checksum、定位配置和全部产物 checksum |

命名统一为 `<module>_<artifact>_<job_id>.<ext>`。这里的 `job_id` 是同步结果关联号，不写入六类 job，也不新增 localize kind。提交级风险概率与行级 suspicion 必须在响应和界面分开展示；无可验证行时返回 commit 级结果及不足原因，file_path/line_number 为 null，不能编造行级数据。

## 5 可配置项

| 配置 | 来源 | 默认 / 约束 |
|---|---|---|
| `localization.weights` | `user_config` 命名空间键 | 仅 `file_types`、`change`、`hunk`、`line_content`、`line_path`、`mix`；非负有限数，拒绝未知键；HTTP run 嵌套部分覆盖保留已保存默认值。解释仅为上下文，不提供行级证明或可调映射权重 |
| `localization.top_n` | `user_config` 命名空间键 | `{files,lines}` 各为 1..1000 整数；出厂 5 文件/30 行，截断必须标记 |
| `localization.file_size_max` | `user_config` 命名空间键 | 1..16MiB 的字节整数，出厂 1MiB；超限整体返回 too_large，不能用范围绕过，二进制单独识别 |
| `localization.suggestion_sources` | `user_config` 命名空间键 | template/llm/history 的非空、无重复组合，出厂 template；LLM 失败回退模板并标来源 |
| `collect.allow_roots` / `collect.protocol_whitelist` | `user_config` 共享安全键；CLI 显式安全参数 | 约束本地仓库与克隆来源；CLI 必须显式 `--allow-root`，不从数据库读取安全默认值 |
| `patch_preview` / `format` / `commit_hash` / `model_name` | 单次 run 配置；源码视图为页面内状态 | patch 默认 true，但当前仅记录 no_reliable_patch，不生成或应用修复补丁；格式决定首选表格；提交/模型为可选预测目标筛选；源码展示状态仅保留于页面内 |
| LLM 服务参数 | 部署安全环境 | 缺少凭证、超时或失败不影响模板回退，凭证不入库或 manifest，run 不接受任意 LLM 连接参数 |

## 6 状态持久化

- 同步定位结果、配置快照和输出关联号持久化；不新增第七种 job kind。统一六类五态规则不适用于 source/localize 同步调用。
- 输出落盘 `backend/var/outputs/<job_id>/`，目录整体加入 gitignore；定位表、完整证据 JSON、建议与同 stem manifest 按提交和配置快照可复验，原始 diff 只在证据中，不另产修复补丁。
- `localization.*` 落 `user_config`，重启恢复；每次运行固化权重版本、Top-N、建议来源、模型/特征版本和可选解释版本。
- 源码不可用或提交不可达通过业务错误表达；文件不存在、过大、二进制有明确文件状态，LLM 失败记录模板回退与不足原因；这些失败不得修改 prediction 或解释文件。
- 本模块只读 Git 对象并写独立输出目录；自动化断言证明没有 apply、checkout 写回、commit、push 或 PR 创建动作。

## 7 与其他模块边界

- 与 predict/explain 仅为 §3.4/§3.7 文件兼容；预测文件必需、解释文件可选。不调用它们的在线服务，独立运行不等于可以省略必需文件，具体解释器实现也不进入本模块。
- 仓库安全规则与 collect 共用配置，但定位可直接接收任意允许根目录内的仓库，不要求先执行采集。
- 预测与解释文件直接消费，无需导入展示库；定位结果不映射展示库 schema，仅作文件交付。产物库文件经所属模块的下载端点取得后按 `files[]` 上传，不通过展示表传递。历史修复只能引用真实存在的提交。
- extension 的客户端、插件和 CI 复用本模块输出与源码服务，不复制评分权重、证据规则或建议提示词。
- 页面层作为⑤预测的子页，可从预测结果/提交详情带入 commit/model；模块本身不依赖⑤在线，仍可独立提供仓库、预测文件与可选解释文件运行。

## 8 验收标准

自动化用例与临时 Git/表格输入见 `backend/tests/test_localization_core.py`、`backend/tests/test_source_api.py` 和 `frontend/tests/Localization.spec.js`；无 predict/explain 服务时可独立运行 CLI/API。验证为 AI 生成、未经人工审阅的自动化验证，不代表人工验收，不在此记录未核实的浏览器或测试数量。

- 能按限额浏览指定提交的目录与文件，支持搜索、行范围和跳转；tree 至多 1000 项并标记 truncated/skipped，file 每次至多 2000 行，end 越界夹取、start 超 EOF 拒绝；自动化检查提交版本读取与路径安全。
- 可疑行按 suspicion 排序并在提交版本源码标记，完整 rows 从 evidence JSON 加载；页面完成证据校验才确认新结果，hash/path/line 高亮绑定已确认快照，不随草稿变化；移动端树/源码单列，代码与表格内部滚动。证据可追溯文件、hunk、代码信号和可选解释上下文，提交级概率与行级可疑度区分明确。
- 建议包含四段、可验证文件行或提交不足原因及真实参考来源；LLM 失败回退模板，缺解释时标明证据不足，缺预测文件则拒绝定位运行，无依据不编造。
- 当前不生成修复 patch；patch 请求为 true 时记录 no_reliable_patch，原始提交 diff 仅为只读输入证据，不是修复补丁；自动化检查 Git 工作区、HEAD 和提交数不变，无自动提交或 PR 行为。
- 无仓库或提交不可达明确报错，文件不存在、超大、二进制与 LLM 回退明确标注且不影响预测文件；超大文件不能用行范围绕过。权重六组、Top-N、文件上限与建议来源配置生效并重启恢复，HTTP 嵌套部分覆盖保留已保存默认项。
- 承接 TODO/08：源码读取、版本一致、行级评分、解释上下文、四段建议、同步输出与失败场景见上述自动化用例；CLI/API 对齐同输入的定位数值与建议结构，不把自动化验证等同人工验收。
