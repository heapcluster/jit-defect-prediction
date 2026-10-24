# 吕建江（@s1mple-less）— 后端

> 更新 2026-10-24（本人订正：§1 补 `backend/tests/**` 与 `infra/schema.sql`、§3 路径条数与联调库命令按仓库现状对齐、§6 待办换成当日真实状态）｜ 变更需本人在 PR 里确认 ｜ 上位规则：`docs/repo/collaboration.md`

## 1. 负责范围（有权直接改）

- `backend/**`：`app/`（`api/{commits,predict,trends}.py`、`model_registry`、`auth`、`config`、`db`、`errors`、`feature_source`、`ingest`、`models`、`schemas`、`main`）、`scripts/`（`seed_dev_data.py`、`security_cases.py`、`perf_loop.py`）、`tests/**`
- `backend/.env.example`（模板值必须与 `integration-log.md` §0 一致）
- `backend/scripts/evidence/**`：性能与安全自测证据
- `docs/backend/**`：`api-spec.md`、`implementation.md`、`acceptance.md`
- 联调库结构（SQLite 四张表）与 seed 脚本口径
- `infra/schema.sql`：MySQL 建表 DDL，必须与 `python -m app.db init` 的 ORM 路径等价（两边都过 `_assert_indexes`）。**文件在 infra 目录，改动需苏哲勋会签**；等价性判据与索引断言由后端线维护

## 2. 不越界（这些必须找别人）

| 事项 | 找谁 |
|---|---|
| 模型权重、`feature_order.txt`、阈值与解释口径 | 蒋励 |
| 契约三的错误码与性能靶子、字段定义 | 苏哲勋 |
| 前端页面与组件 | 刘帅华 |
| 线上部署形态（MySQL 实例、账号与授权） | 苏哲勋（infra） |

## 3. 交付物与验收

- **接口**：契约三所列路径全部可用；仓库侧唯一出处是 `docs/backend/api-spec.md` §三，当前 **4 条**（`GET /api/commits`、`GET /api/commits/{commit_hash}`、`GET /api/trends`、`POST /api/predict`）。`GET /api/models` **不做**（`docs/backend/acceptance.md` 第 5 条：前端维护静态清单）。鉴权 `X-API-Key` fail-closed：`API_TOKEN` 未配置一律拒绝（`backend/app/auth.py`）
- **错误码**：`40001` 参数、`40100` 鉴权、`40400` 不存在、`50000` 内部错误；**不把服务端 message 原文吐给前端**，`50000` 不回显堆栈/SQL/路径
- **联调库**：按 `integration-log.md` §0 的口径 —— `cd backend` → `python -m scripts.seed_dev_data` 一条命令建库灌数（3 提交 / 3 特征 / 3 预测，`commit_hash` = `000…001`~`000…003`）。2026-10-24 实跑核对：不带 `PYTHONPATH` 也 rc=0、重跑幂等、库内 3/0/3/3 行。**联调库只有 `backend/dev.db` 一份**；后端验收跑用的一次性隔离库（全量 83,943 行）不是联调库，不许混用
- **压测**：登记口径是 `python scripts/perf_loop.py --n 100`（`test-plan.md` T-NF-01、`non-functional.md` §2）；`acceptance.md` 第 6 条另要 20 次的 P50/P95。脚本**没有 `--model-name` 参数**（POST body 只带 `commit_hash`），要测单个模型就构造只含该 `.pkl` + 对应 `feature_order.txt` 的单模型 `MODEL_DIR` 起服务
- **自测**：`security_cases.py` 与 `perf_loop.py` 的每一行结论都必须是脚本真跑出来的，且脚本自己能在假数据上复现（回归测试不依赖外部服务）

## 4. 原则（做取舍时按这个顺序）

