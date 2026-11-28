"""预测结果解释：SHAP / LIME / 置换重要性。"""

from __future__ import annotations

import numpy as np
from sqlalchemy import select

from app.constants import EXPERT_FEATURES, SEMANTIC_FEATURES, TECHNIQUES
from app.errors import AppError
from app.models import Model, Prediction, User
from app.services import predict
from data_model import ml


def _model_name_for(db, user: User, job_id: str, commit_hash: str, ref: dict) -> str:
    name = ref.get("model_name")
    if name:
        return name
    dataset = ref.get("_dataset")
    if dataset is not None:
        row = db.scalar(
            select(Prediction).where(
                Prediction.dataset_id == dataset.dataset_id,
                Prediction.commit_hash == commit_hash.lower(),
            )
        )
        if row is not None and row.model_name:
            return row.model_name
    raise AppError(40901, "该结果由导入模型产生，无法解释", {"reason": "model_unavailable"})


def _permutation(model, X: np.ndarray, background: np.ndarray, features: list[str]) -> list[dict]:
    base = float(ml.predict_scores(model, X)[0])
    median = np.median(background, axis=0) if len(background) else np.zeros(X.shape[1])
    items = []
    for index, name in enumerate(features):
        perturbed = X.copy()
        perturbed[0, index] = median[index]
        score = float(ml.predict_scores(model, perturbed)[0])
        items.append({"feature": name, "value": float(X[0, index]), "contribution": round(base - score, 6)})
    return items


def _lime(model, X: np.ndarray, background: np.ndarray, features: list[str]) -> tuple[list[dict], str | None]:
    try:
        from lime.lime_tabular import LimeTabularExplainer
    except Exception:  # noqa: BLE001
        return _permutation(model, X, background, features), "LIME 不可用，已回退置换重要性"
    if len(background) < 2:
        return _permutation(model, X, background, features), "样本不足，已回退置换重要性"
    try:
        explainer = LimeTabularExplainer(
            background, feature_names=features, mode="classification", discretize_continuous=True, random_state=42
        )
        explanation = explainer.explain_instance(
            X[0], lambda data: model.predict_proba(data), num_features=min(len(features), 20)
        )
        mapping = dict(explanation.as_list())
        items = []
        for index, name in enumerate(features):
            contribution = None
            for key, value in mapping.items():
                if key.split(" ")[0] == name or key == name:
                    contribution = float(value)
                    break
            items.append({"feature": name, "value": float(X[0, index]), "contribution": round(contribution or 0.0, 6)})
        return items, None
    except Exception:  # noqa: BLE001
        return _permutation(model, X, background, features), "LIME 解释失败，已回退置换重要性"


def _shap(model, X: np.ndarray, background: np.ndarray, features: list[str]) -> tuple[list[dict], str | None]:
    try:
        import shap
    except Exception:  # noqa: BLE001
        return _permutation(model, X, background, features), "SHAP 不可用，已回退置换重要性"
    try:
        sample = background if len(background) else X
        explainer = shap.Explainer(lambda data: model.predict_proba(data), sample[:50])
        values = explainer(X)
        array = np.asarray(values.values)
        if array.ndim == 3:
            array = array[0, :, -1]
        elif array.ndim == 2:
            array = array[0]
        items = [
            {"feature": name, "value": float(X[0, index]), "contribution": round(float(array[index]), 6)}
            for index, name in enumerate(features)
        ]
        return items, None
    except Exception:  # noqa: BLE001
        return _permutation(model, X, background, features), "SHAP 解释失败，已回退置换重要性"


def explain(db, user: User, job_id: str, commit_hash: str, technique: str) -> dict:
    if technique not in TECHNIQUES:
        raise AppError(40001, "解释方法非法")
    columns, rows, ref = predict.resolve_rows(db, user, job_id)
    line = ref.get("line") or "expert"
    features = EXPERT_FEATURES if line == "expert" else SEMANTIC_FEATURES
    if technique == "shap" and line == "semantic":
        raise AppError(40001, "语义向量模型不支持 SHAP，请选择 LIME 或置换重要性")
    model_name = _model_name_for(db, user, job_id, commit_hash, ref)
    model, _, _ = predict.load_saved_model(db, user, model_name)
    if isinstance(model, ml.TorchModel) and model.line and model.line != line:
        raise AppError(40001, "模型线与数据线不一致")
    target = None
    background = []
    for row in rows:
        if str(row.get("commit_id") or row.get("commit_hash") or "").lower() == commit_hash.lower():
            target = row
        elif len(background) < 100:
            background.append([float(row.get(name, 0) or 0) for name in features])
    if target is None:
        raise AppError(40401, "提交不存在")
    X = np.array([[float(target.get(name, 0) or 0) for name in features]], dtype=float)
    background_array = np.array(background, dtype=float) if background else X
    if technique == "permutation":
        items, note = _permutation(model, X, background_array, features), None
    elif technique == "lime":
        items, note = _lime(model, X, background_array, features)
    else:
        items, note = _shap(model, X, background_array, features)
    items.sort(key=lambda item: abs(item["contribution"]), reverse=True)
    if line == "semantic":
        items = items[:10]
    result_items = [
        {
            "feature": item["feature"],
            "contribution": item["contribution"],
            "direction": "positive" if item["contribution"] >= 0 else "negative",
        }
        for item in items
    ]
    return {"technique": technique, "items": result_items, "note": note}
