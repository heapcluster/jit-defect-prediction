# 蒋励（@jolly326）— 组长 / 数据与模型线

> 更新 2026-10-24 ｜ 变更需本人在 PR 里确认 ｜ 上位规则：`docs/repo/collaboration.md`

## 1. 负责范围（有权直接改）

- `data_model/**`：数据管道 01–05、`expert` / `semantic` / `fused` / `e2e` 四条线训练与评估、`pipelines/verify_all_weights.py`
- `docs/model/**` 全部（含 `model-line-plan.md` 这个模型线唯一权威入口）
- `data_model/pipelines/expert/models/feature_order.txt`、`manifest.txt` 等交付清单
- `docs/repo/defect-records.md` 的模型线条目（D-xx）
- 跨线裁定：D 类缺陷的处置方案、Sprint 范围取舍

## 2. 不越界（这些必须找别人）

| 事项 | 找谁 |
|---|---|
| 契约二/三的字段与错误码变更、OpenSpec 活规格改写、change 归档 | 苏哲勋 |
| 前端页面、组件、联调记录 | 刘帅华 |
| 后端接口实现、鉴权、安全脚本 | @s1mple-less |
| 数据源口径与飞书 PRD 镜像 | 与苏哲勋双签，单方不算 |

## 3. 交付物与验收

- **数据**：`dataset_szz.csv` 等 4 份 CSV 的 SHA256 与 `ENVIRONMENT.md` §4 表一致；重跑必须重新登记哈希
- **模型**：8 个训练口径权重的 `manifest.txt` md5 + 类路径 + 特征宽度可校验（`verify_all_weights --check`）
- **报告**：`model_metrics.md`（训练）+ `model_metrics_from_saved.md`（`--from-saved` 复算，必须与前者物理隔离）
- **验收**：`pytest data_model/tests` 全绿；报告结论必须由结果现算，禁止硬编码数字

## 4. 原则（做取舍时按这个顺序）

1. **证据优先于结论。** 没有可复现命令与输出的结论不写进文档；写"已验证"就必须能指出哪条命令、哪份输出。
2. **不为自己改标准。** 指标不达标先查根因（D-14 就是先测出 SHAP 782ms 才敢定"不改靶子"），改靶子/改口径是最后手段且必须双签。
3. **能力不轻易缩水。** 三模型可切换是交付承诺，遇到性能问题优先优化而不是砍范围；砍范围必须走 change 并留档。
4. **口径单点。** 同一件事只允许一个权威位置（数据→`data-pipeline.md`、特征→`feature-columns.md`、方案→`model-line-plan.md`），别处只能引用。
5. **诚实标注缺口。** 未执行的验收项写"未执行 + 责任 + 回填条件"，不许勾成已完成；带缺口归档必须在状态行写明边界。

## 5. 签字权

- `data_model/**`、`docs/model/**` 类 PR 的批准（模型线）
- `docs/repo/defect-records.md` 中 D 类缺陷的处置结论
- 跨线争议的最终裁定（与苏哲勋无法一致时，由组长定并记录理由）

## 6. 现阶段待办

**本节不维护任务清单。** 按 `AGENTS.md` 硬红线「任务与进度只在飞书，仓库里没有任务清单」，动态待办一律回飞书看板维护——写进仓库的待办在合入当天就会过期，反而让「唯一事实来源」从落地第一天就失效。

本文件只保留**稳定**内容：职责边界、决策原则、签字权。当前在办事项请到飞书看板查。
