"""e2e 线模型定义：CodeBERT 骨干 + 二分类头（本线唯一做反向传播的模型）。

结构：`AutoModelForSequenceClassification(num_labels=2)` —— CodeBERT 编码器 +
[CLS] 之上的线性分类头，整网微调。与任务目标的匹配：输入是原始 diff 文本
（非表格特征），需要代码预训练表征；二分类头与 SZZ 主标签直接对应。
推理概率 = softmax(logits)[:, 1]。
"""

from __future__ import annotations

import numpy as np
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer


def build_model(text_model: str):
    return AutoModelForSequenceClassification.from_pretrained(text_model, num_labels=2)


def load_model(model_dir: str):
    return AutoModelForSequenceClassification.from_pretrained(model_dir, num_labels=2)


def load_tokenizer(source: str):
    return AutoTokenizer.from_pretrained(source)


@torch.no_grad()
def predict_proba(model, loader, device) -> np.ndarray:
    model.to(device).eval()
    out = []
    for batch in loader:
        inputs = {k: v.to(device) for k, v in batch.items() if k != "labels"}
        logits = model(**inputs).logits
        out.append(torch.softmax(logits, dim=1)[:, 1].cpu().numpy())
    return np.concatenate(out)
