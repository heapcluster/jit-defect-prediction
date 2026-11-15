# 集成接口测试报告（2026-11-15 复跑）

> 被测：`2734c1b`（main）。本轮**只跑了测试**，没有改 `backend/app`、`frontend/src` 业务代码；唯一改动是 `backend/scripts/system_exceptions.py` 的「空库」场景前置（见 §7），属测试脚本自身缺陷修复。
>
> 环境：本机 Windows 11，conda `jit-defect-prediction`（Python 3.12.14），MySQL 8.0 `jit_demo`（起始 25,404 提交 / 629,958 预测），后端 `uvicorn app.main:app` @127.0.0.1:8000（8 个 expert 模型在册，同步后加载到 9 个），前端 `vite` @5173。
>
> 结果：**34 / 35 通过，1 条失败**；端点覆盖 **11 / 11**。失败项已复现并定位到根因（`/api/figures` 的图集文件不在仓库里），登记为 BUG-02，不是用例写错。

## 1 · 结论速览

| 指标 | 实测 |
|---|---|
| 接口覆盖率 | **11/11 = 100%**（运行时 `/openapi.json` 与 `docs/api/` 对得上） |
| 用例数 / 通过 / 失败 | 35 / 34 / 1 |
| 四类场景 | 带参数的 9 个端点四类齐全；`/api/health`、`/api/health/live`、`/api/health/ready` 无查询参数，「非法参数」不适用，用「缺令牌 + 无参数幂等」替代 |
| 跨模块链路 | 1 条：`POST /api/predict` → 落库 → 详情读回 → 列表读回，三处风险值一致（`0.97637`） |
| 并发场景 | 1 条：两客户端同时 `POST /api/sync` → 一个 200、一个 500，状态不串扰 |
| 前后端联调留痕 | 13 条真实请求/响应包络（[`execution_records/2026-11-15-linkage.md`](execution_records/2026-11-15-linkage.md)） |
| 浏览器侧取证 | 5 张页面截图 + 缺陷态 1 张 + 补齐图集后复验 1 张（[`../system_test/execution_records/`](../system_test/execution_records/)） |

## 2 · 复现

```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000   # 另开终端；需 backend/.env 已配好
python scripts/integration_cases.py --json out.json           # 35 条，本轮 34 通过 1 失败
python scripts/security_cases.py                              # 18/18
python scripts/perf_loop.py                                   # 单客户端 100 次
python scripts/load_test.py --users 10 --requests 10          # 并发负载
python scripts/linkage_capture.py                             # 联调包络留痕
python scripts/online_models_matrix.py                        # 25 模型在线矩阵
python scripts/acceptance_scenarios.py                        # 验收可自动判定子集
```

前置数据：`jit_demo` 里的 25,404 条提交与 629,958 条预测来自此前的同步与 `data_init.sql`；本轮 `POST /api/sync` 又追加了 10 条（→ 25,414 / 630,038），数字在报告里区分了「同步前 / 同步后」。

> 另需注意：干净检出缺 `backend/static/` 目录会导致 `app.main` 导入失败、服务起不来（BUG-01）。本轮先手工建了该目录才跑通。

## 3 · 逐条结果

来源列：用例由 AI 依据 [`endpoint_inventory.md`](endpoint_inventory.md) §2 生成（`[AI生成]`），核心业务断言（概率区间、14 维列序、鉴权码、排序、空结果语义）按代码逐条对照过；逐条人工签署记录仍缺。

