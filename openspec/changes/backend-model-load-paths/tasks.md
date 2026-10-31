# backend-model-load-paths — 任务清单

> 提案：`proposal.md` ｜ 设计决策：`design.md` ｜ 规格：`specs/predict-api/spec.md`
> 负责人：backend 吕建江 ｜ 创建：2026-10-23 ｜ 更新：2026-10-24 ｜ 状态：进行中（8/11；已 rebase 到 main `f5ca61d` 并叠加在 #96 清单加载之上，SQLite 验证完成，PR #99 head `d806e73` 待复审，真实环境验收与清单范围裁定待收口）
> 关联需求：无（工程化）；支撑契约三 POST /api/predict 与四接口 SQLite 联调
> 统一格式见 `docs/common/openspec-task-template.md`；本文件末的「测试与验证」为强制板块。

## 1. 模型加载与配置说明

- [x] 1.1 在 #96 的 `_delivery_models()` 清单加载之上，为 `load_models()` 加入由 REPO_ROOT 推导的 data_model 导入路径，重复调用不重复插入 — 交付物：`backend/app/model_registry.py`；独立消费者进程加载清单内规范模块路径模型通过。
- [x] 1.2 汇总清单声明却缺失、反序列化失败与宽度不符的模型名，输出 ERROR 日志并保留成功清单；清单缺失或列序漂移仍走 #96 的整目录早退，不编造失败名单 — 交付物：`backend/app/model_registry.py`；损坏文件不阻断有效模型，测试见§1。
- [x] 1.3 `.env.example` 补 MODEL_DIR 默认目录说明，不填写真实令牌/密码、不改本机 .env — 交付物：`backend/.env.example`。

## 2. 测试与回归

- [x] 2.1 补独立进程导入、路径幂等、损坏文件、宽度拒收、清单声明却缺失、空失败清单与主模块类失败测试 — 交付物：`backend/tests/test_model_registry.py`；新增7条（文件合计14条），消费者未预导入自定义模型类，包含独立`__main__`坏导出反例；rebase 后所有临时 MODEL_DIR 用例都补了 `feature_order.txt` 夹具。
- [x] 2.2 新增独立 SQLite 集成夹具及四接口流程测试，四类 CSV 各灌两遍、重复 predict 不增行、空数据与缺特征按契约返回 — 交付物：`backend/tests/test_integration_api.py`，6条全过；夹具自建清单声明 integration_v1/v2，未接触真实数据库。
- [x] 2.3 增加无令牌/畸形参数/加载失败响应脱敏断言，跑 targeted 与后端全量测试 — 交付物：上述测试；定向20 passed、全量143 passed，记录见§5。

## 3. 审阅与跨线交付

- [x] 3.1 严格校验单 change 和全量规格，逐场景核对并提交独立 PR — 交付物：PR #99（https://github.com/heapcluster/jit-defect-prediction/pull/99）；2026-10-24 按苏哲勋 CHANGES_REQUESTED 意见 rebase 到 main `f5ca61d`，实现提交 `15164a0`，两处冲突按「在清单加载之上叠加导入路径与失败汇总」解决；仍未合入，不代表T9验收完成。
- [ ] 3.2 向模型线蒋励说明当前 TabNet 权重的 __main__ 导出问题并核验重新导出结果 — 交付形式：PR 中的复现条件与模型交付回执；本机真实权重复验仍7/8，此项不得勾选。
- [ ] 3.3 2026-10-24 按已授权环境补实际模型 API 与 MySQL 证据 — 交付给 backend 吕建江；包括T9逐个model_name请求、非空真实解释、幂等与性能。未执行前只报告SQLite结果。
- [x] 3.4 把「#96 原三模型清单 vs T9 八模型验收」提交裁定 — 交付物：PR #99 评论（https://github.com/heapcluster/jit-defect-prediction/pull/99#issuecomment-6370955484）与历史 3/8 实测。后续 owner 已批准扩为八模型清单；3.2/3.3 仍须凭当前权重实测后勾选。
- [ ] 3.5 飞书把同一裁定问题发给蒋励/苏哲勋 — 交付形式：吕建江本人粘贴我给的串；发出前本项不勾，不以 PR 评论代替飞书通知。

## 测试与验证（强制板块）

> 命令使用按 `data_model/environment.yml` 建好并激活的 Python 3.12 环境；本次实际解释器版本3.12.15。严格校验与SQLite结果不代表T9完整通过。

### 1. 单元测试

