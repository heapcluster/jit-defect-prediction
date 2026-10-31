# commit（复用表）

提交对象表，一行对应一次 Git 提交，是全库所有表的主键关联源头（靠 `commit_hash` 串联 feature / prediction）。

| 字段 | 含义 |
|---|---|
| commit_hash | 提交 SHA-1，全局唯一，其他表均通过它关联 |
| author_name | 提交者姓名 |
| author_email | 提交者邮箱 |
| committed_at | 提交时间；也是"时间序 70/30 切分"的依据列 |
| message | 提交说明文本 |
| parent_hash | 父提交哈希，用于回溯 diff / 文本来源 |

**角色**：所有明细数据的锚点；测试集明细表从这里取"提交信息"。
