from __future__ import annotations

import base64
import hashlib
import io
import json
import logging
import math
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from collections import OrderedDict
from pathlib import Path
from uuid import uuid4

import joblib
from sqlalchemy import select

from app import config, db, explain_core, model_registry
from app.errors import AppError
from app.explain import explain_label
from app.models import CommitFeature, Job, Model, ModelArtifact, Prediction
from app.services import config_store, job_store, output_store
from app.services import file_contracts as fc

logger = logging.getLogger("backend.explain")
REQUEST_ROOT = config.TEMP_ROOT / "explain_inputs"
SYNC_MAX_ROWS = 20
MAX_WORKER_BYTES = 32 * 1024 * 1024


def _kill_process_group(pid):
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True, check=False)
    else:
        os.killpg(pid, signal.SIGKILL)
COLUMNS = (
    "commit_hash",
    "model_name",
    "technique",
    "feature",
    "raw_value",
    "contribution",
    "direction",
    "rank",
    "label",
    "model_version",
    "feature_version",
    "reason_code",
)
_cache = OrderedDict()
_cache_lock = threading.Lock()
_executor_lock = threading.Lock()
_wakeup = threading.Event()
_worker = None


def _json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True).encode("utf-8")


def code_version():
    digest = hashlib.sha256()
    for path in (
        Path(explain_core.__file__),
        Path(__file__),
        Path(config.REPO_ROOT / "backend/app/explain.py"),
    ):
        digest.update(path.read_bytes())
    return "explain." + digest.hexdigest()


def validate_config(raw):
    if type(raw) is not dict or set(raw) - {
        "techniques",
        "params",
        "top_n",
        "cache_ttl",
        "format",
        "commit_hashes",
    }:
        fc.invalid("解释配置含未知字段")
    techniques = raw.get("techniques")
    if (
        type(techniques) is not list
        or not techniques
        or any(type(t) is not str or t not in ("shap", "lime") for t in techniques)
        or len(set(techniques)) != len(techniques)
    ):
        fc.invalid("techniques 必须为非空去重技术列表")
    params = raw.get("params", {})
    if type(params) is not dict or set(params) - set(techniques):
        fc.invalid("params 必须属于所选技术")
    try:
        params = {t: explain_core.validate_params(t, params.get(t)) for t in techniques}
    except ValueError as error:
        raise AppError(40001, str(error)) from error
    top_n, ttl = raw.get("top_n", 8), raw.get("cache_ttl", 3600)
    if (
        type(top_n) is not int
        or not 1 <= top_n <= 1024
        or type(ttl) is not int
        or not 0 <= ttl <= 2147483647
    ):
        fc.invalid("top_n 或 cache_ttl 超出范围")
    fmt = raw.get("format", "csv")
    if type(fmt) is not str or fmt not in ("csv", "xlsx"):
        fc.invalid("format 只支持 csv/xlsx")
    hashes = raw.get("commit_hashes")
    if hashes is not None and (
        type(hashes) is not list
        or not hashes
        or any(type(h) is not str or not fc.re.fullmatch("[0-9a-f]{40}", h) for h in hashes)
        or len(set(hashes)) != len(hashes)
    ):
        fc.invalid("commit_hashes 必须为非空去重小写哈希列表")
    return {
        "techniques": techniques,
        "params": params,
        "top_n": top_n,
        "cache_ttl": ttl,
        "format": fmt,
        "commit_hashes": hashes,
    }


def loaded_model(name):
    entry = next((m for m in model_registry.all_models() if m.name == name), None)
    if entry is None:
        raise AppError(40001, "模型未加载，请先在模型管理中显式加载")
    return entry


def techniques_payload(session, line=None, model_name=None):
    if line is not None and line not in ("expert", "semantic"):
        fc.invalid("line 非法")
    family = None
    if model_name:
        model = session.get(Model, model_name)
        entry = next((m for m in model_registry.all_models() if m.name == model_name), None)
        if model is None and entry is None:
            raise AppError(40400, "模型不存在")
        if entry:
            family = explain_core.family(entry.model)
        else:
            family = (
                "linear"
                if model.algo == "lr"
                else "tree"
                if model.algo in ("rf", "et", "xgb", "lgbm", "dt")
                else "tabular"
            )
    return {
        "techniques": explain_core.techniques(),
        "compatibility": [
            r for r in explain_core.compatibility() if family is None or r["family"] == family
        ],
        "default_technique": config_store.get_value("default_xai", session),
        "compare_enabled": config_store.get_value("explain.compare_enabled", session),
    }


