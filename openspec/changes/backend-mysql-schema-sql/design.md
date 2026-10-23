## Context

基线为 main `eea910e`。`Base.metadata.create_all()` 已被 `app.db.init_db()` 使用；`INDEX_ASSERTIONS` 要求 commit_hash 唯一、committed_at 普通索引、prediction 的复合唯一键与 commit_hash 普通索引。本次用户明确授权后端在 `infra/schema.sql` 交付四表 SQL，但不在今天操作 MySQL 数据。

## Goals / Non-Goals

**Goals:** SQL 与 ORM 共用字段定义，空库建表与重复执行均可验收；将静态验证和真正 MySQL 执行证据明确分层。

**Non-Goals:** 不增改字段、字符排序规则、外键或性能索引，不修改 ingest 的单事务回滚约定，不创建数据库或授权账号，不改 CI。

## Decisions

- D1：使用 SQLAlchemy `CreateTable(..., if_not_exists=True)` 与 MySQL dialect 生成基础 DDL，不手工抄字段。主键/唯一约束由元数据生成，普通索引按元数据名称和列顺序编译后内联进 CREATE TABLE；以稳定顺序输出，测试逐条与元数据编译结果对照。
- D2：不使用独立 `CREATE INDEX`，MySQL 8 不支持可直接依赖的 `CREATE INDEX IF NOT EXISTS`，第二次执行会遇重复索引。内联索引随缺失表一同创建，已存在表直接跳过；不加存储过程或 information_schema 动态迁移脚手架。
- D3：同时检查 `INDEX_ASSERTIONS` 及 metadata 的全部约束/索引。前者只列运行时核心索引，不覆盖 `commit_label` 的唯一复合键及其普通索引，不能把“自检四条过了”当作完整等价性证明。
- D4：复用现有 pytest/SQLAlchemy，不为解析四张表增加 SQL parser 依赖。`backend/tests/test_schema_sql.py` 比对四条语句、类型/可空性、完整键列表，禁止数据/权限/破坏性语句；构造删除预测唯一约束的反例，证明校验确实拒收漂移。
- D5：SQL 只建表，README 显式给出仓库根下 `mysql -u<user> -p <database> < infra/schema.sql`，凭据交互输入。后续进入 backend 执行 `app.ingest`，不再另造 SQL upsert 路径。

## Risks / Trade-offs

- IF NOT EXISTS 无法修复现有表漂移 → 要求部署后执行现有索引自检；发现问题另走明确迁移，不自动 ALTER。
- DDL 是由元数据生成的快照 → 新增静态一致性测试，未来 models.py 变化须同步更新 SQL。
- Python/dialect 编译成功不等于 MySQL 执行成功 → 今天只报静态结果；空库/重跑/双路径实际对比保持未执行，2026-10-24 再取证。
- 用户提供的“已生成 DDL”未附具体文本 → 实施时从仓库 metadata 重新生成，避免使用未知版本；生成后复核列和全部索引。

## Migration Plan

提案通过后生成 SQL 与静态测试、补 README、独立 PR 审阅；MySQL 实跑使用已授权的隔离空库。此文件不是迁移工具；撤销 SQL 交付只回退仓库文件，不自动删表或数据。

## Open Questions

SQL 内容与生成策略已明确。MySQL 隔离库创建及凭据准备在后续执行前确认；本轮不需要这些权限。
