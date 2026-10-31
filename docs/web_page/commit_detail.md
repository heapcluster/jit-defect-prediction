# 提交详情页（CommitDetail）

## 页面与路由
- 页面名：提交详情
- 路由：`/commits/:hash`
- 入口：风险列表 / 提交列表点击某行进入

## 布局
- 顶部：提交元信息（hash / author / committed_at / message）
- 中部：Kamei 14 维特征展示
- 下部：各模型 risk_score 列表 + 判定

## 交互
- 切换模型查看不同风险分；
- 关联 PR / 标签信息展示。

## 数据接口
| 用途 | 接口 |
|---|---|
| 详情 | `GET /api/commits/{commit_hash}` |
