"""模型构建、训练、保存与预测。sklearn 存 .pkl，dnn / tabnet 存单文件 .pt。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import joblib
import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from data_model import metrics as metric_lib

try:  # torch 是 dnn / tabnet 的运行时依赖
    import torch
    from torch import nn

    class _DNNModule(nn.Module):
        def __init__(self, input_dim: int, hidden_layers: list[int], dropout: float) -> None:
            super().__init__()
            layers: list[nn.Module] = []
            last = input_dim
            for width in hidden_layers:
                layers += [nn.Linear(last, int(width)), nn.ReLU(), nn.Dropout(float(dropout))]
                last = int(width)
            layers.append(nn.Linear(last, 1))
            self.net = nn.Sequential(*layers)

        def forward(self, x):  # noqa: ANN001
            return self.net(x).squeeze(-1)

except Exception:  # noqa: BLE001
    torch = None
    _DNNModule = None  # type: ignore

PT_MARK = "jit-pt-v1"
PYTORCH_ALGOS = {"dnn", "tabnet"}
RANDOM_STATE = 42


def _sklearn_estimator(algo: str, params: dict):
    p = dict(params or {})
    if algo == "lr":
        from sklearn.linear_model import LogisticRegression

        return LogisticRegression(C=float(p.get("C", 1.0)), max_iter=int(p.get("max_iter", 1000)), random_state=RANDOM_STATE)
    if algo == "dt":
        from sklearn.tree import DecisionTreeClassifier

        return DecisionTreeClassifier(max_depth=int(p.get("max_depth", 10)), min_samples_split=int(p.get("min_samples_split", 2)), random_state=RANDOM_STATE)
    if algo in ("rf", "et"):
        from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier

        cls = RandomForestClassifier if algo == "rf" else ExtraTreesClassifier
        return cls(n_estimators=int(p.get("n_estimators", 200)), max_depth=int(p.get("max_depth", 20)), n_jobs=-1, random_state=RANDOM_STATE)
    if algo == "ada":
        from sklearn.ensemble import AdaBoostClassifier

        return AdaBoostClassifier(n_estimators=int(p.get("n_estimators", 100)), learning_rate=float(p.get("learning_rate", 0.1)), random_state=RANDOM_STATE)
    if algo == "gbdt":
        from sklearn.ensemble import GradientBoostingClassifier

        return GradientBoostingClassifier(n_estimators=int(p.get("n_estimators", 200)), learning_rate=float(p.get("learning_rate", 0.1)), max_depth=int(p.get("max_depth", 3)), random_state=RANDOM_STATE)
    if algo == "xgb":
        from xgboost import XGBClassifier

        return XGBClassifier(n_estimators=int(p.get("n_estimators", 300)), learning_rate=float(p.get("learning_rate", 0.1)), max_depth=int(p.get("max_depth", 6)), random_state=RANDOM_STATE, eval_metric="logloss", n_jobs=-1, verbosity=0)
    if algo == "lgbm":
        from lightgbm import LGBMClassifier

        return LGBMClassifier(n_estimators=int(p.get("n_estimators", 300)), learning_rate=float(p.get("learning_rate", 0.1)), num_leaves=int(p.get("num_leaves", 31)), random_state=RANDOM_STATE, n_jobs=-1, verbose=-1)
    if algo == "svm":
        from sklearn.svm import SVC

        return SVC(C=float(p.get("C", 1.0)), kernel=str(p.get("kernel", "rbf")), gamma=p.get("gamma", "scale"), probability=True, random_state=RANDOM_STATE)
    if algo == "knn":
        from sklearn.neighbors import KNeighborsClassifier

        return KNeighborsClassifier(n_neighbors=int(p.get("n_neighbors", 5)), weights=str(p.get("weights", "uniform")))
    if algo == "mlp":
        from sklearn.neural_network import MLPClassifier

        layers = p.get("hidden_layers", [128, 64])
        return MLPClassifier(hidden_layer_sizes=tuple(int(x) for x in layers), alpha=float(p.get("alpha", 0.0001)), max_iter=int(p.get("max_iter", 1000)), random_state=RANDOM_STATE)
    raise ValueError(f"未知算法：{algo}")


def _preprocessor() -> Pipeline:
    return Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())])


@dataclass
class TorchModel:
    algo: str
    line: str
    feature_version: str
    features: list[str]
    params: dict
    preprocess: Pipeline
    net: object = None
    kind: str = "dnn"
    input_dim: int = 0
    hidden_layers: list[int] = field(default_factory=list)
    dropout: float = 0.0
    framework: str = "pytorch"
    format: str = "pt"

    def predict_proba(self, X) -> np.ndarray:
        if not len(X):
            return np.zeros(0)
        transformed = self.preprocess.transform(np.asarray(X, dtype=float))
        if self.kind == "tabnet":
            return np.asarray(self.net.predict_proba(transformed))[:, 1]
        self.net.eval()
        with torch.no_grad():
            logits = self.net(torch.tensor(transformed, dtype=torch.float32))
            return torch.sigmoid(logits).numpy()


def build_pipeline(algo: str, params: dict) -> Pipeline:
    return Pipeline([("preprocess", _preprocessor()), ("clf", _sklearn_estimator(algo, params))])


def _predict(model, X) -> np.ndarray:
    proba = model.predict_proba(X)
    proba = np.asarray(proba)
    return proba[:, 1] if proba.ndim == 2 else proba


def train_model(
    algo: str,
    params: dict,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_valid: np.ndarray | None = None,
    y_valid: np.ndarray | None = None,
    line: str = "expert",
    feature_version: str = "",
    features: list[str] | None = None,
):
    """返回 (model, framework, format, metrics)。"""
    features = features or []
    if algo in PYTORCH_ALGOS:
        if torch is None:
            raise RuntimeError("PyTorch 不可用")
        preprocess = _preprocessor()
        transformed = preprocess.fit_transform(X_train)
        if algo == "tabnet":
            from pytorch_tabnet.tab_model import TabNetClassifier

            p = dict(params or {})
            net = TabNetClassifier(n_d=int(p.get("n_d", 16)), n_a=int(p.get("n_a", 16)), seed=RANDOM_STATE, verbose=0)
            net.fit(
                transformed,
                y_train,
                epochs=int(p.get("epochs", 50)),
                batch_size=int(p.get("batch_size", 256)),
                virtual_batch_size=min(128, max(8, len(transformed) // 4 or 8)),
                drop_last=False,
            )
            model = TorchModel(algo=algo, line=line, feature_version=feature_version, features=features, params=p, preprocess=preprocess, net=net, kind="tabnet", input_dim=transformed.shape[1])
        else:
            p = dict(params or {})
            layers = [int(x) for x in p.get("hidden_layers", [256, 128])]
            dropout = float(p.get("dropout", 0.2))
            net = _DNNModule(transformed.shape[1], layers, dropout)
            optimizer = torch.optim.Adam(net.parameters(), lr=float(p.get("learning_rate", 0.001)))
            loss_fn = torch.nn.BCEWithLogitsLoss()
            dataset = torch.utils.data.TensorDataset(
                torch.tensor(transformed, dtype=torch.float32),
                torch.tensor(y_train, dtype=torch.float32),
            )
            loader = torch.utils.data.DataLoader(dataset, batch_size=int(p.get("batch_size", 256)), shuffle=True)
            net.train()
            for _ in range(int(p.get("epochs", 50))):
                for xb, yb in loader:
                    optimizer.zero_grad()
                    loss = loss_fn(net(xb), yb)
                    loss.backward()
                    optimizer.step()
            model = TorchModel(algo=algo, line=line, feature_version=feature_version, features=features, params=p, preprocess=preprocess, net=net, kind="dnn", input_dim=transformed.shape[1], hidden_layers=layers, dropout=dropout)
        train_scores = model.predict_proba(X_train)
        metrics = {
            "train": metric_lib.compute_metrics(y_train, train_scores, 0.5, ["accuracy", "precision", "recall", "f1", "auc", "mcc"])
        }
        if X_valid is not None and y_valid is not None and len(y_valid):
            valid_scores = model.predict_proba(X_valid)
            metrics["valid"] = metric_lib.compute_metrics(y_valid, valid_scores, 0.5, ["accuracy", "precision", "recall", "f1", "auc", "mcc"])
        return model, "pytorch", "pt", metrics

    pipeline = build_pipeline(algo, params)
    pipeline.fit(X_train, y_train)
    metrics = {
        "train": metric_lib.compute_metrics(y_train, _predict(pipeline, X_train), 0.5, ["accuracy", "precision", "recall", "f1", "auc", "mcc"])
    }
    if X_valid is not None and y_valid is not None and len(y_valid):
        metrics["valid"] = metric_lib.compute_metrics(y_valid, _predict(pipeline, X_valid), 0.5, ["accuracy", "precision", "recall", "f1", "auc", "mcc"])
    return pipeline, "sklearn", "pkl", metrics


def save_model(model, path: Path, framework: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if framework == "sklearn":
        joblib.dump(model, path)
        return
    payload = {
        "jit": PT_MARK,
        "algo": model.algo,
        "line": model.line,
        "feature_version": model.feature_version,
        "features": model.features,
        "params": model.params,
        "preprocess": model.preprocess,
        "kind": model.kind,
        "input_dim": model.input_dim,
        "hidden_layers": model.hidden_layers,
        "dropout": model.dropout,
    }
    if model.kind == "tabnet":
        payload["tabnet_model"] = model.net
    else:
        payload["state_dict"] = model.net.state_dict()
    torch.save(payload, path)


def load_model(path: Path):
    if path.suffix == ".pkl":
        return joblib.load(path)
    payload = torch.load(path, map_location="cpu", weights_only=False)
    if payload.get("jit") != PT_MARK:
        raise ValueError("模型文件缺少 jit-pt-v1 格式标记")
    model = TorchModel(
        algo=payload["algo"],
        line=payload["line"],
        feature_version=payload.get("feature_version") or "",
        features=payload.get("features") or [],
        params=payload.get("params") or {},
        preprocess=payload["preprocess"],
        kind=payload.get("kind", "dnn"),
        input_dim=payload.get("input_dim", 0),
        hidden_layers=payload.get("hidden_layers") or [],
        dropout=payload.get("dropout", 0.0),
    )
    if model.kind == "tabnet":
        model.net = payload["tabnet_model"]
    else:
        model.net = _DNNModule(model.input_dim, model.hidden_layers, model.dropout)
        model.net.load_state_dict(payload["state_dict"])
        model.net.eval()
    return model


def predict_scores(model, X) -> np.ndarray:
    return _predict(model, X)


def model_meta(model) -> dict:
    if isinstance(model, TorchModel):
        return {"framework": "pytorch", "format": "pt", "algo": model.algo, "line": model.line,
                "feature_version": model.feature_version, "features": model.features, "params": model.params}
    return {"framework": "sklearn", "format": "pkl", "n_features": getattr(model, "n_features_in_", None)}
