"""expert 线模型定义：经典机器学习 6 种 + 神经网络 2 种（课程「2 类 ≥ 8 种」）。

与任务目标的匹配关系：
  · 表格型 14 维特征、中等样本量（5.9 万训练）→ 树模型/线性模型为主力；
  · lr / knn 对量纲敏感 → Pipeline 内置 StandardScaler（拟合在训练集内部，不泄漏）；
  · mlp_deep 开早停，验证子集只从训练集内部抽 —— 检验集始终时间在后，不构成「提前看未来」。
依赖版本以 requirements.txt 为准；换 sklearn 大版本可能改变结果，不要静默升级。
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
MODEL_CLASS = {
    "lr": "经典机器学习", "rf": "经典机器学习", "xgb": "经典机器学习",
    "nb": "经典机器学习", "dt": "经典机器学习", "knn": "经典机器学习",
    "mlp": "神经网络（深度学习）", "mlp_deep": "神经网络（深度学习）",
}
MODEL_CLASS = {
    "lr": "经典机器学习", "rf": "经典机器学习", "xgb": "经典机器学习",
    "nb": "经典机器学习", "dt": "经典机器学习", "knn": "经典机器学习",
    "mlp": "神经网络（深度学习）", "mlp_deep": "神经网络（深度学习）",
}
# 有精确 SHAP 解释器的模型（契约三 explanation 由 SHAP 产出）
SHAP_TREE_MODELS = {"rf", "xgb", "dt"}
SHAP_LINEAR_MODELS = {"lr"}
KNN_NEIGHBORS = 25   # 取奇数：二分类平票不会各占一半


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
        return GaussianNB()   # 对量纲单调变换不敏感，不标准化
    if name == "dt":
        return DecisionTreeClassifier(max_depth=12, min_samples_leaf=20,
                                      random_state=seed)
    if name == "knn":
        return Pipeline([("scaler", StandardScaler()),
                         ("knn", KNeighborsClassifier(n_neighbors=KNN_NEIGHBORS,
                                                      n_jobs=-1))])
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
