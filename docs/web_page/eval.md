# 测试集评估看板（TestSetEval）

## 页面与路由
- 页面名：测试集评估看板
- 路由：`/eval/test-set`
- 入口：导航栏"测试集评估"菜单（本次新增）

## 布局
- 顶部：模型切换器（`line` → `model`）
- 主区：测试集明细表
- 下方：性能图集

## 交互
1. 选 `line`（expert/semantic/fused/e2e）→ 选 `model`，下方联动刷新；
2. 明细表：commit 信息 + 14 维 + 真标签(szz) + 选中模型 `risk_score`/判定，支持排序/筛选/分页；
   - **e2e 行无特征列**（端到端模型无结构化特征），该列留空；
3. 图集：ROC/PR/混淆矩阵/校准曲线等，`<img>` 加载后端静态图。

## 数据接口
| 用途 | 接口 |
|---|---|
| 明细 | `GET /api/test-detail?model_name=&page=&sort=` |
| 图 | `GET /api/figures?model_name=` |

## 说明
- 真标签为 szz 口径，来自 `commit_label`；
- 特征只展示 Kamei 14 维。
