# 性能测试报告

> 依据：[`../../../common/test/test-assessment-guide.md`](../../../common/test/test-assessment-guide.md) §4.1 / §4.3。状态：**数据为 2026-11-15 真实实跑**；截图（JMeter/Locust 原生结果）待补。
>
> 被测：`2734c1b`；环境：Windows 11 本机，conda `jit-defect-prediction`（Python 3.12.14），MySQL 8.0 `jit_demo`，后端 `uvicorn` @127.0.0.1:8000（单进程），同机还跑着 `vite` 开发服务器；模型为交付权重真模型（`xgb_v1` / `et_v1`），非占位。

## 1 · 工具与口径

| 项 | 说明 |
|---|---|
| 课程要求工具 | JMeter 或 Locust。**本机两者都没装，也没为跑报告临时装**，不用别的数据冒充。 |
| 实际使用 | `backend/scripts/load_test.py`：标准库线程池 + `httpx` 发真实并发 HTTP 请求，直接输出并发用户数 / 响应时间分位数 / 吞吐量 / 错误率 |
| 备查脚本 | `backend/scripts/locustfile.py`（`POST /api/predict` 权重 5、`GET /api/commits` 权重 1），有 Locust 的环境可直接复跑 |
| 单客户端基线 | `backend/scripts/perf_loop.py`：`POST /api/predict` × 100 顺序循环，输出 p50/p95/p99/max |
| 判据 | 错误率 0% 且 p95 < 500ms（脚本据此给出退出码） |
| 指标来源 | 真实请求计时，不写推断值；每轮追加写入证据文件，不覆盖历史 |

脚本唯一真源在 `backend/scripts/`；提示词见 [`../prompts/system_perf_locust_01.md`](../prompts/system_perf_locust_01.md)。

## 2 · 关键指标实测

### 2.1 并发负载（2026-11-15，证据 [`../../integration_test/execution_records/2026-11-15-load-test.md`](../../integration_test/execution_records/2026-11-15-load-test.md)）

四轮都跑在同一台机器、同一个提交上，`POST /api/predict` 打同一个已落库提交：

| 轮次 | 并发用户 | 每用户请求 / 总请求 | 总耗时 | 吞吐量 | p50 | p95 | max | 错误率 | 判定 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 5 | 5 / 25 | 0.93s | 27.01 req/s | 97.2ms | 404.2ms | 422.0ms | 0.00% | 达标（p95 已接近 500ms） |
| 2 | 10 | 5 / 50 | 1.47s | 33.96 req/s | 307.8ms | 454.4ms | 466.5ms | 0.00% | 达标（擦线） |
| 3 | 10 | 10 / 100 | 2.77s | 36.16 req/s | 205.9ms | 470.6ms | 518.2ms | 0.00% | 达标（擦线） |
| 4 | 20 | 10 / 200 | 5.27s | 37.94 req/s | 482.0ms | **688.9ms** | 808.1ms | 0.00% | **未达标**（p95 超 500ms，脚本退出码 1） |

要注意的是：5×5 这种低并发本轮 p95 也到了 404ms。测的时候机器上还跑着浏览器（Playwright）与 vite，MySQL 也在同一台机，所以**这轮的绝对值不能当容量基线**，只能说明「低并发也可能擦线」这件事本身不稳定。

### 2.2 单客户端循环基线（`perf_loop.py`，2026-11-15）

| 运行 | 请求数 | p50 | p95 | p99 | max | 判定 |
|---|---|---:|---:|---:|---:|---|
| 首次（缓存未热） | 100 成功 / 0 失败 | 38.5ms | 53.3ms | 69.2ms | 83.6ms | 达标 |
| 复跑（记录值） | 100 成功 / 0 失败 | 36.2ms | **68.1ms** | 122.4ms | 3660.6ms | 达标（取较保守值） |

原始输出见 [`../../integration_test/execution_records/2026-11-15-perf.md`](../../integration_test/execution_records/2026-11-15-perf.md)。`max=3660.6ms` 是冷启动离群点，压测结论看分位数不看单点极值。

口径说明：这条只覆盖「特征已落库的重复预测（含 SHAP 归因）」，不代表首次抽取特征的冷启动路径——同步 worker 单条约 40s（本轮 10 条 401.7s，见 [`../../integration_test/report.md`](../../integration_test/report.md) §3 T-IN-20），两者不是一个量级，报告里不能混着写。

## 3 · 关键指标分析

- **吞吐上不去**：四轮吞吐在 27~38 req/s 之间，并发加一倍吞吐只涨不到 40%，说明瓶颈在服务端单进程（GIL + sklearn 推理 + 同步 DB 写），不在网络。要提吞吐得先多 worker 部署（uvicorn `--workers`）+ 推理侧线程池，而不是继续加客户端并发。
- **延迟随并发线性恶化**：p50 从 97ms → 308ms → 206ms → 482ms，p95 从 404ms 一路到 689ms。20 并发时已明显排队，错误率仍 0%，属**延迟劣化而非功能失败**。
- **达标边界**：按本轮数据，单进程在 10 并发以内能守住 p95 < 500ms（且是擦线），20 并发守不住。这个结论比「达标/不达标」更有用，验收和部署都该引用它。
- **未覆盖范围**：只压了 `POST /api/predict`（`load_test.py` 里 `GET /api/commits` 仅在取样时调用）；同步、趋势、图集接口没压，也没有长稳压测与容量上限测试。
- **结论归属**：以上是指标分析，**不是发布结论**；风险判断与发布建议在 [`../summary_report.md`](../summary_report.md)，那份须人工复核。

## 4 · 与课程要求对照

| 课程要求 | 状态 | 说明 |
|---|---|---|
| 记录并发用户数 | 已满足 | 5 / 10 / 10 / 20 四组 |
| 响应时间 | 已满足 | p50 / p95 / max 四组，含未达标轮次 |
| 吞吐量 | 已满足 | 27.01 ~ 37.94 req/s |
| 错误率 | 已满足 | 全部 0.00% |
| JMeter / Locust 结果**截图** | **未满足** | 本机未安装，`locustfile.py` 仅备查；截图须人工采集后放进本目录 |
| 关键指标分析 | 已满足 | 本报告 §3 |

## 5 · 复现命令

```bash
cd backend
python scripts/perf_loop.py                              # 单客户端 100 次，p95 基线
python scripts/load_test.py --users 5  --requests 5      # 低并发
python scripts/load_test.py --users 10 --requests 10     # 中并发（擦线）
python scripts/load_test.py --users 20 --requests 10     # 高并发（可能超标）
# 有 Locust 的环境：locust -f scripts/locustfile.py --host http://127.0.0.1:8000
# 有 JMeter 的环境：jmeter -n -t scripts/jmeter/jit-predict.jmx -l result.jtl -Jtoken=... -Jcommit_hash=...
```

**跑之前请关掉浏览器与前端 dev server**，否则测出来的是整机资源争用，不是服务端容量。

## 6 · 来源与人工审核

- 负载脚本与指标口径为 AI 生成（`[AI生成]`），数据是人在真实服务上跑出来的，不是模型推断；脚本本身仍待人工审核（AI-R3）。
- §3 的分析基于本轮实测数字，性能结论、风险评估与发布建议属人工撰写范畴，见 [`../summary_report.md`](../summary_report.md)。
- 待补：JMeter/Locust 原生结果截图、人工采集的终端截图、以及「关掉其他负载后重测」的一组干净数据。
