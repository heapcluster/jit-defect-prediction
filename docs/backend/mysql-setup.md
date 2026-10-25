# MySQL 演示库 `jit_demo`：安装 → 建库 → 配置 → 验收

> **文档状态（`docs/README.md` §0.2）：权威** —— 本机 MySQL 与演示库 `jit_demo` 的**安装、权限、建库脚本、`.env` 写法、验收清单、常见坑**只此一份。
> **本文不复述**（复述即违反 §0.2「指针不得超 3 行」）：本机全链路跑通顺序（§0–§6）的唯一出处是 `docs/common/local-runbook.md`；四份 CSV 的文件名与产出口径的唯一出处是 `docs/repo/demo-script-sprint1.md` §0.0；四表 DDL 的唯一出处是 `infra/schema.sql`；联调库口径（MySQL `jit_demo`、令牌）的唯一出处是 `docs/frontend/integration-log.md` §0。
> **归属**：后端线（`docs/owners/s1mple-less.md` §1）。**依据**：Issue #142（2026-10-25 裁定「每人本机 MySQL + 后端出 `.sql` 建库脚本 + 配置文档」）；本项目统一用 MySQL，联调 / 演示 / 验收共用 `jit_demo`，双库策略已废除。

> ✅ **建库脚本已在真 MySQL 上跑通（2026-10-25 实测，MySQL 8.0.45 / 演示库 `jit_demo`）**：`mysql -u jit -h 127.0.0.1 < backend/scripts/schema_mysql.sql`（cwd=仓库根）→ **退出码 0**，末尾自检 `SELECT` 列出四张表且排序规则全为 `utf8mb4_unicode_ci`；随后 DDL 路径（`mysql -u jit -h 127.0.0.1 jit_demo < infra/schema.sql`）**连跑两次都 rc=0**（幂等），ORM 路径 `python -m app.db init` 与 `_assert_indexes` 在同一库上输出 `indexes ok`。全链路（建表→灌数→起服务→六条判据）**8/8 通过、退出码 0、330 秒**，实测值见 §8。
>
> ⚠️ **仍未由我在 root 下实测的一步**：**从空实例首次 `CREATE DATABASE`**。本机 root 口令不在我手上（`jit` 账号建库实测 `ERROR 1044`、`root` 免密 `ERROR 1045`），`jit_demo` 是由用户以 root 执行 §6 坑 1 里那两条语句建出来的 —— 建出后我实测其 `DEFAULT_CHARACTER_SET_NAME=utf8mb4`、`DEFAULT_COLLATION_NAME=utf8mb4_unicode_ci`，**与脚本指定的值逐字一致**。我跑的那一次是「库已存在」的路径：此时 `CREATE DATABASE IF NOT EXISTS` 短路，**普通账号也能 rc=0 重跑整条脚本**（见 §6 坑 1 的补充）。

## 0. 十分钟路径

| 步 | 做什么 | 命令（cwd 见每节） | 判据 |
|---|---|---|---|
| 1 | 装 MySQL 8 + 建 conda 环境 | 见 §1 | `mysql --version` 有输出；`python -m pip show PyMySQL` 有版本 |
| 2 | **一条命令**建库 + 建四表 | `mysql -u root -p < backend/scripts/schema_mysql.sql`（cwd = **仓库根**） | 末尾列出 4 张表，排序规则 `utf8mb4_unicode_ci` |
| 3 | 配 `backend/.env` 的连接串 | 见 §3 | `python -m app.db init` 幂等 + 索引自检通过 |
| 4 | 灌真实数据 + 起服务 + 自检 | 见 §4、§5 | `python -m scripts.demo_preflight` 六条判据全 PASS |

第 2–4 步在**空 MySQL** 上就能跑通，不依赖任何既有库、不依赖别人的机器、不需要 infra 授权（#142 已把「授权 `jit@127.0.0.1`」这条作废）。

## 1. 前置：MySQL 与 Python 依赖

### 1.1 MySQL 版本与安装（Windows 优先）

- **版本：MySQL 8.0**。本项目实测服务端 **8.0.45**（`SELECT VERSION()`）；其他 8.0.x 小版本未逐一验证，**5.7 及以下未测**，不要当已验证。
- **安装**：官网 MySQL Installer for Windows（MSI），组件只勾 **MySQL Server 8.0** + **Command Line Client**；安装时选「Development Computer」、认证方式选 **Use Strong Password Encryption**（8.0 默认 `caching_sha2_password`，PyMySQL 1.2.3 支持）、端口保持 **3306**、Windows 服务名默认 `MySQL80` 并勾开机启动。
- **装完自检**（三条都要有输出）：

```bash
mysql --version
mysql -u root -p -e "SELECT VERSION() AS v, @@character_set_server AS cs, @@collation_server AS co, @@time_zone AS tz;"
python -c "import sqlalchemy; print(sqlalchemy.__version__)"
```

本项目实测第二条返回 `8.0.45 / utf8mb4 / utf8mb4_0900_ai_ci / SYSTEM` —— **服务端默认排序规则与建库脚本指定的不同是有意的**，见 §2.3。

### 1.2 Python 依赖（不需要另装驱动）

