# 接口 datasets

数据集属于具体用户；所有端点只处理当前用户的数据集，非本人资源按不存在返回。

## 1 GET /api/datasets

列出当前用户的数据集。

| 参数 | 说明 |
|---|---|
| `scope` | 固定 `mine` |
| `q` | 名称关键字，可选 |
| `page` / `page_size` | 分页 |

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      { "dataset_id": "ds_...", "name": "repo-main-expert", "line": "expert", "source_type": "git_repo",
        "parent_dataset_id": null, "sample_count": 1180, "pos_count": 170, "neg_count": 1010,
        "status": "ready", "created_at": "2026-11-27T10:00:00+08:00" }
    ],
    "total": 1, "page": 1, "page_size": 20
  }
}
```

- 创建接口接受的 `source_type`：`git_repo` / `upload` / `clean`；响应中还会出现 `split` / `prediction`，分别由训练与预测保存接口写入。
- `source_type=prediction` 的数据集，`pos_count` / `neg_count` 表示预测为正 / 负的数量，不是真实标签数量。
- 列表按 `created_at` 倒序，同时间按 `dataset_id` 升序。

## 2 GET /api/datasets/{dataset_id}

详情与成员。

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "dataset_id": "ds_...",
    "name": "repo-main-expert",
    "line": "expert",
    "source_type": "clean",
    "parent_dataset_id": "ds_parent",
    "repo_url": "https://github.com/owner/repo",
    "branch": "main",
    "head_hash": "…",
    "sample_count": 1180,
    "pos_count": 170,
    "neg_count": 1010,
    "status": "ready",
    "created_at": "2026-11-27T10:00:00+08:00",
    "job_id": "job_...",
    "columns": [],
    "members": { "items": [], "total": 1180, "page": 1, "page_size": 20 }
  }
}
```

- `members` 通过 `page` / `page_size` 查询参数分页；非 prediction 按 `row_no` 升序，prediction 按 `commit_hash` 升序。
- `source_type` 不是 `prediction` 时，成员来自 `dataset_commit`，列由 manifest 决定；每个 `items` 元素是「列名 → 值」对象，键集合与 `columns` 一致；语义线同样返回 768 维，前端只展示元数据列。
- `source_type=prediction` 时，成员改读 `prediction` 表，固定为七列：`commit_hash`、`commit_message`、`author_name`、`commit_time`、`bug`、`risk_score`、`predicted_label`；`columns` 返回这七个字段名。导出表仍使用外部契约列名 `commit_id`（Git 哈希）。
- `job_id` 为该数据集的来源任务，可用于跳转预测详情。

## 3 POST /api/datasets

把任务结果保存为个人数据集。

```json
{ "job_id": "job_...", "name": "my-dataset" }
```

- `job_id` 必须是当前用户的收集或清洗任务，且已成功结束。
- 名称必填，长度 1–128，允许中文、字母、数字、`-`、`_`；数据集名称不要求全局唯一，允许重名。
- 同一 `job_id` 重复保存返回已存在的数据集（幂等），不重复创建。
- 新任务再次保存时按 `(owner_user_id, dedupe_key)` 覆盖：`git_repo` 用 `collect|repo_name 小写|branch|line`，`clean` 用 `clean|parent_dataset_id|ops_hash`，`upload` 用 `upload|file_sha256|ops_hash`；命中则更新原数据集（`dataset_id` 与 `created_at` 不变），否则新建。
- 覆盖键取规范化来源串的 SHA-256（64 位小写十六进制）；`ops_hash` 为操作按名称排序并补齐默认参数后的规范 JSON（键名升序、无空格）哈希，默认参数见 [../功能点/03-数据清洗.md](../功能点/03-数据清洗.md) 第 4.1 节。保存时从任务参数读取来源键元素：collect 需 `repo_name` / `branch` / `line`，clean 需 `parent_dataset_id` 或 `file_sha256`，以及 `ops_hash`。
- `split` / `prediction` 没有覆盖键，每次保存独立成条。
- 保存要求结果内 `commit_hash` 唯一；存在重复行时拒绝，提示先按提交哈希去重。仅执行任务不写库。
- `source_type` 由任务来源推导，不接受前端传入：
  - `kind=collect` → `git_repo`；
  - `kind=clean` 且来源为上传文件 → `upload`，`parent_dataset_id` 为空；
  - `kind=clean` 且来源为已保存数据集 → `clean`，`parent_dataset_id` 指向来源数据集。
- `split` / `prediction` 只由训练与预测的保存接口写入，本接口不产生。

错误：

| code | 场景 |
|---|---|
| 40001 | 名称为空或非法、任务未结束 |
| 40401 | 任务不存在或不属于当前用户 |
| 40901 | 任务结果正样本为 0，不可保存为可训练数据集；结果存在重复 `commit_hash` 或多个 `project` |

## 4 DELETE /api/datasets/{dataset_id}

删除数据集记录、成员关系与本数据集的产物目录。

- 所有来源：删除 `temp/datasets/<dataset_id>/` 目录。
- `source_type=prediction`：同事务删除 `prediction` 行。
- 删除后派生数据集的 `parent_dataset_id` 置空，模型的数据集引用置空；不删除其他资产。
- 不删除共享仓库缓存、全局共享表 `commit` / `commit_feature`、已保存模型与评估历史。
- 成功返回 `{ "code": 0, "message": "ok", "data": null }`。
