# 提示词：对运行中服务复跑 35 条接口用例并定位失败项

## 基本信息

- 使用工具：CodeBuddy（DeepSeek-V4.1-Flash）
- 使用日期：2026-11-15
- 关联测试文件：`backend/scripts/integration_cases.py`、`security_cases.py`、`perf_loop.py`、`load_test.py`、`linkage_capture.py`、`online_models_matrix.py`
- 关联文档：`docs/想到什么取什么/integration_test/report.md`、`docs/想到什么取什么/system_test/performance/performance_report.md`

## 提示词原文

```text
起后端 uvicorn 后，跑 integration_cases.py 全量 35 条，把失败项逐条定位到根因，
要能给出可复制的复现命令与响应原文，不能只写"接口不通"。

要求：
- 失败项先判断是产品缺陷还是用例写错，并写出判断依据（状态码、响应体、日志、
  文件是否存在）。
- 已有的 security_cases.py / perf_loop.py / load_test.py / linkage_capture.py
  一并复跑，数字按本轮实测填，不要沿用 11-12 / 11-13 的历史值。
- 负载至少给 3 个并发档位，含一个会超标的档位，别只挑达标数据。
```

追加追问：

```text
T-IN-29 报「/static 图带鉴权不可读」，帮我确认是鉴权中间件的问题还是文件不存在。
带令牌和带错误令牌分别请求一次，把响应体和状态码贴出来。
```

```text
25 模型矩阵里 tabnet 两个模型的错误文案是「参数非法：…权重无法加载」，
这个错误码分类对不对？单独记一条缺陷，别和 CUDA 权重那条混在一起。
```

## 大模型输出摘要

- 35 条中 34 通过、1 失败（T-IN-29）；失败定位到 `/static/figures/expert/et_v1/roc.png` 实体文件不存在：无令牌 401、带正确令牌 404（`{"detail":"Not Found"}`），`git ls-files backend/static` 为空。
- 安全 18/18、单客户端 p95 53.3ms、负载四档（5×5 / 10×5 / 10×10 / 20×10），最后一档 p95 688.9ms 未达标。
- 25 模型矩阵 23/25，两个 tabnet 报 CUDA 反序列化失败；另判定「参数非法」文案属独立的错误分类缺陷。
- 存量 `#217` 本轮不再复现（semantic/fused/e2e 均 200），建议人工确认关闭，但不由 AI 下结论。

## 人工审核与修改记录

- 审核结果：**待人工审核**
- 修改内容：无人工修改；报告中的「建议关闭 #217」明确标注须人工确认，未直接改 Issue 状态
- 备注：T-IN-29 的判定口径（元数据存在 ≠ 图片可取）建议后续固化进 `endpoint_inventory.md`，避免下一轮又漏