| 编号 | 端点 | 场景 | 来源 | 结果 | 关键实测 |
|---|---|---|---|---|---|
| T-IN-01 | `GET /api/commits` | 正常 | [AI生成] | PASS | total=25207 items=5 降序 OK |
| T-IN-02 | `GET /api/commits` | 缺参 | [AI生成] | PASS | 401/40100 文案 OK |
| T-IN-03 | `GET /api/commits` | 非法参数 | [AI生成] | PASS | 类型 / 枚举 / 时间三类非法入参均 40001 |
| T-IN-04 | `GET /api/commits` | 边界值 | [AI生成] | PASS | size 1/100/101、page 0、q 64/65、超末页 OK |
| T-IN-05 | `GET /api/commits/{commit_hash}` | 正常 | [AI生成] | PASS | 3f166232 risk=0.9993，explanation 14 项 |
| T-IN-06 | `GET /api/commits/{commit_hash}` | 缺参 | [AI生成] | PASS | 缺失令牌 401/40100 |
| T-IN-07 | `GET /api/commits/{commit_hash}` | 非法参数 | [AI生成] | PASS | 39/41 位与非十六进制均 40001 |
| T-IN-08 | `GET /api/commits/{commit_hash}` | 边界值 | [AI生成] | PASS | 大小写一致、`model_name` 与列表对齐、未知 hash 40400 |
| T-IN-09 | `GET /api/models` | 正常 | [AI生成] | PASS | 线 = expert/semantic/fused/e2e，共 25 个模型 |
| T-IN-10 | `GET /api/models` | 缺参 | [AI生成] | PASS | 缺失令牌 401/40100 |
| T-IN-11 | `GET /api/models` | 非法参数 | [AI生成] | PASS | 大小写 / 空串 / 未知线均 40001 |
| T-IN-12 | `GET /api/models` | 边界值 | [AI生成] | PASS | `line` 过滤生效：e2e=1、expert=8 |
| T-IN-13 | `POST /api/predict` | 正常 | [AI生成] | PASS | et_v1 risk=0.97637，14 维列序与 `config.FEATURE_COLUMNS` 一致 |
| T-IN-14 | `POST /api/predict` | 缺参 | [AI生成] | PASS | 空 body / 缺字段 40001，缺令牌 40100 |
| T-IN-15 | `POST /api/predict` | 非法参数 | [AI生成] | PASS | 短 hash 与未知模型 40001 |
| T-IN-16 | `POST /api/predict` | 边界值 | [AI生成] | PASS | 同 hash 同模型幂等；semantic 模型本轮返回 200/0（语义向量已就位，与 11-12 的 40001 不同） |
| T-IN-17 | `GET /api/sync/status` | 正常 | [AI生成] | PASS | running=False，total/done 均为 0 |
| T-IN-18 | `GET /api/sync/status` | 缺参 | [AI生成] | PASS | 缺失令牌 401/40100 |
| T-IN-19 | `POST /api/sync` | 非法参数 | [AI生成] | PASS | 未知线 / 非法时间 40001，缺令牌 40100 |
| T-IN-20 | `POST /api/sync` | 正常 | [AI生成] | PASS | accepted 且跑到完结：mode=manual scope=latest done=10/10，耗时 401.7s |
| T-IN-21 | `POST /api/sync` | 边界值 | [AI生成] | PASS | 并发两次 → 200 / 500；用例判据是「状态不串扰」，这一点成立（但 500 本身另登记 BUG-03） |
| T-IN-22 | `GET /api/trends` | 正常 | [AI生成] | PASS | 周粒度 221 个周期 |
| T-IN-23 | `GET /api/trends` | 缺参 | [AI生成] | PASS | 缺失令牌 401/40100 |
| T-IN-24 | `GET /api/trends` | 非法参数 | [AI生成] | PASS | 非法粒度 / 时间 40001 |
| T-IN-25 | `GET /api/trends` | 边界值 | [AI生成] | PASS | 未知模型返回空 series（非 404）；月粒度 53 个周期 |
| T-IN-26 | `GET /api/figures` | 正常 | [AI生成] | PASS | et_v1 图 6 张，顺序符合 `_FIGURE_ORDER` |
| T-IN-27 | `GET /api/figures` | 缺参 | [AI生成] | PASS | 缺 `model_name` 40001、缺令牌 40100 |
| T-IN-28 | `GET /api/figures` | 非法参数 | [AI生成] | PASS | 空串 40001 且文案明确 |
| T-IN-29 | `GET /api/figures` | 边界值 | [AI生成] | **FAIL** | 元数据 6 条齐全，但 `/static/figures/expert/et_v1/*.png` 带正确令牌仍 404（BUG-02）；补齐生成物后复测 200/`image/png` |
| T-IN-30 | `GET /api/health` | 正常 | [AI生成] | PASS | status=ok db=up models=9 commits=25414 |
| T-IN-31 | `GET /api/health` | 缺参 | [AI生成] | PASS | 缺失令牌 401/40100 |
| T-IN-32 | `GET /api/health/live` | 正常 | [AI生成] | PASS | live 恒 ok（不碰 DB） |
| T-IN-33 | `GET /api/health/ready` | 正常 | [AI生成] | PASS | status=ok db=up models=9 |
| T-IN-34 | `GET /api/health/ready` | 缺参 | [AI生成] | PASS | 缺失令牌 401/40100 |
| T-IN-35 | 链路：同步 → 特征 → 预测 → 落库 → 查询 | 正常 | [AI生成] | PASS | 3f166232/et_v1 预测 0.97637 = 详情 = 列表 |

