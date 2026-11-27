# 功能点 2 缺陷数据收集

一句话：从 Git 仓库枚举并选择一个分支采集提交、执行 SZZ 打标，或从公开数据集 URL 拉取已打标数据，统一交付一份核心「已标注数据集」，并自动保存为可复用数据集。

collected_commits 列契约、manifest 契约；API 见 [`../api/collect.md`](../api/collect.md)；页面见 [`../web_page/collect.md`](../web_page/collect.md)。

## 1 职责

- 校验 Git 仓库 URL，并枚举远端分支供页面选择；分支不可手填、不可留空。
- 按已选分支和提交时间范围采集提交元信息；时间范围按 `committed_at` 过滤。
- 执行 SZZ（`szz_v1` / `szz_lite`）得到 `is_bug_inducing` 与修复提交关联，处理打标边界。
- 处理增量采集、去重、跳过合并提交、超出窗口的提交。
- 交付一份核心已打标二维表，并把 summary / audit / quality / manifest 作为内部记录保留。
- 从公开数据集 URL 拉取 CSV/XLSX，按字段映射与标签映射归一化为 `collected_commits`，记录许可证与来源。
- 把核心二维表登记为数据集，支持页面预览与下载。

## 2 不负责

- 不做清洗、特征工程、切分、训练、预测、评估、解释、定位。
- 不写 `commit` / `commit_feature` 等业务表；入库走 storage 的导入端点。
- 不要求上游已有数据，也不作为其他模块运行的前置条件。
- 不向用户展示 summary / audit / quality / manifest；它们是内部记录，不是业务结果文件。

## 3 输入

Web 页面使用 Git 仓库与公开数据集两种入口；API / CLI 保留提交清单与 `dataset_id` 兼容入口。

| 入口 | 说明 |
|---|---|
| Git 仓库 | `repo_source` 为本地绝对路径或 `https`/`git` URL；`branch` 必须来自 `GET /api/collect/branches` 返回的列表 |
| 公开数据集 | `source_url` 仅 `https`；`license`、`field_mapping`、`label_mapping` 必填，按同一 `collected_commits` 契约归一化 |
| 提交清单 | 上传 CSV，仅含 `commit_hash` 一列，每行 40 位十六进制；页面不暴露 |
| 已登记数据集 | `dataset_id`，取其成员提交；页面不暴露 |

关键配置：`source_type`、`dataset_name`、`repo_source`、`branch`、`source_url`、`license`、`field_mapping`、`label_mapping`、`start_time/end_time`、`mode(full|incremental)`、`fetch_remote`、`dedup(commit_hash)`、`szz_method`。

- `dataset_name` 同时作为数据集名称与下载文件基础名；用户不填扩展名。
- `branch` 页面必填且必须存在于刷新后的远端分支列表，默认选中第一项。
- `start_time/end_time` 按提交 `committed_at` 过滤，留空表示全量，结束日期包含当天。
- 训练 / 测试划分不在收集阶段完成，`collected_commits` 不得包含 `is_test` 或切分标记列。
- `format` 不属于运行配置；收集任务只落 CSV，XLSX 在下载时生成。

## 4 流程

1. 用户在页面输入仓库 URL 并刷新分支；后端校验 URL 与权限并返回远端分支列表。
2. 用户从列表选择分支；系统默认选中第一项，并在 URL 改变时清空分支、结果区与结果文件。
3. 用户配置提交时间范围、数据集 / 导出文件名称，并核对配置预览。
4. 用户点击 [开始收集并导出数据集]；任务按“校验仓库与分支 → 拉取提交 → 缺陷标注 → 生成数据集 → 完成导出”推进。
5. 校验配置与输入清单，规范化仓库路径/URL 与时间区间。
6. 定位仓库与 HEAD，校验 `head_expect`，按需 `git fetch`。
7. 按所选分支与范围读取提交，过滤合并提交与重复提交。
8. 对窗口内提交执行 SZZ，生成标签与修复提交关联；窗口外提交保持未标注。
9. 只发布核心 `collected_commits_<job_id>.csv`；summary / audit / quality / manifest 写入内部引用。
10. 成功后自动把核心二维表登记为数据集，供页面预览和 `/storage` 产物库管理。

## 5 输出

用户可见核心产物只有一份：

```text
collected_commits_<job_id>.csv     # collected_commits 列契约 14 列，UTF-8 BOM
```

内部记录（不属于页面结果文件）：

```text
<stem>.manifest.json
collect_summary_<job_id>.json
collect_audit_<job_id>.json
collect_quality_<job_id>.json / .md
collect_repository_snapshot_<job_id>.json  # 有快照时
```

下载：

- `format=csv`：直接返回规范 CSV；
- `format=xlsx`：下载时从同一 CSV 即时生成单 sheet XLSX，不落盘、不登记为新产物。

`summary`：`rows, labeled_rows, positive_rows, negative_rows, unlabeled_rows, head_hash`。

`quality.checks`：缺失率、重复行、跳过行、字段映射、处理说明（不可用检查项为 null 并注明原因）。

## 6 约束

- 分支只能来自远端列表；刷新失败只能重试，不允许手填分支或使用空分支。
- 未打标 `is_bug_inducing=null`，不得当负样本。
- `label_source ∈ {git_szz, public_dataset}`；Git 模式产 `git_szz`，公开数据集模式产 `public_dataset` 且不跑 SZZ。公开数据集只能由 collect 任务创建，storage 不创建 `public_dataset`。
- 结果文件区只展示「已标注数据集」一个逻辑文件；不展示 manifest / summary / audit / quality。
- Excel 格式在下载时生成，避免 CSV / XLSX 双份冗余。
- 网络受限时可以用本地仓库路径完成验收。

## 7 验收

- 分支列表来自仓库 URL 刷新结果；默认选第一项；手填与留空被禁止。
- 刷新失败时分支下拉禁用，只提供重试刷新。
- Git 仓库、公开数据集 URL、上传清单、`dataset_id` 四种入口均可独立运行并下载核心产物；公开数据集产物与 Git 模式同契约。
- 核心产物列严格符合 collected_commits 列契约，CSV UTF-8 BOM；XLSX 下载时生成、单 sheet。
- SZZ 标签不越出采集窗口；未打标保持 null。
- 结果文件区只有一个逻辑文件；内部记录不展示。
- 同一输入与参数重复运行，计数一致（job_id/耗时除外）。
- 非法清单、非法范围、非法 `repo_source`、未知分支均被拒绝并给出可读错误。

## 8 边界

collect 只负责「把提交与标签变成文件」。与清洗、训练之间不共享数据库状态，只通过 `collected_commits` + manifest 交接；数据集登记是可选展示路径。

