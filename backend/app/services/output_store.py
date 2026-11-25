from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from uuid import uuid4

from app import config
from app.errors import AppError
from app.services.file_contracts import (
    MAX_UNPACKED_BYTES,
    invalid,
    read_json,
    sha256,
    validate_upload_name,
)
from app.timeutil import iso_z, now_naive_utc

OUTPUT_ROOT = config.TEMP_ROOT / "outputs"
MODULES = {"storage", "collect", "clean", "train", "predict", "evaluate", "explain", "localize", "datasets"}
EXTENSIONS = {"csv", "xlsx", "json", "zip", "png", "md", "html", "diff"}


def _batch_id(job_id: str) -> None:
    if not isinstance(job_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", job_id):
        invalid("产出批次标识非法")


def _artifact_name(name: str) -> None:
    validate_upload_name(name)
    if name.startswith(".") or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name) or name.rsplit(".", 1)[-1] not in EXTENSIONS:
        invalid("产物名称或格式非法")


def backend_code_version() -> str:
    result = subprocess.run(["git", "-C", str(config.REPO_ROOT), "rev-parse", "--verify", "HEAD"],
                            capture_output=True, text=True, check=False, timeout=10)
    if result.returncode != 0:
        raise AppError(50000, "无法确认后端代码版本")
    digest = hashlib.sha256()
    source = config.REPO_ROOT / "backend" / "app"
    for path in sorted(source.rglob("*.py")):
        digest.update(str(path.relative_to(source)).encode())
        digest.update(path.read_bytes())
    # 未提交工作区不能只用 HEAD 标识当前后端代码。
    return result.stdout.strip() + "+backend." + digest.hexdigest()[:16]


def publish_output(module: str, artifacts: dict[str, bytes], *, inputs: list, config: dict,
                   job_id: str | None = None, code_version: str | None = None) -> dict:
    job_id = job_id or "j-" + uuid4().hex
    _batch_id(job_id)
    if module not in MODULES or not artifacts:
        invalid("输出模块或产物为空")
    for name, content in artifacts.items():
        _artifact_name(name)
        if not isinstance(content, bytes):
            invalid("产物内容必须为字节")
    if sum(len(content) for content in artifacts.values()) > MAX_UNPACKED_BYTES:
        invalid("输出批次大小超限")
    first = next(iter(artifacts))
    manifest_name = first.rsplit(".", 1)[0] + ".manifest.json"
    manifest_names = {name.rsplit('.', 1)[0] + '.manifest.json' for name in artifacts}
    if manifest_names.intersection(artifacts):
        invalid("产物与 manifest 名称冲突")
    for name in manifest_names:
        _artifact_name(name)
    version = code_version if code_version is not None else backend_code_version()
    if not isinstance(version, str) or not version:
        invalid("代码版本不能为空")
    entries = [{"name": name, "sha256": sha256(content), "size_bytes": len(content)} for name, content in artifacts.items()]
    manifest = {"schema_version": "1.0", "module": module, "job_id": job_id, "inputs": inputs,
                "config": config, "outputs": entries, "code_version": version,
                "created_at": iso_z(now_naive_utc())}
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, allow_nan=False, sort_keys=True).encode("utf-8")
    manifests = {name: manifest_bytes for name in sorted(manifest_names - {manifest_name}) + [manifest_name]}
    if sum(len(content) for content in artifacts.values()) + sum(map(len, manifests.values())) > MAX_UNPACKED_BYTES:
        invalid("输出批次大小超限")
    published = entries + [{"name": name, "sha256": sha256(content), "size_bytes": len(content)}
                           for name, content in manifests.items()]
    index = {"module": module, "job_id": job_id, "manifest_name": manifest_name, "outputs": published}
    index_bytes = json.dumps(index, ensure_ascii=False, allow_nan=False).encode("utf-8")
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    destination = OUTPUT_ROOT / job_id
    if destination.exists() or destination.is_symlink():
        invalid("输出批次已存在，不可覆盖")
    try:
        with tempfile.TemporaryDirectory(prefix=".staging-", dir=OUTPUT_ROOT) as temporary:
            directory = Path(temporary)
            for name, content in {**artifacts, **manifests, ".index.json": index_bytes}.items():
                with (directory / name).open("xb") as output:
                    output.write(content)
                    output.flush()
                    os.fsync(output.fileno())
            os.rename(directory, destination)
    except FileExistsError as error:
        raise AppError(40001, "输出批次已存在，不可覆盖") from error
    return {"job_id": job_id, "module": module, "outputs": published, "manifest_name": manifest_name}


def discard_output(module: str, job_id: str) -> None:
    _batch_id(job_id)
    directory = OUTPUT_ROOT / job_id
    if not directory.exists():
        return
    index_path = directory / ".index.json"
    if directory.is_symlink() or index_path.is_symlink() or not index_path.is_file():
        raise AppError(50000, "无法安全清理失败输出")
    index = read_json(index_path.read_bytes())
    if index.get("module") != module or index.get("job_id") != job_id:
        raise AppError(50000, "拒绝清理未确认的输出批次")
    expected = {item["name"] for item in index["outputs"]} | {".index.json"}
    if {path.name for path in directory.iterdir()} != expected:
        raise AppError(50000, "输出批次存在未确认文件，未清理")
    shutil.rmtree(directory)


def _checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_output(module: str, job_id: str, name: str) -> Path:
    _batch_id(job_id)
    if name == ".index.json":
        raise AppError(40400, "文件未登记")
    _artifact_name(name)
    if module not in MODULES:
        invalid("产出模块非法")
    directory = OUTPUT_ROOT / job_id
    index_path = directory / ".index.json"
    if directory.is_symlink() or not directory.is_dir() or index_path.is_symlink() or not index_path.is_file():
        raise AppError(40400, "输出批次不存在")
    index = read_json(index_path.read_bytes())
    if index.get("module") != module or index.get("job_id") != job_id:
        raise AppError(40400, "输出批次不属于该模块")
    entry = next((item for item in index.get("outputs", []) if item.get("name") == name), None)
    path = directory / name
    if entry is None or path.is_symlink() or not path.is_file() or path.stat().st_size != entry.get("size_bytes"):
        raise AppError(40400, "文件未登记或已不可用")
    if _checksum(path) != entry.get("sha256"):
        raise AppError(40400, "输出文件 checksum 不一致")
    return path
