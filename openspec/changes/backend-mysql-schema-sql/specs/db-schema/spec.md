## ADDED Requirements

### Requirement: MySQL SQL 建表入口与元数据等价

仓库 SHALL 提供 `infra/schema.sql`，在已创建且具备权限的目标 MySQL 8 数据库中建立 `commit`、`commit_label`、`commit_feature`、`prediction` 四张表。DDL SHALL 源于 `backend/app/models.py` 的 `Base.metadata`，保留 MySQL dialect 的列类型、可空性、自增、主键、唯一约束与普通索引，并满足 `INDEX_ASSERTIONS`。四表 SHALL 使用 `CREATE TABLE IF NOT EXISTS`，索引 SHALL 内联于建表语句，使同一正确 schema 可重复执行。SQL MUST NOT 包含 CREATE DATABASE、权限变更、DROP、ALTER 或 INSERT；数据灌入仍由 `app.ingest` 执行。

#### Scenario: 在空数据库执行 SQL 建表

- **WHEN** 在已创建的空 MySQL 8 数据库执行 `infra/schema.sql`
- **THEN** 四张表存在，字段与元数据一致，`app.db._assert_indexes` 对同一数据库检查通过

#### Scenario: 对正确 schema 重复执行

- **WHEN** 对已由本 SQL 创建的数据库再次执行同一文件
- **THEN** 不因重复建表或索引失败，已有业务数据与索引保持不变

#### Scenario: SQL 与 Python 建表路径一致

- **WHEN** 两个隔离的空 MySQL 8 数据库分别执行 SQL 和 `python -m app.db init`
- **THEN** 四表的列定义、主键、唯一约束和普通索引等价，两库均通过索引自检

#### Scenario: 唯一键拒绝重复业务行

- **WHEN** 在 SQL 建立的表中重复插入相同 commit_hash、相同标签复合键、相同特征主键或相同预测复合键
- **THEN** MySQL 按对应主键或唯一约束拒绝产生重复行，与 ORM 建表路径一致

#### Scenario: 已有错误 schema 不被掩盖

- **WHEN** 目标库已存在缺少必需索引的同名表，执行 SQL 后再运行 `app.db._assert_indexes`
- **THEN** SQL 不以隐式 ALTER 修改已有表，索引自检仍明确失败，MUST NOT 把 IF NOT EXISTS 成功视为结构已迁移

#### Scenario: 交付文件不夹带数据或权限操作

- **WHEN** 用户按 README 的 mysql 客户端命令执行 SQL
- **THEN** 文件只尝试建立目标库内缺失的四表与内联约束，业务数据需另走 ingest，权限或连接错误不会通过自动提权或改库绕过
