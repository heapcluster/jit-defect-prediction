# figures

## 处理功能
- **用途**：获取某模型的性能图（ROC / PR / 混淆矩阵 / 校准曲线 / 特征重要性）
- **方式一（索引）**：`GET /api/figures?model_name=`，返回图清单
- **方式二（静态）**：`StaticFiles` 挂 `backend/static/figures/{line}/{model}/*.png`，前端直接取
- **权限**：沿用后端既有统一鉴权
- **关联数据**：`model_figure`（图元数据）、`model.line`（路径分组）

## 传输模型
### 请求
- `model_name`（必填）

### 方式一响应（200 OK）
| 字段 | 含义 |
|---|---|
| `model_name` | 模型名 |
| `figures[]` | 图数组 |
| `figures[].figure_type` | `roc` / `pr` / `confusion` / `calibration` / `feat_importance` |
| `figures[].title` | 图标题 |
| `figures[].file_path` | 图 URL（指向静态目录） |

### 方式一响应示例
```json
{
  "model_name": "lr_fused_v1",
  "figures": [
    {"figure_type": "roc", "title": "ROC", "file_path": "/static/figures/fused/lr_fused_v1/roc.png"},
    {"figure_type": "pr", "title": "PR", "file_path": "/static/figures/fused/lr_fused_v1/pr.png"}
  ]
}
```

### 方式二
直接返回图片二进制（`Content-Type: image/png`）。

### 错误响应
| 状态码 | 含义 |
|---|---|
| 400 | 缺少 `model_name` |
| 401 | 未鉴权 |
| 404 | 模型无图或图不存在 |
