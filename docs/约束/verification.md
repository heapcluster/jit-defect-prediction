# 验证与完成定义

## 1 命令

| 范围 | 命令 | 通过标准 |
|---|---|---|
| 后端测试 | `cd backend && python -m pytest` | 全部通过 |
| 前端单测 | `cd frontend && npm run test:unit` | 全部通过 |
| 前端构建 | `cd frontend && npm run build` | 构建成功、无错误 |
| 前端规范 | `cd frontend && npm run lint` | 无错误 |
| 工程化自测 | `python -m pytest -q infra/tests` | 全部通过 |
| 全栈启动 | 本机分别启动 Uvicorn（`127.0.0.1:8000`）与 Vite（`127.0.0.1:5173`） | 两个进程可访问 |
| 健康检查 | `GET /api/health` | 返回 `code: 0` |

## 2 完成定义

一个功能点完成需同时满足：

1. 对应页面、接口、数据库文档中的验收条目全部可复现通过。
2. 后端新增接口有用例，覆盖成功、参数非法、未登录、非本人资源四种情况。
3. 前端页面具备加载、空态、错误、鉴权失效四种状态。
4. 列名、错误码、枚举取值与真源文档逐项一致。
5. 未新增未在文档中声明的接口、页面或配置项。

## 3 回归检查

- 两个账号交叉访问，确认资源不可见、下载返回 404。
- 页面刷新与重新登录后，进度能恢复。
- 重置后未入库产物与导入临时目录被清理，已保存数据集仍可用。
- 同来源再次保存（collect / clean / upload）命中覆盖键时更新原数据集、`dataset_id` 与 `created_at` 不变，成员替换为新结果；`split` / `prediction` 每次保存新增一条。
- 保存成功后本轮结果仍可预览、导出与下载（保存为复制，不移动 `outputs/`）。
- 输入含重复 `commit_hash` 的预测被拒绝；含重复哈希且未去重的清洗结果保存被拒绝。
- `Alice` 与 `alice` 可分别创建并登录，视为两个账号。
- 导出的 CSV / Excel 表头与字段契约一致；预测结果导出为原始列加 `risk_score`、`predicted_label`、`threshold`。
- 模型下载扩展名与 `model_artifact.format` 一致：sklearn 为 `.pkl`，dnn / tabnet 为 `.pt`。
- 登出后使用旧 Cookie 访问任一受保护接口返回 `40101`。
- `infra/schema.sql` 可执行；表名集合与 `docs/数据库/` 各表文档一一对应，共 15 张表。
