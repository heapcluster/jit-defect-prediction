# 质量看板（QualityBoard）

## 页面与路由
- 页面名：质量看板
- 路由：`/quality`
- 入口：导航栏"质量"

## 布局
- 顶部：模型选择
- 主区：性能指标卡（AUC / PR / F1 等）
- 侧栏：阈值校准操作（基于人工标签）

## 交互
- 选择模型查看指标；
- 触发校准（写入 runtime_setting 高风险阈值）。

## 数据接口
| 用途 | 接口 |
|---|---|
| 指标 | `GET /api/quality?model_name=` |
| 校准 | `POST /api/quality/calibrate` |
| 标签样本 | `GET /api/quality/dataset` |
