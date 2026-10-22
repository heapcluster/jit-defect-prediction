# e2e 线（CodeBERT 端到端微调）

> 定位：**对照线**。直接把「一次提交改了什么代码」喂给 CodeBERT **微调**（整网反向传播），
> 与 expert（Kamei14 特征）对比。四条线里**唯一需要 GPU** 的一条（RTX 4060 即可）。
> 默认不进交付链；是否进前端 switch 由后续契约变更决定。
>
> 配置项、产物与 `prediction_result.csv` 字段的完整契约见
> [`../config-and-output-spec.md`](../config-and-output-spec.md) §3。

## 设计思路

1. **任务匹配**：输入是原始 diff 文本（非表格特征），需要代码预训练表征 ——
   `codebert-base` + [CLS] 二分类头，整网微调；概率 = softmax(logits)[:,1]。
2. **同切分**：训练/检验按共享切分 `data/split_szz_{train,test}.csv` 的 commit_hash
   对齐（缺切分文件时按时间序尾部分留验兜底，并在报告标注）—— 与其它三线可比。
3. **可复现**：种子全固定；GPU 非确定性算子可能带来极小抖动，报告登记设备。

## 目录与文件

| 文件 | 内容 |
|---|---|
| `config.py` | 骨干名、MAX_LEN=512、epochs/lr/batch、路径、`feature_version=codebert` |
| `data.py` | 文本加载、共享切分对齐、TextDataset、工作量（LOC） |
| `model.py` | CodeBERT 分类器构建/装载 + 批量推理 |
| `metrics.py` | 两类指标（与 expert 同口径） |
| `train.py` | 入口：Trainer 微调（CUDA 自动 + fp16 + best model 回载）→ 指标 → 保存 |
| `report.py` | Markdown + `figs/` 图表（ROC / effort 曲线） |
| `build_text_dataset.py` | ⑩ diff 文本提取（自包含，格式与 semantic 互通） |
| `predict.py` | ⑦ 等价：全量推理，输出对齐契约一表三的 `prediction_result.csv` |

## 使用方法

```bash
cd data_model
# 依赖统一在 data_model/environment.yml（本包不再有 requirements.txt）
conda env create -f environment.yml                  # 首次建环境
conda activate jit-defect-prediction                 # 必须在装 CUDA 版 / 跑训练前激活
pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cu124  # 4060 必装 CUDA 版

python -m pipelines.e2e.build_text_dataset            # ⑩ 文本
python -m pipelines.e2e.train                         # ⑬+⑭ 微调 + 验证（自动 GPU）
python -m pipelines.e2e.predict                       # ⑦ 全量推理（对照用）
```

## 产物

| 路径 | 内容 | 入库 |
|---|---|---|
| `models/codebert_e2e_v1/` | HF 格式微调权重 + tokenizer（含 checkpoints/，限保留 1 个） | 否 |
| `reports/model_metrics.md` + `figs/*.png` | 两类指标 + 图表 | 是 |
| `data/prediction_result.csv` + `prediction_stats.md` | 全量预测（`feature_version=codebert`） | 否 / 是 |

## 注意事项

- **显存**：CodeBERT-base + batch 16（有效 32）在 8GB 显存可跑；OOM 就把
  `--batch-size` 降到 8（累积步自动补到有效 32）。
- **文本上限** `MAX_CHARS=4000`：超大 diff 截断；合并提交按第一父提交取 diff。
- **首次联网**下载 codebert-base（~500MB）；离线先缓存 + `HF_HUB_OFFLINE=1`。
- `feature_version` 写 `codebert` —— 后端若加载需先登记该版本。
- 微调慢是预期：4060 上约 1–2 小时/4 epoch（8.4 万条 × 512 token）；先 `--epochs 1`
  冒烟再全量。
