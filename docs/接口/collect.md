# 接口 collect

字段契约见 [../功能点/02-数据收集.md](../功能点/02-数据收集.md) 第 4 节。

## 1 GET /api/collect/branches

查询仓库分支。

| 参数 | 位置 | 说明 |
|---|---|---|
| `repo_url` | query | 必填，GitHub / Gitee 公开仓库地址 |

响应：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "platform": "github",
    "default_branch": "main",
    "branches": ["main", "dev"]
  }
}
```

错误：

| code | 场景 |
|---|---|
| 40001 | 地址为空、域名不支持、格式无法归一化 |
| 40401 | 仓库不存在或非公开 |
| 50301 | 平台接口不可用或触发限流 |

## 2 POST /api/collect/precheck

统计规模并给出预估，不启动任务。

请求：

```json
{ "repo_url": "https://github.com/owner/repo", "branch": "main", "mode": "expert" }
```

- `mode` 取 `expert` / `semantic`，默认 `expert`；预估耗时按所选模型线计算（单条 0.3 秒 / 1.0 秒）。
- 切换解析方式后需重新预检；前端在已选仓库与分支时自动重算。

响应：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "platform": "github",
    "commit_count": 1200,
    "issue_count": 86,
    "estimate_seconds": 540,
    "warn_level": "yellow"
  }
}
```

- `warn_level` 取 `none` / `yellow` / `red`，阈值取当前用户配置。
- `estimate_seconds` 为单一预估数值，不返回区间。
- `issue_count` 为 0 时仍返回，由前端提示无法打标。
- 错误：`40001` 地址非法或 `mode` 不在枚举内、`40401` 仓库不存在或非公开、`50301` 平台接口不可用或触发限流。

## 3 POST /api/collect/run

启动收集任务。

请求：

```json
{ "repo_url": "https://github.com/owner/repo", "branch": "main", "mode": "expert" }
```

- `mode` 取 `expert` / `semantic`。
- 只支持公开仓库，无需登录、不需要页面提供 Token；平台接口限流时返回 `50301`，提示稍后重试。

响应 `202`：

```json
{ "code": 0, "message": "ok", "data": { "job_id": "job_..." } }
```

错误：

| code | 场景 |
|---|---|
| 40001 | 参数非法、模式不在枚举内、分支为空 |
| 40901 | 分支无提交、仓库无缺陷 issue、全部缺陷 issue 均未关联到修复提交、SZZ 未标记出缺陷提交 |
| 42901 | 当前用户已有运行中任务 |
| 50301 | 平台接口不可用或触发限流 |

## 4 GET /api/collect/results/{job_id}/rows

分页预览结果，只返回核心字段。

| 参数 | 说明 |
|---|---|
| `page` / `page_size` | 分页，默认 1 / 20，最大 100 |

响应：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "summary": { "total": 1200, "pos": 180, "neg": 1020 },
    "columns": ["commit_id", "commit_time", "author_name", "bug", "ns", "nd", "nf", "entropy", "la", "ld"],
    "items": [],
    "total": 1200,
    "page": 1,
    "page_size": 20
  }
}
```

- 结果来自产物文件，不要求先入库；按结果行顺序返回。
- 非本人任务返回 `40401`。

## 5 GET /api/collect/results/{job_id}/export

导出完整二维表。

| 参数 | 说明 |
|---|---|
| `filename` | 必填，不含扩展名；非法字符返回 `40001` |
| `format` | `csv` / `excel` |

- 返回文件流，`Content-Disposition` 带文件名。
- CSV 为 UTF-8 BOM，逗号分隔；Excel 首行为表头。
- 列名与顺序严格按字段契约，不附加归属与追溯列。

## 6 状态与幂等

- 未重置时重新执行覆盖当前未保存结果；重置或开始新流程后再执行才产生新结果。再次保存时按 `collect|repo_name 小写|branch|line` 的 SHA-256 覆盖键定位已保存数据集，命中则更新，否则新建；仅重新执行不写库。
- 覆盖不检查下游引用；已训练模型与预测结果保留，模型权重不变。
- 保存数据集走 `POST /api/datasets`，`job_id` 幂等。
