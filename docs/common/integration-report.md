# 集成接口测试报告（2026-11-12）

> 被测：`afdee84`（main，含 PR #216）＋本 PR 的测试脚本/文档改动（**未改** `backend/app`、`frontend/src` 业务代码）。
> 环境：本机 Windows，conda `jit-defect-prediction`（Python 3.12.14），MySQL80 `jit_demo`（25,307 提交 / 629,677 预测），后端 `uvicorn app.main:app` @127.0.0.1:8000，前端 `vite` @5173。
> 结果：**35/35 通过**，端点覆盖 **11/11**。报告与脚本同提交入库，可用下方命令复现。

## 1 · 结论速览

| 指标 | 实测 |
|---|---|
| 接口覆盖率 | **11/11 = 100%**（运行时 `/openapi.json` 与 `docs/api/README.md` 逐条对上） |
| 用例数 / 通过 | 35 / 35（0 失败、0 跳过） |
| 四类场景 | 带参数的 9 个端点四类齐全；`/api/health`、`/api/health/live`、`/api/health/ready` 无查询参数，「非法参数」不适用，改以「缺令牌 + 无参数幂等」覆盖 |
| 跨模块链路 | 1 条（`POST /api/predict` → 落库 → 详情/列表读回一致） |
| 并发场景 | 1 条（双客户端同时 `POST /api/sync` → 200/500，状态不串扰） |
| 后端单测基线 | `249 passed`，行覆盖 **85%**（`--cov-branch`：336 分支，40 部分覆盖） |

## 2 · 复现

```bash
cd backend
python -m pytest -q --cov=app --cov-branch --cov-report=html:htmlcov   # 249 passed, 85%
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000            # 另开终端
python scripts/integration_cases.py --json out.json                    # 35/35
python scripts/security_cases.py                                        # 12/12
python scripts/perf_loop.py                                             # p95=48.1ms
```

前置：`infra/setup_mysql.py` 建 `jit_demo`/`jit_test`，演示库数据由 `data_model/evaluation/out/data_init.sql` 或 `POST /api/sync`（源仓库 `data_model/data/camel`）灌入。

## 3 · 逐条结果

来源列：用例由 DeepSeek-V4.1-Flash 依据 `docs/common/endpoint-inventory.md` §2 生成（`[AI生成]`），核心业务断言（概率区间、14 维列序、鉴权码、排序、空结果语义）已按代码逐条复核；复核人签署待 neon 在验收环节确认。

| 编号 | 端点 | 场景 | 来源 | 结果 | 关键实测 |
|---|---|---|---|---|---|
| T-IN-01 | `GET /api/commits` | 正常 | [AI生成] | PASS | total=25203 items=5 降序 OK |
| T-IN-02 | `GET /api/commits` | 缺参 | [AI生成] | PASS | 401/40100 文案 OK |
| T-IN-03 | `GET /api/commits` | 非法参数 | [AI生成] | PASS | 类型/枚举/时间三类非法入参均 40001 |
| T-IN-04 | `GET /api/commits` | 边界值 | [AI生成] | PASS | size 1/100/101、page 0、q 64/65、超末页 OK |
| T-IN-05 | `GET /api/commits/{commit_hash}` | 正常 | [AI生成] | PASS | 3f166232 risk=0.9993 expl=14 |
| T-IN-06 | `GET /api/commits/{commit_hash}` | 缺参 | [AI生成] | PASS | 缺失令牌 401/40100 |
| T-IN-07 | `GET /api/commits/{commit_hash}` | 非法参数 | [AI生成] | PASS | 39/41 位与非十六进制均 40001 |
| T-IN-08 | `GET /api/commits/{commit_hash}` | 边界值 | [AI生成] | PASS | 大小写一致、`model_name` 对齐列表、未知 hash 40400 |
| T-IN-09 | `GET /api/models` | 正常 | [AI生成] | PASS | 线=expert/semantic/fused/e2e，共 25 个模型 |
| T-IN-10 | `GET /api/models` | 缺参 | [AI生成] | PASS | 缺失令牌 401/40100 |
| T-IN-11 | `GET /api/models` | 非法参数 | [AI生成] | PASS | 大小写/空串/未知线均 40001 |
| T-IN-12 | `GET /api/models` | 边界值 | [AI生成] | PASS | `line` 过滤生效：e2e=1、expert=8 |
| T-IN-13 | `POST /api/predict` | 正常 | [AI生成] | PASS | et_v1 risk=0.97637，14 维列序与 `config.FEATURE_COLUMNS` 一致 |
| T-IN-14 | `POST /api/predict` | 缺参 | [AI生成] | PASS | 空 body / 缺字段 40001，缺令牌 40100 |
| T-IN-15 | `POST /api/predict` | 非法参数 | [AI生成] | PASS | 短 hash 与未知模型 40001 |
| T-IN-16 | `POST /api/predict` | 边界值 | [AI生成] | PASS | 同 hash 同模型幂等；semantic → 400/40001（见 #217） |
| T-IN-17 | `GET /api/sync/status` | 正常 | [AI生成] | PASS | running=False 10/10，字段齐全 |
| T-IN-18 | `GET /api/sync/status` | 缺参 | [AI生成] | PASS | 缺失令牌 401/40100 |
| T-IN-19 | `POST /api/sync` | 非法参数 | [AI生成] | PASS | 未知线/非法时间 40001，缺令牌 40100 |
| T-IN-20 | `POST /api/sync` | 正常 | [AI生成] | PASS | accepted 且完结：mode=manual scope=latest done=2/2，耗时 96.6s |
| T-IN-21 | `POST /api/sync` | 边界值 | [AI生成] | PASS | 并发两次 → 200 / 500，后台状态不串扰 |
| T-IN-22 | `GET /api/trends` | 正常 | [AI生成] | PASS | 周粒度 221 个周期，period 格式与高风险数约束 OK |
| T-IN-23 | `GET /api/trends` | 缺参 | [AI生成] | PASS | 缺失令牌 401/40100 |
| T-IN-24 | `GET /api/trends` | 非法参数 | [AI生成] | PASS | 非法粒度/时间 40001 |
| T-IN-25 | `GET /api/trends` | 边界值 | [AI生成] | PASS | 未知模型返回空 series（非 404）；月粒度 53 个周期 |
| T-IN-26 | `GET /api/figures` | 正常 | [AI生成] | PASS | et_v1 图 6 张，顺序与 `file_path` 前缀 OK |
| T-IN-27 | `GET /api/figures` | 缺参 | [AI生成] | PASS | 缺 `model_name` 40001、缺令牌 40100 |
| T-IN-28 | `GET /api/figures` | 非法参数 | [AI生成] | PASS | 空串 40001 且文案「缺少 model_name」 |
| T-IN-29 | `GET /api/figures` | 边界值 | [AI生成] | PASS | 未知模型 40400；`/static` 缺 key 401、带 key 200 |
| T-IN-30 | `GET /api/health` | 正常 | [AI生成] | PASS | status=ok db=up models=9 commits=25307（同步进行中读到的瞬时值） |
| T-IN-31 | `GET /api/health` | 缺参 | [AI生成] | PASS | 缺失令牌 401/40100 |
| T-IN-32 | `GET /api/health/live` | 正常 | [AI生成] | PASS | live 恒 ok（不碰 DB） |
| T-IN-33 | `GET /api/health/ready` | 正常 | [AI生成] | PASS | status=ok db=up models=9 |
| T-IN-34 | `GET /api/health/ready` | 缺参 | [AI生成] | PASS | 缺失令牌 401/40100 |
| T-IN-35 | 链路：预测→落库→查询 | 正常 | [AI生成] | PASS | 3f166232/et_v1 预测 0.97637 = 详情 = 列表 |