- **环境唯一来源是 `data_model/environment.yml`**（conda 环境名 `jit-defect-prediction`）；`conda env create -f data_model/environment.yml` 出来的环境已含 **`pymysql==1.2.3`**（该文件第 55 行）与 **SQLAlchemy 2.0.54**。
- 仓库**没有** `backend/requirements.txt`，不要另建第二份依赖清单（口径单点）。
- 自检：`python -m pip show PyMySQL` → `Version: 1.2.3`。**不要用 `pymysql.__version__`** 判断 —— 该属性报的是驱动内部协议版本号（本机实测 `2.2.8`），与发行版号不是一回事。
- 报 `ModuleNotFoundError: No module named 'pymysql'` 基本只有一个原因：**跑成了系统 Python 而不是 conda 环境**（见 §6 坑 4）。

## 2. 一条命令建库 + 建表

### 2.1 命令

**Git Bash / Linux shell**（cwd 必须是仓库根目录，不是 `backend/`）：

```bash
mysql -u root -p < backend/scripts/schema_mysql.sql
```

**PowerShell**（团队主力是 Windows，而 PowerShell **不支持 `<` 输入重定向** —— 实测报「`<` 运算符保留供将来使用」，见 §6 坑 10）：

```powershell
# cwd = 仓库根。两种都行，实测都 rc=0；推荐第一种（客户端自己读文件，不经 PowerShell 的编码转换）
mysql -u root -p -e "SOURCE backend/scripts/schema_mysql.sql"
Get-Content backend/scripts/schema_mysql.sql | mysql -u root -p
```

口令走 `-p` 的**交互输入**，不要写成 `-p<口令>`（会进 shell 历史，且 MySQL 自己会警告）。

脚本内容只有四条语句：`CREATE DATABASE IF NOT EXISTS jit_demo …` → `USE jit_demo` → `SOURCE infra/schema.sql` → 一条自检 `SELECT`。**四表 DDL 仍只有 `infra/schema.sql` 一份**，脚本不复制 DDL，因此两条建表路径的等价性与幂等性口径不变。

### 2.2 期望输出

```
built_table       TABLE_COLLATION
commit            utf8mb4_unicode_ci
commit_feature    utf8mb4_unicode_ci
commit_label      utf8mb4_unicode_ci
prediction        utf8mb4_unicode_ci
```

**没列出 4 张表、或报 `Failed to open file` 且退出码 1 = `SOURCE` 没找到文件**，九成是 cwd 不在仓库根（§6 坑 2）。注意这种情况下的残留状态：`CREATE DATABASE` 在 `SOURCE` 之前已执行，所以**库会建出来但里面 0 张表**，批模式遇错即中止（除非加 `--force`）→ **一律按退出码判定，别只看「库存在」**；改对 cwd 重跑即可补齐四表（幂等）。

**幂等**：`CREATE DATABASE` 与四表 `CREATE TABLE` 全带 `IF NOT EXISTS`，同一条命令重跑不报错、**不清已有数据**。要重建空库请自己显式 `DROP DATABASE jit_demo`（脚本永不做破坏性操作，`backend/tests/test_schema_mysql_script.py` 把这条钉住了）。

### 2.3 为什么建库头不进 `infra/schema.sql`

`infra/schema.sql` 必须保持「纯四表 DDL、可导入任意目标库」：它同时服务三个调用方（`docs/backend/acceptance.md` 的导入命令、Issue #121 的 `jit_schema_probe` / `jit_orm_probe` 两个探针库、本脚本的 `SOURCE`），里面一旦出现 `USE`，命令行指定的库名就会被**静默改写**，验收会在错误的库上「通过」；而 `backend/tests/test_schema_sql.py` 逐字比对 `Base.metadata`，断言「恰好四条 CREATE TABLE」并显式拒收 `CREATE DATABASE` / `GRANT` / `DROP` 等多余语句（25 条用例）。所以建库头单独放 `backend/scripts/schema_mysql.sql`。

字符集与排序规则**显式写死** `utf8mb4` + `utf8mb4_unicode_ci`（#142 裁定），不跟随服务端默认值 —— 各人本机 `@@collation_server` 可能不同（本项目实测就有默认 `utf8mb4_0900_ai_ci` 的），显式指定才不会让六台机器建出排序规则不一致的库。

### 2.4 ORM 等价路径（可选，用于交叉验证）

```bash
# cwd = backend；连接串走 backend/.env（见 §3），命令行不带 DATABASE_URL 前缀
python -m app.db init
python -c "from app.db import get_engine, _assert_indexes; _assert_indexes(get_engine()); print('indexes ok')"
```

`app.db init` 建表后自动跑 `_assert_indexes`；它只覆盖 `INDEX_ASSERTIONS` 的核心索引，**不是完整列/键对照**，完整验收按 `docs/backend/acceptance.md` 板块 B1。两条路径在同一库上连跑两次都必须无错（幂等）。

## 3. 配 `backend/.env`

```ini
DATABASE_URL=mysql+pymysql://<user>:<pwd>@127.0.0.1:3306/jit_demo?charset=utf8mb4
```

