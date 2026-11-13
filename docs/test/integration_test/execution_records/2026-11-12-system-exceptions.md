# 系统异常场景执行证据（测试代码产物）

> 生成：`backend/scripts/system_exceptions.py --scenario all` ｜ 时间：2026-11-12T23:30:01
> 环境：本机 MySQL80 `jit_demo`；脚本自起/自停独立 uvicorn 子进程（空闲端口），**不移动、不删除任何权重**，不影响 8000 主服务。

| 场景 | 结果 | 实测 |
|---|---|---|
| 缺权重 / health 降级 | PASS | status=degraded db=up models_loaded=0 |
| 缺权重 / predict 明确拒绝 | PASS | 400/40001 msg=参数非法：该模型暂无在线权重，仅离线评估，无法在线预测 |
| 缺权重 / 模型清单仍可读 | PASS | 200（清单来自 catalog，不等于可用） |
| 空库 / 健康检查 | PASS | db=up commits=0 predictions=0 |
| 空库 / 列表返回空而非报错 | PASS | code=0 total=0 |
| 空库 / 趋势返回空 series | PASS | code=0 series=0 |
| 空库 / 图集 40400 | PASS | 404/40400 |
| 失败恢复 / 初始状态 | PASS | running=False |
| 失败恢复 / 触发同步 | PASS | 200/0 |
| 失败恢复 / 重启后健康 | PASS | status=ok db=up |
| 失败恢复 / 状态不残留 | PASS | running=False last_error=None |
| 失败恢复 / 查询链路可用 | PASS | 200/0 |
| 失败恢复 / 可再次预测 | PASS | 200/0 |

汇总：13/13 通过。

- 缺权重：`MODEL_DIR` 指向空目录 → `health=degraded`、`POST /api/predict` 40001 明确文案，不 500、不泄漏路径。
- 空库：`DB_NAME` 指向空的 `jit_test` → 列表/趋势返回 `code=0` 空结果，图集 40400，空数据不是系统错误。
- 失败恢复：同步进行中强杀子进程 → 重启后 `sync/status` 内存态清空、DB 可用、可再次预测。
