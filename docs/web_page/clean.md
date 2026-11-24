# 数据清洗工具台（Clean）

实现状态：目标契约　期次：一期

> 旧页面口径包含 `commits.csv`、`szz_label`、`d5_exclude`、`time_split`、`feature_build`、Kamei 14 维模型特征；本文已废止。本轮只修改设计文档。

## 一句话

独立清洗工具台：上传板块 2 的 `collected_commits.csv/xlsx`，选择常用清洗操作和通用预处理操作，运行 preview/apply，逐步展示数据集变化和指定列/基础特征变化，apply 后导出清洗后数据集 CSV/XLSX。

## 入口与导航

- 顶级 tab：③清洗，路由 `/clean`。
- 页内子视图：

```text
[清洗工具台] [处理记录]
```

- 输出文件契约：[`../file-contracts.md`](../file-contracts.md) §3.2、§3.9。
- 操作元数据来自 `GET /api/clean/operations`，前端不写死操作清单。
- 模型特征选择、Kamei 14 维、训练侧标准化与切分均不在本页，统一放在训练页。

## 线框图

```text
┌─ 清洗工具台 ────────────────────────────────────────────────────────────┐
│ [清洗工具台] [处理记录]                                                  │
│ ── 输入区 ──                                                            │
│ 上传 collected_commits.csv/xlsx [拖拽]                                  │
│ 或从产物库选择 collect 输出 [▾]                                         │
│ 可选同名 manifest [拖拽]                                                │
│ ── 处理链配置 ──                                                        │
│ 清洗操作：                                                              │
│  ☑ schema_validate（固定首步）                                          │
│  ☑ duplicate_drop [参数▾]                                               │
│  ☑ merge_commit_filter [参数▾]                                          │
│  ☐ missing_value_handle [策略▾]                                         │
│  ☐ invalid_time_filter                                                  │
│  ☐ unlabeled_handle [策略▾]                                             │
│  ☐ outlier_filter [方法▾]                                               │
│  ☑ label_validate                                                       │
│  ☐ text_clean                                                           │
│ 通用预处理：                                                            │
│  ☐ type_convert [列选择▾]                                               │
│  ☑ date_normalize                                                       │
│  ☐ text_normalize                                                       │
│  ☐ category_normalize [列选择▾]                                         │
│  ☐ derive_basic_fields [基础列▾]（非模型特征）                          │
│ 支持 ↕ 拖拽排序、启停、参数展开。                                       │
│ 指定列/基础特征用于变化图 [可多选，可为空]                              │
│ 模式 (●preview ○apply) 输出格式 [CSV ▾ / XLSX]                          │
│ [运行]                                                                  │
│ ── job 进度 ──                                                          │
│ 状态[运行中] [████░░] 当前步骤 duplicate_drop [日志][重试][取消]         │
│ ── 输出区 ──                                                            │
│ 步骤时间线：                                                            │
│  步骤1 duplicate_drop                                                   │
│    行数 1200 → 1185  正样本 180→176  缺失 12→12                        │
│    [数据集变化图] [指定列变化图]                                        │
│  步骤2 missing_value_handle                                             │
│    行数 1185 → 1185  缺失 12→0                                          │
│    [数据集变化图]                                                       │
│ 清洗后数据集预览（apply，前20行）                                       │
│ [导出 CSV] [导出 XLSX] [下载 manifest] [下载每步统计] [下载图表]         │
└─────────────────────────────────────────────────────────────────────────┘
```

图中数值均为占位示意。

## 控件与接口映射

