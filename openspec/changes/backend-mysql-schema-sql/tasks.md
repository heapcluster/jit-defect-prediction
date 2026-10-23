# backend-mysql-schema-sql — 任务清单

> 提案：`proposal.md` ｜ 设计决策：`design.md` ｜ 规格：`specs/db-schema/spec.md`
> 负责人：backend 吕建江 ｜ 创建：2026-10-23 ｜ 状态：进行中（5/8；SQL与静态验证完成，PR #100已创建，MySQL未执行）
> 用户故事：无（工程化）；SQL客户端四表初始化交付，infra/schema.sql由用户明确交给后端
> 统一格式见 `docs/common/openspec-task-template.md`；本文件末的「测试与验证」为强制板块。

## 1. SQL 与使用入口

- [x] 1.1 按 `Base.metadata` 的 MySQL dialect 生成四表 `CREATE TABLE IF NOT EXISTS`，主键、唯一约束与普通索引内联 — 交付物：`infra/schema.sql`；不得缺失 metadata 的标签表约束与普通索引。
- [x] 1.2 补已有目标库的 mysql 客户端执行步骤，明确 SQL 只建表、数据由 ingest 灌、IF NOT EXISTS不修错误schema — 交付物：`backend/README.md`；不含真实凭据。

## 2. 静态测试与独立 PR

- [x] 2.1 新增四表完整生成结果比对和主键/索引断言；拒收多余数据/权限/破坏性语句 — 交付物：`backend/tests/test_schema_sql.py`；cwd=backend执行该文件通过。
- [x] 2.2 删除预测唯一约束构造反例，验证漂移检查确实失败；运行后端回归及OpenSpec严格校验 — 交付物：测试输出追加本文件§5，不冒充MySQL执行证据。
- [x] 2.3 提交独立 PR，说明静态已测与MySQL未测的边界 — 交付物：PR #100（https://github.com/heapcluster/jit-defect-prediction/pull/100），实现提交 `76cff35`；已请求infra苏哲勋审阅，未合入，MySQL仍未执行。

## 3. MySQL 后续验收

- [ ] 3.1 2026-10-24 在已授权隔离空库执行SQL两次，保留两次退出码与表/索引输出 — 交付物：后端运行证据；不以SQLite代替。
- [ ] 3.2 另一个隔离空库运行 `app.db init`，逐项对比两库元数据并分别跑 `_assert_indexes` — 交付物：列、主键、唯一约束、普通索引的对照结果。
- [ ] 3.3 测试唯一键拒重、错误schema索引自检失败且业务数据不被重复执行修改 — 交付给 backend 吕建江；完成后补验收记录，再判断归档条件。

## 测试与验证（强制板块）

> 2026-10-23 已完成 SQL、README 与静态测试，以下仅记录真实离线结果。Python环境以 `data_model/environment.yml` 为准；MySQL目标库和授权在实际执行前确认，未来命令不能直接用于共享联调库。今天未连接MySQL；现有SQLite回归不作为MySQL DDL执行证据。

### 1. 单元测试

| 项 | 内容 |
|---|---|
| 覆盖对象 | schema.sql与Base.metadata MySQL编译输出及全部列、主键、唯一约束、普通索引 |
| 测试文件 | `backend/tests/test_schema_sql.py` |
| 用例数与结果 | 25 passed, 1 warning in 0.09s；6条正向、8条漂移负例、11条额外操作负例 |
| 复现命令 | cwd=backend：`python -m pytest tests/test_schema_sql.py`；python为§5记录的指定解释器 |
| 正向 | 四个IF NOT EXISTS完整建表语句与元数据一致；4个主键、3个唯一约束、3个普通索引内联；额外覆盖INDEX_ASSERTIONS之外的标签唯一键与普通索引 |
| 异常/边界 | 删除uq_prediction_hash_model被校验器以metadata drift: prediction拒收；删除标签唯一键/索引、改类型/可空性/自增/键列顺序/IF NOT EXISTS均拒收；额外数据/权限/破坏性语句及独立CREATE INDEX均拒收 |

### 2. 集成测试

| 项 | 内容 |
|---|---|
| 集成范围 | SQL建表与ORM建表在MySQL 8上的字段、键和自检等价性 |
| 测试文件 | 本轮无MySQL执行测试；后续命令与输出追加本文件§5 |
| 用例数与结果 | MySQL 0条执行；用户安排2026-10-24实跑。后端现有回归与新增静态测试合计125 passed, 15 warnings in 4.27s，不是MySQL验收 |
| 后端回归命令 | cwd=backend：`python -m pytest`；conftest将DATABASE_URL设为sqlite://，新增静态测试不创建engine |
| MySQL待执行命令 | cwd=仓库根：设置已授权隔离库的 MYSQL_USER/MYSQL_DATABASE 后 `mysql -u "$MYSQL_USER" -p "$MYSQL_DATABASE" < infra/schema.sql`；执行两次。cwd=backend且DATABASE_URL指向该库：`python -c "from app.db import get_engine, _assert_indexes; _assert_indexes(get_engine())"` |
| 待验证断言 | 两次执行成功且数据不变；与独立ORM库比较完整元数据；两库索引自检均通过 |

