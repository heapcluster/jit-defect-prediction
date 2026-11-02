# 提交详情页（CommitDetail）

## 页面与路由
- 页面名：提交详情
- 路由：`/commit/:hash`
- 入口：风险列表点击某行进入

## 布局
- 顶部：风险分 + 风险等级标签 + 模型名；提交元信息（hash / author / committed_at / message）
- 中部：风险解释条（explanation，正负贡献分色，按 |contribution| 降序取前 8 项）
- 下部：Kamei 14 维特征（按五维度分组：代码分布 / 规模 / 目的 / 历史 / 开发者经验）

## 交互
- 重新预测：选择在线模型 → `POST /api/predict`，刷新风险分 / 模型名 / 解释；
- 三态与错误码：加载中 / 空 / 失败；40001 / 40100 / 40400 / 50000。

## 数据接口
| 用途 | 接口 |
|---|---|
| 详情 | `GET /api/commits/{commit_hash}` |
| 重新预测 | `POST /api/predict` |

## 说明
- 真实缺陷标签（szz）展示依赖 `commit_label` 入库，当前无数据源，待后端补标签入库路径。
