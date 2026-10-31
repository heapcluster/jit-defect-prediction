# PR 详情页（PrDetail）

## 页面与路由
- 页面名：PR 详情
- 路由：`/prs/:number`
- 入口：PR 列表点击进入

## 布局
- 顶部：PR 元信息（编号 / 标题 / 作者 / 门禁结论）
- 中部：该 PR 各提交的风险分列表（按模型）
- 下部：门禁说明（阈值来源）

## 交互
- 选择模型（model_name）查看对应风险；
- 展示门禁 pass/block 结论。

## 数据接口
| 用途 | 接口 |
|---|---|
| PR 详情 | `GET /api/prs/{number}?model_name=` |
| 门禁 | `GET /api/prs/{number}/gate?model_name=` |
