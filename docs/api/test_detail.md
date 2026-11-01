# test-detail

## 处理功能
- **用途**：返回测试集逐条明细（commit 信息 + 14 维特征 + 真标签 + 选中模型判断）
- **方法 / 路径**：`GET /api/test-detail`
- **权限**：沿用后端既有统一鉴权
- **数据范围**：仅 `commit_feature.is_test = 1` 的检验集提交
- **关联数据**：`commit` / `commit_feature` / `prediction` / `commit_label`(szz 真标签)
- **参数（query）**：
  - `model_name`（必填）：如 `lr_v1` / `lr_fused_v1` / `codebert_e2e_v1`
  - `page` / `size`：分页，默认 `page=1`
  - `sort` / `order`：排序字段与方向（如 `risk_score` / `desc`）
  - `q`：关键字（commit_hash / author / message）
  - `is_defect`：按真标签筛选（可选，0/1）

## 传输模型
### 响应（200 OK）
| 字段 | 含义 |
|---|---|
| `total` / `page` / `size` | 分页信息 |
| `items[]` | 明细数组 |
| `items[].commit_hash` | 提交标识 |
| `items[].author` / `committed_at` / `message` | 提交信息 |
| `items[].features{ns..sexp}` | Kamei 14 维（e2e 行为空） |
| `items[].is_bug_inducing` | 真标签（szz，来自 commit_label） |
| `items[].risk_score` | 选中模型概率 `[0,1]` |
| `items[].predicted` | 二值判定（`risk_score >= 阈值`） |

### 响应示例
```json
{
  "total": 12345,
  "page": 1,
  "size": 1,
  "items": [
    {
      "commit_hash": "a1b2c3...",
      "author": "dev1",
      "committed_at": "2024-03-01T10:00:00",
      "message": "fix: null ptr",
      "features": {"ns":3,"nd":1,"nf":2,"entropy":0.5,"la":20,"ld":5,"lt":25,"fix":1,"ndev":4,"age":100,"nuc":2,"exp":30,"rexp":10,"sexp":3},
      "is_bug_inducing": 1,
      "risk_score": 0.83,
      "predicted": 1
    }
  ]
}
```

### 错误响应
| 状态码 | 含义 |
|---|---|
| 400 | 缺少 `model_name` 或参数非法 |
| 401 | 未鉴权 |
| 404 | `model_name` 不存在 |
