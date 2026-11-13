# 集成测试脚本（交付副本）

课程交付目录树要求 `integration_test/scripts/` 存放编程式测试脚本。**仓库内脚本不移动**：它们依赖 `backend/` 运行时与本机 MySQL，`backend/scripts/` 是实际执行位置。本目录是仓库现行版本的只读快照。

## 1 · 当前同步登记

| 项 | 值 |
|---|---|
| 同步日期 | 2026-11-13 |
| 仓库提交 SHA | `bd39d95`（工作副本） |
| 副本内容 | 9 个 `.py` 脚本（下表），不含 `evidence/` 证据原文件 |
| 参与 CI | 否；复跑一律在 `backend/scripts/` 原位置执行 |

> 脚本的实测结果（35/35、12/12、p95 48.1ms、13/13 等）来自 `afdee84`，与副本 SHA 不同；最终交付须按同一 SHA 重新同步并复跑，见 [`../../README.md`](../../README.md) §6、§9。

| 脚本（交付副本 / 仓库内同名） | 用途 | 记录结果 |
|---|---|---|
| `integration_cases.py` | 35 条四类场景用例 | 35/35 通过 |
| `security_cases.py` | 鉴权、畸形参数、模型不可用 | 12/12 通过 |
| `system_exceptions.py` | 缺权重、空库、失败恢复 | 13/13 通过 |
| `perf_loop.py` | `POST /api/predict` 100 次单客户端循环 | p95 48.1ms / 47.2ms |
| `load_test.py` | **并发负载**：并发用户数 / 响应时间 / 吞吐量 / 错误率 | 5×5、10×5 达标；10×10 p95 694.0ms 未达标 |
| `locustfile.py` | Locust `HttpUser` 脚本，供有 Locust 的环境复跑 | 本机未安装，未执行 |
| `linkage_capture.py` | 12 次真实请求的包络 / 字段留痕 | `backend/scripts/evidence/2026-11-12-linkage.md` |
| `acceptance_scenarios.py` | 抽取活规格 124 条 Scenario 对照清单 | 自动子集 10/10 |
| `online_models_matrix.py` | 25 模型在线矩阵门禁 | 当前 23/25，退出码 1 |

逐条结果与复现命令见 [`../report.md`](../report.md) §2；端点清单与四类场景设计见 [`../endpoint_inventory.md`](../endpoint_inventory.md)；性能报告见 [`../../system_test/performance/README.md`](../../system_test/performance/README.md)。

## 2 · 上传前重新同步

```powershell
$sha = git rev-parse --short HEAD
Copy-Item backend/scripts/integration_cases.py, backend/scripts/security_cases.py, backend/scripts/system_exceptions.py, backend/scripts/perf_loop.py, backend/scripts/load_test.py, backend/scripts/locustfile.py, backend/scripts/linkage_capture.py, backend/scripts/acceptance_scenarios.py, backend/scripts/online_models_matrix.py docs/test/integration_test/scripts/ -Force
```

同步后登记 SHA 与日期，并在 [`../../README.md`](../../README.md) §6 核对四类产物 SHA 一致。不在此手工维护第二份脚本正文；修改请在 `backend/scripts/` 进行后重新同步。

## 3 · 合规说明

- 脚本由 AI 生成骨架（`[AI生成]`），提示词见 [`../prompts/`](../prompts/)；核心业务断言（概率区间、14 维列序、鉴权码、排序、空结果语义）须人工逐条复核（AI-R4），审核记录目前**待签署**（AI-R3）。
- 脚本会读取本机 `.env` 的 `API_TOKEN`，副本中不含任何密钥；上传前须再次检查。
