"""fused 线模型定义：与 expert / semantic 完全同款的 8 分类器。

理由：三条线的分类器族、超参、种子全部一致，唯一变量是输入特征（14 维 / 768 维 /
782 维拼接）—— 跨线对比才严格归因于「特征模态」。lr/knn 前置 StandardScaler：
语义向量与 Kamei 特征量纲不同，标准化必不可少。
"""

from __future__ import annotations

from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

MODEL_NAMES = {
    "lr": "逻辑回归", "rf": "随机森林", "xgb": "XGBoost",
    "nb": "高斯朴素贝叶斯", "dt": "决策树", "knn": "k 近邻",
    "mlp": "多层感知机（1 隐藏层）", "mlp_deep": "多层感知机（3 隐藏层 + 早停）",
}


def build_model(name: str, seed: int):
    if name == "lr":
        return Pipeline([("scaler", StandardScaler()),
                         ("lr", LogisticRegression(max_iter=1000, random_state=seed))])
    if name == "rf":
        return RandomForestClassifier(n_estimators=300, min_samples_leaf=2,
                                      random_state=seed, n_jobs=-1)
    if name == "xgb":
        from xgboost import XGBClassifier
        return XGBClassifier(n_estimators=300, learning_rate=0.1, max_depth=6,
                             subsample=0.9, colsample_bytree=0.9,
                             random_state=seed, n_jobs=-1, eval_metric="logloss")
    if name == "nb":
        return GaussianNB()
    if name == "dt":
        return DecisionTreeClassifier(max_depth=12, min_samples_leaf=20,
                                      random_state=seed)
    if name == "knn":
        return Pipeline([("scaler", StandardScaler()),
                         ("knn", KNeighborsClassifier(n_neighbors=25, n_jobs=-1))])
    if name == "mlp":
        return Pipeline([("scaler", StandardScaler()),
                         ("mlp", MLPClassifier(hidden_layer_sizes=(32,),
                                               max_iter=500, random_state=seed))])
    if name == "mlp_deep":
        return Pipeline([("scaler", StandardScaler()),
                         ("mlp", MLPClassifier(hidden_layer_sizes=(64, 32, 16),
                                               max_iter=500, alpha=1e-4,
                                               early_stopping=True,
                                               n_iter_no_change=15,
                                               validation_fraction=0.1,
                                               random_state=seed))])
    raise ValueError("未知模型：%s" % name)
