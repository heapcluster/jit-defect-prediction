"""一键入口：25 模型预测 → 按模型出图 → 导出 schema.sql / data_init.sql。

在 `data_model/` 目录下执行：
    python -m evaluation.run_all
"""

from __future__ import annotations

import pandas as pd

from . import config, export_sql, figures, predict_testset


def load_effort(test: pd.DataFrame):
    raw = pd.read_csv(
        config.FEATURES_RAW_CSV, usecols=["commit_hash", "la", "ld"]
    ).set_index("commit_hash")
    hashes = test["commit_hash"].tolist()
    miss = [h for h in hashes if h not in raw.index]
    if miss:
        raise SystemExit(f"[eval] commit_features_raw.csv 缺 {len(miss)} 条（例：{miss[0]}）")
    sub = raw.loc[hashes]
    return (sub["la"].astype(float) + sub["ld"].astype(float)).to_numpy()


def main() -> int:
    test, preds, probas, models, X14 = predict_testset.predict_all()
    effort = load_effort(test)

    metrics, figs = figures.render_all(test, preds, probas, models, X14, effort)

    config.OUT_DIR.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(config.OUT_DIR / "model_metrics.csv", index=False)
    print(f"[eval] 指标汇总：{config.OUT_DIR / 'model_metrics.csv'}")

    # 建表 DDL 的唯一真源是仓库根 infra/schema.sql（docker compose / CI 实际执行它）；
    # 评测流程不再导出第二份副本，避免双维护漂移。
    export_sql.write_data_init(config.DATA_INIT_SQL, test, preds, figs)

    print(
        f"[eval] 完成：{len(metrics)} 个模型 / {len(preds)} 条预测 / {len(figs)} 张图"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
