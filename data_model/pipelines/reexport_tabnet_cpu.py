"""把保存时绑定 CUDA 的 tabnet 权重重导出为 CPU 版本（issue #222）。

用法（在仓库根目录）：
    python data_model/pipelines/reexport_tabnet_cpu.py
    python data_model/pipelines/reexport_tabnet_cpu.py path/to/model.pkl ...

背景：pytorch-tabnet 的 `TabNetClassifier` 在 GPU 上训练后，对象里 `device` /
`device_name` 与网络张量都指向 cuda；joblib 反序列化会直接抛
`Attempting to deserialize object on a CUDA device but torch.cuda.is_available() is False`。
joblib 没有 map_location 参数，故在加载阶段临时把 `torch.load` 固定到 CPU，
再把 `device` 改回 cpu 重新 dump。原文件先备份为 `*.bak-cuda`。
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import joblib

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WEIGHTS = (
    ROOT / "data_model/pipelines/semantic/models/tabnet_semantic_v1.pkl",
    ROOT / "data_model/pipelines/expert/models/tabnet_v1.pkl",
)


def _force_cpu(model) -> bool:
    changed = False
    candidates = list(getattr(model, "steps", []))
    candidates.append(("", model))
    for _, step in candidates:
        inner = getattr(step, "model_", None)
        if inner is None or not hasattr(inner, "network"):
            continue
        import torch

        inner.device_name = "cpu"
        inner.device = torch.device("cpu")
        inner.network.to(inner.device)
        changed = True
    return changed


def convert(path: Path) -> None:
    import torch

    original_load = torch.load

    def cpu_load(*args, **kwargs):
        kwargs["map_location"] = "cpu"
        return original_load(*args, **kwargs)

    torch.load = cpu_load
    try:
        model = joblib.load(path)
    finally:
        torch.load = original_load
    if not _force_cpu(model):
        raise SystemExit(f"{path}: 未找到 tabnet 模型对象，未修改")
    backup = path.with_suffix(path.suffix + ".bak-cuda")
    if not backup.exists():
        shutil.copy2(path, backup)
    joblib.dump(model, path)
    print(f"[tabnet-cpu] reexported {path}")


def main(argv: list[str]) -> int:
    if str(ROOT / "data_model") not in sys.path:
        sys.path.insert(0, str(ROOT / "data_model"))
    paths = [Path(arg) for arg in argv[1:]] or list(DEFAULT_WEIGHTS)
    for path in paths:
        if not path.is_file():
            print(f"[tabnet-cpu] skip missing {path}", file=sys.stderr)
            continue
        convert(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
