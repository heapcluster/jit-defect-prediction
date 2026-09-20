# 性能压测证据 2026-09-19

- 靶子：`POST /api/predict`（契约三 §4 指定，不用查询接口代替）
- 服务：http://127.0.0.1:8000（构建来源见提交记录）
- 模型来源：占位模型 tree_placeholder_v0（待真 .pkl 重跑）
- 请求数：100（成功 100 / 失败 0）
- 命令：`python scripts/perf_loop.py --base-url http://127.0.0.1:8000 --n 100 --model-source "占位模型 tree_placeholder_v0（待真 .pkl 重跑）" --out scripts/evidence/perf-placeholder-2026-09-19.md`

| 分位 | 耗时(ms) |
|---|---|
| p50 | 31.2 |
| p95 | 33.8 |
| p99 | 36.0 |
| max | 7233.6 |

**目标 p95 < 500ms：达标**（分位数口径：升序第 ceil(q*n) 位，design D4；非平均值）