## 4 · 失败项分析（T-IN-29）

复现很干脆：

```bash
curl -s -H "X-API-Key: $API_TOKEN" "http://127.0.0.1:8000/api/figures?model_name=et_v1"
# → 200，data.figures 6 条，file_path 形如 /static/figures/expert/et_v1/roc.png
curl -s -o /dev/null -w "%{http_code}\n" -H "X-API-Key: $API_TOKEN" \
     "http://127.0.0.1:8000/static/figures/expert/et_v1/roc.png"
# → 404（响应体是 {"detail":"Not Found"}，还没走统一错误包络）
```

- 不带令牌请求同一路径是 401（鉴权中间件生效），带令牌是 404——说明**鉴权没问题，是文件不存在**。
- 根因：图集 PNG 属模型线生成物，`backend/static/figures/` 不入版本控制；`model_figure` 表里却有 6 条记录，于是接口返回了指向空气的路径。前端「模型性能看板」抽屉因此显示「图片加载失败：404」，6 张图全裂（截图：[`model-performance-drawer-404-2026-11-15.png`](../system_test/execution_records/model-performance-drawer-404-2026-11-15.png)，浏览器控制台 6 条 404）。
- 影响面：模型性能页的核心可视化不可用；因为指标数值走 `model_metrics.csv`，数字还能看，容易误判为「页面正常」。
- 已做的验证：模型线其实早就把图生成到了 `pipelines/{line}/reports/figs_by_model/`（expert 48、semantic 40、fused 40、e2e 5，共 133 张 PNG），只是没人拷到 `backend/static/figures/`。把这些文件补过去后同一路径立刻 200（`image/png`，40KB 左右），抽屉 6 张图全部渲染。**代码没问题，缺的是交付流程的最后一步搬运。**
- 修法二选一：把「生成 + 拷贝到 static」固化进部署流程（并在 README 写明），或在文件缺失时不返回 `file_path` 而给出降级提示。

## 5 · 前后端联调留痕

`linkage_capture.py` 逐端点记录真实请求与响应包络，输出 [`execution_records/2026-11-15-linkage.md`](execution_records/2026-11-15-linkage.md) 与 `.json`（87KB，含响应 SHA256，可用于比对契约是否漂移）。

| 端点 | 状态 | 响应顶层字段 |
|---|---|---|
| `GET /api/commits` | 200/0 | items, page, size, total |
| `GET /api/commits/{hash}` | 200/0 | author_name, commit_hash, committed_at, explanation, features, fix_references |
| `GET /api/models` | 200/0 | lines |
| `GET /api/trends` | 200/0 | granularity, model_name, series |
| `GET /api/figures` | 200/0 | figures, line, metrics, model_name |
| `GET /api/sync/status` | 200/0 | current_hash, done, last_error, mode, running, scope |
| `GET /api/health` | 200/0 | commit_count, db, last_sync_at, model_names, models_loaded, prediction_count |
| `GET /api/health/live` | 200/0 | server_time, status |
| `GET /api/health/ready` | 200/0 | db, models_loaded, server_time, status |
| `POST /api/predict` | 200/0 | commit_hash, explanation, features, model_name, predicted_at, risk_score |
| `POST /api/predict`（缺字段） | 400/40001 | null |
| `GET /api/commits`（`size=101`） | 400/40001 | null |

浏览器侧：风险列表、趋势看板、模型性能、提交详情、404 兜底页均正常渲染（Chromium 151 headless，1440×900），列表 20 行/页、降序、`高风险 99.9%` 与接口一致；趋势页 canvas 1350×360 正常绘制，汇总卡显示 25,217 条区间提交、3,226 高风险。

## 6 · 与文档的偏差（本轮实测）