| 项 | 内容 |
|---|---|
| 覆盖对象 | model_registry.load_models 在 #96 清单加载之上的导入路径、注册表与失败汇总日志 |
| 测试文件 | `backend/tests/test_model_registry.py` |
| 用例数与结果 | 14条（rebase 后既有7条、本 change 新增7条），与集成文件合跑20 passed |
| 复现命令 | cwd=backend：`python -m pytest tests/test_model_registry.py tests/test_integration_api.py` |
| 正向 | 独立生产者按包路径保存、独立消费者加载清单内模型；调用两次仅一条路径；路径来自repo而非外部权重目录 |
| 异常/边界 | 损坏文件、非14维、清单声明却缺失与`__main__`坏导出被拒并汇总；恢复正常文件后旧失败清单不残留；缺失目录清空注册表；清单缺失/列序漂移不产生失败名单 |

### 2. 集成测试

| 项 | 内容 |
|---|---|
| 集成范围 | SQLite建四表 → 四类CSV灌入 → 清单驱动模型注册 → GET列表/详情/趋势与POST预测 |
| 测试文件 | `backend/tests/test_integration_api.py` |
| 用例数与结果 | 6条通过（包含在定向20条与全量143条内） |
| 复现命令 | cwd=backend：`python -m pytest tests/test_integration_api.py` |
| 关键断言 | 四类CSV重复灌入行数不变；重复预测复合键只一行且值更新；夹具清单声明的两个模型注册成功且SHAP非空；列表/详情读到新预测；week/month与闭区间计数一致；无数据不是404；缺特征POST为40400（SOURCE_REPO 未配置，沿用只查库行为） |

### 3. 验收测试

| 场景 | 测试定位 |
|---|---|
| 规范包路径从backend加载 | `backend/tests/test_model_registry.py::test_repository_model_module_loads_in_clean_process` |
| 重复加载路径不重复 | 同上及 `backend/tests/test_model_registry.py::test_import_path_comes_from_repo_not_weights` |
| 损坏文件不阻断有效模型 | `backend/tests/test_model_registry.py::test_failed_models_summary_includes_corrupt_and_wrong_width` |
| 特征宽度拒收并汇总 | 同上 |
| 清单声明的权重文件缺失 | `backend/tests/test_model_registry.py::test_declared_but_missing_weight_enters_failed_summary` |
| 全成功无失败汇总 | `backend/tests/test_model_registry.py::test_failed_summary_does_not_persist_after_success` |
| `__main__`坏导出真实失败 | `backend/tests/test_model_registry.py::test_main_module_model_is_reported_without_alias` |
| HTTP不泄露加载异常 | `backend/tests/test_integration_api.py::test_auth_validation_and_failed_load_do_not_leak` |

本 change 的8个Scenario均有测试覆盖；T9八模型真实联调仍未通过，§5 的三模型结果是历史基线。现行清单已扩至八项，不把清单扩容视为 8/8 实测通过。复现：cwd=backend `python -m pytest tests/`；cwd=仓库根 `openspec validate backend-model-load-paths --strict`、`openspec validate --all --strict`。

### 4. 非功能验证

| 维度 | 是否触及 | 证据与命令 |
|---|---|---|
| 性能 | 不承诺改善；在线模型集由 #96 清单决定，本 change 不扩不缩 | 启动耗时、RAM及模型P95未测，不由pkl磁盘大小推算RAM |
| 安全 | 是 | 集成测试覆盖四路由缺令牌、畸形参数与无模型50000；响应无堆栈/本地路径 |
| 可靠 | 是 | 有效模型不受损坏模型影响；失败汇总只输出当次失败名称 |
| 易用 | 是 | `.env.example` 已说明默认expert/models路径；未改本机配置或前端 |

### 5. 已知缺口与后续计划

| 缺口 | 原因 | 归属 | 计划 |
|---|---|---|---|
| PR审阅与合入 | PR #99 首轮 CHANGES_REQUESTED（与已合并的 #96 清单加载冲突、夹具缺清单、措辞像反对白名单）；2026-10-24 已 rebase 到 `f5ca61d` 并逐条修正，待复审 | backend 吕建江 + 苏哲勋 | 复审通过后 squash 合入；不把「已 rebase」当成合入或T9验收 |
| 八模型实际加载与性能待验收 | 原三模型冲突已裁定为扩充清单；当前清单八项，但本 change 的历史实测仅覆盖三项 | 苏哲勋 + 蒋励 + backend 吕建江 | 使用现行权重逐项加载、预测、压测并附当前提交证据；此前不报 8/8 |
| TabNet 权重可加载性待复核 | 旧权重引用 `__main__.TabNetWithEarlyStop`；当前清单已声明该项，旧报告不能证明新包可加载 | model 蒋励 + backend 吕建江 | 用现行交付包在独立进程实测；不做任意主模块别名 |
| 八模型逐个POST非空解释与P95 | 路径修复不等于新增非线性SHAP支持；fixture非空不代替真权重验证 | backend 吕建江 | 后续补真正解释器及八模型证据，不返回伪造非空值 |
| MySQL建表、灌库和幂等实测 | `infra/schema.sql` 已随 #100 合入 main，但本轮按要求只跑SQLite | backend 吕建江 | 2026-10-24 在已授权隔离库实跑建表两次 + `app.db init` 双路径对照 |
| D-09独立change | 用户最新要求另开，不与模型导入小修混合 | backend 吕建江 | 后续单独change统一GET/POST小写查库；现P3记录不等于修复 |