### 3. 验收测试

| 项 | 内容 |
|---|---|
| 验收依据 | `openspec/changes/backend-mysql-schema-sql/specs/db-schema/spec.md` 六个Scenario |
| 用例数与结果 | 静态门禁已通过；6个Scenario尚无MySQL实机验收证据，不标为端到端通过 |
| 复现命令 | cwd=backend：`python -m pytest tests/test_schema_sql.py tests/test_db.py` → 28 passed, 1 warning in 0.18s；cwd=仓库根：`openspec validate backend-mysql-schema-sql --strict` → valid；`openspec validate --all --strict` → 20 passed, 0 failed；MySQL待测按§2操作 |
| 证据归档 | 本文件§5记录基线、命令、执行时间与真实输出；2.3已由PR #100闭环，第3节MySQL验收仍全部未勾选 |

### 4. 非功能验证

| 维度 | 是否触及 | 证据与命令 |
|---|---|---|
| 性能 | 否 | 只导出现有表结构，不新增查询性能索引；未跑性能压测 |
| 安全 | 是 | 静态测试11条额外操作负例通过；仅四条建表语句，无凭据或新权限路径；未连接MySQL |
| 可靠 | 是 | 完整元数据比对与8条漂移负例通过；MySQL重复执行与唯一键拒重未执行，按§2后续补证 |
| 易用 | 是 | 人工核对README中的cwd、已有数据库、交互密码、SQL只建表、只读索引自检及app.ingest四类灌入命令；未实际执行其中数据库命令 |
| 维护 | 是 | 仓库根 `python -m ruff check backend/tests/test_schema_sql.py` → All checks passed!；无新增依赖、运行时抽象、CI或AGENTS变更 |

### 5. 已知缺口与后续计划

| 缺口 | 原因 | 归属 | 计划 |
|---|---|---|---|
| PR审阅与合入 | PR #100已创建，源码与文件清单已复核 | backend 吕建江 + infra 苏哲勋 | 等待PR自身CI及非作者审阅，不代表MySQL验收完成 |
| MySQL空库、重跑、双路径等价性、唯一键拒重与错误schema自检 | 静态生成不能证明真实引擎行为；本轮不动库 | backend 吕建江 | 2026-10-24，先确认隔离库授权；第3节全部保持未完成 |
| 已有错误表的迁移 | IF NOT EXISTS故意不覆盖已有表 | backend 吕建江 | 若自检失败另立迁移，不在本SQL自动修复 |
| 真实数据灌入 | 用户明确留后续，且与schema交付独立 | backend 吕建江 + model 蒋励 | 确认四份正确CSV与备份后执行 |

#### 2026-10-23 本轮离线执行证据

- 执行时段：2026-10-23 23:20–23:23（+08:00）。工作目录：`D:/TeamWork/jit-backend-schema`；测试cwd为其`backend`子目录。
- 分支：`chore/backend/mysql-schema-sql`；基线/HEAD：`eea910eba80e74608c2da34e88c390879c4e0b14`，未创建提交、push或PR。
- 所有Python命令使用 `C:/Users/simple/anaconda3/envs/jit-defect-prediction/python.exe`；实测版本Python 3.12.15、SQLAlchemy 2.0.54、pytest 9.1.1。
- SQL生成：cwd=backend，使用同一解释器通过runpy加载测试纯函数`_mysql_statements(Base.metadata)`，逐表调用MySQL dialect的`CreateTable(if_not_exists=True)`与`CreateIndex`编译，移除独立索引外壳后内联；输出存为`infra/schema.sql`，仅调整排版。无运行时导出模块、无新增依赖。

| cwd | 命令（python为上述绝对路径） | 真实输出摘要 | 退出码 |
|---|---|---|---|
| backend | `python -m pytest tests/test_schema_sql.py tests/test_db.py` | `28 passed, 1 warning in 0.18s` | 0 |
| backend | `python -m pytest tests/test_schema_sql.py` | `25 passed, 1 warning in 0.09s` | 0 |
| backend | `python -m pytest` | `125 passed, 15 warnings in 4.27s` | 0 |
| 仓库根 | `python -m ruff check backend/tests/test_schema_sql.py` | `All checks passed!` | 0 |
| 仓库根 | `openspec validate backend-mysql-schema-sql --strict` | `Change 'backend-mysql-schema-sql' is valid` | 0 |
| 仓库根 | `openspec validate --all --strict` | `Totals: 20 passed, 0 failed (20 items)` | 0 |

警告如实保留：target为FastAPI/Starlette TestClient使用httpx的弃用提示；全量另有matplotlib调用pyparsing的弃用提示，共15条。本次未通过新增依赖或修改配置消除它们。

设计偏离：无。上述离线测量时完成1.1/1.2/2.1/2.2，之后主助手独立复跑联合测试得28 passed（0.14s），复核代码并创建PR #100，现2.3也已完成。第3节MySQL操作仍待后续：未创建数据库、修改权限、建表或灌入数据；SQLite仅运行回归。旧`openspec/changes/env-single-source/evidence/env-create-verify-log.txt`原有换行dirty未处理，前后`git hash-object`均为`d2ef8bbb9c2fb42933c0249be97ade55d5dee8cc`。