| 编号 | 偏差 | 现状 |
|---|---|---|
| D-03 | `POST /api/predict` 传多余字段仍 200（Pydantic 忽略未知字段），与 `docs/api/predict.md`「非法请求体 40001」不符 | 未修；#220 已关闭，由 #228 承接 |
| D-06 | `sync/status.started_at` 输出不带 `Z`，其余接口时间带 `Z` | 未修；#220 已关闭，由 #228 承接 |
| 新增 | `README.md` §二 第 5 步把 `GET /api/health` 写成「公开的」，实际三条健康探针都要求 `X-API-Key`（`docs/api/health.md` 与实现一致，README 写反了） | 登记 BUG-05（文档缺陷） |
| 新增 | 并发 `POST /api/sync` 用 HTTP 500 + `internal error` 表达「已有同步在跑」 | 登记 BUG-03 |

## 7 · 系统侧异常与空库（本轮补测）

`system_exceptions.py --scenario all` 现在 **13/13 通过**（证据：[`execution_records/2026-11-15-system-exceptions.md`](execution_records/2026-11-15-system-exceptions.md)）。

第一次跑是 12/13：`空库 / 健康检查` 报 `db=up commits=4 predictions=3`。查下来不是被测系统的毛病，而是脚本自己假设 `jit_test` 是空的——只要当天先跑过 pytest，`conftest` 的种子数据（4 提交 / 3 预测）还在，这条必然红。已给脚本加 `clear_test_db()`，进场景前先清五表，再起独立 uvicorn 子进程；复跑后 4/4 绿、整轮 13/13。

| 场景 | 断言 | 实测 |
|---|---|---|
| 缺权重 | health 降级 | `status=degraded db=up models_loaded=0` |
| 缺权重 | predict 明确拒绝 | 400/40001「该模型暂无在线权重…」，无堆栈泄漏 |
| 缺权重 | 模型清单仍可读 | 200（清单来自 catalog，不等于可用） |
| 空库 | health | `commits=0 predictions=0` |
| 空库 | 列表 / 趋势 | `code=0`，`total=0`，`series=0` |
| 空库 | 图集 | 404/40400 |
| 失败恢复 | 重启后 | `status=ok`，`running=False`，`last_error=None`，可再预测 200 |

## 8 · 25 模型在线矩阵

`online_models_matrix.py` 逐个 `POST /api/predict`，本轮 **23 通过 / 2 失败**：

- 通过的 23 个覆盖 expert（8）、semantic（7）、fused（7）、e2e（1，`codebert_e2e_v1` 首跑 62.3s，之后命中缓存）；
- 失败的仍是 `tabnet_semantic_v1`、`tabnet_fused_v1`：`RuntimeError: Attempting to deserialize object on a CUDA device but torch.cuda.is_available() is False`（#222）。

顺带一个观察：`#217`、`#218`（语义表 / e2e 文本表未按布局生成）本轮**不再复现**——semantic / fused / e2e 预测全部返回 200，两张输入表已在 `pipelines/*/data` 就位。这两单已关闭，剩余风险（新同步提交不生成向量/文本）由 [#226](https://github.com/heapcluster/jit-defect-prediction/issues/226) 跟踪。

## 9 · 与文档偏差之外的两点注意

- `POST /api/sync` 真实同步 10 条提交耗时 **401.7s**（约 40s/条），这是特征抽取的冷路径成本，不是接口超时；前端轮询期间页面能正常切换（进度跨页保持已验证）。
- 25 模型里 2 个不可用、1 个 e2e 首跑 62s，意味着「25 模型在线」这句承诺目前只能算 92% 兑现，验收里必须写明。

## 10 · 用例来源与 AI/手写比例

| 项 | 数值 |
|---|---:|
| 用例总数 | 35 |
| `[AI生成]` | 35 |
| `[AI生成-人工修改]` | 0 |
| `[手写]` | 0 |
| 通过 / 失败 / 跳过 | 34 / 1 / 0 |
| 端点覆盖 | 11 / 11 = 100% |
| AI 用例采纳率 | 100% |

**如实申报**：采纳率 100% 落在「>90% 视为盲目采纳」的口径里，扣 2 分风险；AI-R3 的逐条审核记录仍缺。整改方向是人工复核后把确有修改的用例改标 `[AI生成-人工修改]`、核心断言完全自己写过的改标 `[手写]`，把采纳率拉回 40%–70%。

提示词归档在 [`prompts/`](prompts/)；本轮新增的提示词与执行说明见 `prompts/integration_rerun_02.md`。
