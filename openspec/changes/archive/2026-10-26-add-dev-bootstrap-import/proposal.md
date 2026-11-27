# 本地开发数据初始化（bootstrap）与「实时同步才是唯一入口」的边界

## Why

2026-10-25 裁定移除离线 CSV 灌库后，活规格 `db-schema` 写的是「MUST NOT 保留离线 CSV 灌库路径」。
但本地要**看到东西**（列表 3000 条、趋势、风险分），不可能让第一次 clone 的人等几十分钟去跑
`POST /api/sync`（还要先 clone 一份 Camel 历史索引）。仓库里已经有数据线产物
（`data_model/data/commits.csv` / `commit_features.csv` / `dataset_szz.csv`）与真实权重
（`data_model/pipelines/expert/models/*.pkl`），用它们一次性初始化开发库是最短路径。

两者不冲突的前提是**把边界写清楚**：

- 运行时数据入口：仍然只有 `POST /api/sync` 与 `POST /api/sync-prs`；
- 本地初始化：`infra/bootstrap_dev.py`，只在开发者手工执行，不被服务进程调用。

## What Changes

- `db-schema`：**修改**「实时同步入库」—— 在「MUST NOT 保留离线 CSV 灌库路径」后补上例外说明：
  该禁令针对**运行时入口**；仓库根的 `infra/bootstrap_dev.py` 属本地开发初始化，允许一次性导入
  既有数据线产物，且 MUST NOT 被服务进程调用。
- `db-schema`：**新增**「本地开发数据初始化」Requirement ——
  写清它读什么、写什么、幂等口径，以及「初始化完仍由实时同步接管增量」。
- 代码：`infra/bootstrap_dev.py`（新增）、`infra/setup_mysql.py`（账号口令同步：`CREATE USER IF NOT EXISTS`
  对已存在账号不改口令，本机实测踩过 `jit@127.0.0.1` 旧口令导致永远 1045）。

## Capabilities

### Modified Capabilities

- `db-schema`：数据入口口径不变（实时同步唯一），新增「开发初始化脚本」的例外边界。

## Impact

- 规格：`openspec/specs/db-schema/spec.md`（经本 change 归档后生效）。
- 代码：`infra/bootstrap_dev.py`（新增）、`infra/setup_mysql.py`（ALTER USER 同步口令 + 建 `jit@127.0.0.1`）。
- 文档：`README.md`（Quick Start）、`docs/backend/mysql-setup.md`（坑 13：账号已存在时口令不生效）、
  `docs/common/local-runbook.md`（一条命令灌演示数据）。
- 不碰：契约一/二/三的字段与接口格式；`app/` 下任何运行时逻辑。

## 不做什么

- 不把 `bootstrap_dev.py` 接进任何 API、启动钩子或 CI 必需步骤。
- 不做增量同步（那是 `POST /api/sync` 的职责），初始化只负责「库里先有点东西」。
- 不改 MySQL 为其它数据库（本地与服务端一律 MySQL）。
