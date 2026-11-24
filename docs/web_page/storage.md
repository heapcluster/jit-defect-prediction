# 数据导入导出工具台（Storage）

实现状态：部分　期次：一期

W2 已接通 `/storage` 的数据导入导出、数据集列表/成员与 W1 用户配置两个页内子视图；已有业务任务产物选择待 W3 等生产任务提供标准输出引用后接入。导入为同步请求，不伪造 job；模块不会因为数据库为空而失去文件运行能力。

## 一句话

功能①数据管理 tab：上传模块交换文件或选择已有产物，自动识别写入目标表并按自然键幂等 upsert，逐表反馈导入结果，同时提供 12 表按表导出、数据集版本列表与 [用户配置区](settings.md)；本页不执行收集、清洗、训练、预测、评估、解释或定位计算。

## 入口与导航

- 本页为功能①（数据库存储）tab「数据管理」，路由 `/storage`；页内子视图（子签）为数据导入导出（本页下文）与 [用户配置区](settings.md)，索引见 [README.md](README.md)。
- `/settings` 重定向到 `/storage` 并选中用户配置区；各工具台的 [导入库] 与本页均调用 `POST /api/storage/import`；风险列表、趋势看板和提交详情的空库引导均落到本页。
- 交换文件列 schema 以 [../file-contracts.md](../file-contracts.md) §3.1–3.9 为准；12 表字段与约束见 [../database/README.md](../database/README.md)。
- 导入只是展示与资产登记的可选路径，不是任何模块独立运行的前置；未导入的文件仍可通过原工具下载。

## 线框图

```
┌─ 数据导入导出工具台 ────────────────────────────────────────────────────┐
│ ── 文件导入：上传/选文件 → 配置 → 执行 → 结果预览 ──                   │
│ ┌────────────────────────────────────────────────────────────────────┐ │
│ │ 拖拽上传 CSV/XLSX/ZIP/PNG + 同名 manifest                  │ │
│ │ 或选工具产物 [▾ module / output_ref / filename]                    │ │
│ └────────────────────────────────────────────────────────────────────┘ │
│ 目标表 [自动识别▾]  冲突策略[幂等 upsert]  数据集名[可选________]       │
│ [导入]                                                                │
│ ── 执行状态 / job 进度 ──                                             │
│ 状态[校验中/导入中/成功/失败]（同步请求，不创建 job、不轮询 jobs）     │
│ 识别：predictions.csv §3.4 → prediction                               │
│ ┌─ 逐表 upsert 反馈 ────────────────────────────────────────────────┐ │
│ │ target_table  inserted  updated  unchanged  rejected  自然键/原因   │ │
│ │ prediction    __        __       __       __         (hash,model)  │ │
│ └──────────────────────────────────────────────────────────────────┘ │
│ ── 按表导出 ──                                                        │
│ 表[▾ prediction] 数据集[▾ 全部] 模型[▾ 全部] 时间[______至______]      │
│ [预览前20行]  下载 [CSV] [XLSX] [manifest]                            │
│ ┌─ 导出预览 ────────────────────────────────────────────────────────┐ │
│ │ commit_hash  model_name  risk_score  predicted_label  …           │ │
│ └──────────────────────────────────────────────────────────────────┘ │
│ ── 数据集版本列表（每行一个 dataset_id）──                            │
│ 名称/版本标识    来源仓库    HEAD    样本数  正/负/未打标  状态  创建时间│
│ camel_v3        ______       ______  __     __/__/__      ready  ______│
│ [查看成员] [导出该数据集]                                             │
└─────────────────────────────────────────────────────────────────────────┘
```

图中数值均为占位示意。数据集版本以已登记 `dataset_id` 标识，一期不改变现有主键。

## 控件与接口映射

| 控件 | 端点 | 说明 |
|---|---|---|
| 选择本机文件 | `POST /api/storage/import`（multipart files[] + config JSON part） | W2 校验文件与 companion manifest；已有任务产物选择待生产模块提供标准输出引用后接入 |
| 自动识别目标表 | `POST /api/storage/import`（不接受 target_table 覆盖） | 列 schema 与已验证工件决定目标表；未知或歧义输入明确拒绝，不猜测写入 |
| 冲突策略 [幂等 upsert] | `POST /api/storage/import` | 策略固定；按目标表自然键更新或插入，重复导入不产生重复行 |
| 数据集名（可选） | `POST /api/storage/import` | commits/cleaned 等数据集文件使用；新建登记行，不覆盖原始数据集 |
| [导入] / 执行状态 | `POST /api/storage/import` | 同步返回识别结果与逐表计数；不新增 job kind |
| 逐文件 upsert 反馈 | 同上（items：target_tables/status/inserted/updated/unchanged/rejected/errors） | 计数按源文件逻辑行，不冒充每张表物理写入数；单文件多表同事务，失败整体回滚 |
| 表 [▾] / 数据集 / 模型 / 时间 | `GET /api/storage/export?table=&dataset_id=&model_name=&start_time=&end_time=` | 表选项限 12 表白名单；筛选只读 |
| [预览前20行] | `GET /api/storage/export?table=&format=csv&limit=20&…` | 以同一导出查询生成预览，不另造数据口径 |
| [CSV][XLSX][manifest] | `GET /api/storage/export?table=&format=csv\|xlsx&…` 后按 `GET /api/storage/outputs/{job_id}/{name}` 下载 | manifest 使用同批次返回文件名，不作为 format 参数；CSV 带 BOM，XLSX 单 sheet |
| 数据集版本列表 | `GET /api/datasets?page=&size=&status=&q=` | 名称、dataset_id、仓库、HEAD、样本统计、状态、创建时间 |
| [查看成员] | `GET /api/datasets/{id}/commits?page=&size=&with_features=1` | 只读成员、14 维 log 值、标签与 is_test |
| [导出该数据集] | `GET /api/storage/export?table=commit&dataset_id=&format=csv\|xlsx` | 与成员筛选口径一致；缺预测和未打标留空 |