- **口令只写进本机 `backend/.env`**（已被 `.gitignore` 忽略），不进任何入库文档、不进 `.env.example`（§0 硬规矩 1 的同源要求）。`<user>` 用你自己建的账号即可 —— 建库要 `CREATE DATABASE` 权限（§6 坑 1），但**灌数与起服务只需要该库的 DML/DDL 权限**。
- **必须带 `?charset=utf8mb4`**，否则中文提交信息可能按服务端默认字符集写入（§6 坑 5）。
- **坑（最容易踩）**：`backend/app/config.py` 只调用 `load_dotenv()`，而 **`load_dotenv()` 默认不覆盖已存在的环境变量** —— 所以 `DATABASE_URL=... python -m app.ingest ...` 这种**行内前缀会压过 `.env`**。两者只能选一种；本口径选 `.env`，**命令里一律不带前缀**（`backend/scripts/evidence/system-layer-backend-2026-10-24.md` §1 的复跑命令、`docs/repo/demo-script-sprint1.md` §0.0 同此口径）。
- `API_TOKEN` 必须等于前端 `frontend/.env.local` 的 `VITE_API_KEY`，否则前端全部 40100。当前值与其余基线项**只认** `docs/frontend/integration-log.md` §0，本文不抄。
- `MODEL_DIR` 留空即回落到仓库内 `data_model/pipelines/expert/models/`（#99 自动插 `sys.path`，不要再手工设 `PYTHONPATH`）。

## 4. 灌真实数据

### 4.1 先建 Camel 历史索引（现算特征的数据来源）

在线预测（`POST /api/predict`、`POST /api/sync`、`POST /api/sync-prs`）在提交或特征缺失时要现算 14 项特征，数据来源是本地一份 **blobless 历史索引**（只取提交 + 树、不含 blob，几十 MB），由 `backend/.env` 的 `SOURCE_REPO` 指向。第一次跑预测前先建它：

```bash
# cwd = 仓库根；路径放仓库外（不要放仓库里，也不要写进入库文档）
python infra/clone_camel_history.py --repo apache/camel --path <本机路径>/camel-history
python infra/clone_camel_history.py --path <本机路径>/camel-history --fetch   # 增量更新
```

- 索引**不是开发库、不进工作流、不持有预测状态**；`SOURCE_REPO` 配它的路径（见 §3）。
- 它取代了原「离线 CSV 灌库」成为数据入口：灌库（`app.ingest`）已移除，实时预测见 `docs/common/local-runbook.md` §4。

```bash
# cwd = backend；连接串已在 backend/.env（命令行不带前缀，见 §3）
python -m app.ingest commits     <提交清单.csv>
python -m app.ingest labels      <标签表.csv>
python -m app.ingest features    <特征表.csv>
python -m app.ingest predictions <prediction_result.csv>
```

- **四份 CSV 的文件名、来源与产出口径只认 `docs/repo/demo-script-sprint1.md` §0.0**，本文不抄第二份。
- **行数口径**（本机实测 CSV 数据行数，不含表头）：

| 类别 | 数据行数 | 说明 |
|---|---|---|
| `commits` | **84,461** | 全量提交清单（含 518 条无对应特征/标签的行） |
| `predictions` | **83,943** | 方案 C 离线预测结果，= 数据集规模 |
| `labels` | **83,943** 或 83,887 | 两个都合法：`commit_label` 表**没有任何接口读取**（四接口只读 `commit` / `commit_feature` / `prediction`），差 56 行的定位方法与影响面见 `backend/scripts/evidence/system-layer-backend-2026-10-24.md` §6.1 与 §7 |
| `features` | **只有 83,943 一个合法值** | 且**必须是契约二 v1.2「对数变换后」的形态**，见下面那条警告 |

