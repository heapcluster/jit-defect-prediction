# semantic 线（冻结 CodeBERT 语义特征）

> 定位：**对照线**。把「一次提交改了什么代码」用**冻结**的 CodeBERT 压成 768 维向量，
> 再走与 expert 完全相同的 12 个分类器 —— 与 baseline 的差异只归因于特征模态。
>
> 配置项与产物的完整契约见 [`../config-and-output-spec.md`](../config-and-output-spec.md) §1。

## 设计思路

1. **冻结 = 不训练 CodeBERT**：只做前向 mean-pool 提向量，没有反向传播——所以 GPU
   不是**硬依赖**。但 8.4 万条 × 512 token 的 Transformer 前向本身就是重活：CPU 约
   50–150ms/条（全量数小时~半天），**实际请按「需要 GPU」规划**，CPU 只够 `--limit`
   冒烟；真正被训练的只有 12 个分类器（sklearn，CPU 秒级）。
2. **同切分、同分类器族**：训练/检验行来自 `data/split_szz_{train,test}.csv` 的
   `commit_hash`；分类器超参与 expert 逐字一致 —— 跨线对比才干净。
3. **编码缓存**：`data/semantic_embeddings.npz`（hash + 768 维 + 标签），
   二次运行秒级；**fused 线直接吃这份缓存**（包间唯一的数据级衔接）。

## 目录与文件

| 文件 | 内容 |
|---|---|
| `config.py` | 编码器名、MAX_LEN=512、batch、文本/缓存路径、切分路径、种子 |
| `data.py` | 文本加载 / 自建文本（自包含，格式与 e2e 一致）/ 冻结编码 / 缓存读写 / 切分对齐 |
| `model.py` | 冻结编码器装载 + 分类器定义（默认训练 8 个，注册表 12 个） |
| `metrics.py` | 两类指标（与 expert 同口径） |
| `train.py` | 入口：文本 → 编码（缓存）→ 对齐 → 训练 → 指标 → 产物 |
| `report.py` | Markdown + `figs/` 三张图（命名与 expert 一致） |

## 使用方法

```bash
cd data_model
# 首次：需要文本。二选一：
#   a) 传 --repo 让本包自建：python -m pipelines.semantic.train --repo ../data/camel
#   b) 复用 e2e 已建的文本：python -m pipelines.semantic.train \
#        --text-csv pipelines/e2e/data/commit_text.csv
# 之后（有缓存）：
python -m pipelines.semantic.train
python -m pipelines.semantic.train --force-encode   # 忽略缓存重编码
python -m pipelines.semantic.train --models lr,xgb  # 只训子集
```

## 产物

| 路径 | 内容 | 入库 |
|---|---|---|
| `data/semantic_embeddings.npz` | 编码缓存（hash + 768 维 + 标签） | 否 |
| `models/*_semantic_v1.pkl` + `manifest.txt` | 分类器 + 编码器说明 | 否 / 是 |
| `reports/model_metrics.md` + `figs/*.png` | 两类指标 + 图表 | 是 |

## 注意事项

- **单条文本上限** `MAX_CHARS=4000`：512 token ≈ 2000 字符，超大 diff 截断并如实登记。
- **首次编码要联网**下载 `microsoft/codebert-base`（~500MB）；离线设 `HF_HUB_OFFLINE=1`。
- **编码耗时**：CPU 约 50–150ms/条，全量数小时级；4060 上批量十几分钟。先 `--models lr`
  小规模冒烟，再全量。
- 语义指标**不优时如实报告**（样本量、文本构造、模型容量），不得只报更好的一组。
- 产物**仅评估**，不进 expert 的交付链。
