# T-FE-01 三态截图（9 张）

- 采集日期：2026-10-24
- 采集人：蒋励（组长代前端执行，前端同学只提供启动方式与账号）
- 截图目录：[`docs/frontend/screenshots/`](../screenshots/)

## 环境（按 `integration-log.md` §0 联调基线执行）

口径唯一出处：`docs/frontend/integration-log.md` §0。本次未偏离任何一项。

| 项 | 值 |
|---|---|
| 库 | `DATABASE_URL=sqlite:///./dev.db`，由 `backend/scripts/seed_dev_data.py` 生成：3 提交 / 3 特征 / 3 预测，`commit_hash` 为 `000...001`~`000...003` |
| 令牌 | `API_TOKEN=dev-token-20260918`，前端 `VITE_API_KEY` 同值 |
| 模型目录 | `MODEL_DIR` 留空 → 回落 `<repo>/data_model/pipelines/expert/models/`（8 个训练口径权重 + `feature_order.txt` + `manifest.txt`），符合 §0 硬规矩 1「不写个人绝对路径」 |
| 后端 | `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000` |
| 前端 | `npm run dev`，`:5173`，vite proxy `/api` → `:8000` |
| 浏览器 | Chromium headless，视口 1280×900，整页截图 |

## 九张对应关系

| 文件 | 页面 | 态 | 造态方式 |
|---|---|---|---|
| `01-risk-list-normal.png` | 风险列表 | 正常 | 真实后端，3 条 seed 提交（30.0% / 20.0% / 10.0%） |
| `02-risk-list-empty.png` | 风险列表 | 空数据 | 「最低风险」= 0.99 后查询 → 后端真实返回空集（不是前端 mock） |
| `03-risk-list-loading.png` | 风险列表 | 加载中 | 重写 `window.XMLHttpRequest` 使请求不发、永不返回，再点「查询」，表格显示 v-loading 遮罩 + 骨架 |
| `04-commit-detail-normal.png` | 提交详情 | 正常 | `/commit/000...001`，seed 预测行在库 |
| `05-trend-normal.png` | 趋势看板 | 正常 | `/trend` |
| `06-commit-detail-40400.png` | 提交详情 | 40400 | `/commit/ffff...ffff`（库中不存在），走 `40400` 分支提示 |
| `07-risk-list-error.png` | 风险列表 | 请求失败 | 停掉后端后重新加载页面 |
| `08-commit-detail-error.png` | 提交详情 | 请求失败 | 同上 |
| `09-trend-error.png` | 趋势看板 | 请求失败 | 同上 |

## 两点需要如实说明

1. **只有加载态是模拟的**：后端没有延迟开关，`03` 用 XHR 挂起制造；`02`/`07`/`08`/`09` 都是真实后端行为（空结果 / 服务不可达）。
2. **`07`/`08`/`09` 的文案是 axios 兜底**：显示 `Request failed with status code 502`（vite proxy 转发失败），不是契约 §5 的 `50000` 文案。若验收要求必须展示契约文案，需要让后端返回 5xx 而不是直接停进程 —— 那样才走 `50000` 分支，届时可重截这三张。
3. **提交详情没有独立「空数据」态**：`GET /api/commits/{hash}` 不存在即 `40400`，没有「有提交、无预测」的第三种空态（seed 三条提交都带预测）。所以详情页的第三张用 `40400` 而不是「空数据」。
