# feedback

人工标签反馈接口（模块 `feedback.py`）。

## 处理功能
- **方法 / 路径**：`PUT /api/commits/{commit_hash}/label`
- **用途**：写入 / 更新 / 撤销某提交的人工标签（落 `commit_label`，`label_method=manual`）。
- **权限**：沿用后端统一鉴权（通常为评审员）。
- **关键参数**：`commit_hash`（路径）、请求体（标签值）。

## 传输模型
### 请求体
| 字段 | 含义 |
|---|---|
| `is_bug_inducing` | 人工判定（0/1，撤销可置空） |
### 响应
| 字段 | 含义 |
|---|---|
| `commit_hash` | 提交标识 |
| `is_bug_inducing` | 写入的标签值 |
| `label_method` | 固定 `manual` |
| `labeled_at` | 打标时间 |

**说明**：本设计评估只用 `szz`；`manual` 标签供质量校准使用，不纳入测试集评估范围。
