# pipelines/ — 四条模型线（各自独立成包）

> 每条线一个**独立功能包**，禁止合并为单一包；包间只通过**数据文件**衔接，不互相 import。

## 统一目录结构（四包一致，命名规范一致）

```
pipelines/<line>/
├── __init__.py        # 包标识
├── config.py          # 配置集中管理：路径、超参数、特征列、种子
├── data.py            # 数据加载与预处理（含校验断言）
├── model.py           # 模型定义（与该线任务目标严格匹配）
├── metrics.py         # 两类指标（口径与 06_train_model.py 逐字一致）
├── train.py           # 训练 + 验证主流程（唯一入口）
├── report.py          # 结果报告生成（Markdown 表格 + matplotlib 图表）
├── README.md          # 技术说明：设计思路 / 参数 / 用法 / 注意事项
├── requirements.txt   # 本线依赖（精确版本）
├── data/              # 中间数据与预测产物（.gitignore 排除）
├── models/            # 模型产物（.pkl / HF 权重，不入库）
└── reports/           # 指标报告 + 图表（可入库，横向比对的证据）
```

## 四条线一览

| 包 | 输入 | 模型 | 定位 | 需要 GPU |
|---|---|---|---|---|
| `expert/` | Kamei 14 特征（`data/split_szz_*.csv`） | 经典 ML 6 + 神经网络 2（sklearn/xgb） | **baseline** | 否 |
| `semantic/` | commit diff 文本 → 冻结 CodeBERT 768 维向量 | 同上 8 种 | 对照线：纯语义模态 | **建议**（CPU 仅够冒烟） |
| `fused/` | Kamei 14 ⊕ 语义 768 = 782 维 | 同上 8 种 | 对照线：特征融合 | 否（吃 semantic 缓存） |
| `e2e/` | commit diff 文本 → CodeBERT **微调** | CodeBERT + 二分类头 | 对照线：端到端 | **是**（唯一反向传播） |

## 数据流（跑序）

```
data_model 01–05（共享上游：样本集 / 切分 / 原始特征）
      │
      ├─→ expert/train.py          ← 直接吃 split_szz_*.csv
      ├─→ semantic/train.py        ← 文本 → 冻结编码缓存 data/semantic_embeddings.npz
      ├─→ fused/train.py           ← 吃 expert 的 split + semantic 的缓存
      └─→ e2e/build_text_dataset.py → e2e/train.py（微调）
```

- **同一切分**：四条线的训练/检验集都来自 `data/split_szz_{train,test}.csv` 的
  `commit_hash`（时间序 70/30），跨线指标天然可比（Gate G3）。
- **同一套指标**：各包 `metrics.py` 与 `data_model/06_train_model.py` 逐字同口径
  （含随机基线种子 0 / 200 次抽样），横向对比不需要换算。
- **报告可横向对比**：各包 `reports/model_metrics.md` 表结构一致；图表命名统一
  （`figs/roc_curves.png`、`figs/effort_curves_loc.png`、`figs/metric_bars.png`）。

## 通用命令（在 `data_model/` 目录下）

```bash
python -m pipelines.expert.train        # baseline（CPU，约 10 分钟）
python -m pipelines.semantic.train      # 需先有文本（见该包 README）
python -m pipelines.fused.train         # 需先跑 semantic 产出编码缓存
python -m pipelines.e2e.build_text_dataset && python -m pipelines.e2e.train   # 需 GPU
```

## 对照汇总

四条线跑完后，把各包 `reports/model_metrics.md` 的「Effort-unaware」表与
「Effort-aware / P_norm(model 排序)」行并排即得跨线对比；expert 一列就是 baseline。
