## Why

现有 `python -m app.db init` 依赖 Python 环境；本次交付另要求通过 mysql 客户端直接建立四张表，而仓库尚无 `infra/schema.sql`。从同一份 SQLAlchemy 元数据生成 SQL，避免维护两套字段和索引定义。

## What Changes

- 新增 `infra/schema.sql`：使用 `backend/app/models.py` 的 `Base.metadata` 和 MySQL dialect 生成 `commit`、`commit_label`、`commit_feature`、`prediction` 四表 DDL。
- 四条建表语句均使用 `CREATE TABLE IF NOT EXISTS`；主键、唯一约束与普通索引全部内联于建表语句，避免单独 `CREATE INDEX` 在第二次执行时失败。
- 保留 metadata 中列类型、可空性、自增、键名及列顺序；静态测试比对完整 SQL 生成结果，并检查 `INDEX_ASSERTIONS` 的约束覆盖。
- 在 `backend/README.md` 补充 mysql 客户端执行入口，说明目标数据库须已创建、具备权限；SQL 仅建表，数据统一由 `app.ingest` 按既有幂等口径灌入。
- 不做：不创建数据库/用户、不改权限或现有数据、不加入种子 INSERT、不做已有表迁移、不改 ingest 事务策略、不修改 CI 或模型文件。本轮先规划；MySQL 空库执行、重复执行与索引自检证据留到后续实跑。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `db-schema`：新增独立 requirement，提供 MySQL SQL 建表入口并约束其与 Python 建表路径等价及重复执行行为。

## Impact

- 文件：`infra/schema.sql`、`backend/README.md`、`backend/tests/test_schema_sql.py`；`infra/schema.sql` 已获用户本次明确跨目录授权。
- 规格：`openspec/changes/backend-mysql-schema-sql/specs/db-schema/spec.md`，归档后并入现行 `db-schema`；不改冻结契约或 `docs/design/sprint0-scope.md` 的功能范围。
- 不新增依赖。SQL 文件与生成验证均使用现有 SQLAlchemy MySQL dialect，不把 MySQL DDL 交给 SQLite 假验收。
- 部署：仅在预先创建的目标数据库中创建缺失表；`IF NOT EXISTS` 不会修正已有错误表结构，该情况仍由 `app.db._assert_indexes` 报错并要求正式迁移。