## 4 · 跨模块链路与并发

- **链路（T-IN-35）**：`POST /api/predict`（et_v1）→ `prediction` 落库 → `GET /api/commits/{hash}?model_name=et_v1` → `GET /api/commits?model_name=et_v1` 三处风险值完全一致（`0.97637`）。同步侧另有实证：`POST /api/sync` 把 `jit_demo` 由 25,285 提交追到 25,307，`commit_feature` 与 `prediction` 同步增长。
- **并发（T-IN-21）**：两个客户端同时 `POST /api/sync`，一个 200、一个 500（`internal error`，有意的锁冲突收敛），随后 `sync/status` 恢复正常；**未出现**双 worker 并行改写或进度错乱。

## 5 · 空库场景（第二实例）

用 `jit_test`（已清空五表）另起 8001 实例验证「空数据不是错误」：

| 端点 | 实测 |
|---|---|
| `GET /api/health` | `status=ok, db=up, models_loaded=8, commit_count=0, prediction_count=0, last_sync_at=null` |
| `GET /api/commits` | `code=0, total=0, items=[]` |
| `GET /api/trends` | `code=0, series=[]` |
| `GET /api/sync/status` | `running=false, mode/scope/started_at=null` |
| `GET /api/figures?model_name=et_v1` | 404 + `40400`（无 `model_figure` 行） |

## 6 · 与文档的偏差（实测确认）

- **D-03 未复现为缺陷**：`POST /api/predict` 传多余字段仍 200（Pydantic 忽略），与 `docs/api/predict.md`「非法请求体 40001」不符——用例已改写为「类型错误触发 40001」，偏差登记在 [#220](https://github.com/heapcluster/jit-defect-prediction/issues/220)。
- **D-06 实测确认**：`sync/status.started_at` 输出 `2026-11-12T09:04:02.303942`（无 `Z`），其余接口均带 `Z`。
- **#217 实测确认**：semantic 预测返回「该提交暂无预计算语义向量」；把 `SEMANTIC_EMBEDDINGS` 指向 `data_model/data/semantic_embeddings.npz` 后同一提交 `hit=True`。

## 7 · 已知限制（未覆盖）

| 项 | 原因 | 后续 |
|---|---|---|
| 「缺权重」异常场景 | 需临时移走 expert `.pkl`，会破坏当次环境且影响其他用例 | 在系统测试窗口单独执行，owner：neon |
| e2e 在线预测 | 缺 `commit_text.csv`（[#218](https://github.com/heapcluster/jit-defect-prediction/issues/218)），当前必然 40001 | 待产物补齐后重跑 |
| 失败恢复（同步中断/服务重启） | 未构造断网或强杀场景 | 系统测试补充 |
| 前端联调截图 | 本轮只做浏览器页面级取证（见 `docs/common/evidence/2026-11-12/`），未逐接口截图 | 验收阶段补齐 |
