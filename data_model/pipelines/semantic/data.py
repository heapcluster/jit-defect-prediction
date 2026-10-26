"""semantic 线数据：文本加载 / 自建文本 / 冻结编码 / 缓存读写。

自建文本与 e2e 包的 `build_text_dataset.py` **共用 `pipelines/text_source.py`**（同字段、
同截断规则、同占位串与来源分类），两边的 `commit_text.csv` 可以互换使用；默认各建各的。
口径只留一份实现，不靠「两边各抄一遍」维持一致 —— 同名两份必然分叉（见 text_source 模块头）。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .. import text_source


def load_texts(path: Path) -> pd.DataFrame:
    if not path.is_file():
        print(
            f"[semantic] 找不到文本数据集：{path}（传 --repo 自动建，或先跑 e2e 的 "
            "build_text_dataset.py 后把 --text-csv 指过去）",
            file=sys.stderr,
        )
        raise SystemExit(2)
    df = pd.read_csv(path)
    missing = [c for c in ("commit_hash", "text") if c not in df.columns]
    if missing:
        print(f"[semantic] 文本数据集缺列：{missing}", file=sys.stderr)
        raise SystemExit(2)
    return df.dropna(subset=["text"]).reset_index(drop=True)


def extract_texts_from_repo(
    repo_path: Path, dataset_csv: Path, out_csv: Path, max_chars: int
) -> Path:
    """diff 文本提取（依赖 GitPython）；口径与 e2e 包共用 `pipelines/text_source.py`。"""
    from git import Repo
    from git.exc import BadName, BadObject, GitCommandError

    if not (repo_path / ".git").exists():
        print(f"[semantic] 仓库不存在：{repo_path}", file=sys.stderr)
        raise SystemExit(2)
    repo = Repo(str(repo_path))
    df = pd.read_csv(dataset_csv)
    rows = []
    unreachable = 0
    for _, r in df.iterrows():
        h = str(r["commit_hash"])
        try:
            commit = repo.commit(h)
            has_parents = bool(commit.parents)
            diffs = commit.diff(commit.parents[0], create_patch=True, R=True) if has_parents else []
        except (BadName, BadObject, GitCommandError, OSError, ValueError) as exc:
            # 取不到提交 ≠ 无文本变更：跳过并单独计数，不落占位串
            unreachable += 1
            print(f"[semantic] 跳过在仓库里取不到的提交 {h}: {exc}", file=sys.stderr)
            continue
        assembled = text_source.assemble(diffs, max_chars)
        text, source = text_source.classify(has_parents, assembled)
        rows.append(
            text_source.make_row(h, text, source, int(r["is_bug_inducing"]), r["feature_version"])
        )
    if not rows:
        print("[semantic] 0 条有效文本", file=sys.stderr)
        raise SystemExit(1)
    out = pd.DataFrame(rows, columns=text_source.TEXT_COLUMNS)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_csv, index=False, quoting=1)  # QUOTE_ALL：text 含换行逗号
    stats = text_source.summarize(out["text_source"])
    positives = {
        name: int(((out["text_source"] == name) & (out["label"] == 1)).sum())
        for name in text_source.SOURCES
    }
    print(
        "[semantic] 文本 {} 条；来源：{}".format(
            len(out), "，".join(f"{k}={v}" for k, v in stats.items())
        )
    )
    print(
        "[semantic] 占位行中的正样本：{}".format(
            "，".join(
                f"{k}={positives[k]}"
                for k in (text_source.SOURCE_NO_TEXT_CHANGE, text_source.SOURCE_ROOT_COMMIT)
            )
        )
    )
    if unreachable:
        print(
            f"[semantic] ⚠ 另有 {unreachable} 条在克隆仓库里取不到（未落占位串）", file=sys.stderr
        )
    return out_csv


def encode_texts(texts: list[str], text_model: str, max_len: int, batch_size: int) -> np.ndarray:
    """冻结 CodeBERT mean-pool 编码 → (N, 768) float32。只前向、无梯度。"""
    import torch
    from transformers import AutoModel, AutoTokenizer

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[semantic] 编码设备：{device}（冻结，只前向）")
    tokenizer = AutoTokenizer.from_pretrained(text_model)
    encoder = AutoModel.from_pretrained(text_model).to(device).eval()
    for p in encoder.parameters():
        p.requires_grad_(False)
    out = []
    with torch.no_grad():
        for i in range(0, len(texts), batch_size):
            batch = tokenizer(
                texts[i : i + batch_size],
                truncation=True,
                padding="max_length",
                max_length=max_len,
                return_tensors="pt",
            ).to(device)
            hidden = encoder(**batch).last_hidden_state  # (B, L, 768)
            mask = batch["attention_mask"].unsqueeze(-1)  # (B, L, 1)
            pooled = (hidden * mask).sum(1) / mask.sum(1).clamp(min=1)
            out.append(pooled.cpu().numpy().astype(np.float32))
            if (i // batch_size) % 20 == 0:
                print(f"[semantic] 已编码 {min(i + batch_size, len(texts))} / {len(texts)}")
    return np.concatenate(out)


def _as_str_array(values) -> np.ndarray:
    """Return a fixed-width Unicode array instead of an object array.

    实现只有一份，放在 ``pipelines/text_source.py``：``np.savez`` 把 object 数组存成
    pickle，而 semantic 与 fused 两个 loader 都用 ``allow_pickle=False`` 读，存成
    object 就等于让缓存对消费方不可读。本函数保留为该实现的别名，既有调用点与测试不动。
    """
    return text_source.as_str_array(values)


def save_embeddings(path: Path, df: pd.DataFrame, emb: np.ndarray) -> None:
    """Persist the encoding cache.

    Every string column must be written with a fixed-width Unicode dtype.
    ``pandas`` string columns hand back an ``object`` array, and
    ``np.savez_compressed`` then stores it as a pickled object array -- which
    ``np.load(..., allow_pickle=False)`` refuses to read. Both the semantic and
    the fused loader load with allow_pickle=False, so an object-dtype save
    makes the cache unreadable by the very loaders that consume it.

    键：``commit_hash`` / ``embeddings`` / ``labels`` / ``feature_version`` /
    ``text_source``。最后一个是本次新增（供 fused 线与报告的「文本来源与覆盖率」登记用）；
    旧缓存没有该键，读方用 ``text_source.load_sources()`` 得到 ``None`` 时，
    报告必须如实写「未登记」，不得按 ``diff`` 冒充。
    """
    sources = text_source.sources_of(df)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path,
        commit_hash=_as_str_array(df["commit_hash"]),
        embeddings=emb,
        labels=df["label"].to_numpy() if "label" in df.columns else np.array([]),
        feature_version=_as_str_array(sorted(set(df["feature_version"]))),
        text_source=_as_str_array(sources),
    )


def load_embeddings(path: Path) -> tuple[list[str], np.ndarray, np.ndarray | None, list[str]]:
    if not path.is_file():
        print(f"[semantic] 找不到编码缓存：{path}（先跑本线 train.py 生成）", file=sys.stderr)
        raise SystemExit(2)
    z = np.load(path, allow_pickle=False)
    hashes = [str(h) for h in z["commit_hash"]]
    labels = z["labels"] if z["labels"].size else None
    return hashes, z["embeddings"], labels, [str(v) for v in z["feature_version"]]


def load_split_hashes(csv_path: Path) -> tuple[list[str], np.ndarray]:
    """从 expert 共用的切分文件取 (commit_hash 序列, 标签) —— 保证同一切分。"""
    if not csv_path.is_file():
        print(f"[semantic] 找不到切分文件：{csv_path}（先跑 05）", file=sys.stderr)
        raise SystemExit(2)
    df = pd.read_csv(csv_path)
    return df["commit_hash"].tolist(), df["is_bug_inducing"].astype(int).to_numpy()


def load_effort(path: Path, hashes: pd.Series) -> np.ndarray:
    raw = pd.read_csv(path).set_index("commit_hash")
    missing = [h for h in hashes if h not in raw.index]
    if missing:
        print(f"[semantic] 原始特征表缺 {len(missing)} 条（例：{missing[0]}）", file=sys.stderr)
        raise SystemExit(2)
    sub = raw.loc[list(hashes)]
    return (sub["la"].astype(float) + sub["ld"].astype(float)).to_numpy()
