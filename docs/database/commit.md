# commit（复用表）

**一句话**：提交对象表，一行对应一次 Git 提交，是全库的「锚点」——其余所有表都通过 `commit_hash` 挂到它上面。

## 字段

| 字段 | 类型 | 键 | 含义 |
|---|---|---|---|
| commit_hash | CHAR(40) | 主键 | 提交 SHA-1，全局唯一，全库关联用的业务键 |
| repo_name | VARCHAR(64) | — | 来源仓库名（如 `apache/camel`） |
| author_name | VARCHAR(128) | — | 提交者姓名 |
| author_email | VARCHAR(128) | — | 提交者邮箱（可空） |
| committed_at | DATETIME | 索引 | 提交时间；也是「时间序 70/30 切分」与趋势分桶的依据列 |
| message | TEXT | — | 提交说明全文 |
| parent_hash | CHAR(40) | — | 父提交哈希（可空，用于回溯 diff） |

## 主键为什么直接用 `commit_hash`（不用代理 id）
- `commit_hash` 是 40 位 SHA-1：**内容寻址、全局唯一、不可变**，本身就是完美的自然主键；加自增 `id` 只会多一个没人引用的死键（子表外键都指 `commit_hash`）。
- 与 `model` 表同口径：`model_name` 同样是交付契约锁定的自然主键，两表都不造自增 id。
- 当前代码仍残留 `Commit.id`，迁移时删除；文档口径以本表为准。

## 约束与索引
- `commit_hash` 主键唯一。
- `committed_at` 单列索引：时间区间筛选、趋势分桶都按它取数。

## 被谁所用
| 方向 | 谁 | 用途 |
|---|---|---|
| 写入 | 后端 `sync` / `predict` 服务 | 拉取或现算提交时 upsert |
| 读取 | 后端 `commits` / `trends` 服务 | 列表、详情、趋势聚合都 join 它取 `author_name` / `message` / `committed_at` |
| 展示 | 前端风险列表、提交详情、趋势看板、模型性能看板 | 提交的「谁 / 什么时候 / 说了什么」都来自这张表 |

## 口径
- 一张表只存「提交本身」，不含特征、分数、标签——那些各归各表，靠 `commit_hash` 1:N 关联。
- `committed_at` 是全局时间权威：任何「按时间切分 / 筛选 / 分桶」都必须用它，不得用别的表冗余时间。
- `repo_name` / `author_email` / `parent_hash` 是同步时写入的提交元数据，当前接口不返回、查询不读取；保留用于追溯与后续 diff 定位。