> ⚠️ **`commit_features_raw.csv`（84,461 行）不能灌** —— 它是**模型线的训练输入形态**（`fused` 线的 `FEATURES_RAW_CSV` 就是它），不是「多 518 行的超集」，而是**另一套特征空间**。灌进去之后 `POST /api/predict` 会**静默算出错误概率**（模型不报错、接口 200、页面照常显示），本机实测同一条提交、同一个 `xgb_v1`：
>
> | 特征来源 | 在线预测概率 |
> |---|---|
> | `commit_features_raw.csv`（原始计数：`ns=1, nd=10, nf=42, entropy=5.3923…`） | **0.82657** ← 错的 |
> | `dataset_szz.csv`（契约形态：`ns=0.0, nd=2.30259=ln(10), nf=3.73767=ln(42), entropy=1.68498=ln(5.3923)`） | **0.79963** ← 与离线批量产物 `prediction_result.csv` 的存量值**逐位相同** |
>
> 依据是**冻结契约二 v1.2 第四节**：「全部 14 项取对数变换 …… 非 0 值取 `ln(x)`、0 值记 0」，`fix` 除外。所以 `commit_feature` 表里该存的是 `ln` 之后的值。
>
> **两份文件逐列的实测关系**（取交集前 3,000 条提交，`dataset` 值与 `ln(raw)` 比对，容差 1e-9）：
>
> | 列 | `dataset == ln(raw)` | `dataset == raw` | 说明 |
> |---|---|---|---|
> | `ns` `nd` `nf` `entropy` `ndev` `age` `exp` `rexp` `sexp` | **3000/3000** | 0~206/3000 | 严格满足契约的 `ln` 口径 |
> | `fix` | —（`ln(1)=0` 会误判） | **3000/3000** | 契约明文「`fix` 不做对数变换」，逐字相等 |
> | `la` `ld` `lt` `nuc` | **132 / 471 / 1125 / 1122 每 3000** | 128~469/3000 | ⚠️ **不满足 `ln` 关系** —— 这四列在两份文件里是不同口径的产物 |
>
> **由此得出一条硬结论：不能拿 `commit_features_raw.csv` 自己取 `ln` 补救。** 9 列可以，`la`/`ld`/`lt`/`nuc` 这四列**无论怎么变换都对不上**（那 132~1125 条「命中」基本是两边都为 0 的行）。要得到契约形态的特征，**只能用 `dataset_szz.csv`（或数据线由它投影出的 `commit_features.csv`）**。
>
> 顺带说明这两份文件各自的正当用途，别把 raw 当成「错文件」：`commit_features_raw.csv` 是**融合/语义线的训练输入**（`data_model/pipelines/fused/config.py::FEATURES_RAW_CSV` 实测就指向它），它归模型线用；**入 `commit_feature` 表必须是契约形态那一份**。两者用途不同，不是同一份数据的两种形态。
>
> **当前缺口**：`docs/repo/demo-script-sprint1.md` §0.0 第 3 条写的是 `data_model/data/commit_features.csv`，而**这个文件目前不存在**（该目录下只有 `commit_features_raw.csv`）。照 §0.0 复制会在第三类直接报文件不存在；改用 raw 那份就会踩上面这个坑。正解是数据线补出这份投影（属 `data_model/`，不归后端代做）；临时自救按下面两步做。
>
> **第 1 步**：把下面这段存成 `project_features.py`（放哪个目录都行，**不要用 heredoc** —— `python - <<'PY'` 只在 Git Bash/Linux 下有效，PowerShell 与 cmd 都会失败）：
>
> ```python
> # 列名以 docs/model/feature-columns.md 第三节（= backend/app/config.py::FEATURE_COLUMNS）为准
> import csv
> import pathlib
>
> KEEP = ["commit_hash", "committed_at", "feature_version",
>         "ns", "nd", "nf", "entropy", "la", "ld", "lt", "fix",
>         "ndev", "age", "nuc", "exp", "rexp", "sexp"]
> src = pathlib.Path("data_model/data/dataset_szz.csv")     # 相对仓库根
> dst = pathlib.Path("data_model/data/commit_features.csv")
> count = 0
> with src.open(encoding="utf-8", newline="") as fin, dst.open("w", encoding="utf-8", newline="") as fout:
>     writer = csv.DictWriter(fout, fieldnames=KEEP, extrasaction="ignore")
>     writer.writeheader()
>     for row in csv.DictReader(fin):
>         writer.writerow(row)
>         count += 1
> print(f"写出 {count} 行 -> {dst}")
> ```
>
> **第 2 步**：在**仓库根**执行（三种终端同一条命令，无 shell 特有语法）：
>
> ```
> python project_features.py
> ```
>
> 期望输出 `写出 83943 行 -> data_model\data\commit_features.csv`。随后 `cd backend` → `python -m app.ingest features ../data_model/data/commit_features.csv` 重灌一次即可（ingest 幂等、同 hash 覆盖，不用重建库、不用重灌其他三类）。
>
> 灌完**必须验一次口径**（一条 SQL，能挡住这个坑）：契约形态下 `la` / `ld` 会出现**大量负值**（`ln(x)` 在 x<1 时为负），原始计数则**恒为非负**且量级完全不同。本机全量实测两份文件的判据值：
>
> | 文件 | `min(la)` | `min(ld)` | `max(nf)` | `la < 0` 的行数 |
> |---|---|---|---|---|
> | `dataset_szz.csv`（契约形态，**该灌这份**） | **−12.9444** | **−12.1698** | **9.7940** | **76,444 / 83,943**（91.1%） |
> | `commit_features_raw.csv`（变换前，**不可灌**） | 0.0000 | 0.0000 | **17,925** | **0** |
>
> ```sql
> SELECT MIN(la) AS min_la, MIN(ld) AS min_ld, MAX(nf) AS max_nf,
>        SUM(la < 0) AS neg_la_rows, COUNT(*) AS total FROM commit_feature;
> -- 契约形态：min_la/min_ld 为负、max_nf 约 9.8、neg_la_rows ≈ 0.91 × total
> -- 灌错了（raw）：neg_la_rows = 0、max_nf 上万
> ```
>
> 佐证：契约二 v1.2 的变更日志本身就把「`la` / `ld` 出现负值」当作 `ln(x)` 口径的判据（该日志记的是当时数据集上的 −8.7612 / −9.1363；上表是我在当前 Camel 全量数据上的实测值，两者符号与量级一致）。

**必须守的不变式**：「有预测必有特征行」（否则详情页与 `POST /api/predict` 会 40400），在本机 MySQL `jit_demo` 实测 **0 例外**；以及上面那条「特征必须是对数变换后的契约形态」。

- **灌入幂等**：同一文件重跑不增行（按表幂等键 upsert：`commit=commit_hash`、`label=(commit_hash, label_method)`、`feature=commit_hash`、`prediction=(commit_hash, model_name)`）；缺主键字段的行整批回滚并报行号。该幂等性在 MySQL `jit_demo` 四类各灌两遍实测通过（组长本机 #147）。

## 5. 验收清单

灌完起服务后逐条核（也可用 §5.2 的脚本一条命令跑完）：

### 5.1 数字判据

