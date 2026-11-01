"""对测试集跑 25 个模型，返回 (样本表, 预测长表, 各模型概率, 模型对象, 14 维矩阵)。

- expert  : 14 维 → 8 个 joblib pkl
- semantic: npz 的 768 维 → 8 个 joblib pkl
- fused   : 14 ⊕ 768 = 782 维 → 8 个 joblib pkl
- e2e     : 直接读现成 prediction_result.csv（全量含检验集）
"""

from __future__ import annotations

import sys

import joblib
import numpy as np
import pandas as pd

from . import config


def load_test() -> pd.DataFrame:
    if not config.TEST_CSV.is_file():
        raise SystemExit(f"[eval] 找不到测试集：{config.TEST_CSV}")
    df = pd.read_csv(config.TEST_CSV)
    missing = [c for c in config.FEATURE_FIELDS + ["commit_hash", config.LABEL_COL] if c not in df]
    if missing:
        raise SystemExit(f"[eval] 测试集缺列：{missing}")
    return df.sort_values(["committed_at", "commit_hash"]).reset_index(drop=True)


def load_embeddings() -> tuple[dict[str, int], np.ndarray]:
    if not config.EMBEDDINGS_NPZ.is_file():
        raise SystemExit(f"[eval] 找不到语义编码缓存：{config.EMBEDDINGS_NPZ}")
    z = np.load(config.EMBEDDINGS_NPZ, allow_pickle=False)
    emb = z["embeddings"]
    if emb.ndim != 2 or emb.shape[1] != 768:
        raise SystemExit(f"[eval] 编码维度异常：{emb.shape}（期望 N×768）")
    hashes = [str(h) for h in z["commit_hash"]]
    return {h: i for i, h in enumerate(hashes)}, emb


def _patch_torch_cpu() -> None:
    """部分 tabnet 模型是在 CUDA 上存的 pkl；本机无 CUDA 时强制 map_location=cpu。"""
    import torch

    if getattr(torch, "_jit_cpu_patched", False):
        return
    orig = torch.load

    def _load(*args, **kwargs):
        kwargs.setdefault("map_location", torch.device("cpu"))
        return orig(*args, **kwargs)

    torch.load = _load
    torch._jit_cpu_patched = True


def _force_cpu(model) -> None:
    import torch

    if hasattr(model, "named_steps"):
        for step in model.named_steps.values():
            _force_cpu(step)
    inner = getattr(model, "model_", None)
    if inner is not None:
        if hasattr(inner, "device"):
            inner.device = torch.device("cpu")
        net = getattr(inner, "network", None)
        if net is not None:
            net.to(torch.device("cpu"))
    if hasattr(model, "device"):
        try:
            model.device = torch.device("cpu")
        except (AttributeError, TypeError):
            pass


def _load_model(path):
    _patch_torch_cpu()
    try:
        model = joblib.load(path)
    except AttributeError:
        # 旧产物把包装类 pickle 成 __main__.TabNetWithEarlyStop，注入别名后重试
        from pipelines.expert.model import TabNetWithEarlyStop

        import __main__

        if not hasattr(__main__, "TabNetWithEarlyStop"):
            __main__.TabNetWithEarlyStop = TabNetWithEarlyStop
        model = joblib.load(path)
    _force_cpu(model)
    return model


def predict_all() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, np.ndarray], dict, np.ndarray]:
    test = load_test()
    hashes = test["commit_hash"].to_numpy()
    y = test[config.LABEL_COL].astype(int).to_numpy()

    emb_index, emb = load_embeddings()
    miss = [h for h in hashes if h not in emb_index]
    if miss:
        raise SystemExit(f"[eval] 编码缓存缺 {len(miss)} 条测试集提交（例：{miss[0]}）")

    X14 = test[config.FEATURE_FIELDS].to_numpy(dtype=float)
    Xsem = emb[[emb_index[h] for h in hashes]]
    Xfused = np.concatenate([X14, Xsem], axis=1)

    X_by_line = {"expert": X14, "semantic": Xsem, "fused": Xfused}

    probas: dict[str, np.ndarray] = {}
    models: dict[str, object] = {}
    rows = []
    for line in config.LINES:
        X = X_by_line[line]
        for algo in config.ALGOS:
            name = config.model_name(line, algo)
            pkl = config.models_dir(line) / f"{name}.pkl"
            if not pkl.is_file():
                print(f"[eval] 缺模型，跳过：{pkl}", file=sys.stderr)
                continue
            model = _load_model(pkl)
            proba = model.predict_proba(X)[:, 1]
            probas[name] = proba
            models[name] = model
            fv = config.FEATURE_VERSION[line]
            for h, s in zip(hashes, proba, strict=True):
                rows.append((line, name, h, float(s), fv))
            print(f"[eval] {name:<22} AUC={_auc(y, proba):.4f}")

    # e2e：读现成全量预测
    pred = pd.read_csv(config.E2E_PRED_CSV)
    pred = pred[pred["model_name"] == config.E2E_MODEL_NAME]
    m = dict(
        zip(
            pred["commit_hash"].astype(str),
            pred["risk_score"].astype(float),
            strict=True,
        )
    )
    missing = [h for h in hashes if h not in m]
    if missing:
        raise SystemExit(f"[eval] e2e 预测缺 {len(missing)} 条测试集提交（例：{missing[0]}）")
    proba = np.array([m[h] for h in hashes], dtype=float)
    probas[config.E2E_MODEL_NAME] = proba
    for h, s in zip(hashes, proba, strict=True):
        rows.append(("e2e", config.E2E_MODEL_NAME, h, float(s), "codebert"))
    print(f"[eval] {config.E2E_MODEL_NAME:<22} AUC={_auc(y, proba):.4f}")

    preds = pd.DataFrame(
        rows,
        columns=["line", "model_name", "commit_hash", "risk_score", "feature_version"],
    )
    return test, preds, probas, models, X14


def _auc(y: np.ndarray, proba: np.ndarray) -> float:
    from sklearn.metrics import roc_auc_score

    return float(roc_auc_score(y, proba))