## 自动识别与幂等口径

| 输入示例 | 可识别目标 | 关键校验 / 自然键示例 |
|---|---|---|
| commits.csv / cleaned.csv（§3.1/§3.2） | `dataset`、`dataset_commit`、`commit`、`commit_feature` | commit_hash；成员键 (dataset_id, commit_hash)；未打标保持 NULL |
| model_package.zip（§3.3） | `model_artifact` → 派生 `model` | model_name、checksum_sha256、feature_version；先验 checksum |
| predictions.csv（§3.4） | `prediction` | (commit_hash, model_name)；risk_score 范围与版本字段 |
| labels.csv（§3.5） | `commit_feature` | commit_hash；is_bug_inducing 仅 1/0/空，空不得写 0 |
| evaluate 图 PNG（§3.6） | `model_figure` | (model_name, figure_type)；图类型与文件路径白名单 |
| 其他契约文件 | 由识别结果明确给出 | 无法安全映射到 12 表时拒绝或列 unchanged，不写入语义不符的表 |

- 12 表导出白名单：`commit / commit_feature / model / prediction / model_figure / user / user_config / job / algorithm / model_artifact / dataset / dataset_commit`。
- `user_config` 按设计不含敏感信息；`job.params_json` 与错误日志导出前脱敏。任何 API Key、密码或 LLM Key 不得通过导入写入库。
- 多表文件先完成全部校验再开启事务；任一目标准入失败则不留下部分提交、特征、成员或模型登记。

## 交互流程

1. 上传一个交换文件及可选同名 manifest，或选择已有工具产物。前端显示文件名、大小和 checksum 校验状态，后端执行最终校验。
2. 目标表保持「自动识别」。服务综合文件名、schema、manifest 和工件内容返回目标表及待写行数；若存在多个合法候选，页面展示候选并要求用户确认后再提交。
3. 冲突策略固定为幂等 upsert。数据集文件可填写新数据集名称；其他文件复用 manifest 中的来源、模型与版本元信息。
4. [导入] 后显示同步请求的校验中、导入中、成功或失败状态，不显示六类 job 进度。成功后逐表展示 inserted/updated/unchanged/rejected 与自然键冲突原因。
5. 对同一文件重复导入，第二次应主要计为 updated 或 unchanged，总行数不重复增长；checksum 相同且完全无变化时标记 unchanged。
6. 切换到按表导出，选择 12 表之一及可用筛选，先预览前 20 行，再下载 CSV/XLSX/manifest。导出仅读当前库，不触发任何模块运行。
7. 数据集版本列表从 `GET /api/datasets` 刷新；可查看成员或直接导出某个 dataset_id。列表为空时提示「暂无已导入数据集，可从上方上传 commits.csv」。
8. 导入成功后提供 [查看风险列表] / [查看趋势] 等只读导航；若导入的是模型工件，则提示模型选项已更新，不自动加载或预测。

## 空态与错误

- 上传区空态提示支持的契约文件；工具产物清单为空不影响拖拽上传。数据集版本为空、按表导出无行和筛选无结果分别显示对应原因。
- 文件缺列、错类型、公式注入、超大小、扩展名与魔数不符、manifest checksum 不符、目标表歧义或无法映射返回 40001，不产半成品。
- 外键对象缺失、自然键冲突不可安全合并或版本不兼容时逐行给原因；多表事务失败整体回滚，不把部分成功显示为成功。
- 40100 禁用导入与导出；40400 表示数据集、产物或导出对象不存在；50000 显示内部错误与可重试入口，不回显 SQL、堆栈或敏感路径。
- 未打标 `is_bug_inducing` 在预览和导出中保持空值；缺预测行留空，不得填 0。导出失败不得留下伪装成完整文件的半截下载。

## 验收

- 在空库仅上传合法 commits.csv + manifest，即可自动识别目标表并完成事务导入；重复导入不产生重复 commit 或成员。
- predictions.csv 按 (commit_hash, model_name) 幂等 upsert，逐表 inserted/updated/unchanged/rejected 反馈准确；模型 zip 先验 checksum 再登记。
- 非法文件、目标歧义、checksum 错误和敏感键输入均被 40001 拒绝；多表写入失败整体回滚。
- 12 表均在导出白名单内，CSV/XLSX/manifest 可下载；CSV 带 BOM、XLSX 单 sheet、manifest 行数与 checksum 正确。
- 导出筛选与预览一致，未打标与缺预测保持空值；导出过程不触发模块业务计算。
- 数据集版本列表字段完整，查看成员与按 dataset_id 导出可用；列表为空时有明确上传引导。
- 导入与导出使用同步请求状态，不新增 job kind；导入后展示页可读取结果，不导入时原模块文件交付不受影响。
