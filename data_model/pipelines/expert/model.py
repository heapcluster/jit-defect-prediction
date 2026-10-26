"""expert 线模型定义：经典机器学习 9 种 + 神经网络 2 种（课程「2 类 ≥ 8 种」）。

与任务目标的匹配关系：
  · 表格型 14 维特征、中等样本量（5.9 万训练）→ 树模型/线性模型为主力；
  · lr / knn / svm 对量纲敏感 → Pipeline 内置 StandardScaler（拟合在训练集内部，不泄漏）；
  · mlp_deep / tabnet 开早停，验证子集只从训练集内部抽 —— 检验集始终时间在后，
    不构成「提前看未来」。
依赖版本以 data_model/environment.yml 为准；换 sklearn 大版本可能改变结果，不要静默升级。

性能优先选型（2026-10-14）：lgbm / et / svm / tabnet 四种在
docs/model/model-line-plan.md §2.3 登记。此前四线分包迁移时这一节被
遗漏，本文件仅保留旧 8 模型 —— 现已完整迁回，见下方 build_model。
"""

from __future__ import annotations

from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

MODEL_NAMES = {
    "lr": "逻辑回归",
    "rf": "随机森林",
    "xgb": "XGBoost",
    "lgbm": "LightGBM",
    "et": "极端随机树（Extra Trees）",
    "svm": "RBF 核支持向量机",
    "nb": "高斯朴素贝叶斯",
    "dt": "决策树",
    "knn": "k 近邻",
    "mlp": "多层感知机（1 隐藏层）",
    "mlp_deep": "多层感知机（3 隐藏层 + 早停）",
    "tabnet": "TabNet（深度表格）",
}
MODEL_CLASS = {
    "lr": "经典机器学习",
    "rf": "经典机器学习",
    "xgb": "经典机器学习",
    "lgbm": "经典机器学习",
    "et": "经典机器学习",
    "svm": "经典机器学习",
    "nb": "经典机器学习",
    "dt": "经典机器学习",
    "knn": "经典机器学习",
    "mlp": "神经网络（深度学习）",
    "mlp_deep": "神经网络（深度学习）",
    "tabnet": "神经网络（深度学习）",
}
# 有精确 SHAP 解释器的模型（契约三 explanation 由 SHAP 产出）
SHAP_TREE_MODELS = {"rf", "xgb", "lgbm", "et"}
SHAP_LINEAR_MODELS = {"lr"}
KNN_NEIGHBORS = 25  # 取奇数：二分类平票不会各占一半


class TabNetWithEarlyStop(BaseEstimator, ClassifierMixin):
    """TabNet + 标准早停（与 ``MLPClassifier(early_stopping=True)`` 同语义）。

    ── 为什么必须包一层 ──────────────────────────────────────────────────
    pytorch-tabnet 的早停回调**只在 ``fit()`` 收到 ``eval_set`` 时才启用**。
    若直接把 ``TabNetClassifier`` 放进 ``Pipeline``，``Pipeline.fit(X, y)`` 只会
    调用 ``tabnet.fit(X, y)`` —— 没有 ``eval_set``，``patience`` **静默失效**，
    实际会跑满 ``max_epochs``（看起来配了早停，其实没有）。本类在 ``fit`` 内部
    **从训练集切出** ``validation_fraction`` 作为 ``eval_set``，做法与
    ``MLPClassifier`` 完全一致。

    ── 为什么不算「提前看到未来」（红线第 1 条）────────────────────────────
    ``eval_set`` 取自**训练集内部**；检验集按 ``committed_at`` 时间序切分、
    始终在时间上更晚，**从不参与早停决策**。

    ── 复现性 ────────────────────────────────────────────────────────────
    内部切分带随机性（种子固定），且 torch 多线程的浮点求和顺序不保证一致 ——
    故本模型**不属于「同一命令连跑两次逐字节一致」那一类**，与 ``mlp_deep``
    同口径；复现核对比对以固定迭代的模型（lr / rf / xgb / lgbm / et / svm）为准。
    登记见 docs/model/model-line-plan.md §2.3。
    """

    def __init__(
        self,
        seed: int = 42,
        max_epochs: int = 100,
        patience: int = 15,
        validation_fraction: float = 0.1,
    ):
        self.seed = seed
        self.max_epochs = max_epochs
        self.patience = patience
        self.validation_fraction = validation_fraction

    def fit(self, X, y):
        # pytorch-tabnet 4.1.0 的分类器在 `pytorch_tabnet.tab_model`，
        # 没有 `pytorch_tabnet.tabnet` 这个模块（2026-10-14 实测：原写法直接
        # ModuleNotFoundError，tabnet 一个模型都训不出来）。
        from pytorch_tabnet.tab_model import TabNetClassifier

        # 分层切分：保持训练集内部的正负样本比例（正例属少数类，不能随机切丢）
        X_tr, X_val, y_tr, y_val = train_test_split(
            X, y, test_size=self.validation_fraction, random_state=self.seed, stratify=y
        )
        # 14 维小样本设小容量（n_d/n_a=8, n_steps=3），避免过拟合。
        # ⚠️ pytorch-tabnet 4.1.0 起 `max_epochs` / `patience` 只是 **fit() 的参数**，
        # 不再是构造器参数（写进构造器直接 TypeError）。故此处只留容量类超参。
        self.model_ = TabNetClassifier(
            n_d=8, n_a=8, n_steps=3, gamma=1.3, verbose=0, seed=self.seed
        )
        self.model_.fit(
            X_tr,
            y_tr,
            eval_set=[(X_val, y_val)],
            eval_name=["internal_val"],
            eval_metric=["auc"],
            max_epochs=self.max_epochs,
            patience=self.patience,
        )
        self.classes_ = self.model_.classes_
        return self

    def predict_proba(self, X):
        return self.model_.predict_proba(X)

    def predict(self, X):
        return self.model_.predict(X)


