# 功能点 8 缺陷定位及修复

一句话：给定一次预测与仓库提交，按可疑文件/行排序给出证据与四段式修复建议，交付定位表、证据 JSON 与建议文档。

实现状态：已实现（无可靠补丁时只交付建议）　期次：一期

localization 列契约；API 见 [`../api/source.md`](../api/source.md)；页面见 [`../web_page/predict_detail.md`](../web_page/predict_detail.md)。入口唯一：从预测结果行进入的预测详情页进入，不在预测配置页重复提供按钮。预测详情页在预测详情信息之后提供当前 commit 的“缺陷定位及修复”普通板块，支持展示源码、标出可疑代码行并给出修复建议；UI 不刻意展示功能编号 ⑧；补丁只预览不应用。

## 1 职责

- 读取 Git 对象（目录树、文件内容），提供行窗口浏览。
- 结合特征/预测与改动范围，按权重合成可疑文件与行排序。
- 汇总证据（命中原因、改动行、相关提交）并生成建议。
- 无可靠补丁时明确说明，不伪造 diff。

## 2 不负责

- 不重算模型预测，不训练、不评估、不解释。
- 不修改仓库、不执行仓库代码、不写业务表。
- 不保证一定给出补丁：证据不足时只给建议。

## 3 输入

| 输入 | 说明 |
|---|---|
| 仓库定位 | `repo_source` 或 `dataset_id`（二选一） |
| 提交 | `commit_hash`（40 位十六进制） |
| 特征/预测 | 既有数据或上传文件 |
| 配置 | `weights`、`top_n{files,lines}`、`file_size_max`、`suggestion_sources`、`patch_preview`、`format`、`model_name` |

## 4 流程

1. 解析仓库与提交，读取目录树（最多 1000 条）。
2. 定位可疑文件，读取文件行窗口（≤2000 行，单文件上限可配）。
3. 按权重合成文件/行分数并截断 `top_n`。
4. 汇总证据，生成四段式建议（问题说明、建议修改、风险提示、参考依据）。
5. 发布 CSV/XLSX、evidence JSON、suggestions Markdown 与 manifest。

## 5 输出

```text
localization_localization_<job_id>.csv / .xlsx
localization_evidence_<job_id>.json
localization_suggestions_<job_id>.md
<stem>.manifest.json
```

响应内 `localization` 只回前 20 行，完整内容在文件里。

## 6 约束

- 二进制或非 UTF-8 文件不返回内容（`status=binary`）。
- 超限文件返回 `too_large`，不截断后伪装成完整内容。
- 行窗口上限 2000 行；路径必须是安全相对路径。
- 建议来源仅 `template|llm|history`，非空且唯一。

## 7 验收

- tree/file 对同一提交稳定返回，路径穿越与非法行范围被拒绝。
- 定位结果含文件、行号、优先程度与证据。
- 无可靠补丁时明确提示，不输出空 diff。
- 产物可下载，列符合 localization 列契约。
- 不修改仓库、不执行仓库代码。

## 8 边界

定位是独立工具，页面入口挂在预测页下，但运行不依赖预测是否先执行；证据不足时降级为建议交付。