| # | 判据 | 期望值 | 怎么查 |
|---|---|---|---|
| 1 | 四表行数 | `commit` **84,461**、`prediction` **83,943**、`commit_feature` **83,943**、`commit_label` 83,943 或 83,887 | `SELECT COUNT(*)`，或脚本 |
| 1b | **特征口径**（防「灌了 raw 那份」） | `MIN(la)` 为负、`SUM(la < 0)` ≈ 0.91 × 总行数、`MAX(nf)` ≈ 9.8。**MySQL 实测**：`MIN(la) = −12.9443795988`、`MIN(ld) = −12.1697872202`、`MAX(nf) = 9.7939516655`、`SUM(la<0) = 76444`、总行数 83943（与 §4 CSV 层实测逐项吻合；小数位比 CSV 少是因为列类型是 `DECIMAL(20,10)`，按 10 位截断，属预期） | §4 那条 SQL |
| 2 | 高风险行 | `risk_score ≥ 0.5` 恰 **14,596** 条（占 83,943 的 17.39%） | `SELECT COUNT(*) FROM prediction WHERE risk_score >= 0.5` |
| 3 | 列表接口 | `GET /api/commits?size=1` → `data.total = 83943` | curl / 浏览器 |
| 4 | 趋势接口 | `GET /api/trends` → **236** 期，各期 `commit_count` 之和 = 83,943 | curl |
| 5 | 模型加载 | 启动日志 `loaded models: ['lr_v1', 'rf_v1', 'xgb_v1']`，**不得出现** `failed models:` | 终端 A |
| 6 | 在线预测幂等 | 同一 `(commit_hash, model_name)` 连 POST 两次，`prediction` 只留 1 行 | 两次 curl + `COUNT(*)` |

判据 5 的清单来源是 `data_model/pipelines/expert/models/feature_order.txt` 的 `[models]` 段；同目录另有 5 个 `[evaluated]` 权重（`lgbm_v1` / `et_v1` / `svm_v1` / `mlp_deep_v1` / `tabnet_v1`），**不进后端加载清单**（`openspec/specs/model-coverage` 冻结项），指定它们查询返回 **40001** 属预期行为、不判失败。

### 5.2 一条命令自检

```bash
# cwd = backend；连接串、令牌、MODEL_DIR 一律读 backend/.env（脚本不提供覆盖它们的开关）
python -m scripts.demo_preflight --out scripts/evidence/preflight-<日期>.md
# 从零到断言（--init-db / --ingest 两个前置阶段）：建表 → 灌数 → 起服务 → 六条判据
python -m scripts.demo_preflight --init-db --ingest --out scripts/evidence/preflight-<日期>.md
```

脚本（Issue #138）**实际支持的开关**（`python -m scripts.demo_preflight --help` 是唯一权威，下表只是速查）：

| 开关 | 作用 | 默认 |
|---|---|---|
| `--init-db` | 前置阶段 0a：建表（等价 `python -m app.db init`，含索引自检）。**只建表不建库** | 关 |
| `--ingest` | 前置阶段 0b：四类 CSV 依次 `app.ingest`，逐类报行数 | 关 |
| `--ingest-csv KIND=PATH` | 覆盖某一类 CSV 路径，可重复；KIND 取 `commits\|labels\|features\|predictions` | §0.0 的四条路径 |
| `--expect-predictions N` | 判据 2 的期望 `prediction` 行数；**联调库跑要写 3** | `83943` |
| `--expect-models a,b,c` | 判据 4 的期望加载清单 | `lr_v1,rf_v1,xgb_v1` |
| `--host` / `--port` | 脚本自己起的服务地址 | `127.0.0.1` / `8055` |
| `--timeout S` | 等服务就绪的秒数（模型加载约 40s，首次跑建议放宽） | `120` |
| `--backend-env` / `--frontend-env` | 两份 `.env` 的位置（判据 1 比对令牌用） | `backend/.env` / `frontend/.env.local` |
| `--out PATH` | 把结果写成证据 markdown | 不写 |

**没有** `--db-url` 与 `--token` 这两个开关：库与令牌只从 `backend/.env`（或已存在的环境变量）读，脚本刻意不提供命令行覆盖 —— 命令行传口令会进 shell 历史，也会让「判据 1 比对的两份 `.env`」与「实际连的库」脱钩。

脚本逐条判六项：令牌一致性 → 库四表行数 → 存在 `risk_score ≥ 0.5` 的行 → 交付模型全部加载 → 契约三的四条路径全 200 → 同 hash 两次预测只留一行。**任一不满足退出码 1 并打印实际值**；证据文件里的口令、连接串与个人绝对路径一律自动掩码。

> ⚠️ **六条判据全绿 ≠ 特征口径对**：判据里没有一条比对 `commit_feature` 的**值**，所以灌了 §4 那份 raw 特征表也会 8/8 全绿（本机实测就是这个结果）。灌完请另跑 §4 的那条 SQL 验一次。

## 6. 常见坑（现象 → 根因 → 解法）

