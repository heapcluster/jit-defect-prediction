# 接口 page-state

页面进度按用户与服务端持久化，刷新、重新登录、换设备后恢复。

## 1 页面取值

`page` 只能取：`collect`、`clean`、`train`、`predict`、`evaluate`、`storage`。

## 2 GET /api/page-state/{page}

读取当前用户该页面的进度。

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "page": "collect",
    "state": {
      "step": 3,
      "form": { "repo_url": "https://github.com/owner/repo", "branch": "main", "mode": "expert" },
      "job_id": "job_...",
      "result_ref": { "job_id": "job_...", "kind": "collect" }
    },
    "updated_at": "2026-11-27T10:10:00+08:00"
  }
}
```

- 无记录时返回 `data: null`，不返回空对象冒充。
- 记录不属于当前用户时按不存在处理。

### 2.1 各页面的 state 结构

至少包含以下字段，允许附加展示用字段：

| page | state |
|---|---|
| `collect` | `step`、`form{repo_url,branch,mode}`、`job_id`、`result_ref{job_id,kind}` |
| `clean` | `step`、`source{kind,id}`、`operations[]`、`job_id`、`result_ref` |
| `train` | `step`、`source{kind,id}`、`algorithms[]`、`split{mode,ratios}`、`job_id`、`result_ref` |
| `predict` | `step`、`source{kind,id}`、`model{kind,model_name,model_ref,label,line}`、`threshold`、`job_id`、`result_ref` |
| `evaluate` | `step`、`source{kind,id,label}`、`metrics[]`、`threshold`、`job_id`、`result_ref` |
| `storage` | `section` |

- `source` 与对应启动接口同构：`kind=dataset` 时 `id=dataset_id`，`kind=file` 时 `id=file_id`。
- `operations[]` / `algorithms[]` 的元素结构与对应启动接口的请求体一致。
- `file_id` 为本次上传的临时文件标识，用于重置时定位 `temp/uploads` 目录。
- `result_ref` 只存任务与结果引用，不存结果行。

## 3 PUT /api/page-state/{page}

整份替换当前用户的页面进度。

请求：

```json
{ "step": 3, "form": { "...": "..." }, "job_id": "job_...", "result_ref": { "job_id": "job_...", "kind": "collect" } }
```

- 服务端整体覆盖，不做字段合并。
- `state` 序列化后上限 64KB，超限返回 `40001`。
- 只允许存引用，不允许把结果行数据写入进度。

响应：`200`，返回写入后的 `updated_at`。

## 4 DELETE /api/page-state/{page}

清空当前用户该页面进度，并删除其引用的未入库产物。

- 同时删除该页面上传的临时目录与任务产物：按 `import.json.page` 匹配 `temp/uploads/<user_id>/` 下的目录，并删除该页面引用的 `temp/outputs/<user_id>/<job_id>/`。
- 已保存的数据集、模型与评估历史不受影响。
- 响应：`{ "code": 0, "message": "ok", "data": null }`。

## 5 约束

- 页面进度与用户配置分开存储，不写入 `user_config`。
- 写入失败不阻断主流程，但前端需提示“进度未同步”。
- 旧版本页面进度不迁移：读取时以当前默认结构为底合并，缺失字段回落到默认值，多余旧字段不参与页面逻辑；点击「重置」后整条删除并清理未入库产物。
