# 性能测试报告

> 依据：[`../../../common/test-assessment-guide.md`](../../../common/test-assessment-guide.md) §4.1 / §4.3；状态：**数据为真实实跑，报告已整理成文**；截图仍待人工采集（不得伪造）。
>
> 被测：`afdee84`（main，含 PR #216）+ 测试脚本改动（未改推理代码）；环境：Windows 本机，conda `jit-defect-prediction`（Python 3.12.14），MySQL80 `jit_demo`，后端 `uvicorn` @127.0.0.1:8000；模型为**交付权重真模型** `xgb_v1`，非占位。

## 1 · 工具与口径

| 项 | 说明 |
|---|---|
| 课程要求工具 | JMeter 或 Locust。**本机未安装且按要求未安装**，不等价冒充。 |
| 实际使用 | `backend/scripts/load_test.py`：标准库线程池 + `httpx` 的真实并发 HTTP 请求，直接输出并发用户数 / 响应时间分位数 / 吞吐量 / 错误率 |
| 备查脚本 | `backend/scripts/locustfile.py`（Locust `HttpUser`，`POST /api/predict` 权重 5、`GET /api/commits` 权重 1），供具备 Locust 的环境复跑 |
| 单客户端基线 | `backend/scripts/perf_loop.py`：`POST /api/predict` × 100 顺序循环 |
| 指标来源 | 真实请求计时，不含推断值；每次复跑追加写入证据文件，不覆盖历史 |
| 判据 | 错误率 0% 且 p95 < 500ms（脚本据此给出退出码） |

脚本副本已归档于 [`../../integration_test/scripts/`](../../integration_test/scripts/README.md)；提示词见 [`../prompts/system_perf_locust_01.md`](../prompts/system_perf_locust_01.md)。

## 2 · 关键指标实测

### 2.1 并发负载（2026-11-13，`backend/scripts/evidence/2026-11-13-load-test.md`）

| 轮次 | 并发用户数 | 每用户请求 / 总请求 | 总耗时 | 吞吐量 | p50 / p95 / max | 错误数 / 错误率 | 判定 |
|---|---:|---:|---:|---:|---|---|---|
| 1 | 5 | 5 / 25 | 0.33s | 76.20 req/s | 48.5 / 68.8 / 69.0 ms | 0 / 0.00% | 达标 |
| 2 | 10 | 5 / 50 | 0.98s | 50.89 req/s | 188.8 / 243.7 / 251.6 ms | 0 / 0.00% | 达标 |
| 3 | 10 | 10 / 100 | 终端实跑，未写入证据文件 | — | 210.5 / **694.0** / 699.2 ms | 0 / 0% | **未达标**（p95 超 500ms，脚本退出码 1） |

> 第 3 轮数据来自同日终端真实输出，当时旧版脚本会覆盖证据文件，故在证据文件中**补录而非伪造文件记录**；三轮波动明显，不能只挑达标数据当结论。另有同日复跑 5×5 一轮 p50/p95/max = 71.5 / 107.7 / 108.4 ms、错误率 0%。

### 2.2 单客户端循环基线（2026-11-12，`backend/scripts/evidence/2026-11-12-perf.md`）

| 运行 | 请求数 | p50 | p95 | p99 | max | 判定 |
|---|---:|---:|---:|---:|---:|---|
| 首次 | 100 成功 / 0 失败 | 28.3ms | **48.1ms** | 48.9ms | 56.0ms | 达标 |
| lint/format 修正后复跑 | 100 | 26.7ms | **47.2ms** | 49.0ms | 53.1ms | 达标 |

该基线只覆盖**特征已落库**的重复预测（含 SHAP 归因），不代表首次抽取特征的冷启动路径（同步 worker 单条约 40–100s，见 [`../execution_records/system-test-run.md`](../execution_records/system-test-run.md)）。

## 3 · 关键指标分析

- **并发扩展性**：并发从 5 升到 10、请求量从 25 升到 50 时，吞吐量由 76.20 降到 50.89 req/s，p95 由 68.8ms 升到 243.7ms；10×10 时 p95 达 694.0ms，超出 500ms 判据。错误率始终 0%，说明是**延迟劣化**而非功能失败。
- **波动与风险**：同日多轮结果差异较大，原因未定位（可能与模型懒加载、同机 MySQL / 前端 dev server 争用有关）。已登记 Issue 跟踪复测；在原因定位前**不给出「性能达标」的发布结论**。
- **适用范围**：仅覆盖 `POST /api/predict` 与 `GET /api/commits`；未覆盖同步、趋势、图集接口，也未做长时间稳定性 / 容量上限测试。
- **结论归属**：以上为指标分析，**不构成系统测试结论**；发布建议与风险判断由 neon 在 [`../summary_report.md`](../summary_report.md) 人工撰写（AI-R5）。

## 4 · 与课程要求对照

| 课程要求 | 状态 | 说明 |
|---|---|---|
| 记录并发用户数 | 已满足 | 5 / 10 两组 |
| 响应时间 | 已满足 | p50 / p95 / max 三组实测，含未达标轮次 |
| 吞吐量 | 已满足 | 76.20 / 50.89 req/s |
| 错误率 | 已满足 | 0.00% |
| JMeter / Locust 结果**截图** | **未满足** | 本机未安装，`locustfile.py` 仅备查；截图须人工采集后补入本目录 |
| 关键指标分析 | 已满足 | 本报告 §3 |

## 5 · 复现命令

```bash
cd backend
python scripts/perf_loop.py                              # 单客户端 100 次，p95 基线
python scripts/load_test.py                              # 默认 20 并发 × 10
USERS=5 REQUESTS=5 python scripts/load_test.py          # 低并发复跑
USERS=10 REQUESTS=10 python scripts/load_test.py        # 高并发复跑（曾出现 p95 超标）
# 有 Locust 的环境：locust -f scripts/locustfile.py --host http://127.0.0.1:8000
```

## 6 · 来源与人工审核

- 负载脚本与指标口径由 AI 生成（`[AI生成]`，提示词见 `../prompts/system_perf_locust_01.md`），**数据由人工在真实服务上实跑取得**，不是 AI 推断值；脚本须经人工审核后方可计入交付（AI-R3）。
- 本报告为结构化整理，§3 分析为基于实测数据的客观描述；性能结论、风险评估与发布建议属人工撰写范畴。
- 待补：JMeter / Locust 原生结果截图、人工采集的终端 / UI 截图，以及 10×10 超标问题的复测记录。截图脱敏后再归档。