#### 2026-10-24 rebase 到 `f5ca61d` 后的执行证据（当前有效）

- 工作树：本机 `fix/backend/model-load-paths` 分支的独立工作树（个人绝对路径按 `docs/repo/collaboration.md` §0 第 3 条不复述，下同），rebase 基线 main `f5ca61d`；实现提交 `15164a0`。两处冲突（`backend/app/model_registry.py`、`backend/tests/test_model_registry.py`）按「清单加载之上叠加」解决：保留 `_delivery_models()` 与 #96 新增的 2 条清单测试，导入路径与失败汇总只加在其后。
- Python：conda 环境 `jit-defect-prediction` 的解释器，3.12.15；pytest 9.1.1、SQLAlchemy 2.0.54、FastAPI 0.141.1、joblib 1.6.0、ruff 0.16.8。
- 计数取自 `--junitxml` 的 testsuite 属性，不凭终端回显：本机 CLI 会吞掉 pytest 末行汇总（`-q` 输出只剩进度点），因此以 XML 为准。
- cwd=backend：`python -m pytest tests/test_model_registry.py tests/test_integration_api.py -q --junitxml=...` → exit 0，`tests=20 failures=0 errors=0 skipped=0 time=3.812`；`python -m pytest tests/ -q --junitxml=...` → exit 0，`tests=143 failures=0 errors=0 skipped=0 time=7.420`。
- cwd=仓库根：`python -m ruff check backend/app/model_registry.py backend/tests/test_model_registry.py backend/tests/test_integration_api.py` → `All checks passed!`；`openspec validate backend-model-load-paths --strict` → `Change 'backend-model-load-paths' is valid`；`openspec validate --all --strict` → `Totals: 24 passed, 0 failed (24 items)`。
- 真实权重只读验证（不连数据库、不写文件）：cwd=backend，`MODEL_DIR=<仓库根>/data_model/pipelines/expert/models`（`<仓库根>` 为读者自己的 checkout 根目录，个人绝对路径不复述；该目录含 8 个 `.pkl` 与仓库同源 `feature_order.txt`，清单只声明 `lr_v1`/`rf_v1`/`xgb_v1`）→ 日志 `loaded models: ['lr_v1', 'rf_v1', 'xgb_v1']`，`sorted(_REGISTRY)` 同值，`sys.path` 含仓库 `data_model`。其余 5 个权重（含 `tabnet_v1`）未被反序列化，故本轮不再出现 `failed models: ['tabnet_v1']`；这是清单范围造成的，不是导出缺陷已修。此结果不能作为 T9 8/8 通过证据。

#### 2026-10-23 首轮离线执行证据（rebase 前，数字已过期，仅留痕）

- 基线：`eea910eba80e74608c2da34e88c390879c4e0b14`；实现提交 `c920e50`（已被 rebase 取代）。
- cwd=backend：`python -m pytest tests/test_model_registry.py tests/test_integration_api.py` → `17 passed, 15 warnings in 2.86s`；`python -m pytest tests/` → `112 passed, 15 warnings in 5.03s`。
- cwd=仓库根：ruff → `All checks passed!`；单change strict → valid；全量strict → `Totals: 20 passed, 0 failed (20 items)`。
- 15条警告均为FastAPI/Starlette和matplotlib/pyparsing依赖弃用提示，未禁用警告或绕过检查。
- 当时真实权重只读验证（`load_models()` 仍遍历目录）：成功名称 et_v1/lgbm_v1/lr_v1/mlp_deep_v1/rf_v1/svm_v1/xgb_v1，汇总 `failed models: ['tabnet_v1']`，异常 `AttributeError: Can't get attribute 'TabNetWithEarlyStop' on __main__`。
