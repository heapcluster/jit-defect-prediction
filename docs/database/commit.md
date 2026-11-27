# commit

**一句话**：提交对象表，一行对应一次 Git 提交，是全库的锚点——其余所有表都通过 `commit_hash` 挂到它上面。

实现锚点：backend/app/models.py:49-58

## 字段（逐字对齐 infra/schema.sql）

| 字段 | 类型 | 空值/默认 | 键/索引 | 含义 |
|---|---|---|---|---|
| commit_hash | CHAR(40) | NOT NULL | 主键 | 提交 SHA-1，内容寻址、全局唯一、不可变 |
| repo_name | VARCHAR(64) | NOT NULL | — | 来源仓库名（如 `camel`） |
| author_name | VARCHAR(128) | NOT NULL | — | 提交作者姓名（不是系统用户，见 [user.md](user.md)） |
| author_email | VARCHAR(128) | 可空 | — | 提交作者邮箱 |
| committed_at | DATETIME | NOT NULL | ix_commit_committed_at | 提交时间（UTC），全局时间权威 |
| message | TEXT | NOT NULL | — | 提交说明全文 |
| parent_hash | CHAR(40) | 可空 | — | 父提交哈希，用于回溯 diff |

## 主键与约束理由

- `commit_hash` 是 40 位 SHA-1，本身就是完美的自然主键；子表外键全部指向它，不造无人引用的代理 id。
- `committed_at` 单列索引：时间区间筛选、时间分桶、时间序切分都按它取数。
- 合并提交不入表（采集脚本 `01_extract_commits.py` 过滤）。

## 被谁所用

| 方向 | 谁 | 用途 |
|---|---|---|
| 写入 | 收集服务（`job.kind=collect`）、预测服务现算提交 | 按 `commit_hash` 幂等 upsert |
| 读取 | commits / predict 服务、`dataset_commit` 关联、导出服务 | 列表、详情、数据集成员 |
| 展示 | 提交详情 | 提交的「谁 / 什么时候 / 说了什么」 |

## 口径

- 一张表只存提交本身；特征、分数、标签各归各表，靠 `commit_hash` 关联。
- `committed_at` 是全局时间权威：任何按时间切分 / 筛选 / 分桶 MUST 用它，不得用其他表的冗余时间。
- 时间字段一律 UTC。
- `repo_name` / `author_email` / `parent_hash` 用于追溯与 diff 定位。
- 采集窗口参数只限制输出提交，不得截断历史类特征所需的前序提交。

## 验收

- 同一仓库同配置重复收集：行数不变、无重复提交。
- 时间筛选与时间分桶结果与 `committed_at` 一致。
- 合并提交不出现在表中。