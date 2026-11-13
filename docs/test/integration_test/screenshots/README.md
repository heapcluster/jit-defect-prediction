# 前后端联调记录

课程 §3.3 要求「前端调用后端接口的测试截图或录屏，证明数据契约匹配」。为避免同一份证据存两份，浏览器截图统一放在 [`../../system_test/execution_records/`](../../system_test/execution_records/)，本目录只作索引。

| 证据 | 对应联调场景 |
|---|---|
| `risk-list-2026-11-12T09-09-57-241Z.png` | `GET /api/commits` → 风险列表分页、排序、模型级联 |
| `commit-detail-2026-11-12T09-10-10-400Z.png` | `GET /api/commits/{hash}` → 详情、解释、定位、修复参考 |
| `trend-board-2026-11-12T09-10-30-729Z.png` | `GET /api/trends` → 周粒度趋势 |
| `model-performance-2026-11-12T09-10-45-181Z.png` | `GET /api/figures` + 性能评估区 |
| `commit-not-found-*.png`、`not-found-*.png` | 40400 / 未知路由异常态 |
| `backend/scripts/evidence/2026-11-12-linkage.md` / `.json` | `linkage_capture.py` 的 12 次真实请求（含 2 个异常），逐端点包络 / 字段形状留痕 |

环境与基线见 [`../report.md`](../report.md) §9.2；四类产物 SHA 对照见 [`../../README.md`](../../README.md) §6（证据来自 `afdee84`，文档副本同步于 `bd39d95`，最终交付须同一 SHA 复跑）。

## 待补（如实申报）

- 按 `todo/neon-1-测试-集成测试.md` 的验收清单，**逐接口联调截图尚未齐全**：当前为四页面 + 两种异常态，缺按 11 个端点一一对应的界面 / 请求响应对照截图。课程按「前后端联调记录」给分，缺口须在 [`../../README.md`](../../README.md) §8 中保持可见。
- 补齐后在此登记文件名、被测提交 SHA、浏览器与环境；截图上传前须检查不含密钥、令牌、本机绝对路径等敏感信息。
- 截图须人工采集，AI 不生成、不补画；系统测试与验收执行的截图不能互相替代。
