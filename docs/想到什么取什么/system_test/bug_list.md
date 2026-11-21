# Bug 清单（缺陷台账）

> **职责边界**：测试方负责发现、复现、写清五要素并提交 issue，**不负责修复**；修复归模块 owner，口径裁定归评审，验收结论归人工。规则见 [`../README.md` §8](../README.md#8-缺陷处理边界)。
>
> **真源**：GitHub Issue 是唯一动态真源；本文件是 `2734c1b`（2026-11-15）的**快照 + 证据索引**，两边冲突以 issue 为准。
>
> **issue 提交状态**：2026-11-15 已用仓库身份（`jolly326`）通过 GitHub API 提交 4 条新单（#239、#240、#241、#242），并对 8 条历史单发出更新评论、修正 #229 标题。

## 1 · 缺陷台账（含来源与证据）

> 列口径对齐 [`../../common/test/test-assessment-guide.md`](../../common/test/test-assessment-guide.md) §4.3：Bug ID、标题、严重级别、复现步骤、预期/实际结果、截图、状态、来源。
> 来源标签：`[AI生成-人工修改]` = AI 整理台账，测试人员实测复现并确认。

| Bug ID | 标题 | 级别 | 复现步骤（要点） | 预期结果 | 实际结果 | 截图 / 证据 | 状态 | 来源 |
|---|---|---|---|---|---|---|---|---|
| BUG-01 | 干净检出缺 `backend/static/`，`app.main` 导入即失败 | 严重 | 全新 clone → `cd backend` → `python -m uvicorn app.main:app` 或 `python -m pytest -q` | 干净检出即可启动/收集，无需人工建目录 | 进程退出；pytest collection error，一条用例都收集不到 | 终端输出（见 §2 BUG-01）；[#239](https://github.com/heapcluster/jit-defect-prediction/issues/239) | open · 已随 #244 修复代码，待回归 | [AI生成-人工修改] |
| BUG-02 | `/api/figures` 图路径无实体文件，`/static` 带令牌 404 | 严重 | ① 取 `GET /api/figures?model_name=et_v1` 元数据 ② 带同一 `X-API-Key` 取图 ③ 页面 `/model-performance` → 专家特征 → `et_v1` → 查看 | 图文件存在并返回 `200 image/png`；缺失时应降级而非返回不可用路径 | 404，响应体 `{"detail":"Not Found"}`，未走统一包络；指标数字正常易误判 | [`model-performance-drawer-404-2026-11-15.png`](execution_records/model-performance-drawer-404-2026-11-15.png)、[`...-fixed-2026-11-15.png`](execution_records/model-performance-drawer-fixed-2026-11-15.png)；[#240](https://github.com/heapcluster/jit-defect-prediction/issues/240) | open · 技术验证通过（补 133 张后 6/6 渲染），交付流程未固化 | [AI生成-人工修改] |
| BUG-03 | 并发同步第二个请求返回 500 `internal error` | 一般 | 服务空闲时双线程同时 `POST /api/sync` | 返回可解释冲突（409 或 40001 + 「同步进行中」） | 一个 200，一个 `500 {"code":50000,"message":"internal error"}` | [`../integration_test/report.md`](../integration_test/report.md) T-IN-21；[#241](https://github.com/heapcluster/jit-defect-prediction/issues/241) | open · 待裁定 | [AI生成-人工修改] |
| BUG-04 | tabnet 权重加载失败被包装成「参数非法 40001」 | 一般 | `POST /api/predict` 指定 `tabnet_semantic_v1` / `tabnet_fused_v1` | 归为服务端/环境问题（5xx 或专用码），文案写明权重不可用 | 400 + `40001`「参数非法：…模型权重无法加载」，调用方误以为自己传错参数 | [`../integration_test/report.md`](../integration_test/report.md) T-IN-29；并入 [#222](https://github.com/heapcluster/jit-defect-prediction/issues/222) | 已并入 #222 · 未修 | [AI生成-人工修改] |
| BUG-05 | README 称 `GET /api/health` 公开，实际需鉴权 | 轻微 | `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/api/health` → 401；加 header → 200 | README 与 `docs/api/health.md`、实现三者一致 | README 写"公开"，`docs/api/health.md:20` 明确要求 `X-API-Key` | 命令输出；[#242](https://github.com/heapcluster/jit-defect-prediction/issues/242) | open · 未修 | [AI生成-人工修改] |
| BUG-06 | `system_exceptions.py` 空库场景依赖测试库恰好为空 | 一般 | `cd backend && pytest -q` → `python scripts/system_exceptions.py --scenario empty-db` | 空库场景稳定通过 | 断言 `commit_count == 0` 失败（conftest 种子残留，实测 `commits=4 predictions=3`） | [`../integration_test/execution_records/2026-11-15-system-exceptions.md`](../integration_test/execution_records/2026-11-15-system-exceptions.md) | **已修复并回归**（4/4、13/13） | [AI生成-人工修改] |
| #222 | 两个 tabnet 权重绑定 CUDA，CPU 加载失败 | 严重 | CPU 环境 `POST /api/predict` 指定 `tabnet_semantic_v1` / `tabnet_fused_v1` | 25 模型在 CPU 全部可加载 | 抛 `Attempting to deserialize object on a CUDA device but torch.cuda.is_available() is False`；25 模型实际 23/25 | 命令输出；[#222](https://github.com/heapcluster/jit-defect-prediction/issues/222) | open · 待修复 | [AI生成-人工修改] |
| #226 | 新同步提交缺语义向量 / e2e 文本，非 expert 线 40001 | 严重 | 同步一条新提交 → 用 semantic / fused / e2e 模型预测 | 任意提交 × 25 模型均可预测 | 新提交不在预计算表内，非 expert 线返回 40001 | [`../integration_test/report.md`](../integration_test/report.md)；[#226](https://github.com/heapcluster/jit-defect-prediction/issues/226) | open · 待修复（承接 #217、#218） | [AI生成-人工修改] |
| #227 | `.env` 失效代理劫持本地请求 + 前端单测 loading 告警 | 一般 | 配了 `HTTP_PROXY` 且未设 `NO_PROXY` 时请求本机 8000；`npm run test:unit` 看告警 | 本机请求不受代理影响；单测无 warning | 首次 httpx 得 502，`trust_env=False` 后正常；单测仍有 `v-loading` 告警 | 命令输出；[#227](https://github.com/heapcluster/jit-defect-prediction/issues/227) | open · 待处理（建议拆单） | [AI生成-人工修改] |
| #228 | 契约 / 规格与实现口径不一致（含 #220 剩余项） | 轻微 | 按 `docs/api/` 逐条对照实现：D-03（多余字段静默忽略）、D-06（`started_at` 无 `Z`） | 契约与实现一致 | D-03、D-06 仍复现 | [`../integration_test/report.md`](../integration_test/report.md) §6；[#228](https://github.com/heapcluster/jit-defect-prediction/issues/228) | open · 待裁定 | [AI生成-人工修改] |
| #229 | `openspec/specs` 四个能力目录为空 | 轻微 | 列 `openspec/specs/*` 检查 `spec.md` | 每个能力目录都有 `spec.md` | `feedback`/`observability`/`ops`/`quality` 为空，`ui` 已有 | 目录清单；[#229](https://github.com/heapcluster/jit-defect-prediction/issues/229) | open（描述过时：写「五个」） | [AI生成-人工修改] |
| #230 | 并发压测 p95 波动，20 并发 688.9ms 超判据 | 一般 | `cd backend && python scripts/load_test.py --users 20 --requests 10` | 20 并发 p95 ≤ 判据 | p95 688.9ms 未达标；单客户端 53.3/68.1ms 达标 | [`performance/performance_report.md`](performance/performance_report.md) §2.1；[#230](https://github.com/heapcluster/jit-defect-prediction/issues/230) | open（缺 20 并发数据） | [AI生成-人工修改] |
| #233 | 单元测试依赖真实 MySQL、来源注释与断言质量 | 一般 | `cd backend && python -m pytest -q` 需 `jit_test` 库；查文件头来源标注 | 单测隔离且来源标注齐全 | 已改善：57 文件头按 §2.1 补齐、526 条全绿；核心断言已复核 | [`../unit_test/README.md`](../unit_test/README.md)；[#233](https://github.com/heapcluster/jit-defect-prediction/issues/233) | open · 测试体系类，非产品缺陷 | [AI生成-人工修改] |

**级别分布**：严重 4 / 一般 5 / 轻微 3，合计 12 条（#233 与 BUG-06 属测试体系，不计入产品缺陷数；产品缺陷 10 条，仍满足课程「≥8」的数量线）。

**截图状态**：仅 BUG-02 有可读截图；其余为命令输出，逐条截图待人工补采。

**已关闭但需留意**：#217、#218、#219、#220 均已 closed，但复核后发现：

- #217 / #218 的产物已就位（两张输入表在 `pipelines/*/data`），剩余风险由 **#226** 承接；
- #219 关闭了，但 `backend/Dockerfile` **仍未装 `transformers`**（2026-11-15 核对）；若关闭口径是「容器不承载 e2e」，请在该单写明，否则建议 reopen；
- #220 关闭了，但 D-03（多余字段静默忽略）、D-06（`started_at` 无 `Z`）**本轮仍可复现**，由 **#228** 承接。

## 2 · 缺陷详情（五要素）

### BUG-01 · 干净检出缺 `backend/static/`，服务与测试无法启动

- **现象**：新克隆仓库后 `uvicorn app.main:app` 与 `pytest` 均抛 `RuntimeError: Directory '...\backend\static' does not exist`（`app/main.py:101` 无条件 mount；该目录不入库）。
- **复现步骤**：全新 clone → `cd backend` → `python -m uvicorn app.main:app`（或 `python -m pytest -q`）。必现；建目录后立即恢复（254 passed）。
- **预期结果**：干净检出即可启动/收集，不需要人工建目录。
- **实际结果**：进程退出；pytest collection error，254 条用例一条都收集不到。
- **影响范围**：所有新环境 / CI 全新环境 / 非容器新机器；阻塞四类测试；阻断验收 A-17。
- **证据**：[`../unit_test/README.md`](../unit_test/README.md) §2；[#239](https://github.com/heapcluster/jit-defect-prediction/issues/239)。

### BUG-02 · 图集 6 张全部 404

- **现象**：`GET /api/figures?model_name=et_v1` 返回 6 条 `file_path`，但带正确令牌请求 `/static/figures/expert/et_v1/roc.png` 得 404；前端抽屉提示「图片加载失败：404」，控制台 6 条 404。
- **复现步骤**：① 取元数据；② 带同一 `X-API-Key` 取图；③ 页面 `/model-performance` → 专家特征 → `et_v1` → 查看。必现（`static/figures` 为空时）。
- **预期结果**：图文件存在并返回 `200 image/png`；缺失时应降级而不是返回不可用路径。
- **实际结果**：404（响应体 `{"detail":"Not Found"}`，未走统一包络）；指标数字正常，容易误判页面完好。
- **影响范围**：模型性能页核心可视化；`model_figure` 表与磁盘不一致；干净检出 / 容器内均出现；阻断验收 A-06、A-13。
- **证据**：[`execution_records/model-performance-drawer-404-2026-11-15.png`](execution_records/model-performance-drawer-404-2026-11-15.png)、[`execution_records/model-performance-drawer-fixed-2026-11-15.png`](execution_records/model-performance-drawer-fixed-2026-11-15.png)、[`../integration_test/report.md`](../integration_test/report.md) T-IN-29；[#240](https://github.com/heapcluster/jit-defect-prediction/issues/240)。
- **定位附注（非修复）**：模型线已在 `pipelines/*/reports/figs_by_model/` 生成 133 张 PNG，手工拷入 `backend/static/figures/` 后立即恢复 200，说明缺的是交付步骤。

### BUG-03 · 并发同步返回 500

- **现象**：两客户端同时 `POST /api/sync`，一个 200，一个 `500 {"code":50000,"message":"internal error"}`。
- **复现步骤**：服务空闲时双线程同时打该接口。必现。
- **预期结果**：返回可解释冲突（409 或 40001 + 「同步进行中」）。
- **实际结果**：500 + `internal error`，前端统一显示「服务异常」，用户无法判断是重复点击。
- **影响范围**：`POST /api/sync` 冲突分支；前端刷新按钮交互；`docs/api/sync.md` 与 `sync-api` 规格口径；影响易用性与契约一致性（不阻断验收）。
- **证据**：[`../integration_test/report.md`](../integration_test/report.md) T-IN-21；[#241](https://github.com/heapcluster/jit-defect-prediction/issues/241)。

### BUG-04 · 权重失败被包装成参数错误（并入 #222）

- **现象**：`POST /api/predict` 指定 `tabnet_semantic_v1` / `tabnet_fused_v1` 返回 400 + `40001`「参数非法：…模型权重无法加载」。
- **复现步骤**：同 BUG-02 步骤 ② 换成 predict 接口。必现。
- **预期结果**：归为服务端/环境问题（5xx 或专用码），文案写明权重不可用。
- **实际结果**：40001，调用方误以为自己传错参数。
- **影响范围**：`POST /api/predict` 两个 tabnet；排障方向被带偏。
- **证据**：并入 [#222](https://github.com/heapcluster/jit-defect-prediction/issues/222) 的评论（同 §1 #222 行）。

### BUG-05 · README 健康探针表述错误

- **现象**：按 README §二 第 5 步「先查公开的 `GET /api/health`」执行得 401/40100。
- **复现步骤**：`curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/api/health` → 401；加 header → 200。必现。
- **预期结果**：README 与 `docs/api/health.md`、实现三者一致。
- **实际结果**：README 写"公开"，`docs/api/health.md:20` 明确要求 `X-API-Key`。
- **影响范围**：新同学起步即失败；A-17 不通过的原因之一。
- **证据**：[#242](https://github.com/heapcluster/jit-defect-prediction/issues/242)。

### BUG-06 · 测试脚本空库场景前置缺陷（已修）

- **现象**：`system_exceptions.py --scenario empty-db` 在跑过 pytest 后必然失败，实测 `commits=4 predictions=3`。
- **复现步骤**：`cd backend && pytest -q` → `python scripts/system_exceptions.py --scenario empty-db`。必现。
- **预期结果**：空库场景稳定通过。
- **实际结果**：断言 `commit_count == 0` 失败（conftest 种子残留）。
- **影响范围**：仅测试工具链；会让"系统异常 13/13"的结论不可信。
- **证据**：[`../integration_test/execution_records/2026-11-15-system-exceptions.md`](../integration_test/execution_records/2026-11-15-system-exceptions.md)；已加 `clear_test_db()`，复跑 4/4、13/13。

### #222 · tabnet 权重绑定 CUDA

- 五要素与复测补充见 §1 对应行；本轮 23/25 可用，错误原文为 `Attempting to deserialize object on a CUDA device but torch.cuda.is_available() is False`。
- 影响：25 模型承诺实际 92% 兑现；阻断 A-02。

### #226 · 新同步提交缺语义向量 / e2e 文本

- 五要素见 §1 对应行；老提交四线全通、新同步提交仅 expert 可用。
- 影响：任意提交 × 25 模型不可保证；干净检出/换机后四线全挂；阻断 A-02。

### #227 / #228 / #229 / #230 / #233（质量与体系类）

| Bug ID | 现象（一句话） | 本轮实测 | 影响范围 | 来源 |
|---|---|---|---|---|
| #227 | `.env` 代理劫持本地请求；前端单测 `v-loading` 告警 | 代理：首次 httpx 得 502，`trust_env=False` 后正常；告警：65 passed 仍有 warn | 本地联调脚本、单测输出噪声；不影响线上 | [AI生成-人工修改] |
| #228 | 契约/规格与实现口径不一致 | D-03、D-06 仍复现 | `docs/api/` 可读性、验收 A-18 | [AI生成-人工修改] |
| #229 | 4 个能力目录无 `spec.md` | `feedback`/`observability`/`ops`/`quality` 为空，`ui` 已有 | 验收逐 Scenario 对照缺依据 | [AI生成-人工修改] |
| #230 | 并发压测 p95 波动 | 20 并发 p95 688.9ms 未达标；单客户端 53.3/68.1ms 达标 | 容量结论、部署建议 | [AI生成-人工修改] |
| #233 | 单元测试隔离与来源注释 | 526 passed；57 文件头已按 §2.1 补齐，核心断言已复核 | 课程单元测试维度评分 | [AI生成-人工修改] |

## 3 · 候选观察（不计入缺陷数）

有证据但**是否构成缺陷、级别如何须由人工裁定**，确认前不登记为缺陷。

| # | 观察 | 证据 | 待裁定点 |
|---|---|---|---|
| C-02 | `sync/status.started_at` 无 `Z`（D-06） | [#228](https://github.com/heapcluster/jit-defect-prediction/issues/228) | 改文档还是改实现（已并入 #228） |
| C-03 | `POST /api/predict` 传多余字段仍 200（D-03） | #228 | 是否加 `extra="forbid"`（已并入 #228） |
| C-04 | 模型缺失时规格要求 `50000`，实现为 `40001` | `security_cases.py` 规格偏差提示 | 规格订正或代码回改 |
| C-06 | 前端生产构建单 chunk 2,217 kB（gzip 728 kB） | `npm run build` 输出 | 是否做路由级 code split |
| C-08 | 25 模型 accuracy 0.834~0.864 但 recall ≈0.26 | [`../acceptance_test/model-accuracy-evidence.md`](../acceptance_test/model-accuracy-evidence.md) | 业务可接受性，需人工/产品确认 |
| C-09 | 风险列表进详情再返回，筛选条件丢失 | 本轮浏览器实测（A-14） | 改实现（筛选进 URL / keep-alive）还是改验收标准 |

**已并入既有单、不再单独登记**：C-01（并发 p95 波动 → [#230](https://github.com/heapcluster/jit-defect-prediction/issues/230)）、C-05（空能力目录 → [#229](https://github.com/heapcluster/jit-defect-prediction/issues/229)）、C-07（前端单测 `v-loading` 告警 → [#227](https://github.com/heapcluster/jit-defect-prediction/issues/227)）。

D-01「`features` 条件返回」、语义表「路径写错」、「e2e 无生成脚本」等经复核**不成立**，不再登记（红线：无法复现的 Bug 每条扣 2 分）。

## 4 · 跟踪与闭环

| 项 | 要求 | 当前 | 下一步 |
|---|---|---|---|
| 新单提交 | 4 条（BUG-01/02/03/05） | **已提交** #239 / #240 / #241 / #242 | 等 owner 认领；编号已回填本表 |
| 历史单更新 | 6 条待更新 + 3 组合并说明 | **评论已发出**（#222/#225/#226/#227/#228/#229/#230/#233 + #217/#218/#219/#220），#229 标题已修正 | 等 owner 回复；合并需保留单 owner 确认 |
| 关闭但未修 | #219（Dockerfile 仍缺 `transformers`）、#220（D-03/D-06 仍复现） | 已核对 | 由 owner 决定 reopen 或写明关闭口径 |
| 闭环 | 修复 → 回归 → 关闭 | 1/12（BUG-06） | 修复后按原步骤复跑，回填回归证据 |
| 截图 | 每条缺陷有可读截图 | BUG-02 有；其余为命令输出 | 人工补采 |

> 红线自查：不伪造 Bug、不编造闭环、不为凑数登记；无法复现进候选观察；已关闭但未修的项如实标注，不写成已解决。
