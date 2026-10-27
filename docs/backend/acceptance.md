# 后端验收功能板块（达到什么效果）

> 验收人：sober / 蒋励 ｜ 对应 Sprint：Sprint 1（MVP 接口）→ Sprint 3（非功能证据）

## 板块 B1：库表与建表

- **效果**：别人 `clone` 后一条命令建好四张表，字段与 `docs/design/database.md` 逐字一致（含易漏的 `commit_feature`）。
- **证据**：建表脚本 + 一条命令建库成功的终端输出。
- **一票否决**：`features` 键名与契约不一致 → 课程判定「规格与代码不一致」。

## 板块 B2：四个接口

- **效果**：四个接口严格按 `api-spec.md` 返回；空数据返回 `null`/空数组而非 `40400`；`risk_score` 不得用 `0.0` 冒充未预测。
- **证据**：每个接口至少 1 条正常路径 + 1 条异常路径测试。
- **一票否决**：前端要的字段接口没返回（联调才发现）→ 阻塞。

## 板块 B3：鉴权

- **效果**：四接口缺 `X-API-Key` 一律 401；`50000` 不回显堆栈/SQL/路径。
- **证据**：两组请求返回截图。

## 板块 B4：在线预测 + 模型加载

- **效果**：`POST /api/predict` 实时推理返回概率与 `explanation`；幂等 upsert 不累积重复行；特征顺序以 `feature-columns.md` 为准（错序静默错答，必须核对）。
- **证据**：实时推理返回示例 + 重复调用后库里仅一行。

## 板块 B5：性能（非功能）

- **效果**：`POST /api/predict` 95% 请求 < 500ms。
- **证据**：压测脚本循环 100 次，输出 **p50/p95/p99** 分位数（非均值）+ 截图，放 `backend/scripts/`。
- **一票否决**：只写「已实现」无分位数证据 = 缺项。

## 板块 B6：安全（非功能）

- **效果**：非法/缺失参数返回明确错误且不泄露内部信息。
- **证据**：「缺失参数」「参数非法」两类用例截图，答辩可当场出示。

## 板块 B7：设计文档（sober 验收主证据）

- **效果**：L3 设计文档 v0.5 含四张图（架构/流程/predict 时序/类图，各带生成方式标注），§四 1.3→1.4、补 #44/#47、合并重复两节。
- **证据**：文档可点开 + 四图齐全。

## 三端联调 · 后端要求（2026-10-23 定稿）

**目标**：前端能在浏览器里把「列表 → 详情 → 重新预测 → 趋势」跑通，中间不出现 500。

1. **建表**：演示 / 验收库名固定 **`jit_demo`**（Issue #130 更正裁定、#142），一条命令建好库与四张表 —— `python infra/setup_mysql.py`（一键建库 + 建表，权限与常见报错见 `docs/backend/mysql-setup.md` §2）。四表 DDL 的**单一来源仍是 `infra/schema.sql`**：它必须保持「纯四表、可导入任意目标库」，**不要往里加 `CREATE DATABASE` / `USE`** —— 加了会静默改写调用方指定的目标库（本条命令与 Issue #121 的 `jit_schema_probe` / `jit_orm_probe` 两个探针库都走这一份文件），并被 `backend/tests/test_schema_sql.py` 判红。`python -m app.db init` 作为等价性校验，两条路径都必须通过索引自检。日常**联调**库也是它（`jit_demo`，与演示/验收同一套）：见 `docs/frontend/integration-log.md` §0。
2. **数据**：离线 CSV 灌库已于 2026-10-25 移除，数据只由实时同步端点写入 —— 调 `POST /api/sync`（主干最新 N 条）或 `POST /api/sync-prs`（open PR），留档返回的 `commits_predicted` / `skipped` 明细。**不做种子数据、不做历史回填**（2026-10-27 裁定，`scripts/seed_dev_data.py` 已删除）：建表后库内为空是预期状态，界面上能看到的内容就是「最近被同步的那几条」。
3. **模型**：`MODEL_DIR` 指向 `data_model/pipelines/expert/models/`；**在线模型集 = 该目录 `feature_order.txt` 的 `[models]` 段**（#96 定义的唯一来源，2026-10-25 组长裁定 Issue #139 起为**全部 8 个**：`lr_v1` / `rf_v1` / `xgb_v1` / `lgbm_v1` / `et_v1` / `svm_v1` / `mlp_deep_v1` / `tabnet_v1`）。清单内声明的模型必须全部加载成功，启动日志不得出现 `model load failed` 或 `failed models:`。
   - `feature_order.txt` 的 `[evaluated]` 段当前为空（8 模型全部上线）；该段只登记「只进评估、不进交付」的权重，按 `openspec/specs/model-coverage`「交付模型 MUST 保持不变」，新增模型 MUST NOT 静默进 `[models]`。
   - 导入路径无需手工处理：#99 已让后端在 `load_models()` 自动把 `<repo>/data_model` 的绝对路径插入 `sys.path`（幂等，不接受请求参数或 `MODEL_DIR` 传入），不要再手工设 `PYTHONPATH`。
   - **待裁定（不阻塞本板块）**：T9 原文写「8 个模型全部可用」。若 PO 裁定扩大交付范围，须先按 R6 另立「模型切换」change 并升版契约三 / `docs/backend/api-spec.md`，再回来同步本条；裁定前按上面 `[models]` 的口径验收。
4. **接口**：4 条 200；空数据返回 `[]`/`null` 而非 404；缺 `X-API-Key` → 40100；畸形 `commit_hash` → 40001；同一 hash 连调两次不产生第二行 prediction（幂等）。
5. **给前端的模型清单**：与第 3 条同源，即 `feature_order.txt` 的 `[models]` 段当前声明的 **8 个**模型。前端下拉按这份清单排（`frontend/src/utils/models.js` 已同步），MVP **不新增** `GET /api/models`（`docs/frontend/pages.md` §6 已裁定由前端维护静态清单）。**清单内缺一即视为本板块未达标**；清单外的模型名加载不上不算本板块缺陷。
6. **证据**：四条接口的 curl 输出、`POST /api/predict` 连跑 20 次的 P50/P95（<500ms）、缺令牌与畸形参数两组截图。