| # | 现象 | 根因 | 解法 |
|---|---|---|---|
| 1 | `ERROR 1044 (42000): Access denied for user 'jit'@'127.0.0.1' to database 'jit_demo'` | 只被授予「某个库 ALL PRIVILEGES」的账号**没有** `CREATE DATABASE`（全局只有 `GRANT USAGE ON *.*`）。本项目实测：`jit@127.0.0.1` 建 `jit_demo` 必报 1044 | 用 **root** 跑 §2.1；或让有权限的人执行一次 `CREATE DATABASE IF NOT EXISTS jit_demo CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;` + `GRANT ALL PRIVILEGES ON jit_demo.* TO '<你的账号>'@'127.0.0.1'; FLUSH PRIVILEGES;`。<br>**补充（本机实测）**：库建好并授权之后，**普通账号重跑 §2.1 那条脚本会 rc=0** —— `CREATE DATABASE IF NOT EXISTS` 在库已存在时短路，不再检查全局 `CREATE` 权限。所以 root 只需出手一次，之后每人自己重跑脚本都安全（幂等、不清数据） |
| 2 | `ERROR at line 3: Failed to open file 'infra\schema.sql', error: 2`（本机实测原文，Windows 下路径分隔符显示为反斜杠），退出码 1 | `SOURCE` 是 **mysql 客户端内建命令**，按**当前工作目录**解析相对路径 | cwd 切到**仓库根**再跑；此时 `jit_demo` 已被建出但 0 张表，重跑即补齐（§2.2）。另外 `SOURCE` 只有客户端认，pymysql / SQLAlchemy 都不认（ORM 路径走 `python -m app.db init`） |
| 3 | `ERROR 2003 (HY000): Can't connect to MySQL server on '127.0.0.1:3306'` | 服务没起，或 3306 被另一个实例占用 | Windows：`Get-Service MySQL80` / `net start MySQL80`；查占用 `netstat -ano \| findstr :3306`，再按 PID 看是哪个进程 |
| 4 | `ModuleNotFoundError: No module named 'pymysql'` | 跑成了系统 Python，不是 conda 环境 `jit-defect-prediction` | `conda activate jit-defect-prediction` 后重试；依赖清单只有 `data_model/environment.yml` 一份 |
| 5 | 中文提交信息乱码，或 `Incorrect string value: '\xF0\x9F...'` | 库/连接不是 `utf8mb4`（`utf8` 在 MySQL 里是 `utf8mb3`，存不下 4 字节字符） | 用 §2.1 的脚本建库（已钉 `utf8mb4`），连接串带 `?charset=utf8mb4` |
| 6 | 担心时间被时区偏移 | 不成立：四表时间列都是 `DATETIME`（不是会按会话时区转换的 `TIMESTAMP`），后端一律在 Python 侧取 UTC 再去 `tzinfo` 后写入，`backend/app` 内没有任何 SQL 侧 `NOW()` / `CURRENT_TIMESTAMP` / `server_default`（grep 实测 0 命中） | 无需设 `time_zone`；本机实测 `@@time_zone = SYSTEM` 也不产生偏移。**别把时间列改成 `TIMESTAMP`** |
| 7 | 改了 `backend/.env` 的连接串，服务却还连旧库 | 命令行带了 `DATABASE_URL=...` 前缀，而 `load_dotenv()` **不覆盖已存在的环境变量** | 命令里去掉前缀（§3）；`docs/common/local-runbook.md` §2.2 里那种带前缀的写法与本口径二选一，别混用 |
| 8 | 建到了共享实例上那份旧库 | 那份库里有 2 提交 / 4 预测的**占位脏数据**（假哈希 `1111…`/`2222…`、`repo_name=activemq`、`model_name` 为 `smoke_v1` / `tree_placeholder_v0`），灌真数据不会覆盖它们（哈希不同），演示列表会只剩一条假数据还排在前面 | 演示与验收一律用本机新建的 `jit_demo`；那份旧库**不是演示库**，其存量清理归 infra、不阻断演示（#142「存量处置（降级，不阻断）」） |
| 9 | **在线预测的概率与库内存量值对不上**（同一提交、同一模型，详情页点「重新预测」后数字变了） | 灌的是 `commit_features_raw.csv` —— 那是模型线的训练输入形态（`ln` 变换之前），专家模型按契约二 v1.2 的 `ln` 形态训练，喂它不报错、只给错答案 | 按 §4 从 `dataset_szz.csv` 投影出契约形态的 `commit_features.csv` 重灌 `features`（ingest 幂等，同 hash 覆盖，不用重建库），再用 §4 那条 SQL 验 `MIN(la)` 为负。本机实测差多少：同一提交 `xgb_v1` raw → **0.82657**、契约形态 → **0.79963**（= 离线批量产物的存量值） |
| 10 | PowerShell 里跑 `mysql … < backend/scripts/schema_mysql.sql` 报「`<` 运算符保留供将来使用」，一条语句都没执行 | PowerShell **不支持** `<` 输入重定向（bash/cmd 才支持），这是 shell 语法差异、不是 MySQL 的问题 | 用 §2.1 的 PowerShell 写法：`mysql -u root -p -e "SOURCE backend/scripts/schema_mysql.sql"`（实测 rc=0），或 `Get-Content … \| mysql -u root -p`（实测 rc=0）。`cmd /c "mysql -u root -p < backend\scripts\schema_mysql.sql"` 也可以 |

## 7. 与其他文档的关系

| 要看什么 | 去哪 |
|---|---|
| 本机从零跑通全链路的**步骤顺序**（§0–§6，含六条自检与前端） | `docs/common/local-runbook.md` |
| 四份 CSV 的**文件名与产出口径**、演示脚本与判据 | `docs/repo/demo-script-sprint1.md` §0.0 / §0.0.1 |
| 联调库（MySQL `jit_demo`）、`API_TOKEN`、端口等**联调基线** | `docs/frontend/integration-log.md` §0 |
| 四表 DDL 本体、字段与索引要求 | `infra/schema.sql` + `docs/design/data-fields.md` |
| 接口路径、错误码、非功能靶子 | `docs/backend/api-spec.md`（契约三 v1.5，冻结） |
| 后端验收板块（B1 建表、B4 在线预测、B5/B6 非功能） | `docs/backend/acceptance.md` |
| 已在库上跑过的实测记录（SQLite 全量、T-ST 后端半边 43 项断言） | `backend/scripts/evidence/integration-2026-10-24.md`、`backend/scripts/evidence/system-layer-backend-2026-10-24.md` |

