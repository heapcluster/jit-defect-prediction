# MySQL 演示库 jit_demo 安装与建库指南

> 版本 1.0 ｜ 更新 2026-10-30 ｜ 主笔 吕建江 ｜ 审核 苏哲勋
> 对应 Issue #142：演示库 `jit_demo` 的 MySQL 安装 / 一条命令建库 / `.env` 写法 / 验收清单 / 常见坑。本文件是权威，其它 README 不重复本文件内容，只挂入口。

演示库名固定 **`jit_demo`**（Issue #130 更正裁定、#142），与日常联调库、`jit_test` 测试库区分开。旧库名 `jit_defect` 是共享实例上的占位脏库，**一律不再使用**。

---

## §1 版本要求与驱动

- **MySQL `8.0`**（实测 8.0.45）。字符集要求见 §2。
- 后端用 **`pymysql`** 作 SQLAlchemy 驱动（`mysql+pymysql://...`）；不能用 SQLite，双库方案已废除。
- 连接账号需有目标库的 `CREATE DATABASE` + 建表权限（权限不足报错见 §2）。

---

## §2 一条命令建库（jit_demo）

仓库根目录跑下面这条，建出 `jit_demo` 库与四张表（`commit` / `commit_feature` / `commit_label` / `prediction`）：

```bash
mysql -u root -p < backend/scripts/schema_mysql.sql
```

`backend/scripts/schema_mysql.sql` 是**建库包装脚本**，只做三件事：建 `jit_demo`（`CREATE DATABASE IF NOT EXISTS jit_demo CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci`）、`USE jit_demo`、`SOURCE infra/schema.sql`。四表 DDL 的**单一来源仍是 `infra/schema.sql`**，包装脚本不复制第二份 DDL（复制会漂移，被 `backend/tests/test_schema_sql.py` 判红）。

字符集显式写死 **`utf8mb4`** + `utf8mb4_unicode_ci`（#142 裁定），不跟随服务端 `@@collation_server` 默认值（实测有机器默认 `utf8mb4_0900_ai_ci`，不写死会让多机建出排序规则不一致的库）。

### 常见报错

- **ERROR 1044 (42000): Access denied ... to database 'jit_demo'**：账号无 `CREATE DATABASE` 权限。普通账号只被授予某库 `ALL PRIVILEGES` 时会报 1044，先用 root 执行 `GRANT ALL PRIVILEGES ON jit_demo.* TO 'jit'@'127.0.0.1'; FLUSH PRIVILEGES;` 再跑包装脚本。
- **端口 `3306` 被占用 / 连接拒绝**：确认本机 MySQL 在 `3306` 监听，`DB_HOST` / `DB_PORT` 与实例一致；容器或 CI 场景端口映射要对上。
- **`Failed to open file`**：包装脚本的 `SOURCE infra/schema.sql` 按**仓库根**解析相对路径，必须在仓库根执行，否则找不到 `infra/schema.sql`。
- **时区**：建议连接设 `time_zone='+00:00'`（统一 UTC），`committed_at` 等时间字段与时间序切分都依赖它；时区不一致会让趋势分桶与 `committed_at` 过滤偏移。

---

## §3 `.env` 分字段写法（不塞进一行 URL）

按 `backend/.env.example` 把五项连接字段**分字段**填（账号与口令分开，不再拼成 `DATABASE_URL`）：

```bash
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=jit
DB_PASSWORD=<你的口令>
DB_NAME=jit_demo
```

- `DB_NAME` 必须就是 `jit_demo`（与建库脚本、验收口径三处一致）。测试库默认 `jit_test`，由 `pytest` 自动切换，不要和演示库混用。
- **`load_dotenv()` 的坑**：`config` 用 `load_dotenv()` 加载 `.env`，但若运行环境的环境变量里**已设 `DATABASE_URL` 前缀**，它会压过分字段配置（分字段只在未设 `DATABASE_URL` 时生效）。CI / 容器里若设了 `DATABASE_URL`，本地 `.env` 的分字段会被静默覆盖，排障时优先查环境变量。
- 现场预测开关：`SOURCE_REPO=<本地 Apache Camel 历史索引绝对路径>`（见 §5），未设时同步端点返回 40400。

---

## §4 特征口径警告（承重，删掉等于埋雷）

> 灌特征表**只能**用契约形态（`dataset_szz.csv` 的投影），**绝不能**灌 `commit_features_raw.csv`。

`commit_features_raw.csv` 是模型线（`fused`）的训练输入形态（每个提交一行，84,461 行），**未按契约二 v1.2 第四节做对数变换**；而后端 `commit_feature` 表存的是契约二要求的 `ln` 形态。两份文件不是超集关系，是**两套特征空间**：`ns/nd/nf/entropy/ndev/age/exp/rexp/sexp` 满足 `dataset == ln(raw)`（3000/3000），`fix` 满足 `dataset == raw`（3000/3000，契约明文 `fix` 不取对数），但 **`la/ld/lt/nuc` 无法由 raw 反推**（自行取 `ln` 也补不出来，四列命中率仅 132/471/1125/1122 每 3000）。

后果实测（同一提交 `77b260b6…`、同一 `xgb_v1`）：喂 raw → **0.82657**，喂 `dataset_szz.csv` 契约形态 → **0.79963**（与离线批量产物 `prediction_result.csv` 存量值逐位相同）。**灌 raw 会让 `POST /api/predict` 静默算错**——接口 200、模型不报错、页面照常显示，但分数错了。

判别 SQL（投影配方校验键，判据 1b 实测）：`MIN(la)=-12.9443795988`、`MIN(ld)=-12.1697872202`、`MAX(nf)=9.7939516655`、`SUM(la<0)=76444`、`COUNT(*)=83943`。特征表行数应为 **83,943**，且 `MIN(la)` 为负；若 `MIN(la)>=0` 说明灌进了 raw，立即重建 `commit_feature`。

---

## §5 建 Camel blobless 历史索引（取代离线 CSV 灌库）

实时同步端点需要从本地 Camel 仓库现算特征，先建只读历史索引（只存提交+树、不含 blob，几十 MB）：

```bash
python infra/clone_camel_history.py
```

该索引用 `--filter=blob:none` 克隆，供 `git log --numstat` / `git cat-file` 算 14 项特征，**不持有业务状态、不入库**。离线 CSV 灌库（`app.ingest`）已于 2026-10-25 移除，数据只走实时同步端点（`POST /api/sync` / `POST /api/sync-prs`）。

---

## §6 一条命令自检

建库、灌数、四接口与三模型加载用一个脚本跑完、任一步不符即退出码 1：

```bash
python -m scripts.demo_preflight
```

验收要求三模型全加载（`lr_v1` / `rf_v1` / `xgb_v1`），`/api/health` 返回 `models_loaded>=3`、`model_names` 含这三项的名称。

---

## §7 验收清单三个数

| 项目 | 数值 |
|---|---|
| 非合并提交总数 `commit` | **84,461** |
| `commit_label` / `commit_feature` / `prediction` 行数 | **83,943** |
| `risk_score >= 0.5` 行数（17.39%） | **14,596** |

列表 `GET /api/commits` 的 `total` 由 `prediction` 与 `commit` 内连接决定，两边都是 83,943，故演示口径一致。

---

## §8 步骤口径指针

完整本地跑通步骤（含前端联调、同步用法、CI 描述）见 `docs/common/local-runbook.md`，本文不复述；本文只守 `jit_demo` 建库与特征口径这两条承重项。