def build_model(name: str, seed: int):
    if name == "lr":
        return Pipeline(
            [
                ("scaler", StandardScaler()),
                ("lr", LogisticRegression(max_iter=1000, random_state=seed)),
            ]
        )
    if name == "rf":
        # D-14：原 min_samples_leaf=2、不限深度，长成 300 棵 / 366 万节点 / 279MB，
        # SHAP 单次 782ms 把 p95 顶到 713.8ms。收敛到叶数上限后节点数降一个量级，
        # 换取 SHAP 可算（验收：p95<500ms 且 AUC 降 ≤0.01，见 docs/repo/defect-records.md D-14）。
        return RandomForestClassifier(
            n_estimators=300, min_samples_leaf=100, max_depth=15, random_state=seed, n_jobs=-1
        )
    if name == "xgb":
        from xgboost import XGBClassifier

        return XGBClassifier(
            n_estimators=300,
            learning_rate=0.1,
            max_depth=6,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=seed,
            n_jobs=-1,
            eval_metric="logloss",
        )
    # ── 性能优先选型（2026-10-14）：经典机器学习族另外三种 ──
    if name == "lgbm":
        from lightgbm import LGBMClassifier

        # ⚠️ LightGBM 的 bagging（行采样）必须配 `subsample_freq > 0` 才生效；
        #    默认 0 = 关闭，此时 `subsample=0.9` 是**空转**（静默不生效、不报错），故显式打开。
        return LGBMClassifier(
            n_estimators=300,
            learning_rate=0.1,
            num_leaves=31,
            subsample=0.9,
            subsample_freq=1,
            colsample_bytree=0.9,
            random_state=seed,
            n_jobs=-1,
            verbose=-1,
        )
    if name == "et":
        # 极端随机树：分裂阈值完全随机，方差低于随机森林、抗过拟合
        return ExtraTreesClassifier(
            n_estimators=300, min_samples_leaf=2, random_state=seed, n_jobs=-1
        )
    if name == "svm":
        # RBF 核按距离度量，必须先标准化。
        # `probability=True` 会触发 libsvm **内部 5 折 Platt 校准** —— 输出的概率是
        # **校准后的概率**、并非 SVC 原生输出（原生是 `decision_function`）。保留它是为了
        # 与其余模型共用同一套 `predict_proba` 口径；单独改用它模型间就不可比了。
        # 该口径已登记于 docs/model/model-line-plan.md §2.3。
        return Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "svm",
                    SVC(kernel="rbf", C=1.0, gamma="scale", probability=True, random_state=seed),
                ),
            ]
        )
    if name == "nb":
        return GaussianNB()  # 对量纲单调变换不敏感，不标准化
    if name == "dt":
        return DecisionTreeClassifier(max_depth=12, min_samples_leaf=20, random_state=seed)
    if name == "knn":
        return Pipeline(
            [
                ("scaler", StandardScaler()),
                ("knn", KNeighborsClassifier(n_neighbors=KNN_NEIGHBORS, n_jobs=-1)),
            ]
        )
    if name == "mlp":
        return Pipeline(
            [
                ("scaler", StandardScaler()),
                ("mlp", MLPClassifier(hidden_layer_sizes=(32,), max_iter=500, random_state=seed)),
            ]
        )
    if name == "mlp_deep":
        return Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "mlp",
                    MLPClassifier(
                        hidden_layer_sizes=(64, 32, 16),
                        max_iter=500,
                        alpha=1e-4,
                        early_stopping=True,
                        n_iter_no_change=15,
                        validation_fraction=0.1,
                        random_state=seed,
                    ),
                ),
            ]
        )
    if name == "tabnet":
        # 用 TabNetWithEarlyStop 包装：它把「训练集内部切出的验证子集」作为 eval_set
        # 传给 pytorch-tabnet —— 只有这样 `patience` 才真正生效。
        return Pipeline(
            [
                ("scaler", StandardScaler()),
                ("tabnet", TabNetWithEarlyStop(seed=seed)),
            ]
        )
    raise ValueError(f"未知模型：{name}")