def _reason(rows, techniques, reason, message):
    return [
        {
            "commit_hash": row["commit_hash"],
            "technique": technique,
            "items": [],
            "reason_code": reason,
            "message": message,
            "base_value": None,
            "output_space": None,
        }
        for row in rows
        for technique in techniques
    ]


def _worker_env(root):
    """跨平台最小环境：缓存/临时目录全部落本次任务目录，禁 JIT 与多线程 BLAS。"""
    common = {
        "HOME": str(root),
        "USERPROFILE": str(root),
        "TEMP": str(root),
        "TMP": str(root),
        "TMPDIR": str(root),
        "MPLCONFIGDIR": str(root),
        "NUMBA_DISABLE_JIT": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
    }
    if os.name == "nt":
        return {
            **common,
            "PATH": os.environ.get("PATH", ""),
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
        }
    return {**common, "PATH": "/usr/bin:/bin", "VECLIB_MAXIMUM_THREADS": "1"}


def isolated_results(weights, rows, techniques, params, top_n, progress=None):
    with tempfile.TemporaryDirectory(prefix="jit-explain-") as directory:
        root = Path(directory).resolve()
        input_file, output_file, error_file = (
            root / "input.json",
            root / "output.json",
            root / "error.log",
        )
        readable = [
            str(Path(sys.prefix).resolve()),
            str(Path(sys.base_prefix).resolve()),
            str(config.REPO_ROOT / "backend" / "app"),
            str(config.REPO_ROOT / "data_model"),
            str(root),
        ]
        payload = {
            "weights": base64.b64encode(weights).decode(),
            "rows": rows,
            "feature_names": list(config.FEATURE_COLUMNS),
            "techniques": techniques,
            "params": params,
            "top_n": top_n,
            "allowed_read_roots": readable,
            "writable_root": str(root),
        }
        if sys.platform == "darwin":
            profile = "(version 1)(allow default)(deny network*)(deny process-fork)(deny file-read*)(allow file-read-metadata)"
            profile += (
                "(allow file-read* "
                + " ".join("(subpath " + json.dumps(p) + ")" for p in readable)
                + ")"
            )
            profile += (
                "(deny file-write*)(allow file-write* (subpath "
                + json.dumps(str(root))
                + ')(literal "/dev/null"))'
            )
            payload["sandbox_profile"] = profile
        input_file.write_bytes(_json(payload))
        env = _worker_env(root)
        popen_options = (
            {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
            if os.name == "nt"
            else {"start_new_session": True}
        )
        with (
            input_file.open("rb") as source,
            output_file.open("wb") as target,
            error_file.open("wb") as errors,
        ):
            process = subprocess.Popen(
                [sys.executable, "-I", "-B", explain_core.__file__],
                stdin=source,
                stdout=target,
                stderr=errors,
                cwd=root,
                env=env,
                **popen_options,
            )
            started = time.monotonic()
            try:
                while process.poll() is None:
                    if progress:
                        progress()
                    if (
                        time.monotonic() - started > 120
                        or output_file.stat().st_size + error_file.stat().st_size > MAX_WORKER_BYTES
                    ):
                        _kill_process_group(process.pid)
                        process.wait()
                        return _reason(
                            rows, techniques, "execution_limit_exceeded", "解释执行超时或输出超限"
                        )
                    try:
                        process.wait(timeout=0.2)
                    except subprocess.TimeoutExpired:
                        continue
            except BaseException:
                try:
                    _kill_process_group(process.pid)
                except ProcessLookupError:
                    pass
                process.wait()
                raise
        if output_file.stat().st_size + error_file.stat().st_size > MAX_WORKER_BYTES:
            return _reason(rows, techniques, "execution_limit_exceeded", "解释子进程输出超限")
        if process.returncode != 0:
            logger.debug(
                "explain sandbox failed code=%s: %s",
                process.returncode,
                job_store.sanitize_text(error_file.read_text(errors="replace")[:2048]),
            )
            return _reason(
                rows, techniques, "explainer_failed", "受限解释进程执行失败；未修改在线模型"
            )
        try:
            result = json.loads(output_file.read_bytes())
            if not isinstance(result, list) or len(result) != len(rows) * len(techniques):
                raise ValueError
            expected = {(r["commit_hash"], t) for r in rows for t in techniques}
            seen = set()
            for item in result:
                required = {
                    "commit_hash",
                    "technique",
                    "items",
                    "reason_code",
                    "message",
                    "base_value",
                    "output_space",
                }
                if (
                    not isinstance(item, dict)
                    or not required <= set(item)
                    or not isinstance(item["items"], list)
                ):
                    raise ValueError
                pair = (item["commit_hash"], item["technique"])
                if pair not in expected or pair in seen:
                    raise ValueError
                seen.add(pair)
                if item["reason_code"] is not None and (
                    type(item["reason_code"]) is not str or not item["reason_code"]
                ):
                    raise ValueError
                if item["message"] is not None and type(item["message"]) is not str:
                    raise ValueError
                if item["base_value"] is not None and (
                    type(item["base_value"]) not in (int, float)
                    or not math.isfinite(item["base_value"])
                ):
                    raise ValueError
                if item["reason_code"] is None and not item["items"]:
                    raise ValueError
                if (
                    item["commit_hash"] not in {r["commit_hash"] for r in rows}
                    or item["technique"] not in techniques
                ):
                    raise ValueError
                if len(item["items"]) > top_n:
                    raise ValueError
                for contribution in item["items"]:
                    fields = {
                        "feature",
                        "raw_value",
                        "contribution",
                        "direction",
                        "rank",
                        "output_space",
                    }
                    if not isinstance(contribution, dict) or not fields <= set(contribution):
                        raise ValueError
                    if (
                        type(contribution["rank"]) is not int
                        or not 1 <= contribution["rank"] <= top_n
                        or contribution["direction"] not in ("increase", "decrease", "neutral")
                        or type(contribution["output_space"]) is not str
                    ):
                        raise ValueError
                    if (
                        contribution["feature"] not in config.FEATURE_COLUMNS
                        or not math.isfinite(contribution["contribution"])
                        or not math.isfinite(contribution["raw_value"])
                    ):
                        raise ValueError
            return result
        except (ValueError, KeyError, TypeError, OverflowError, RecursionError):
            return _reason(rows, techniques, "invalid_worker_output", "解释子进程输出不符合契约")


def prepare_files(raw, files, *, model=None):
    from app.services import storage
    from app.services.predict_run import _parse_table

    cfg = validate_config(raw)
    if (
        not files
        or len(files) > 6
        or len({n for n, _ in files}) != len(files)
        or sum(len(b) for _, b in files) > fc.MAX_UPLOAD_BYTES
    ):
        fc.invalid("解释须有输入文件，文件数/大小/名称不能重复或超限")
    uploaded = dict(files)
    tables, packages, checks, inputs = [], [], [], []
    for name, content in files:
        fc.validate_upload_name(name)
        if name.endswith(".zip"):
            packages.append((name, content))
        elif name.endswith(".manifest.json"):
            fc.read_json(content)
        else:
            columns, _ = fc.read_table(name, content)
            if tuple(columns) in (tuple(fc.COLLECTED_COMMITS_COLUMNS), tuple(fc.CLEAN_DATASET_COLUMNS)):
                tables.append((name, content))
            elif columns == list(fc.PREDICTIONS_COLUMNS):
                checks.append((name, content))
            else:
                fc.invalid("解释输入须为 commits/cleaned 或可选 predictions")
        inputs.append({"name": name, "sha256": fc.sha256(content)})
    if len(tables) != 1 or len(packages) > 1 or len(checks) > 1:
        fc.invalid("须有一个特征表和至多一个模型包/预测核对表")
    for name in uploaded:
        if name.endswith(".manifest.json"):
            bases = [
                n
                for n in uploaded
                if not n.endswith(".manifest.json")
                and n.rsplit(".", 1)[0] == name[: -len(".manifest.json")]
            ]
            if len(bases) != 1:
                fc.invalid("manifest 缺少同 stem 主文件")
            fc.verify_manifest(bases[0], uploaded[bases[0]], uploaded[name])
    name, content = tables[0]
    rows, metadata = _parse_table(
        name, content, uploaded.get(name.rsplit(".", 1)[0] + ".manifest.json")
    )
    if not rows:
        fc.invalid("解释特征表为空")
    if packages:
        package_name, package = packages[0]
        meta = storage.model_package(package_name, package)
        meta["trained_at"] = meta["trained_at"].isoformat() + "Z"
        members = fc.read_zip(package_name, package)
        weights = [b for n, b in members.items() if n.endswith(".pkl")]
        if meta["line"] == "expert" and len(weights) != 1:
            fc.invalid("模型包必须有唯一权重文件")
        model = {
            "meta": meta,
            "weights": base64.b64encode(weights[0]).decode() if weights else None,
            "checksum": fc.sha256(package),
        }
    if model is None:
        fc.invalid("请上传模型包或选择已加载模型")
    declared_version = metadata.get("feature_version")
    if (
        model["meta"]["line"] == "expert"
        and declared_version
        and model["meta"]["feature_version"] != declared_version
    ):
        fc.invalid("模型与特征版本不兼容")
    if cfg["commit_hashes"]:
        if set(cfg["commit_hashes"]) - {r["commit_hash"] for r in rows}:
            fc.invalid("提交范围含特征表外哈希")
        rows = [r for r in rows if r["commit_hash"] in cfg["commit_hashes"]]
    if checks:
        from app.services.storage import table_rows

        prediction_name, prediction_bytes = checks[0]
        _, predictions = fc.read_table(prediction_name, prediction_bytes)
        table_rows("predictions", predictions, None)
        selected = []
        for prediction in predictions:
            if (
                prediction["model_name"] != model["meta"]["model_name"]
                or prediction["model_version"] != model["meta"]["version_key"]
                or prediction["feature_version"] != model["meta"]["feature_version"]
            ):
                fc.invalid("预测核对表模型/特征版本不匹配")
            selected.append(prediction["commit_hash"])
        if set(selected) - {r["commit_hash"] for r in rows}:
            fc.invalid("预测核对表提交缺少对应特征")
        rows = [r for r in rows if r["commit_hash"] in selected]
        if not rows:
            fc.invalid("预测核对范围为空")
    # 新契约输入表不含 Kamei14：从配置仓库现算特征，不伪造向量。
    if rows and not all(field in rows[0] for field in config.FEATURE_COLUMNS):
        from app import feature_source
        try:
            computed = {item["commit_hash"]: item for item in
                        feature_source.extract_many([r["commit_hash"] for r in rows])}
        except Exception as error:
            fc.invalid(f"解释特征现算失败：{error}")
        missing = [r["commit_hash"] for r in rows if r["commit_hash"] not in computed]
        if missing:
            fc.invalid(f"解释特征现算缺少 {len(missing)} 个提交")
        feature_rows = [{"commit_hash": r["commit_hash"],
                         "features": feature_source.vector_from(computed[r["commit_hash"]])}
                        for r in rows]
    else:
        feature_rows = [
            {"commit_hash": r["commit_hash"], "features": [r[f] for f in config.FEATURE_COLUMNS]}
            for r in rows
        ]
    return {
        "config": cfg,
        "rows": feature_rows,
        "model": model,
        "inputs": inputs,
    }


def runtime_snapshot(session, name):
    entry = loaded_model(name)
    model = session.get(Model, name)
    artifact = session.scalar(select(ModelArtifact).where(ModelArtifact.model_name == name))
    buffer = io.BytesIO()
    joblib.dump(entry.model, buffer)
    weights = buffer.getvalue()
    meta = {
        "model_name": name,
        "line": entry.line,
        "algo": model.algo if model else type(entry.model).__name__,
        "version_key": model.version_key if model and model.version_key else name,
        "feature_version": model.feature_version if model and model.feature_version else "v1",
    }
    return {
        "meta": meta,
        "weights": base64.b64encode(weights).decode(),
        "checksum": fc.sha256(weights),
        "artifact_checksum": artifact.checksum_sha256 if artifact else None,
    }


def run_files(prepared, progress=None):
    cfg, model, rows = prepared["config"], prepared["model"], prepared["rows"]
    cfg = validate_config(cfg)
    results, hits = [], 0
    fingerprint = code_version()
    if model["meta"]["line"] != "expert":
        results = _reason(
            rows,
            cfg["techniques"],
            "input_shape_unsupported",
            "当前特征表不含该模型线所需的嵌入向量或文本",
        )
    else:
        for technique in cfg["techniques"]:
            missing, keys = [], {}
            for row in rows:
                key = hashlib.sha256(
                    _json(
                        {
                            "row": row,
                            "model": model["checksum"],
                            "meta": model["meta"],
                            "technique": technique,
                            "params": cfg["params"][technique],
                            "top_n": cfg["top_n"],
                            "code": fingerprint,
                        }
                    )
                ).hexdigest()
                keys[row["commit_hash"]] = key
                with _cache_lock:
                    cached = _cache.get(key)
                    if (
                        cfg["cache_ttl"]
                        and cached
                        and time.monotonic() - cached[0] < cfg["cache_ttl"]
                    ):
                        results.append(cached[1])
                        hits += 1
                    else:
                        missing.append(row)
            if missing:
                generated = isolated_results(
                    base64.b64decode(model["weights"]),
                    missing,
                    [technique],
                    cfg["params"],
                    cfg["top_n"],
                    progress,
                )
                for result in generated:
                    results.append(result)
                    if result["reason_code"] is None and cfg["cache_ttl"]:
                        with _cache_lock:
                            _cache[keys[result["commit_hash"]]] = (time.monotonic(), result)
                            while len(_cache) > 1024:
                                _cache.popitem(last=False)
    results.sort(key=lambda r: (r["commit_hash"], cfg["techniques"].index(r["technique"])))
    exchanged = []
    for result in results:
        base = {
            "commit_hash": result["commit_hash"],
            "model_name": model["meta"]["model_name"],
            "technique": result["technique"],
            "model_version": model["meta"]["version_key"],
            "feature_version": model["meta"]["feature_version"],
        }
        if result["reason_code"]:
            exchanged.append(
                {**dict.fromkeys(COLUMNS), **base, "reason_code": result["reason_code"]}
            )
        else:
            for item in result["items"]:
                exchanged.append(
                    {
                        **base,
                        **{
                            k: item[k]
                            for k in ("feature", "raw_value", "contribution", "direction", "rank")
                        },
                        "label": explain_label(item["feature"]),
                        "reason_code": None,
                    }
                )
    reasons = {}
    for result in results:
        if result["reason_code"]:
            reasons[result["reason_code"]] = reasons.get(result["reason_code"], 0) + 1
    summary = {
        "input_rows": len(rows),
        "success_count": sum(r["reason_code"] is None for r in results),
        "techniques": cfg["techniques"],
        "reason_counts": reasons,
        "cache_hits": hits,
    }
    return {
        "rows": exchanged,
        "results": results,
        "summary": summary,
        "config": {
            **cfg,
            **model["meta"],
            "model_checksum": model["checksum"],
            "input_checksums": prepared["inputs"],
        },
    }


def artifacts(result, job_id):
    cells = [
        {k: "" if row.get(k) is None else row.get(k) for k in COLUMNS} for row in result["rows"]
    ]
    formats = [result["config"]["format"], "xlsx" if result["config"]["format"] == "csv" else "csv"]
    output = {
        f"explain_explanations_{job_id}.{fmt}": fc.encode_table(COLUMNS, cells, fmt)
        for fmt in formats
    }
    output[f"explain_summary_{job_id}.json"] = _json(result["summary"])
    output[f"explain_comparison_{job_id}.json"] = _json(
        {"results": result["results"], "rows": result["rows"], "summary": result["summary"]}
    )
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    figure = Figure(figsize=(8, 4), dpi=100)
    FigureCanvasAgg(figure)
    axis = figure.subplots()
    items = next((r["items"] for r in result["results"] if r["items"]), [])
    if items:
        axis.barh(
            [r["feature"] for r in reversed(items)],
            [r["contribution"] for r in reversed(items)],
            color=["#267c64" if r["contribution"] >= 0 else "#b75a40" for r in reversed(items)],
        )
        axis.axvline(0, color="#555555", linewidth=0.8)
        axis.set_xlabel(items[0]["output_space"])
    else:
        axis.text(
            0.5, 0.5, "Explanation unavailable", ha="center", va="center", transform=axis.transAxes
        )
    figure.tight_layout()
    buffer = io.BytesIO()
    figure.savefig(buffer, format="png")
    figure.clear()
    output[f"explain_contributions_{job_id}.png"] = buffer.getvalue()
    return output


def submit(session, raw_config, files):
    raw = fc.read_json(raw_config.encode())
    name, dataset_id = raw.pop("model_name", None), raw.pop("dataset_id", None)
    raw.setdefault("cache_ttl", config_store.get_value("explain.cache_ttl", session))
    validated = validate_config(raw)
    if len(validated["techniques"]) > 1 and not config_store.get_value(
        "explain.compare_enabled", session
    ):
        fc.invalid("多技术比较已关闭，请先在用户配置开启")
    model = None
    if not any(n.endswith(".zip") for n, _ in files):
        if not name:
            fc.invalid("未上传模型包时必须显式指定 model_name，不设默认模型")
        model = runtime_snapshot(session, name)
    def _is_feature_table(name: str, raw: bytes) -> bool:
        if not name.endswith((".csv", ".xlsx")):
            return False
        columns = fc.read_table(name, raw)[0]
        return tuple(columns) in (tuple(fc.COLLECTED_COMMITS_COLUMNS), tuple(fc.CLEAN_DATASET_COLUMNS))

    if dataset_id and not any(_is_feature_table(n, b) for n, b in files):
        from app.services import storage

        storage.require_dataset(session, dataset_id)
        members, _ = storage.bounded_rows(session, storage.member_query(dataset_id))
        if not members:
            fc.invalid("数据集没有提交成员")
        rows = [storage.member_record(member) for member in members]
        files = [*files, ("dataset_commits.csv", fc.encode_table(fc.COLLECTED_COMMITS_COLUMNS, rows, "csv"))]
    prepared = prepare_files(raw, files, model=model)
    REQUEST_ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    if REQUEST_ROOT.is_symlink():
        fc.invalid("解释输入目录非法")
    directory = REQUEST_ROOT / uuid4().hex
    directory.mkdir(mode=0o700)
    serialized = _json(prepared)
    if len(serialized) > fc.MAX_UPLOAD_BYTES:
        directory.rmdir()
        fc.invalid("解释重试输入快照超限")
    (directory / "request.json").write_bytes(serialized)
    try:
        job = job_store.create(
            session,
            "explain",
            params={
                "module": "explain",
                "input_ref": directory.name + "/request.json",
                "input_sha256": fc.sha256(serialized),
                "config": prepared["config"],
            },
            total=len(prepared["rows"]),
        )
    except Exception:
        shutil.rmtree(directory)
        raise
    if len(prepared["rows"]) <= SYNC_MAX_ROWS:
        _execute(job["job_id"], job["retry_count"])
        dispatch()
        current = job_store.get(session, job["job_id"])
        reference = current["output_ref_json"] or {}
        return {
            "job_id": current["job_id"],
            "status": current["status"],
            "outputs": reference.get("outputs", []),
            "summary": reference.get("summary"),
            "error_log": current["error_log"],
        }
    dispatch()
    return {"job_id": job["job_id"], "status": job["status"]}


def _execute(job_id, attempt):
    try:
        with db.SessionLocal() as session:
            job = job_store.start(session, job_id, attempt=attempt)
    except AppError as error:
        if error.code == 40001:
            return False
        raise
    published = False
    try:
        reference = (job["params_json"] or {}).get("input_ref", "")
        if not fc.re.fullmatch("[0-9a-f]{32}/request\\.json", reference):
            fc.invalid("解释输入引用非法")
        path = REQUEST_ROOT / reference
        if (
            path.is_symlink()
            or path.parent.is_symlink()
            or REQUEST_ROOT.is_symlink()
            or path.stat().st_size > fc.MAX_UPLOAD_BYTES
        ):
            fc.invalid("解释输入不可用或超限")
        content = path.read_bytes()
        if fc.sha256(content) != job["params_json"]["input_sha256"]:
            fc.invalid("解释重试输入 checksum 不一致")
        prepared = fc.read_json(content)

        def progress():
            with db.SessionLocal() as session:
                job_store.assert_running(session, job_id, attempt=attempt)

        progress()
        result = run_files(prepared, progress)
        assets = artifacts(result, job_id)
        with db.SessionLocal() as session:
            job_store.update_progress(
                session, job_id, attempt=attempt, done=job["total"], current_item="publish"
            )
        with db.SessionLocal() as session:
            job_store.assert_running(session, job_id, attempt=attempt)
            reference = output_store.publish_output(
                "explain",
                assets,
                inputs=prepared["inputs"],
                config=result["config"],
                job_id=job_id,
                code_version=output_store.backend_code_version() + "+" + code_version(),
            )
            published = True
            reference["summary"] = result["summary"]
            job_store.finish(session, job_id, attempt=attempt, output_ref=reference)
        return True
    except Exception as error:
        if published:
            output_store.discard_output("explain", job_id)
        try:
            with db.SessionLocal() as session:
                job_store.fail(session, job_id, attempt=attempt, error=error)
        except AppError as conflict:
            if conflict.code != 40001:
                raise
        if not isinstance(error, AppError):
            logger.exception("explain executor failed")
        return True


def explain_single(session, commit_hash, model_name=None, technique=None, params=None):
    from app.validate import normalize_commit_hash

    commit_hash = normalize_commit_hash(commit_hash)
    if not model_name:
        raise AppError(40001, "参数非法：model_name 必填，不设默认模型")
    name = model_name
    loaded_model(name)
    feature = session.get(CommitFeature, commit_hash)
    prediction = session.get(Prediction, (commit_hash, name))
    if feature is None or prediction is None:
        raise AppError(40400, "解释所需特征或已存预测不存在")
    selected = technique or config_store.get_value("default_xai", session)
    top_n = (params or {}).get("top_n", 8)
    technical = {k: v for k, v in (params or {}).items() if k != "top_n"}
    cfg = validate_config(
        {
            "techniques": [selected],
            "params": {selected: technical},
            "top_n": top_n,
            "cache_ttl": config_store.get_value("explain.cache_ttl", session),
        }
    )
    model = runtime_snapshot(session, name)
    if feature.feature_version != model["meta"]["feature_version"]:
        fc.invalid("解释模型与特征版本不一致")
    prepared = {
        "config": cfg,
        "model": model,
        "rows": [
            {
                "commit_hash": commit_hash,
                "features": [float(getattr(feature, f)) for f in config.FEATURE_COLUMNS],
            }
        ],
        "inputs": [],
    }
    result = run_files(prepared)
    data = result["results"][0]
    return {
        **data,
        "model_name": name,
        "model_version": model["meta"]["version_key"],
        "feature_version": feature.feature_version,
        "items": [{**r, "label": explain_label(r["feature"])} for r in data["items"]],
    }


def _drain():
    while True:
        with db.SessionLocal() as session:
            job = session.scalar(
                select(Job)
                .where(
                    Job.kind == "explain",
                    Job.status == "queued",
                    Job.params_json.contains('"module": "explain"'),
                )
                .order_by(Job.created_at, Job.job_id)
                .limit(1)
            )
            token = (job.job_id, job.retry_count) if job else None
        if token is None or not _execute(*token):
            return


def _worker_loop():
    while True:
        _wakeup.wait()
        _wakeup.clear()
        try:
            _drain()
        except Exception:
            logger.exception("explain queue failed")


def dispatch():
    global _worker
    with _executor_lock:
        if _worker is None or not _worker.is_alive():
            _worker = threading.Thread(target=_worker_loop, daemon=True, name="explain-worker")
            _worker.start()
        _wakeup.set()


def dispatch_retry(data):
    if data["kind"] == "explain" and (data["params_json"] or {}).get("module") == "explain":
        dispatch()