---

## 8. 本文档的实测边界（哪些是测过的、哪些不是）

**本文档只写已验证或已裁定的内容**，未验证的一律如实登记，不当已验证。

| 内容 | 状态 | 依据 |
|---|---|---|
| `SOURCE` 按 cwd 解析相对路径（正例 rc=0 / 反例 rc=1 + 错误原文） | ✅ 本机实测 | 临时目录里造 `backend/scripts/outer.sql` + `infra/inner.sql` 正反两跑，反例输出即 §6 坑 2 的原文 |
| 普通账号建 `jit_demo` 报 `ERROR 1044 (42000)` | ✅ 本机实测 | `jit@127.0.0.1` 只有全局 `GRANT USAGE ON *.*` + **单个既有库**的 `ALL PRIVILEGES`，无 `CREATE DATABASE` |
| 服务端 `8.0.45` / `utf8mb4` / `utf8mb4_0900_ai_ci` / `time_zone=SYSTEM` | ✅ 本机实测 | §1.1 第二条自检命令 |
| `PyMySQL 1.2.3`、`SQLAlchemy 2.0.54` | ✅ 本机实测 | `pip show PyMySQL`、`import sqlalchemy` |
| 四份 CSV 的数据行数（84,461 / 83,943 / 84,461 / 83,943） | ✅ 本机实测 | 逐份数数据行（不含表头） |
| **特征口径判别**（§4 那张对照表与两个在线概率） | ✅ 本机实测 | 两份文件全量扫 `min(la)`/`min(ld)`/`max(nf)`/`la<0` 行数；再用 `joblib.load(xgb_v1.pkl)` 对同一提交分别喂两套特征，得 0.82657 / 0.79963，后者与 `prediction_result.csv` 存量值逐位相同 |
| **两份特征文件逐列的变换关系**（§4 那张 3,000 条比对表） | ✅ 本机实测 | 取交集前 3,000 条提交，逐列比对 `dataset` 与 `ln(raw)`（容差 1e-9）：9 列 3000/3000 命中、`fix` 逐字相等 3000/3000、`la`/`ld`/`lt`/`nuc` 仅 132/471/1125/1122 命中 → 结论「不能自己取 `ln` 补救」由此而来 |
| **建库→灌数→起服务→六条判据全链路**（SQLite 形态） | ✅ 本机实测 **两轮各 8/8 通过、rc=0** | `python -m scripts.demo_preflight --init-db --ingest …`。**这是一组 A/B 对照**，两轮只差 `features` 用哪份 CSV：<br>**第一轮**（`features=commit_features_raw.csv`，84,461 行，86 秒）→ 判据 6 信息行显示在线重算 **0.82657**、库内存量 **0.79963**，**两者不等** = 特征口径错；<br>**第二轮**（`features=` 按 §4 投影出的 `commit_features.csv`，83,943 行，120 秒）→ 在线重算 **0.79963 / 0.79963**，与库内存量**逐位相同** = 口径对。<br>两轮其余判据输出完全一致：`prediction=83943`、`risk≥0.5` = **14,596**、`loaded models: ['lr_v1','rf_v1','xgb_v1']`、四接口全 200 code=0、两次 POST 后 `(hash, xgb_v1)` 恒 1 行且总行数不变。**结论：判据 1~6 全绿抓不到特征口径错**（没有一条比对 `commit_feature` 的值），这正是 §5.1 判据 1b 存在的原因 |
| §4 的投影配方 | ✅ 本机实跑 | 存成 `project_features.py` 后在仓库根执行 → 输出 `写出 83943 行 -> data_model\data\commit_features.csv`；产物 17 列、`min(la) = −12.944379598832155`、`la<0` 的行 **76,444**、`max(nf) = 9.793951665467821`，与上表判别值逐项吻合 |
| 时间列不受 `time_zone` 影响 | ✅ 代码级实测 | `infra/schema.sql` 四个时间列全为 `DATETIME`；`backend/app` 内 `NOW()` / `CURRENT_TIMESTAMP` / `server_default` grep 0 命中 |
| **§2.1 的建库脚本在真 MySQL 上跑通**（`SOURCE infra/schema.sql` + 四表 + 排序规则） | ✅ 本机实测 **rc=0** | `mysql -u jit -h 127.0.0.1 < backend/scripts/schema_mysql.sql`（cwd=仓库根，MySQL 8.0.45）→ 退出码 0，自检 `SELECT` 输出 `commit / commit_feature / commit_label / prediction` 四行、`TABLE_COLLATION` 全为 `utf8mb4_unicode_ci`。**账号形态 = 普通账号 `jit`（非 root）**：库已由 root 建出，`CREATE DATABASE IF NOT EXISTS` 短路，所以普通账号也能整条跑通（§6 坑 1 补充）。**仍缺的一步**：从**空实例**首次 `CREATE DATABASE`，需要 root（本机 `jit` 实测 1044、`root` 免密 1045）；`jit_demo` 由用户以 root 建出，我实测其 `DEFAULT_CHARACTER_SET_NAME=utf8mb4`、`DEFAULT_COLLATION_NAME=utf8mb4_unicode_ci`，与脚本指定值逐字一致 |
| **两条建表路径在同一个 MySQL 库上的等价性与幂等性** | ✅ 本机实测 | DDL 路径 `mysql -u jit -h 127.0.0.1 jit_demo < infra/schema.sql` **连跑两次都 rc=0**；ORM 路径 `python -m app.db init`（经 preflight 的 0a 阶段）在同一个库上 rc=0 且 `_assert_indexes` 通过；单独再跑 `python -c "from app.db import get_engine, _assert_indexes; _assert_indexes(get_engine())"` → `indexes ok` |
| **§5.1 六条判据 + 判据 1b 在本机 MySQL 上** | ✅ 本机实测 **8/8 通过、rc=0、330 秒** | 见下面「补记 2026-10-25」的完整实测值。同口径另有两份旁证：SQLite 全量库（`backend/scripts/evidence/system-layer-backend-2026-10-24.md`，43 项断言全过）与组长本机 MySQL `jit_demo`（#147 正文） |

