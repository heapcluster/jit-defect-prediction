# fused 线（Kamei14 ⊕ 语义 768 = 782 维）

> 定位：**对照线**。专家特征与语义向量拼接后训练，回答「两模态是否互补」。
>
> 配置项与产物的完整契约见 [`../config-and-output-spec.md`](../config-and-output-spec.md) §2。

## 设计思路

1. **双模态拼接**：Kamei 14（共享切分文件自带）⊕ semantic 线的冻结 CodeBERT 768 维
   编码，按 `commit_hash` 内连接对齐 → 782 维。
2. **同分类器族**：与 expert / semantic 完全一致的 12 个模型、超参、种子 —— 三线对比
   严格归因于特征模态（14 / 768 / 782 维）。
3. **依赖 semantic 的缓存**：本包不装 torch、不跑编码，吃
   `pipelines/semantic/data/semantic_embeddings.npz`（包间唯一的数据级衔接）。
   **跑序：先 semantic，后 fused。**

## 目录与文件

| 文件 | 内容 |
|---|---|
| `config.py` | 双模态路径、EXPECTED_DIM=782、切分路径、种子 |
| `data.py` | 切分加载 + 编码缓存读取 + 内连接拼接（覆盖率 < 99% 拒绝训练） |
| `model.py` | 12 分类器（与 expert 同款） |
| `metrics.py` | 两类指标（同口径） |
| `train.py` | 入口：对齐 → 拼接 → 训练 → 指标 → 产物 |
| `report.py` | Markdown + `figs/` 三张图 |

## 使用方法

```bash
cd data_model
python -m pipelines.semantic.train          # 先产出语义缓存（若没有）
python -m pipelines.fused.train             # 再跑本线
python -m pipelines.fused.train --models xgb,lr   # 只训子集
```

## 产物

| 路径 | 内容 | 入库 |
|---|---|---|
| `models/*_fused_v1.pkl` + `manifest.txt` | 分类器 + 输入口径说明 | 否 / 是 |
| `reports/model_metrics.md` + `figs/*.png` | 两类指标 + 图表 | 是 |

## 注意事项

- **覆盖率断言**：语义缓存与切分文件内连接后覆盖 < 99% 直接失败 —— 特征缺一大半
  的「融合」没有对比意义。
- 782 维里 768 维来自冻结编码器，量纲与 Kamei 特征不同；lr/knn 的 StandardScaler
  必须保留。
- 结论解读：fused 不优于 expert 时**如实登记**（语义无增量），并讨论可能原因。
- 产物**仅评估**，不进交付链。
