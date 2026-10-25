-- 演示库 jit_demo 的一条命令建库脚本（Issue #142，后端线）。
-- 用法（cwd 必须是仓库根目录）：
--     mysql -u root -p < backend/scripts/schema_mysql.sql

-- 为什么是包装脚本而不是往 infra/schema.sql 里加建库头：
--   四表 DDL 的**单一来源**仍是 infra/schema.sql —— 它是 Base.metadata 经 SQLAlchemy
--   MySQL dialect 编译的快照，被 backend/tests/test_schema_sql.py 逐字比对（该测试断言
--   「恰好四条 CREATE TABLE」，并显式拒收 CREATE DATABASE / GRANT / DROP 等多余语句）。
--   把建库头塞进那份文件会同时弄红 25 条静态校验，并让 `USE` 改写所有调用方指定的目标库
--   （docs/backend/acceptance.md 的导入命令、Issue #121 的两个探针库都走同一份文件）。
--   所以：建库头单独放这里，DDL 不复制第二份。

-- 三条硬约束：
--   1. 只能用 mysql **客户端**执行。SOURCE 是客户端内建命令、按当前工作目录解析相对路径，
--      pymysql / SQLAlchemy 都不认它（ORM 路径请走 `cd backend && python -m app.db init`）。
--   2. 必须在**仓库根**执行，否则 SOURCE infra/schema.sql 找不到文件（报 Failed to open file）。
--   3. 需要 CREATE DATABASE 权限。只被授予某个库 ALL PRIVILEGES 的普通账号（例如本项目的
--      jit@127.0.0.1）会报 ERROR 1044 (42000): Access denied ... to database 'jit_demo'，
--      这时用 root，或先让 DBA 执行：
--          GRANT ALL PRIVILEGES ON jit_demo.* TO 'jit'@'127.0.0.1'; FLUSH PRIVILEGES;

-- 幂等：CREATE DATABASE / CREATE TABLE 全部带 IF NOT EXISTS，重跑不报错、不清数据。
-- 字符集显式写死 utf8mb4 + utf8mb4_unicode_ci（#142 裁定），**不跟随服务端默认值** ——
-- 各人本机 @@collation_server 可能不同（本项目实测有 8.0.45 默认 utf8mb4_0900_ai_ci 的），
-- 显式指定才不会让六台机器建出排序规则不一致的库。

CREATE DATABASE IF NOT EXISTS jit_demo CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE jit_demo;

SOURCE infra/schema.sql;

-- 自检：跑完应列出 4 张表（commit / commit_feature / commit_label / prediction）。
-- 少于 4 张说明 SOURCE 没找到 infra/schema.sql（多半是 cwd 不在仓库根）。
SELECT TABLE_NAME AS built_table, TABLE_COLLATION
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'jit_demo'
ORDER BY TABLE_NAME;