| 控件 | 端点 | 说明 |
|---|---|---|
| 上传文件 | `POST /api/clean/run` | `files[]` 上传 collected_commits |
| 产物库选择 | `GET /api/jobs?kind=collect` + `/api/collect/outputs/{job_id}/{name}` | 下载后以 `files[]` 提交 |
| 操作列表 | `GET /api/clean/operations` | 返回分组操作、参数 schema、顺序约束 |
| 运行 | `POST /api/clean/run` | 返回 `job_id` |
| 进度/日志/重试/取消 | `GET /api/jobs/{id}`；`POST /api/jobs/{id}/retry\|cancel` | 五态 |
| 每步统计 | `GET /api/clean/outputs/{job_id}/clean_steps_stats_{job_id}.json` | 行数、标签、缺失、重复、排除样本 |
| 数据集变化图 | `GET /api/clean/outputs/{job_id}/{name}.png` | 鉴权 fetch 转 ObjectURL |
| 指定列变化图 | 同上 | 按步骤和列命名 |
| 清洗后数据集预览 | `GET /api/clean/preview/{job_id}` | 仅 apply 成功提供前 20 行 |
| 导出 CSV/XLSX | `GET /api/clean/outputs/{job_id}/{name}` | 下载 `clean_dataset_<job_id>.csv/xlsx` |
| 处理记录 | `GET /api/jobs?kind=clean` | 只读展示历史清洗任务 |

## 交互流程

1. 用户上传 `collected_commits.csv/xlsx`，或从 collect 产物库选择文件。
2. 前端调用 `GET /api/clean/operations` 渲染操作列表，按“清洗操作 / 通用预处理”分组展示。
3. 页面文案明确提示：模型特征、Kamei 14 维、训练测试切分请到训练页配置。
4. 用户拖拽排序、启停、填写参数；系统即时校验顺序约束。
5. 用户选择需要画图的列/基础特征；可以为空，为空时只展示数据集级变化。
6. 用户选择 preview/apply 和输出格式，点击运行。
7. 页面轮询任务状态，逐步高亮当前操作。
8. 完成后：
   - preview：展示每步统计、数据集变化图、可选指定列变化图。
   - apply：额外展示清洗后数据集前 20 行和导出按钮。
9. 用户导出 CSV 或 XLSX，下载 manifest、统计和图表。
10. 失败时展示脱敏错误、失败步骤和重试入口。

## 变化展示规则

### 数据集级变化

每一步必须展示：

```text
rows_before / rows_after
removed_rows / modified_rows
label_dist_before / label_dist_after
missing_before / missing_after
duplicate_before / duplicate_after
excluded_samples
```

图表：

- 行数变化柱状图。
- 标签分布堆叠柱状图。
- 缺失和重复变化折线图。

### 指定列/基础特征变化

用户指定列后，每一步展示：

```text
mean / median / std / min / max / quantiles / missing_count
```

图表：

- 数值列：前后直方图、箱线图、密度图。
- 类别列：前后频数柱状图。

若某一步之前列不存在，图表中明确标注“该步骤前无此列”，不伪造数值。

## 空态与错误

- 加载中：骨架屏。
- 空态：无上传文件、无历史处理记录时给出明确提示。
- 列为空：允许运行，但只展示数据集级变化，不显示列级图空壳。
- 非法输入：缺列、错类型、公式注入、超大小、标签值非法 → 40001。
- 顺序冲突：清洗步骤放在通用预处理后、基础派生出现在时间规范化前 → 40001。
- 模型特征配置请求：`feature_build` / `feature_set` / `split_ratio` / `is_test` → 40001，并提示到训练页配置。
- 运行期失败：显示失败步骤和脱敏原因，不保留半成品主表。

## 验收

- 空库、无 collect 在线服务时，上传文件可完成 preview/apply。
- 操作列表来自注册表，按“清洗 / 通用预处理”分组，支持启停、排序、参数配置。
- preview 不生成清洗后数据集；apply 生成并可导出 CSV/XLSX。
- 每一步都有数据集级统计和图表。
- 指定列后可看到处理前后分布变化图。
- 页面不出现 `feature_build`、Kamei 14 维模型特征、训练测试切分、SZZ 重打标相关文案。
- 输出 CSV 中文不乱码，XLSX 单 sheet。
- manifest 包含处理链、列 schema、派生列、输入输出 checksum。
- 处理记录可回看历史任务，但不作为运行前提。
