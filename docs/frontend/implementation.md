# 前端实现设计（三页面 + 联调）

> 负责人：刘帅华 ｜ 合并自原 `docs/implementation/frontend-design.md`（已并入本文件） ｜ 审核：蒋励
> 设计稿以 `frontend/pages.md` 为唯一字段依据。

## 1. 技术落地

- Vue 3 + Element Plus（组件）+ ECharts（所有图表）。
- 每个 `.vue` 顶部注释「本页用接口的哪些字段」（指 `pages.md`）。
- 三态（加载中/空数据/请求失败）必须各有注释标明——这是前端测试最低要求。
- 请求封装统一带 `X-API-Key`（构建期环境变量）。

## 2. 三页面实现要点

| 页面 | 关键实现 |
|---|---|
| 风险列表 | `el-table` 分页；`risk_score`×100 显示；点击行 `router.push` 带 `commit_hash`；筛选条件映射到 `min_risk`/`start_time`/`end_time`/`model_name` |
| 提交详情 | 风险解释条用横向 bar（`direction` 控制左右）；特征值按五维度 `el-descriptions` 分组；`explanation` 为空显示占位 |
| 趋势看板 | ECharts 折线（`avg_risk` 为 y、`period` 为 x）；汇总行加权；数据点<2 不渲染折线 |

## 3. 联调（与吕建江）

- 联调前先核对 `pages.md` 每个页面字段是否都在 `docs/backend/api-spec.md` 响应里存在；**列出「接口没有但页面要用」的字段**——这是最容易埋雷的核对。
- 影响接口的待确认项（分组/多模型对比）已在契约三 2026-09-19 冻结前反馈给吕建江。
- 三态与错误码照 `pages.md` §5。

## 4. 分步清单（F2/F3/F4）

| 步 | 动作 | 验收 | OpenSpec |
|---|---|---|---|
| F2 | 建 `frontend-integration` change（proposal+design+tasks+spec） | `openspec validate` 通过 | change 已立 |
| F3 | 实现三页面（字段照 `pages.md`，三态齐全） | 三页面可点开、阈值统一一处 | 按 tasks 勾选 |
| F4 | 前后端联调（#33 脚手架已合） | 字段对得上、空数据非错误 | PR 非作者审阅 |

## 5. 测试（前端部分，课程 40 分测试实践）

- 三态各有测试：加载中骨架、空数据文案、请求失败提示。
- 字段映射一致性：断言页面用的字段都在接口响应内（可用 mock 校验）。
- 至少 1 条正常路径 + 1 条异常路径（如 `40100`/`40400` 处理）。
