# 测试集评估看板（TestSetEval）

## 页面与路由
- 页面名：测试集评估看板
- 路由：`/eval/test-set`
- 入口：顶部导航 Tab「测试集评估」（本次新增）

## 布局
- 顶部：模型切换器（`line` → `model` 两级联动）
- 板块一「测试集信息 + 预测结果」：
  - 测试集逐条 commit 信息（hash / author / committed_at / message）
  - 真标签（szz）+ 选定模型的 `risk_score` / 判定
  - Kamei 14 维特征（仅 expert 线展示）
- 板块二「模型效果图」：选定模型的一组性能图

## 交互
1. 选 `line`（expert / semantic / fused / e2e）→ 选 `model`，两个板块联动刷新；
2. 明细表支持排序 / 筛选 / 分页；
3. 特征列展示规则：
   - **expert**：展示 Kamei 14 维（唯一可读、有意义的特征，按五维度分组）；
   - **semantic / fused / e2e**：不展示特征列——768 维语义向量 / 端到端向量不落关系表，
     仅展示 commit 信息 + 真标签 + 选定模型判断；
4. 图集：ROC / PR / 混淆矩阵 / 校准曲线 / 特征重要性，`<img>` 加载后端静态图，随 `model_name` 刷新。

## 数据接口
| 用途 | 接口 |
|---|---|
| 明细 | `GET /api/test-detail?model_name=&page=&size=&sort=&order=&q=&is_defect=` |
| 图 | `GET /api/figures?model_name=` |

## 说明
- 真标签仅取 `szz` 口径（来自 `commit_label`），`manual` 不纳入；
- 特征只展示 Kamei 14 维，语义 / 融合 / 端到端特征不落关系表；
- 图集由 `model_figure` 登记元数据、后端静态托管。
