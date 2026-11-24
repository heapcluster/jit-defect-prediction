# 缺陷定位及修复工具台（Localization）

实现状态：已实现（定位工具台、源码浏览、高亮、建议与下载；当前不生成修复补丁）　期次：一期

验证口径：2026-11-23 本轮前端全量 253 项测试通过；浏览器自动化已检查 1200/375px 的独立源码浏览、真实预测与 SHAP 文件输入、高亮与证据、版本不符拒绝、提交级回退、下载及八 tab 旧链接兼容。测试为 AI 生成、未经人工审阅，不代表人工验收。

## 一句话

独立定位工具：输入仓库与提交版本的源码，上传或从产物库选择必需的 `predictions.csv`，可选提供 `explanations.csv`，配置行级权重、Top-N 与建议来源后同步运行，交付可疑行、完整证据 JSON、提交版本源码高亮、四段式建议及可下载文件与同 stem manifest。原始提交 diff 单独作为只读证据展示，不是修复补丁；当前无可靠修改，不生成 patch。本页作为⑤预测的子页，可从预测结果/提交详情带入 commit/model，也可独立访问 `/localization`。

## 入口与导航

- 本页为功能⑧（缺陷定位及修复），作为⑤模型预测的页内子页（子签），保留独立路由 `/localization`；页内为定位及修复工具台，源码浏览、行级高亮与建议在输出区展示，导航见 [README.md](README.md)。提交详情通过 `/localization?commit_hash=&model_name=` 进入并回填对象。
- 从⑤风险列表/提交详情进入时带入 `commit_hash`、`model_name` 和本次预测结果；独立访问时自行提供仓库、预测文件与可选解释文件。两种入口调用同一源码读取、行级评分和建议服务。
- CLI 与本页调用同一源码读取、行级评分和建议服务；页面不计算可疑度，不直接调用具体 XAI 解释器。
- 文件契约：[../file-contracts.md](../file-contracts.md) §3.4（必需预测输入）、§3.7（可选解释输入）、§3.8（定位与四段式建议）、§3.9（manifest）。当前交付定位 CSV/XLSX、完整证据 JSON、建议 Markdown 及同 stem manifest，不生成 §3.8 所述修复补丁。
- 定位运行必须提供预测文件与对应提交的源码；仅解释文件缺失时可标注证据不足继续。源码 tree/file 浏览可只凭仓库与提交独立使用，不等于可以省略定位 run 的预测输入。

