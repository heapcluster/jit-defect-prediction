## Context

基线为 main `f5ca61d`（已含 #96 清单加载、#97 单条提交现算特征、#100 `infra/schema.sql`）。`backend/app/model_registry.py` 的 `load_models()` 现在先经 `_delivery_models()` 读 `MODEL_DIR/feature_order.txt`，再逐个加载清单声明的权重并校验14维；单文件异常已有 `logger.exception`，但没有一次加载的失败模型名汇总。同时后端从 `backend/` 启动时 `sys.path` 不含仓库 `data_model/`，按规范包路径序列化的权重无法反序列化。设计涉及 Python 模块解析与错误信息边界，因此保留 design。

## Goals / Non-Goals

**Goals:** 从 backend 目录启动时支持仓库内规范模型类路径；成功/失败模型能分别定位；用 SQLite 覆盖建表到接口的集成流程。

**Non-Goals:** 不改变清单驱动的加载范围（`feature_order.txt` 的 `[models]` 段仍是在线模型唯一来源）、默认模型排序和 SHAP 降级，不改共享数据库；不把八个权重的存在等同于八个可服务模型，不修复 D-09 或改变其 P3 状态。

## Decisions

- D1：在 `load_models()` 中由 `config.REPO_ROOT / "data_model"` 得到绝对路径，检查是否存在于 `sys.path` 后插入。相较要求每个人手设 PYTHONPATH，可避免 cwd 差异；不从 MODEL_DIR 取导入路径，避免把任意权重投放目录同时当作代码目录。
- D2：在一次加载内维护失败名称列表，清单声明却缺失的权重、反序列化失败与宽度不符均追加文件主干；循环结束仅当列表非空时 `logger.error`。清单缺失或列序漂移走 #96 的整目录早退，此时不输出失败名单（没有可信的声明集合，编造名单等于伪造证据）。保留现有逐文件异常、宽度自检和成功日志，不新增 API 字段或改变错误码。
- D3：不注册 `__main__` 别名。独立进程仅加搜索路径后，当前 TabNet 权重仍抛 `AttributeError`；在 `python -c` 顶层先 `from pipelines.expert.model import TabNetWithEarlyStop` 会把类绑定进 `__main__`，这种验证不能证明单纯路径修复有效。正例测试须先在生产者子进程按规范模块路径保存，再在独立消费者中加载。
- D4：扩充 `test_model_registry.py` 验证导入、重复调用、损坏文件、宽度拒收与日志；`test_integration_api.py` 使用独立 SQLite engine 和临时四类 CSV，真实调用 ingest 与 TestClient 四接口。夹具负责恢复全局 engine/registry，禁止依赖外部 .env、MySQL 或真实权重。
- D5：D-09 已在 `docs/repo/defect-records.md:25` 登记处理方式，按用户最新要求后续单独开 change，而非仅以登记结案。当前SQLite集成测试不改变大写哈希行为；GET/POST归一化及MySQL对照不混入模型导入PR。
- D6（2026-10-24 历史记录）：#96 当时只声明三个在线模型，8 权重目录里只加载 3 项。后续 owner 已批准八模型在线清单，详见 `online-eight-model-selection`；该三模型裁定项已被新裁定取代。当前仍须实测八项清单与 8/8 加载，不以当时 3/8 的结果冒充现行验收。

## Risks / Trade-offs

- Python 搜索路径属于进程全局状态 → 仅添加确定的仓库路径且幂等，测试隔离并恢复路径。
- Pickle/joblib 可执行代码 → 只验证已信任的团队交付权重，不建立上传或任意路径加载入口。
- TabNet 旧权重曾因未在三模型清单内而未触发反序列化 → 现行八模型清单下必须逐项复核新权重，不能沿用旧 3/8 验收结果。
- SQLite 不能证明 MySQL 方言和并发行为 → MySQL证据留待后续，不把测试框架覆盖写成生产联调完成。

## Migration Plan

先完成提案审核，再修改后端与测试；在干净解释器跑测试及日志脱敏检查，然后提交独立 PR。部署不迁移数据；回滚只回退该 PR 的代码，不删除模型或数据库。

## Open Questions

本次两项后端改动的范围无待定问题；旧 `__main__` 权重如何重新导出由模型线跟进，不纳入“仅加导入路径”的完成承诺。