1. **不静默通过。** 检查项不可用、库为空、外部依赖缺失，一律判 FAIL 并让退出码变 1；跳过就等于纵容。
2. **fail closed。** 令牌没配、模型目录缺失这类配置问题，宁可 50000 拒绝，也不许"先跑起来再说"。
3. **不吞异常。** 宽泛捕获必须写明理由并加 `# noqa: BLE001`，且要打印后 `continue`，不许静默 return。
4. **性能结论先拆环节。** 单次耗时拆成 推理 / 解释 / 序列化 三段再下判断（D-14 就是拆完才发现慢在 SHAP 而不是 `predict_proba`）。
5. **证据可复现。** 每个"已验证"都要给命令 + 输出片段；改完的 bug 要补一条不需要外部服务的回归测试。
6. **实测数字只追加、不改写。** 结论过期就在原文件加"补记"行并指向新证据，不回头改当时测出的数；作废的旧证据文首标「历史，不作为现行口径」。
7. **权威只有一份。** 同一事实别处只指路（§0.2 的"指针"），复述正文超过 3 行就是造了第二份口径。

## 5. 签字权

- `backend/**` 的实现类改动
- 接口实现层与契约不一致时的"实现侧复议"（契约本身仍需苏哲勋改）

## 6. 现阶段待办（滚动，2026-10-24 晚）

**已完成（原待办那条已过期）**：`#113` 的 `mask_result` 作用域问题已按苏哲勋推荐的第二种改法落地 —— 掩码探测提为模块级 `probe_mask() -> (ok, detail, body)`、`main()` 持有返回值，并补 4 条 monkeypatch 回归（500/50000 → PASS 且 rc=0；404 → FAIL 且 rc=1；库空 → FAIL 且 rc=1；不传 `--mask-url` → 未测且 rc=0、悬空引用不回潮），在 `backend/tests/test_security_cases_script.py`，不依赖外部服务。**已合入 main `655b487`，CI 绿，描述里的修前证据已换成修后真实输出。**

**在办**：

| # | 事项 | 状态 / 卡点 |
|---|---|---|
| 1 | main 的 CI 红在 `Lint Python`（`infra/pr_auto_review.py:47` TRY004，#89 引入） | 已开 **Issue #126** 报 infra 线；**不代改**。它红着，§0 第 1 条谁都做不到；main 转绿后我重跑 #120 并回填 |
| 2 | `#120`：联调记录补三线产物灌库兼容实测 + §0 口径指针 + 验收库/联调库区分 | 已同步 main（head `ec63419`，净差异 1 文件 6 行），等复审 |
| 3 | MySQL 真库验收（`#100` tasks 3.x、`acceptance.md` 第 1/6 条） | 卡在 **Issue #121**：`jit` 账号无 `CREATE DATABASE`，等 infra 建 `jit_schema_probe` / `jit_orm_probe` 两个隔离空库并授权。验证脚本已备好（schema.sql 连跑两次 + `app.db init` + 两边 `_assert_indexes` + 两路径 DDL 等价 + 4×ingest×2 幂等 + 四接口 + 同哈希两次只留一行 + 20/100 次压测），授权到手即可跑；**在此之前不用 SQLite 结果冒充真库验收** |
| 4 | D-14 落地后的后端侧收尾（等 `#124` 合入） | ① 用登记口径 `perf_loop.py --n 100` + 单模型 `MODEL_DIR` 复测收敛后 `rf_v1`，数字作为补记落 `perf-2026-10-24.md`；② 两份旧压测证据的横幅补 §0.2「历史，不作为现行口径」原文并把 rf 措辞翻成收敛后状态；③ 修 `predict-real-models-2026-10-16.md:970` 那条仍指向作废文件的旧指针。**等 #124 合入再动**，否则会引用尚未进 main 的文件（悬空引用，`check_spec_references.py links` 会拦） |
| 5 | 换权重对已入库 `prediction` 行的可比性 | 已在 `#124` 提为非阻断建议 3：`model_name` 仍是 `rf_v1` 但权重变了，旧行与新输出不可比且会被 upsert 静默覆盖；建议在 D-14 行与 `non-functional.md` §5.2 明写"2026-10-24 起 `rf_v1` = 收敛版权重"，或重灌演示库 |

**不属我、我不代做**：`data_model/**` 的重训与报告（蒋励）、`frontend/**` 的 T-FE-01/02 用例（刘帅华）、`infra/**` 的 CI 与授权（苏哲勋）。