产物选择与下载再提交统一遵循 [公共流程](../api/README.md#产物库选择与上传等价)：必需预测文件取自 predict_batch，可选解释文件取自 explain，下载文件及 manifest 后以 `files[]` 提交。已登记数据集只便利回填仓库，不代替预测输入。

## 线框图

```
┌─ 缺陷定位及修复工具台 ──────────────────────────────────────────────────┐
│ ── 输入区 ──                                                            │
│ 仓库路径/URL [________________]  commit_hash [40hex，可选筛选]         │
│ model_name [可选筛选]  或选登记数据集 [▾ dataset_id / repo_source]       │
│ 预测（必需） [上传 predictions.csv CSV/XLSX] [或选产物库文件▾]           │
│ 解释（可选） [上传 explanations.csv CSV/XLSX] [或选产物库文件▾]          │
│ ── 配置区 ──                                                            │
│ weights 嵌套 JSON [file_types/change/hunk/line_content/line_path/mix]    │
│ Top-N [5] 文件 / [30] 行（各1..1000） 文件上限[1..16MiB，按字节填写]     │
│ 建议来源 [☑模板 □LLM □历史修复]  ☑ 请求 patch_preview（当前无可靠补丁） │
│ 输出格式 [CSV/XLSX▾]  [运行] [保存当前定位默认值]                      │
│ ── 同步请求 / 完整证据加载状态 ──                                      │
│ 状态[处理中/校验完整证据/成功/失败]（不创建 job、不轮询 jobs）           │
│ ── 输出预览：可疑行 + 完整源码 ──                                       │
│ 视图 [原始提交 diff | 提交版本全文] 文件搜索[______] 行跳转[____]       │
│ ┌─ 目录树 ────────┐ ┌─ 文件：core/A.java（提交版本）─────────────────┐ │
│ │ ▾ core/         │ │ 118  …                                         │ │
│ │   A.java        │ │ 119  …                                         │ │
│ │ ▸ util/         │ │ 120 █ if (source == null) {       suspicion .81│ │
│ │                 │ │ 121 █ throw new IllegalArgument…  rank 2       │ │
│ └─────────────────┘ └────────────────────────────────────────────────┘ │
│ 点击高亮行 → [证据：文件/hunk/内容信号/相关特征/关联提交]               │
│ 完整 evidence rows：file_path line_number suspicion rank evidence…    │
│ ── 四段式建议预览 ──                                                    │
│ ①问题说明（含文件:行） ②建议修改 ③风险提示 ④参考依据                   │
│ 来源[模板|LLM|历史修复]                                                 │
│ patch_reason [no_reliable_patch：仅提供建议，当前无修复补丁]            │
│ 原始提交 diff 在源码视图单独只读展示；不是建议修复 patch               │
│ 下载 [CSV] [XLSX] [evidence.json] [同 stem manifest] [suggestions.md]    │
└─────────────────────────────────────────────────────────────────────────┘
```

图中数值均为占位示意。提交级风险概率与行级 suspicion 分区标注，行级分数不得称为独立训练的行级缺陷概率。

## 控件与接口映射

| 控件 | 端点 | 说明 |
|---|---|---|
| 仓库路径/URL、commit_hash / model_name / 登记数据集 [▾] | `POST /api/localize/run`；数据集选项 `GET /api/datasets` | 仓库限定允许根目录与协议白名单；commit_hash/model_name 可选筛选预测目标；源码浏览必须提供完整 40 位 hex，不接受 ref/短哈希 |
| 预测 / 解释文件上传或选产物库文件 | `GET /api/jobs?kind=predict_batch`、`GET /api/jobs?kind=explain` 查询来源；经对应 outputs 端点下载文件及 manifest，再以 `files[]` 提交 `POST /api/localize/run` | 预测必需、解释可选；最多 4 个文件、合计 64MiB（含 manifest）；CSV/XLSX 按 §3.4/§3.7 校验，不能用 dataset_id 或服务器路径代替文件 |
| 嵌套权重 JSON / Top-N / 文件大小上限 / 建议来源 / patch 请求 / 格式 | `POST /api/localize/run`；默认值 `GET/PUT /api/config`（`localization.weights`、`localization.top_n`、`localization.file_size_max`、`localization.suggestion_sources`） | 权重仅 file_types/change/hunk/line_content/line_path/mix，HTTP 嵌套部分覆盖保留已保存默认；Top 文件/行各 1..1000，文件上限为 1..16MiB 字节整数；解释只是上下文，不是行级证明或可调映射权重；patch 请求不保证产物 |
| [运行] | `POST /api/localize/run` | 同步返回 `{job_id,module,status,outputs[],manifest_name,summary,localization,suggestions}`；localization 仅前 20 行，job_id 仅作 UUID 输出批次标识，不新增 job kind；筛选后最多 20 目标且预估 `targets * top_n.files * top_n.lines <= 5000` |
| 运行状态 | 本次 HTTP 请求与完整证据加载状态 | 不调用 jobs 轮询；完整 evidence JSON 下载并校验成功后才确认新结果，失败保留上次结果并提供重试 |
| 目录树 / 文件搜索 | `GET /api/source/tree`，携带 commit_hash、可选 path、非空 search 和 repo_source/dataset_id | 返回至多 1000 个 tree/blob entries 及 truncated/skipped；空搜索省略参数；禁止绝对路径与 `..` |
| 文件全文 / 行范围 / 行跳转 | `GET /api/source/file`，携带 commit_hash、path、可选 start_line/end_line 和 repo_source/dataset_id | ok/binary/too_large/not_found 明确状态；每次最多 2000 行，end 越界夹取、start 超 EOF 非法；超大文件整体拒绝，范围不能绕过；分页不丢高亮 |
| 可疑行与证据抽屉 | 下载 `localization_evidence_<job_id>.json`，通过 `GET /api/localize/outputs/{job_id}/{name}` | 验证 `{rows,evidence,summary}` 后以完整 rows 展示；文件、行号、suspicion、rank 与 evidence_json 可追溯，提交级与行级数值分开 |
| 四段式建议 | `POST /api/localize/run` 的 suggestions；下载 `GET /api/localize/outputs/{job_id}/{name}` | job_id 来自同步响应，name 取 outputs 中已登记的建议文件 |
| 原始提交 diff / patch_reason 提示 | 完整 evidence 中该提交的 diff；summary.patch_reason | 原始 diff 仅为只读输入证据，不是修复补丁；当前不生成 patch，true 请求记录 no_reliable_patch，无应用、提交或 PR 操作 |
| [CSV][XLSX][evidence.json][suggestions.md] | `GET /api/localize/outputs/{job_id}/{name}` | 仅下载本次 outputs 已登记产物；当前 CSV/XLSX 均输出，不用 format 查询参数转换文件；表格 schema §3.8 |
| [manifest] | `GET /api/localize/outputs/{job_id}/{name}` | 从 outputs 选已登记同 stem manifest，包含输入 checksum、仓库提交与配置快照 |

## 交互流程

1. 填仓库与提交版本，或选登记数据集便利回填仓库；必须上传预测文件或选择 predict_batch 产物，可选上传解释文件或选择 explain 产物。选择产物后下载文件及 manifest，并按 `files[]` 提交；dataset_id 不代替预测输入。校验大小、魔数、schema、版本与 checksum。
2. 从 `GET /api/config` 读取定位命名空间默认值，按需调整嵌套权重 JSON、Top-N、文件大小上限、建议来源、patch 请求和输出格式；HTTP 权重部分覆盖保留已保存的未提供项。解释仅为上下文，不是行级证明或可调映射权重，不允许编造缺失历史提交。
3. [运行] 调 `POST /api/localize/run`，固化本次仓库、提交/模型筛选与配置快照。页面先显示同步请求处理中，再下载本批次已登记的 `localization_evidence_<job_id>.json` 并校验 `{rows,evidence,summary}`；只有完整证据校验成功才替换结果并显示成功。失败保留此前结果和输入，可重试证据加载；不创建 job，不出现 jobs 五态进度条。
4. 响应 localization 仅前 20 行预览；结果表、行级排名、高亮和证据均使用完整 evidence JSON 的 rows。源码读取固定为已确认结果的仓库与所选结果 commit_hash，按 commit_hash + file_path + line_number 匹配 suspicion；修改输入草稿不能改变已确认结果或高亮，只有新结果确认后才替换快照。
5. 原始提交 diff/提交版本全文切换、文件搜索、内容分页与行跳转均保留同版本定位标记。点击可疑行打开证据抽屉，展示文件类型、修改方式、hunk、内容信号、解释上下文和真实关联提交。移动端目录树与源码为单列，代码与表格在各自容器内滚动，不撑宽页面。
6. 建议区固定显示「问题说明 / 建议修改 / 风险提示 / 参考依据」四段，引用本次结果文件行；无可验证行则引用提交并注明不足。LLM 不可用时回退模板并标注来源；无历史修复则不编造历史引用，仍保留可验证文件行或提交依据。
7. 当前无可靠修改，不生成修复补丁；patch 请求为 true 时显示 `summary.patch_reason="no_reliable_patch"`。原始提交 diff 单独标为只读输入证据，不是修复 patch；页面没有应用补丁、写文件或创建提交按钮，不保证 patch 预览或下载。
8. 按本次 outputs 登记文件名下载定位 CSV/XLSX、完整 evidence JSON、同 stem manifest 与 suggestions Markdown；定位输出不映射展示库 schema，仅作文件交付。

## 空态与错误

- 无历史产物时提示「暂无可选产物，可直接上传文件」；缺少必需预测文件时禁用定位运行并提示上传。仅解释缺省不是错误，可按预测、源码与 diff 运行并显示证据不足；源码浏览仍可独立使用。
- 无源仓库、提交不可达或 diff 读取/解析失败按业务错误显示，不当作成功的 commit 级归因。仓库与提交可读但空 diff、无可验证新增文本行时可降级为 commit 级结果并注明不足，不得编造文件行号。
- 文件状态 binary、too_large、not_found 以明确文案展示；超大文件整体拒绝，缩小行范围不能解决，不强行解码；其他已确认输出保留。
- 路径越界、非完整 40 位 hash、空 search 参数、非法行范围、权重或 Top-N 非法、输入缺列/错类型/公式注入/超大小、筛选无目标或批量超限返回 40001，不产半成品。
- 40100 禁用运行、写入与下载；40400 表示提交、仓库或产物不存在；50000 显示内部错误并允许重新运行。LLM 失败只降级建议来源，不让整个定位失败。
- 完整 evidence JSON 未登记、下载失败或结构非法时不确认新结果，保留上次结果并提供重试；定位失败不影响已有提交级预测，截断时显示 truncated 与当前 Top-N。

## 验收

自动化用例与临时输入见 `backend/tests/test_localization_core.py`、`backend/tests/test_source_api.py` 和 `frontend/tests/Localization.spec.js`；验证为 AI 生成、未经人工审阅的自动化验证，不代表人工验收，不在此记录未核实的浏览器或测试数量。

- 只提供符合 §3.4 的预测文件与对应源码，在库空且 predict/explain 服务未运行时也能定位并下载；可选 §3.7 解释补充上下文。缺预测文件拒绝定位 run；仅凭仓库与完整 40 位提交哈希仍可独立调用 source/tree、source/file 浏览源码。
- `POST /api/localize/run` 同步返回 job_id、outputs、前 20 行 localization 预览和 suggestions，不新增 job kind；完整 evidence JSON 校验通过后才确认输出成功，失败保留此前结果并允许重试；按登记文件名下载，manifest checksum 一致。
- 目录浏览、路径搜索、源码分页和行跳转遵循每次 tree 至多 1000 项、file 至多 2000 行的限制，显示 truncated/skipped；源码与结果提交一致，hash/path/line 高亮绑定已确认结果快照，不随输入草稿变化。原始提交 diff 与源码全文切换保留同版本证据；移动端单列树/源码，代码与表格内部滚动。
- 定位 CSV/XLSX 列与 §3.8 一致；完整 rows 来自 evidence JSON，行级 suspicion、rank 与 evidence 可见，且与提交级风险概率明确区分。
- 四段式建议齐全，引用可验证文件行或提交不足原因；来源真实，LLM 失败回退模板，无依据不编造。
- 当前不生成修复补丁，patch 请求为 true 时明确 no_reliable_patch；原始 diff 是只读输入证据，不是修复 patch，不存在应用补丁、修改源码、自动提交或创建 PR 的路径。
- 已登记定位 CSV/XLSX、完整 evidence JSON、同 stem manifest 与 suggestions Markdown 可下载，CSV 中文不乱码；定位结果不映射展示库 schema。
- 权重、Top-N、文件大小上限和建议来源读配置并可保存，HTTP 嵌套部分覆盖保留已保存默认值，重启后恢复；仓库错误、二进制与超大文件状态明确，超大文件不能靠行范围绕过。
- 从⑤带 `commit_hash/model_name` 进入时自动预填对象；未运行预测也可独立提供仓库、预测文件与可选解释文件完成定位。
