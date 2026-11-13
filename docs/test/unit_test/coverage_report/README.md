# 覆盖率报告

**当前状态：报告未入库，本目录无 HTML / PDF 产物。** 2026-11-12 本机实跑行覆盖 85%（分支 336，40 部分覆盖，`afdee84`），但 HTML 产物未随提交归档，本地亦无 `htmlcov` 目录，**不能作为本次交付的覆盖率证明**（红线：覆盖率报告伪造该测试类型计 0 分；历史数值不得沿用）。

## 1 · 生成与归档

```powershell
cd backend
python -m pytest -q --cov=app --cov-branch --cov-report=html:htmlcov --cov-report=term-missing
```

把 `htmlcov/` 拷入本目录，按最终提交 SHA 命名，例如 `htmlcov-<sha>/` 与 `coverage-<sha>.pdf`，并在 [`../../README.md`](../../README.md) §6 登记环境、命令与被测 SHA。课程要求 **HTML 报告 + PDF 截图**；PDF / 截图须由实际操作者从真实 HTML 报告导出或采集，不得由 AI 生成或使用旧版本图片。

## 2 · 归档清单（上传前核对）

| 项 | 状态 |
|---|---|
| 后端 HTML 报告（`htmlcov-<sha>/`） | 待按最终 SHA 生成 |
| 后端 PDF / 截图（`coverage-<sha>.pdf`） | 待人工采集 |
| 前端覆盖率（`npm run test:unit -- --coverage`） | 待 CI 覆盖率插件合入后生成 |
| 模型线覆盖率 | 未要求，但如引用须同样按同一 SHA 实跑 |
| 行覆盖 ≥80% / 分支覆盖 ≥70% 的核算 | 待报告生成后填写，分支覆盖加分项须单独列出 |

## 3 · 约束

- 报告未生成前不得宣称覆盖率达标；[`../README.md`](../README.md) §4 与顶层统计表中的 85% 只标注为 `afdee84` 历史记录值。
- 归档前检查报告不含本机绝对路径、密钥、令牌或真实数据集内容。