### 补记 2026-10-25｜本机 MySQL `jit_demo` 实机验收（只追加，不改写上文）

- **环境**：MySQL 8.0.45（Windows 服务 `MySQL80`）、库 `jit_demo`（`utf8mb4` / `utf8mb4_unicode_ci`）、账号 `jit@127.0.0.1`（**普通账号，非 root**；库由用户以 root 建出并 `GRANT ALL ON jit_demo.*`）、conda 环境 `jit-defect-prediction`（Python 3.12.15 / SQLAlchemy 2.0.54 / PyMySQL 1.2.3）、权重目录为已交付的 `data_model/pipelines/expert/models/`（含 2026-10-24 的 rf 收敛版）。
- **建库脚本**：`mysql -u jit -h 127.0.0.1 < backend/scripts/schema_mysql.sql`（cwd=仓库根）→ **rc=0**，自检 `SELECT` 列出四张表、排序规则全 `utf8mb4_unicode_ci`。
- **两条建表路径**：DDL 路径连跑两次 **rc=0 / rc=0**（幂等）；ORM 路径（preflight 的 0a 阶段）在同一库上 **rc=0** + `_assert_indexes` 通过，单独复核输出 `indexes ok`。
- **一条命令全链路**：`python -m scripts.demo_preflight --init-db --ingest --expect-predictions 83943 …` → **8/8 通过、退出码 0、15:16:31 → 15:22:01 共 330 秒**。逐条实际值：

| 阶段 / 判据 | 实际值 |
|---|---|
| 0a 建库建表 | 四表 + 索引自检通过（库已由 DDL 路径建好，ORM 路径重跑幂等） |
| 0b 灌真实数据 | `commits=84461`（87.3s）、`labels=83943`（80.6s）、`features=83943`（66.0s）、`predictions=83943`（82.1s），合计 **336,290 行** |
| 1 令牌一致 | `API_TOKEN` 与 `VITE_API_KEY` 各 `***（18 字符）`，逐字相等 |
| 2 库行数 | `prediction=83943`（期望 83943）；`commit=84461`、`commit_label=83943`、`commit_feature=83943` |
| 3 存在高风险行 | `risk_score >= 0.5` 的行 = **14596** |
| 4 交付模型全部加载 | `loaded models: ['lr_v1', 'rf_v1', 'xgb_v1']`，无 `failed models:` |
| 5 四接口 200 | 列表 / 详情 / 趋势 / 预测 四条全 `HTTP 200 code=0` |
| 6 同 hash 两次预测只留一行 | 两次 POST `200/200`；`(77b260b6…, xgb_v1)` 行数 `1 → 1`；`prediction` 总行数 `83943 → 83943` |

- **判据 1b（特征口径，§4 的判别 SQL）**：`MIN(la) = −12.9443795988`、`MIN(ld) = −12.1697872202`、`MAX(nf) = 9.7939516655`、`SUM(la<0) = 76444`、`COUNT(*) = 83943` → **契约二 v1.2 的对数形态确认**。与 §4 CSV 层实测逐项吻合；小数位比 CSV 少是因为列类型 `DECIMAL(20,10)` 按 10 位截断，属预期。
- **趋势期数**：`SELECT COUNT(DISTINCT DATE_FORMAT(committed_at,'%Y-%m')) FROM commit_feature` → **236** 期，与组长本机 MySQL 实测一致。
- **在线重算与库内存量逐位相同**：判据 6 的样本 `77b260b6…` / `xgb_v1`，两次 POST 都返回 **0.79963**，库内原值也是 **0.79963** —— 这正是 §4/§6 坑 9 那个反例的正面对照（同一提交灌 raw 那份时返回 0.82657）。
- **本轮 `features` 用的是按 §4 投影出的契约形态文件（83,943 行），不是 `commit_features_raw.csv`。**
- 证据文件（脚本 `--out` 产出，令牌/连接串/CSV 路径全部自动掩码）：连接串在证据里显示为 `mysql+pymysql://jit:***@127.0.0.1:3306/jit_demo?charset=utf8mb4`。

**仍未闭合的一项**：从**空 MySQL 实例**首次执行 `CREATE DATABASE`（需 root）。本机 root 口令不在后端线手上，`jit_demo` 由用户以 root 建出后我只核了它的字符集与排序规则。若要在文档里把这一步也标成「已实测」，需要有 root 的人在**删掉 `jit_demo` 之后**跑一次 §2.1 并记录输出 —— 这属破坏性操作，我不会自行执行。

