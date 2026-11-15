# 缺陷遗留评估报告

> **撰写说明**：本文档由 AI 依据本轮（`2734c1b`，2026-11-15）实测证据整理，**未经人工签署**。影响评估与修复计划是基于现有证据的草案，责任人与完成时间未承诺。按 AI-R5，涉及「是否接受交付」的判断须人工做出。不编造「已修复」或回归结果。来源：`[AI生成]`。

## 1 · 遗留缺陷清单与影响评估

| Bug ID | 级别 | 标题 | 影响评估 | 修复计划（草案） | 责任模块 | Issue / 状态 |
|---|---|---|---|---|---|---|
| BUG-01 | 严重 | 干净检出缺 `backend/static/` 目录，`app.main` 导入即崩 | **最致命的一条流程缺陷**：新克隆仓库的人按 README 走第一步就 `RuntimeError`，后端起不来、pytest 连用例都收集不到。新人 / CI 全新环境 100% 撞上，本机靠手工建目录绕过 | `create_app()` 里 `config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)`，或提交 `backend/static/figures/.gitkeep`；判据：干净克隆后直接 `pytest -q` 与 `uvicorn` 可用 | 后端 | [#239](https://github.com/heapcluster/jit-defect-prediction/issues/239) open · 未修 |
| BUG-02 | 严重 | `/api/figures` 的 6 条 `file_path` 指向不存在的静态文件，带令牌 404 | 模型性能页的图集区完全不可用（前端提示「图片加载失败：404」）；因为指标数字仍正常，浅测容易误判为没问题。直接导致验收 A-06、A-13 不通过 | 把图集生成固化进部署流程并写进 README；或文件缺失时不返回 `file_path`、给出降级文案。判据：抽屉 6 张图正常渲染 + 回归截图 | 后端 / 交付流程 | [#240](https://github.com/heapcluster/jit-defect-prediction/issues/240) open · **技术验证通过**（补 133 张生成物后 6/6 渲染），交付流程未固化 |
| #222 | 严重 | `tabnet_semantic_v1` / `tabnet_fused_v1` 权重绑定 CUDA | 25 模型实际 23/25；CPU 部署环境下这两个模型不可用，影响「四方案 25 模型在线」承诺与验收 A-02 | 重新导出 CPU 可加载权重；`online_models_matrix.py` 回归至退出码 0 | 模型线 | [#222](https://github.com/heapcluster/jit-defect-prediction/issues/222) open · 未修 |
| #226 | 严重 | 新同步提交缺语义向量 / e2e 文本，非 expert 线 40001 | 「任意提交 × 25 模型」只在输入表覆盖范围内成立；干净检出/换机后四线全挂 | 补两张输入表的生成与交付流程，并为新提交增量生成向量/文本 | 模型线 / 交付流程 | [#226](https://github.com/heapcluster/jit-defect-prediction/issues/226) open · 承接已关闭的 #217、#218 |
| BUG-03 | 一般 | 并发触发同步时第二个请求返回 500 `internal error` | 用户重复点「刷新」会看到「服务异常」，无法分辨是「已有同步在跑」还是真故障，容易反复重试 | 改为 409 或 40001 + 「同步进行中，请稍候」文案；前端据此做禁用态 | 后端 | [#241](https://github.com/heapcluster/jit-defect-prediction/issues/241) open · 待裁定 |
| BUG-04 | 一般 | 权重加载失败被包装成「参数非法」40001 | 调用方会以为自己传错参数；排障时误导方向（真实原因是 CUDA 权重） | 归入 5xx 或专用错误码，文案写明「该模型权重不可用」 | 后端 | 并入 [#222](https://github.com/heapcluster/jit-defect-prediction/issues/222) 评论 · 未修 |
| BUG-06 | 一般 | `system_exceptions.py` 空库场景依赖测试库恰好为空 | 只在测试工具链，产品无影响；但会让系统测试结论不可信（pytest 之后必然红） | 已在脚本内加 `clear_test_db()`，复跑 13/13 | 测试方 | 不开单 · **已修复并回归** |
| BUG-05 | 轻微 | README 把 `GET /api/health` 写成「公开的」 | 按文档操作会拿到 401，浪费时间；`docs/api/health.md` 与实现一致，属文档写反 | 改 README 一句话 | 文档 | [#242](https://github.com/heapcluster/jit-defect-prediction/issues/242) open · 未修 |
| #228 | 轻微 | 契约 / 规格与实现口径不一致（含 #220 剩余项） | 契约可读性下降，验收 A-18 不通过；不影响在线功能 | 逐条裁定「改文档 / 改代码」；D-03、D-06 本轮仍复现 | 文档 / 后端 | [#228](https://github.com/heapcluster/jit-defect-prediction/issues/228) open · 承接已关闭的 #220 |
| #229 | 轻微 | `openspec/specs` 四个能力目录为空 | 验收逐 Scenario 对照缺规格依据 | 补 spec 或删目录并在 changes 说明下线 | 规格 / 文档 | [#229](https://github.com/heapcluster/jit-defect-prediction/issues/229) open（描述过时：写「五个」） |
| #219 | 一般 | `backend/Dockerfile` 未装 `transformers` | 容器内 e2e 必然降级；本机开发路径不受影响 | 补依赖并构建复现，留日志与截图 | 后端 / 工程化 | **已关闭但未修**：2026-11-15 核对 Dockerfile 仍无 `transformers`，需 owner 说明关闭口径或 reopen |
| #217 / #218 | — | 语义表 / e2e 文本表未放到约定路径 | 产物已就位（`pipelines/*/data` 存在），本轮 semantic/fused/e2e 均 200 | 无新增动作；剩余风险由 #226 承接 | 模型线 | 已关闭（合并至 #226） |

**级别分布**：致命 0 / 严重 4 / 一般 4 / 轻微 3，合计 11 条（不含仅测试体系的 BUG-06 与 #233）；已闭环 1 条（BUG-06），已关闭但未修 2 条（#219、#220 剩余项），其余待修。

> 职责边界：测试方只提单与回归，不修代码；修复与口径裁定见 [`../defect-handling.md`](../defect-handling.md)。issue 草稿与更新文本见 [`../issues/`](../issues/)。

## 2 · 课程通过标准对照

| 条件 | 课程要求 | 当前事实 | 判定 |
|---|---|---|---|
| 无致命 / 严重缺陷遗留 | 全部修复并回归 | BUG-01、BUG-02、#222、#226 四条严重缺陷均未修复；BUG-02 只做了技术验证 | **不满足** |
| 一般缺陷遗留 ≤3 | 且有明确修复计划与影响评估 | 4 条一般（#219、BUG-03、BUG-04、BUG-06 已修） | **不满足**（差 1 条） |
| 影响评估与修复计划 | 每条列明责任人与影响范围 | §1 已列；完成时间未承诺 | 部分满足 |
| 文档完整 | 手册 / API / 部署 / 测试交付物齐备 | 用户手册、覆盖率 PDF、逐条验收取证缺 | **不满足** |
| 验收结论 | 明确「通过 / 不通过」 | [`acceptance_report.md`](acceptance_report.md)：**验收不通过** | 已满足（不通过） |

按课程 §5.1，严重缺陷未闭环时不得给出「验收通过」。

## 3 · 候选遗留项（有证据，未计入缺陷数）

| # | 观察 | 证据 | 待确认点 |
|---|---|---|---|
| C-01 | 20 并发 × 10 请求 p95 688.9ms 超判据，10 并发 470.6ms 擦线 | [`../system_test/performance/performance_report.md`](../system_test/performance/performance_report.md) §2.1 | **已登记**为 [#230](https://github.com/heapcluster/jit-defect-prediction/issues/230)，不重复计入 |
| C-02 | `sync/status.started_at` 无 `Z`（D-06） | [`../integration_test/report.md`](../integration_test/report.md) §6 | **已并入** [#228](https://github.com/heapcluster/jit-defect-prediction/issues/228) |
| C-03 | 模型缺失时规格要求 `50000`，实现为 `40001` | `security_cases.py` 规格偏差提示 | 规格订正或代码回改（#228 范围） |
| C-05 | 空能力目录 | [`../integration_test/endpoint_inventory.md`](../integration_test/endpoint_inventory.md) §3.1 | **已登记**为 [#229](https://github.com/heapcluster/jit-defect-prediction/issues/229)（实际剩 4 个，`ui` 已有 spec） |
| C-06 | 前端生产构建单 chunk 2,217 kB（gzip 728 kB） | `npm run build` 输出 | 是否做路由级 code split |
| C-07 | 前端单测触发 `Failed to resolve directive: loading` | `vitest run` stderr | **已并入** [#227](https://github.com/heapcluster/jit-defect-prediction/issues/227)，属测试挂载问题 |
| C-08 | 25 模型 accuracy 0.834~0.864 全部 ≥80%，但 recall ≈0.26 | [`model-accuracy-evidence.md`](model-accuracy-evidence.md) | 业务可接受性，需人工确认（见 [`../human-todo.md`](../human-todo.md) A2） |
| C-09 | 风险列表进详情再返回，筛选条件丢失 | 本轮浏览器实测，A-14 证据 | 改实现还是改验收标准（人工裁定，A3） |

## 4 · 闭环判定标准与处置顺序

1. **先清严重的两条「白捡」缺陷**：BUG-01 是一行 `mkdir`、BUG-05 是一句话，改动小、收益大，优先做。
2. **再修 BUG-02 与 #222**：都属产物交付问题（图集、CPU 权重），需要一次交付流程整理，不是编码难点。
3. **补证据**：每条缺陷补人工采集截图与复现签字；缺项不得计入「Bug 描述规范」加分。
4. **裁定文档与语义类**：BUG-03 / BUG-04 / #228（含 C-02、C-03）逐条给出「改文档 / 改代码 / 不成立」。
5. **关闭条件**：状态置已修复 + 回归用例结果 + Issue 关闭 + [`acceptance_report.md`](acceptance_report.md) 复验重判。
6. **快照口径**：本文件为 `2734c1b`（2026-11-15）快照；动态状态以 GitHub Issues / 飞书缺陷看板为准。

> 红线自查：Bug 报告每条都有可执行复现步骤；无法复现的观察不登记；不编造闭环记录。
