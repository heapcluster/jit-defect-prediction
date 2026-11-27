"""Optional display imports and read-only exports; registered ZIP weights stay opaque.

W2 never deserializes weights. Registration is not permission to execute pickle;
trusted, checksum-verified loading belongs to W6.
"""
from __future__ import annotations

import io
import json
import re
from datetime import UTC, datetime
from decimal import Decimal, DecimalException, InvalidOperation
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, uuid4, uuid5

from PIL import Image, UnidentifiedImageError
from sqlalchemy import case, delete, func, select
from sqlalchemy.engine import Row
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app import config, model_registry
from app.errors import AppError
from app.models import (
    Base,
    Commit,
    CommitFeature,
    Dataset,
    DatasetCommit,
    Job,
    Model,
    ModelArtifact,
    ModelFigure,
    Prediction,
    UserConfig,
)
from app.services import config_store, job_store, output_store
from app.services import file_contracts as fc
from app.timeutil import iso_z, now_naive_utc, parse_time_param

MAX_ROWS = fc.MAX_ROWS
FIGURE_TYPES = {"roc", "pr", "confusion", "calibration", "effort_unaware", "effort_aware", "feat_importance"}
# 历史导入使用合并的 effort 类型；写入时归一，读取层再兼容。
FIGURE_ALIASES = {"effort": "effort_unaware"}
TABLES = {name: table for name, table in Base.metadata.tables.items()}
COUNTS = ("inserted", "updated", "unchanged", "rejected")


def text(value, field, maximum, optional=False):
    if optional and value in (None, ""):
        return None
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or "\x00" in value:
        fc.invalid(f"{field} must be a nonempty string of at most {maximum} characters")
    return value


def hash40(value, field="commit_hash", optional=False):
    if optional and not value:
        return None
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{40}", value):
        fc.invalid(f"{field} requires 40 lowercase hexadecimal characters")
    return value


def utc(value, field, optional=False):
    if optional and not value:
        return None
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z", value):
        fc.invalid(f"{field} requires ISO 8601 UTC ending in Z")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
        if parsed.year < 1000:
            raise ValueError
        # Current MySQL DATETIME columns have second precision.
        return parsed.replace(tzinfo=None, microsecond=0)
    except ValueError:
        fc.invalid(f"{field} is not a valid UTC date")


def binary(value, field, optional=False):
    if optional and value == "":
        return None
    if value not in ("0", "1"):
        fc.invalid(f"{field} requires 0/1" + (" or empty" if optional else ""))
    return int(value)


def number(value, field, probability=False):
    try:
        result = Decimal(value)
        if not result.is_finite() or abs(result) >= Decimal("10000000000"):
            raise InvalidOperation
        precision = Decimal("0.00001" if probability else "0.0000000001")
        if result != result.quantize(precision) or probability and not 0 <= result <= 1:
            raise InvalidOperation
        return result.quantize(precision)
    except (DecimalException, ValueError, TypeError):
        fc.invalid(f"{field} requires a finite representable decimal" + (" in [0,1]" if probability else ""))


def parse_threshold(value):
    try:
        result = Decimal(str(value))
        if not result.is_finite() or not 0 <= result <= 1:
            raise InvalidOperation
        return result
    except (DecimalException, ValueError, TypeError):
        fc.invalid("decision_threshold requires a finite decimal in [0,1]")


def scrub(value):
    value = job_store.sanitize(value)
    if isinstance(value, dict):
        return {key: scrub(item) for key, item in value.items()}
    if isinstance(value, list):
        return [scrub(item) for item in value]
    return job_store.sanitize_text(value) if isinstance(value, str) else value


def import_config(raw):
    value = fc.read_json(raw.encode())
    allowed = {"dataset_id", "create_dataset", "model_artifact_status", "register_figures"}
    if set(value) - allowed or "dataset_id" in value and "create_dataset" in value:
        fc.invalid("unknown or conflicting storage config keys")
    if "dataset_id" in value:
        text(value["dataset_id"], "dataset_id", 36)
    if value.get("model_artifact_status", "available") not in ("available", "retired"):
        fc.invalid("model_artifact_status requires available/retired")
    if type(value.get("register_figures", True)) is not bool:
        fc.invalid("register_figures requires a boolean")
    if "create_dataset" in value:
        dataset = value["create_dataset"]
        allowed_dataset = {"name", "source_type", "source_url", "repo_name", "repo_source", "branch", "head_hash"}
        if not isinstance(dataset, dict) or set(dataset) - allowed_dataset:
            fc.invalid("create_dataset has unknown fields")
        text(dataset.get("name"), "name", 128)
        source_type = text(dataset.get("source_type"), "source_type", 16)
        # 公开数据集只能由 collect 任务创建；storage 只登记 Git 仓库数据集。
        if source_type != "git_repo":
            fc.invalid("source_type requires git_repo; public datasets must be collected via /api/collect/run")
        text(dataset.get("source_url"), "source_url", 512, True)
        text(dataset.get("repo_name"), "repo_name", 128, True)
        text(dataset.get("repo_source"), "repo_source", 255, True)
        text(dataset.get("branch"), "branch", 128, True)
        hash40(dataset.get("head_hash"), "head_hash", True)
        source = dataset.get("source_url") or dataset.get("repo_source") or ""
        if source and "://" in source:
            try:
                parsed = urlsplit(source)
                _ = parsed.port  # Validate malformed ports as well as IPv6 syntax.
            except ValueError:
                fc.invalid("source_url URL is malformed")
            if parsed.scheme not in ("https", "git") or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
                fc.invalid("source_url requires a credential-free https/git URL or an allowed local repository")
    return value


def verified_manifest(name, raw, companion):
    if companion is None:
        return None
    value = fc.verify_manifest(name, raw, companion)
    utc(value["created_at"], "manifest.created_at")
    for entry in value["inputs"]:
        if not isinstance(entry, dict) or not re.fullmatch(r"[0-9a-f]{64}", str(entry.get("sha256", ""))):
            fc.invalid("manifest.inputs requires explicit SHA-256 values")
        fc.validate_upload_name(text(entry.get("name"), "manifest.inputs.name", 255))
    return value


def schema(columns):
    """识别对外交换 schema；labels.csv 已废止，commits（内部特征表）不再作为导入类型。"""
    candidates = []
    for kind, allowed, required in (
        ("collected_commits", fc.COLLECTED_COMMITS_COLUMNS, fc.COLLECTED_COMMITS_REQUIRED),
        ("clean_dataset", fc.CLEAN_DATASET_COLUMNS, fc.CLEAN_DATASET_REQUIRED),
        ("predictions", fc.PREDICTIONS_COLUMNS, fc.PREDICTIONS_REQUIRED),
    ):
        if set(columns) <= set(allowed) and required <= set(columns):
            candidates.append((kind, len(set(allowed) - set(columns))))
    if not candidates:
        fc.invalid("unsupported_storage_schema: unknown columns or missing required columns; use collected_commits, clean_dataset or predictions")
    # clean_dataset 是 collected_commits 的超集：缺失列最少者胜出，避免歧义。
    candidates.sort(key=lambda item: item[1])
    if len(candidates) > 1 and candidates[0][1] == candidates[1][1]:
        fc.invalid("unsupported_storage_schema: ambiguous columns")
    return candidates[0][0]


def table_rows(kind, rows, manifest):
    validated, keys = [], set()
    for row in rows:
        item = {"commit_hash": hash40(row["commit_hash"])}
        key = (item["commit_hash"], row.get("model_name")) if kind == "predictions" else item["commit_hash"]
        if key in keys:
            fc.invalid("duplicate natural key within file")
        keys.add(key)
        if kind in ("collected_commits", "clean_dataset"):
            item.update(
                repo_name=text(row.get("repo_name"), "repo_name", 128),
                repo_url=text(row.get("repo_url"), "repo_url", 512, True),
                author_name=text(row.get("author_name"), "author_name", 128, True),
                author_email=text(row.get("author_email"), "author_email", 128, True),
                committed_at=utc(row.get("committed_at", ""), "committed_at", True),
                message=text(row.get("message"), "message", 65535, True),
                parent_hash=hash40(row.get("parent_hash"), "parent_hash", True),
                is_bug_inducing=binary(row.get("is_bug_inducing", ""), "is_bug_inducing", True),
                label_method=text(row.get("label_method"), "label_method", 32, True),
                label_source=text(row.get("label_source"), "label_source", 32),
                labeled_at=utc(row.get("labeled_at", ""), "labeled_at", True),
                fix_commit_hash=hash40(row.get("fix_commit_hash"), "fix_commit_hash", True),
                source_type=text(row.get("source_type"), "source_type", 16),
            )
            if item["label_source"] not in ("git_szz", "public_dataset"):
                fc.invalid("label_source requires git_szz or public_dataset")
            if item["source_type"] not in ("git_repo", "public_dataset"):
                fc.invalid("source_type requires git_repo or public_dataset")
            if item["label_method"] and item["label_method"] not in ("szz_v1", "szz_lite", "third_party"):
                fc.invalid("label_method requires szz_v1/szz_lite/third_party or empty")
            if len(item["message"].encode()) > 65535:
                fc.invalid("message exceeds TEXT byte capacity")
        if kind == "predictions":
            for field, maximum in (("model_name", 64), ("model_version", 64), ("feature_version", 32)):
                item[field] = text(row[field], field, maximum)
            item.update(risk_score=number(row["risk_score"], "risk_score", True), predicted_at=utc(row["predicted_at"], "predicted_at"))
            threshold = parse_threshold(row["decision_threshold"])
            predicted_label = binary(row["predicted_label"], "predicted_label")
            if predicted_label != int(item["risk_score"] >= threshold):
                fc.invalid("predicted_label disagrees with risk_score/decision_threshold")
            item.update(predicted_label=predicted_label, decision_threshold=threshold,
                        is_bug_inducing=binary(row.get("is_bug_inducing", ""), "is_bug_inducing", True))
        validated.append(item)
    return validated


def model_meta(meta, order=None):
    """校验模型侧车元数据（训练 .pkl 的 _meta_ 与外部 ZIP 的 model_meta.json 共用）。"""
    try:
        json.dumps(meta, allow_nan=False)
    except ValueError:
        fc.invalid("model metadata numerics must be finite")
    for field, maximum in (("model_name", 64), ("line", 16), ("algo", 64), ("version_key", 64), ("feature_version", 32)):
        text(meta.get(field), field, maximum)
    line = meta["line"]
    algos = {"lr", "rf", "xgb", "lgbm", "et", "svm", "mlp_deep", "tabnet", "nb", "dt", "knn", "mlp"}
    if line not in ("expert", "semantic") or meta["algo"] not in algos:
        fc.invalid("illegal model line/algo architecture")
    declared_order = meta.get("feature_order", meta.get("text_columns"))
    effective_order = declared_order if order is None else order
    if effective_order is not None:
        try:
            effective_order = list(effective_order)
        except TypeError:
            fc.invalid("feature order requires an ordered column list")
        if not effective_order or len(set(effective_order)) != len(effective_order) or any(
                not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_]*", field) for field in effective_order):
            fc.invalid("feature_order requires unique plain ordered column names")
        if line == "expert" and effective_order != list(config.FEATURE_COLUMNS) or line == "semantic" and len(effective_order) != 768:
            fc.invalid("model feature order/width does not match its architecture")
        if declared_order is not None and declared_order != effective_order:
            fc.invalid("feature order disagrees with model metadata")
    meta["trained_at"] = utc(meta.get("trained_at"), "trained_at")
    for field in ("hyperparams_snapshot", "hyperparams", "split"):
        if field in meta and not isinstance(meta[field], dict):
            fc.invalid(f"{field} requires an explicit object snapshot")
    if "seed" in meta and (type(meta["seed"]) is not int or not 0 <= meta["seed"] <= 4294967295):
        fc.invalid("seed requires a nonnegative integer")
    return meta


def model_package(name, raw):
    """外部交付 ZIP：含 model_meta.json / feature_order.txt / checksum.sha256 与权重。

    训练自产模型不再打包 ZIP；此入口只服务外部交付导入与解释模块的 ZIP 上传。
    """
    members = fc.read_zip(name, raw)
    if not {"model_meta.json", "feature_order.txt", "checksum.sha256"} <= members.keys():
        fc.invalid("model package requires model_meta.json, feature_order.txt and checksum.sha256")
    try:
        checks = {}
        for line in members["checksum.sha256"].decode("utf-8").splitlines():
            match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
            if not match or match[2] in checks:
                fc.invalid("checksum.sha256 requires unique GNU SHA-256 entries")
            checks[match[2]] = match[1]
        if set(checks) != set(members) - {"checksum.sha256"} or any(fc.sha256(members[key]) != digest for key, digest in checks.items()):
            fc.invalid("model package checksum must cover and match every member")
        order = members["feature_order.txt"].decode("utf-8").splitlines()
    except UnicodeDecodeError:
        fc.invalid("model package metadata/order must be UTF-8")
    if not any(key.endswith(".pkl") and content for key, content in members.items()):
        fc.invalid("model package is missing opaque architecture weights")
    return model_meta(fc.read_json(members["model_meta.json"]), order)


def upsert(session, cls, values):
    identity = tuple(values[column.name] for column in cls.__table__.primary_key)
    row = session.get(cls, identity[0] if len(identity) == 1 else identity, with_for_update=True)
    if row is None:
        session.add(cls(**values))
        return "inserted"
    changed = any(getattr(row, key) != value for key, value in values.items())
    for key, value in values.items():
        setattr(row, key, value)
    return "updated" if changed else "unchanged"


def dataset_record(session, dataset, detail=False):
    # 统计直接来自 dataset_commit 二维表成员行（新契约：成员自带标签与时间）。
    count, pos, neg, start, end = session.execute(select(
        func.count(DatasetCommit.commit_hash),
        func.sum(case((DatasetCommit.is_bug_inducing == 1, 1), else_=0)),
        func.sum(case((DatasetCommit.is_bug_inducing == 0, 1), else_=0)),
        func.min(DatasetCommit.committed_at), func.max(DatasetCommit.committed_at))
        .where(DatasetCommit.dataset_id == dataset.dataset_id)).one()
    result = serialize({column.name: getattr(dataset, column.name) for column in Dataset.__table__.columns})
    result.update(sample_count=count, pos_count=int(pos or 0), neg_count=int(neg or 0), time_start=iso_z(start), time_end=iso_z(end))
    if detail:
        unlabeled = int(count or 0) - int(pos or 0) - int(neg or 0)
        result.update(unlabeled_count=unlabeled,
                      pos_rate=int(pos or 0) / (pos + neg) if pos or neg else None,
                      label_method=None, label_method_source="not_stored")
    return result


def refresh_datasets(session, hashes):
    session.flush()
    ids = session.scalars(select(DatasetCommit.dataset_id).where(DatasetCommit.commit_hash.in_(hashes)).distinct()).all()
    for identifier in ids:
        row = session.get(Dataset, identifier, with_for_update=True)
        stats = dataset_record(session, row)
        for field in ("sample_count", "pos_count", "neg_count"):
            setattr(row, field, stats[field])
        row.time_start = utc(stats["time_start"], "time_start", True)
        row.time_end = utc(stats["time_end"], "time_end", True)


def import_table(session, kind, rows, settings, manifest):
    counts = dict.fromkeys(COUNTS, 0)
    dataset_id = settings.get("dataset_id") if kind in ("collected_commits", "clean_dataset") else None
    tables = {
        "collected_commits": ["commit", "dataset_commit"],
        "clean_dataset": ["commit", "dataset_commit"],
        "predictions": ["prediction"],
    }[kind].copy()
    if kind in ("collected_commits", "clean_dataset") and "create_dataset" in settings:
        meta = settings["create_dataset"]
        source = meta.get("source_url") or meta.get("repo_source", "")
        if source and "://" not in source:
            from pathlib import Path
            if "::" in source:
                fc.invalid("repo_source local path must not contain '::'")
            path = Path(source).resolve()
            if not any(path.is_relative_to(Path(root).resolve()) for root in config_store.get_value("collect.allow_roots", session)):
                fc.invalid("repo_source is outside allowed local repository roots")
        source_key = json.dumps({"dataset": meta}, sort_keys=True)
        dataset_id = str(uuid5(NAMESPACE_URL, source_key))
        if session.get(Dataset, dataset_id, with_for_update=True) is None:
            session.add(Dataset(dataset_id=dataset_id, **meta, status="ready", created_at=now_naive_utc().replace(microsecond=0)))
            session.flush()
        tables.append("dataset")
    if dataset_id:
        if session.get(Dataset, dataset_id) is None:
            raise AppError(40400, "dataset not found")
        if "dataset_commit" not in tables:
            tables.append("dataset_commit")
    for values in rows:
        hash_ = values["commit_hash"]
        if kind in ("collected_commits", "clean_dataset"):
            commit_values = {
                "commit_hash": hash_,
                "repo_name": values["repo_name"],
                "author_name": values["author_name"],
                "author_email": values["author_email"],
                "committed_at": values["committed_at"],
                "message": values["message"],
                "parent_hash": values["parent_hash"],
            }
            statuses = [upsert(session, Commit, commit_values)]
            if dataset_id:
                session.flush()
                member_values = {column.name: values[column.name] for column in DatasetCommit.__table__.columns
                                 if column.name in values}
                member_values["dataset_id"] = dataset_id
                member_values["commit_hash"] = hash_
                member_values.setdefault("row_no", 0)
                statuses.append(upsert(session, DatasetCommit, member_values))
            status = "inserted" if "inserted" in statuses else "updated" if "updated" in statuses else "unchanged"
        else:
            model = session.get(Model, values["model_name"], with_for_update=True)
            if model is None or session.get(Commit, hash_) is None:
                fc.invalid("prediction references a missing registered Model/Commit; import those objects first")
            if model.version_key != values["model_version"] or not model.feature_version or model.feature_version != values["feature_version"]:
                fc.invalid("prediction model_version/feature_version disagrees with registered Model")
            # 只写入导入契约提供的列；job_id/output_name 由预测任务维护，导入时保持为空。
            status = upsert(session, Prediction, {
                column.name: values[column.name] for column in Prediction.__table__.columns
                if column.name in values
            })
        counts[status] += 1
    if kind != "predictions":
        refresh_datasets(session, [row["commit_hash"] for row in rows])
    return tables, counts


def publish_asset(raw, extension, audit, created_batches):
    job_id = "j-" + uuid4().hex
    name = f"storage_asset_{job_id}.{extension}"
    batch = output_store.publish_output("storage", {name: raw}, inputs=[{"name": "uploaded_artifact", "sha256": fc.sha256(raw)}], config=scrub(audit), job_id=job_id)
    created_batches.append(batch["job_id"])
    return f"{config.OUTPUTS_REL}/{batch['job_id']}/{name}"


def register_model_file(session, pkl_name, raw, meta_name, meta_raw, settings=None):
    """登记训练自产 .pkl 与侧车元数据；权重路径直接指向 .pkl，不做 ZIP 解包。"""
    if not isinstance(pkl_name, str) or not pkl_name.endswith(".pkl"):
        fc.invalid("训练模型登记要求 .pkl 权重文件")
    if not isinstance(meta_name, str) or not meta_name.endswith(".json"):
        fc.invalid("训练模型登记要求侧车 .json 元数据")
    if not raw or len(raw) > fc.MAX_UPLOAD_BYTES or not meta_raw or len(meta_raw) > fc.MAX_UPLOAD_BYTES:
        fc.invalid("模型权重或侧车元数据为空或超出大小限制")
    try:
        meta = model_meta(fc.read_json(meta_raw))
    except UnicodeDecodeError:
        fc.invalid("模型侧车元数据必须为 UTF-8")
    created_batches = []
    try:
        tables, counts = import_model(session, raw, meta, settings or {}, created_batches, extension="pkl")
        session.commit()
    except Exception:
        session.rollback()
        for job_id in created_batches:
            output_store.discard_output("storage", job_id)
        raise
    return tables, counts


def import_model(session, raw, meta, settings, created_batches, extension="zip"):
    model_name = meta["model_name"]
    model = session.get(Model, model_name, with_for_update=True)
    artifact = session.scalar(select(ModelArtifact).where(ModelArtifact.model_name == model_name).with_for_update())
    loaded_names = {entry.name.casefold() for entry in model_registry.all_models()}
    existing_name = model.model_name if model is not None else model_name
    if existing_name.casefold() in loaded_names and (artifact is None or artifact.checksum_sha256 != fc.sha256(raw)):
        fc.invalid("model_name is currently loaded; register the package under a distinct model_name")
    predictions = list(session.execute(select(Prediction.commit_hash, CommitFeature.feature_version).select_from(Prediction).outerjoin(CommitFeature, CommitFeature.commit_hash == Prediction.commit_hash)
                                      .where(Prediction.model_name == model_name)))
    fields = ("model_name", "line", "algo", "version_key", "feature_version", "trained_at")
    if predictions and (model is None or any(getattr(model, field) != meta[field] for field in ("line", "algo", "version_key", "feature_version")) or any(version != meta["feature_version"] for _, version in predictions) or artifact and artifact.checksum_sha256 != fc.sha256(raw)):
        fc.invalid("model package change conflicts with existing predictions/features; register a distinct model_name")
    upsert(session, Model, {field: meta[field] for field in fields})
    session.flush()
    status = settings.get("model_artifact_status", "available")
    if artifact and artifact.checksum_sha256 == fc.sha256(raw):
        changed = artifact.status != status
        artifact.status = status
        return ["model_artifact", "model"], {**dict.fromkeys(COUNTS, 0), "updated" if changed else "unchanged": 1}
    audit = {key: serialize(value) for key, value in meta.items()}
    audit["opaque_registration"] = True
    path = publish_asset(raw, extension, audit, created_batches)
    values = {field: meta[field] for field in fields}
    values.update(artifact_id=artifact.artifact_id if artifact else str(uuid5(NAMESPACE_URL, model_name)), weight_path=path,
                  checksum_sha256=fc.sha256(raw), size_bytes=len(raw), status=status,
                  created_at=artifact.created_at if artifact else now_naive_utc().replace(microsecond=0))
    result = upsert(session, ModelArtifact, values)
    return ["model_artifact", "model"], {**dict.fromkeys(COUNTS, 0), result: 1}


def validate_figure(raw, manifest):
    if manifest is None:
        fc.invalid("PNG registration requires a verified companion manifest")
    settings = manifest["config"]
    text(settings.get("model_name"), "figure.model_name", 64)
    text(settings.get("figure_type"), "figure_type", 32)
    text(settings.get("title", settings.get("figure_type")), "figure.title", 128)
    kind = FIGURE_ALIASES.get(settings.get("figure_type"), settings.get("figure_type"))
    if kind not in FIGURE_TYPES:
        fc.invalid("unsupported figure_type; use roc/pr/confusion/calibration/effort_unaware/effort_aware/feat_importance")
    try:
        if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError
        with Image.open(io.BytesIO(raw)) as image:
            if image.format != "PNG" or image.width * image.height > 25000000:
                raise ValueError
            image.verify()
        with Image.open(io.BytesIO(raw)) as image:
            image.load()
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, Image.DecompressionBombError):
        fc.invalid("PNG magic/structure validation failed")


def import_figure(session, raw, manifest, settings, created_batches):
    meta = manifest["config"]
    if session.get(Model, meta["model_name"]) is None:
        fc.invalid("figure references a missing registered model")
    if not settings.get("register_figures", True):
        return [], {**dict.fromkeys(COUNTS, 0), "unchanged": 1}
    figure_type = FIGURE_ALIASES.get(meta["figure_type"], meta["figure_type"])
    existing = session.get(ModelFigure, ("", meta["model_name"], figure_type), with_for_update=True)
    path = None
    if existing and existing.file_path.startswith(config.OUTPUTS_REL + "/"):
        parts = existing.file_path[len(config.OUTPUTS_REL) + 1:].split("/")
        if len(parts) == 2 and all(parts):
            try:
                published = output_store.read_output("storage", *parts)
                if fc.sha256(published.read_bytes()) == fc.sha256(raw):
                    path = existing.file_path
            except AppError:
                pass  # Missing/tampered prior assets are replaced, never loaded.
    path = path or publish_asset(raw, "png", {"model_name": meta["model_name"], "figure_type": figure_type}, created_batches)
    result = upsert(session, ModelFigure, {"job_id": "", "model_name": meta["model_name"],
        "figure_type": figure_type,
        "figure_name": f"{meta['model_name']}_{figure_type}.png"[:128],
        "title": text(meta.get("title", meta["figure_type"]), "title", 128), "file_path": path,
        "testset_ref": None, "generated_at": utc(manifest["created_at"], "manifest.created_at")})
    return ["model_figure"], {**dict.fromkeys(COUNTS, 0), result: 1}


def import_files(session: Session, files: list[tuple[str, bytes]], raw_config="{}"):
    settings = import_config(raw_config)
    if not files or len(files) > 100 or len({name for name, _ in files}) != len(files) or sum(len(raw) for _, raw in files) > fc.MAX_UPLOAD_BYTES:
        fc.invalid("empty/duplicate uploaded filenames or batch upload size/count exceeds limits")
    uploaded = dict(files)
    for name, raw in files:
        fc.validate_upload_name(name)
        if not raw or len(raw) > fc.MAX_UPLOAD_BYTES:
            fc.invalid("file is empty or exceeds upload size limit")
    artifacts = [(name, raw) for name, raw in files if not name.endswith(".manifest.json")]
    stems = {name.rsplit(".", 1)[0] for name, _ in artifacts}
    if len(stems) != len(artifacts) or any(name[:-14] not in stems for name in uploaded if name.endswith(".manifest.json")) or not artifacts:
        fc.invalid("ambiguous or standalone companion manifest")
    prepared = []
    for name, raw in artifacts:
        item = {"name": name, "schema": None, "target_tables": [], "status": "rejected", **dict.fromkeys(COUNTS, 0), "errors": []}
        manifest, content = None, None
        row_count = 1
        try:
            extension = name.rsplit(".", 1)[-1].lower()
            if extension in ("csv", "xlsx"):
                columns, content = fc.read_table(name, raw)
                row_count = len(content)
                item["schema"] = schema(columns)
            elif extension in ("zip", "png"):
                item["schema"] = "model_package" if extension == "zip" else "figure"
            else:
                fc.invalid("unsupported_storage_schema: no result table for this file")
            item["target_tables"] = {
                "collected_commits": ["commit", "dataset_commit"], "clean_dataset": ["commit", "dataset_commit"],
                "predictions": ["prediction"], "model_package": ["model_artifact", "model"], "figure": ["model_figure"],
            }[item["schema"]]
            if item["schema"] in ("collected_commits", "clean_dataset") and settings.get("create_dataset"):
                item["target_tables"] = ["dataset", "commit", "dataset_commit"]
            manifest = verified_manifest(name, raw, uploaded.get(name.rsplit(".", 1)[0] + ".manifest.json"))
            if extension in ("csv", "xlsx"):
                content = table_rows(item["schema"], content, manifest)
            elif extension == "zip":
                content = model_package(name, raw)
            else:
                validate_figure(raw, manifest)
        except AppError as error:
            item.update(rejected=max(row_count, 1), errors=[error.message])
        prepared.append((item, raw, content, manifest, row_count))
    if settings.get("dataset_id") and session.get(Dataset, settings["dataset_id"]) is None:
        raise AppError(40400, "dataset not found")
    for item, raw, content, manifest, row_count in prepared:
        if item["errors"]:
            continue
        created_batches = []
        try:
            if item["schema"] == "model_package":
                tables, counts = import_model(session, raw, content, settings, created_batches)
            elif item["schema"] == "figure":
                tables, counts = import_figure(session, raw, manifest, settings, created_batches)
            else:
                tables, counts = import_table(session, item["schema"], content, settings, manifest)
            session.commit()
            item.update(target_tables=tables, status="imported", **counts)
        except (AppError, SQLAlchemyError) as error:
            session.rollback()
            for job_id in created_batches:
                output_store.discard_output("storage", job_id)
            if isinstance(error, AppError):
                item.update(rejected=max(row_count, 1), errors=[error.message])
            elif isinstance(error, IntegrityError):
                item.update(rejected=max(row_count, 1), errors=["database natural-key/foreign-key conflict; check referenced objects"])
            else:
                raise AppError(50000, "internal error") from None
    items = [item for item, *_ in prepared]
    if all(item["status"] == "rejected" for item in items):
        raise AppError(40001, f"{items[0]['name']}: {items[0]['errors'][0]}")
    return {"items": items, "summary": {key: sum(item[key] for item in items) for key in COUNTS}}


def serialize(value):
    if isinstance(value, datetime):
        return iso_z(value.astimezone(UTC).replace(tzinfo=None) if value.tzinfo else value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [serialize(item) for item in value]
    return value


def time_filters(start_time=None, end_time=None):
    if start_time == "" or end_time == "":
        fc.invalid("time filters must not be empty")
    start = parse_time_param(start_time, "start_time") if start_time else None
    end = parse_time_param(end_time, "end_time", "end") if end_time else None
    if start and end and start > end:
        fc.invalid("start_time must not be later than end_time")
    return start, end


def snapshot(session):
    if not session.in_transaction() and session.get_bind().dialect.name == "mysql":
        session.connection(execution_options={"isolation_level": "REPEATABLE READ"})


def bounded_rows(session, statement, limit=None):
    total = session.scalar(select(func.count()).select_from(statement.order_by(None).subquery()))
    if limit is None and total > MAX_ROWS:
        fc.invalid("export exceeds MAX_ROWS; specify limit or narrower filters")
    return session.execute(statement.limit(limit or MAX_ROWS)).all(), total


def export_result(module, artifact, columns, rows, settings, total=None):
    job_id = "j-" + uuid4().hex
    name = f"{module}_{artifact}_{job_id}.{settings['format']}"
    rows, settings = serialize(rows), serialize(settings)
    source = json.dumps({"rows": rows, "query": settings}, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
    encoded_rows = [{column: row.get(column) if row.get(column) is not None else "" for column in columns} for row in rows]
    batch = output_store.publish_output(module, {name: fc.encode_table(columns, encoded_rows, settings["format"])}, 
        inputs=[{"name": "database_snapshot.json", "sha256": fc.sha256(source), "rows": len(rows)}], config=settings, job_id=job_id)
    return {**batch, **settings, "columns": list(columns), "preview": rows[:20], "row_count": len(rows), "total": total if total is not None else len(rows)}


def export_table(session, table, format="csv", dataset_id=None, model_name=None, start_time=None, end_time=None, limit=None):
    if table not in TABLES or format not in ("csv", "xlsx") or limit is not None and not 1 <= limit <= fc.MAX_ROWS:
        fc.invalid("illegal table/format/limit")
    snapshot(session)
    target = TABLES[table]
    statement = select(target)
    filters = {"dataset_id": dataset_id, "model_name": model_name, "start_time": start_time, "end_time": end_time, "limit": limit}
    start, end = time_filters(start_time, end_time)
    if dataset_id is not None:
        text(dataset_id, "dataset_id", 36)
        if table not in {"dataset", "dataset_commit", "commit", "commit_feature", "prediction"}:
            fc.invalid("dataset_id filter is not applicable to this table")
        if session.get(Dataset, dataset_id) is None:
            raise AppError(40400, "dataset not found")
        statement = statement.where(target.c.dataset_id == dataset_id) if "dataset_id" in target.c else statement.where(target.c.commit_hash.in_(select(DatasetCommit.commit_hash).where(DatasetCommit.dataset_id == dataset_id)))
    if model_name is not None:
        text(model_name, "model_name", 64)
        if "model_name" not in target.c:
            fc.invalid("model_name filter is not applicable to this table")
        statement = statement.where(target.c.model_name == model_name)
    if start or end:
        if table in {"commit", "commit_feature", "prediction", "dataset_commit"}:
            member = select(Commit.commit_hash)
            if start:
                member = member.where(Commit.committed_at >= start)
            if end:
                member = member.where(Commit.committed_at <= end)
            statement = statement.where(target.c.commit_hash.in_(member))
        else:
            field = {"model": "trained_at", "model_artifact": "trained_at", "model_figure": "generated_at", "user": "created_at", "user_config": "updated_at", "job": "created_at", "dataset": "created_at"}.get(table)
            if field is None:
                fc.invalid("time filters are not applicable to this table")
            if start:
                statement = statement.where(target.c[field] >= start)
            if end:
                statement = statement.where(target.c[field] <= end)
    if table == "user_config":
        statement = statement.where(UserConfig.config_key.in_(config_store.CONFIG_SCHEMA))
    result, total = bounded_rows(session, statement.order_by(*target.primary_key.columns), limit)
    rows = [dict(row._mapping) for row in result]
    if table in ("job", "user_config"):
        for row in rows:
            for key in ("value_json", "params_json", "output_ref_json"):
                if row.get(key) is not None:
                    row[key] = json.dumps(scrub(json.loads(row[key])), ensure_ascii=False, allow_nan=False)
            for key in ("error_log", "current_item"):
                if row.get(key):
                    row[key] = "[redacted]" if re.search(r"(?i)traceback|select\s|insert\s|update\s|sqlalchemy", row[key]) else job_store.sanitize_text(row[key])
    return export_result("storage", table, list(target.columns.keys()), rows, {"table": table, "format": format, "filters": filters}, total)


def require_dataset(session, dataset_id):
    dataset = session.get(Dataset, dataset_id)
    if dataset is None:
        raise AppError(40400, "dataset not found")
    return dataset


def delete_dataset(session, dataset_id):
    dataset = require_dataset(session, dataset_id)
    session.execute(delete(DatasetCommit).where(DatasetCommit.dataset_id == dataset_id))
    session.delete(dataset)
    session.commit()
    return {"dataset_id": dataset_id, "deleted": True}


def list_datasets(session, page, size, status=None, q=None):
    snapshot(session)
    query = select(Dataset)
    if status:
        query = query.where(Dataset.status == status)
    if q:
        query = query.where(Dataset.name.contains(q, autoescape=True) | Dataset.repo_source.contains(q, autoescape=True))
    total = session.scalar(select(func.count()).select_from(query.subquery()))
    items = session.scalars(query.order_by(Dataset.created_at.desc(), Dataset.dataset_id).offset((page - 1) * size).limit(size)).all()
    return {"total": total, "page": page, "size": size, "items": [dataset_record(session, item) for item in items]}


def member_query(dataset_id, start_time=None, end_time=None):
    """数据集成员 = dataset 的已打标二维表（DatasetCommit），不再 join CommitFeature 展示标签。"""
    start, end = time_filters(start_time, end_time)
    query = select(DatasetCommit).where(DatasetCommit.dataset_id == dataset_id)
    if start:
        query = query.where(DatasetCommit.committed_at >= start)
    if end:
        query = query.where(DatasetCommit.committed_at <= end)
    return query.order_by(DatasetCommit.committed_at, DatasetCommit.commit_hash)


def _json(value):
    if not value:
        return {}
    try:
        decoded = json.loads(value)
    except (TypeError, ValueError):
        return {}
    return decoded if isinstance(decoded, dict) else {}


def lineage(session, *, kind=None, status=None, search=None, start_time=None, end_time=None, page=1, size=20):
    """按 `job.chain_id` 汇总数据链路；链路关系只来自已落库字段，不按文件名猜测。"""
    if kind is not None and kind not in job_store.KINDS:
        fc.invalid("kind 非法")
    if status is not None and status not in job_store.STATUSES:
        fc.invalid("status 非法")
    if page < 1 or not 1 <= size <= 100:
        fc.invalid("page/size 非法")
    start, end = time_filters(start_time, end_time)
    jobs = session.scalars(select(Job).order_by(Job.created_at.asc(), Job.job_id.asc())).all()
    groups: dict[str, list[Job]] = {}
    for job in jobs:
        groups.setdefault(job.chain_id or job.job_id, []).append(job)
    entries = []
    for chain_id, rows in groups.items():
        created = min(row.created_at for row in rows)
        if start and created < start or end and created > end:
            continue
        matched = rows
        if kind is not None:
            matched = [row for row in matched if row.kind == kind]
        if status is not None:
            matched = [row for row in matched if row.status == status]
        if not matched:
            continue
        title = None
        for row in rows:
            params = _json(row.params_json)
            settings = params.get("config") if isinstance(params.get("config"), dict) else params
            title = settings.get("dataset_name") or settings.get("repo_name") or settings.get("source_url")
            if title:
                break
        if not title:
            title = "未关联 · " + chain_id[:8] if len(rows) == 1 else chain_id
        if search:
            needle = search.lower()
            haystack = [chain_id, str(title)] + [row.job_id for row in rows]
            if not any(needle in str(item).lower() for item in haystack):
                continue
        ids = [row.job_id for row in rows]
        model_map: dict[str, list[str]] = {}
        for model_name, train_job_id in session.execute(
            select(ModelArtifact.model_name, ModelArtifact.train_job_id).where(ModelArtifact.train_job_id.in_(ids))
        ).all():
            model_map.setdefault(train_job_id, []).append(model_name)
        dataset_map = {
            job_id: dataset_id
            for dataset_id, job_id in session.execute(
                select(Dataset.dataset_id, Dataset.job_id).where(Dataset.job_id.in_(ids))
            ).all()
        }
        kinds: dict[str, int] = {}
        for row in rows:
            kinds[row.kind] = kinds.get(row.kind, 0) + 1
        nodes = []
        for row in matched:
            reference = _json(row.output_ref_json)
            artifacts = [
                {"name": item.get("name"), "size_bytes": item.get("size_bytes")}
                for item in reference.get("outputs", [])
                if isinstance(item, dict) and item.get("name")
            ]
            nodes.append({
                "job_id": row.job_id,
                "kind": row.kind,
                "status": row.status,
                "parent_job_ids": json.loads(row.parent_job_ids) if row.parent_job_ids else [],
                "model_names": model_map.get(row.job_id, []),
                "dataset_id": dataset_map.get(row.job_id),
                "created_at": iso_z(row.created_at),
                "finished_at": iso_z(row.finished_at),
                "artifacts": artifacts,
            })
        entries.append({
            "chain_id": chain_id,
            "title": title,
            "created_at": iso_z(created),
            "node_count": len(rows),
            "kinds": kinds,
            "nodes": nodes,
        })
    entries.sort(key=lambda item: item["created_at"] or "", reverse=True)
    total = len(entries)
    window = entries[(page - 1) * size:(page - 1) * size + size]
    return {"items": window, "total": total, "page": page}


def delete_chain(session, chain_id):
    """整链删除：先做共享引用检查，通过后删除链内任务、产物、模型与数据集。"""
    rows = session.scalars(select(Job).where(Job.chain_id == chain_id)).all()
    if not rows:
        raise AppError(40400, "链路不存在")
    ids = {row.job_id for row in rows}
    artifacts = sum(
        len(_json(row.output_ref_json).get("outputs", []))
        for row in rows
    )
    models = session.scalars(select(ModelArtifact).where(ModelArtifact.train_job_id.in_(ids))).all()
    datasets = session.scalars(select(Dataset).where(Dataset.job_id.in_(ids))).all()
    model_names = {model.model_name for model in models}
    dataset_ids = {dataset.dataset_id for dataset in datasets}
    references = []
    if model_names:
        for prediction in session.scalars(select(Prediction).where(Prediction.model_name.in_(model_names))).all():
            if prediction.job_id not in ids:
                references.append({"kind": "prediction", "model_name": prediction.model_name, "job_id": prediction.job_id})
        for figure in session.scalars(select(ModelFigure).where(ModelFigure.model_name.in_(model_names))).all():
            if figure.job_id not in ids:
                references.append({"kind": "model_figure", "model_name": figure.model_name, "job_id": figure.job_id})
    if dataset_ids:
        for job in session.scalars(select(Job).where(Job.job_id.notin_(ids))).all():
            text = job.params_json or ""
            for dataset_id in dataset_ids:
                if dataset_id in text:
                    references.append({"kind": "job", "job_id": job.job_id, "dataset_id": dataset_id})
    if references:
        raise AppError(40001, "链路资产被链路外任务引用，未执行删除", {"references": references})
    for row in rows:
        module = _json(row.output_ref_json).get("module") or ("predict" if row.kind == "predict_batch" else row.kind)
        try:
            output_store.discard_output(module, row.job_id)
        except AppError:
            pass  # 已清理或历史批次不阻塞整链删除
    session.execute(delete(ModelFigure).where(ModelFigure.job_id.in_(ids)))
    session.execute(delete(Prediction).where(Prediction.job_id.in_(ids)))
    for model in models:
        session.delete(model)
    if model_names:
        session.execute(delete(Model).where(Model.model_name.in_(model_names)))
    if dataset_ids:
        session.execute(delete(DatasetCommit).where(DatasetCommit.dataset_id.in_(dataset_ids)))
        for dataset in datasets:
            session.delete(dataset)
    for row in rows:
        session.delete(row)
    session.commit()
    return {"chain_id": chain_id, "jobs": len(ids), "artifacts": artifacts,
            "models": len(models), "datasets": len(datasets)}


def member_record(member, feature=None, with_features=True):
    if isinstance(member, Row):
        member = member[0]
    item = {column.name: getattr(member, column.name) for column in DatasetCommit.__table__.columns}
    # 新契约：成员行自带标签与元信息；is_test 不再是文件 handoff 契约的一部分。
    item.pop("is_test", None)
    if with_features and feature is not None:
        item.update({field: getattr(feature, field) for field in config.FEATURE_COLUMNS})
    return serialize(item)


def dataset_members(session, dataset_id, page, size, with_features=1, **filters):
    snapshot(session)
    query = member_query(dataset_id, **filters)
    require_dataset(session, dataset_id)
    total = session.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    rows = session.scalars(query.offset((page - 1) * size).limit(size)).all()
    return {"total": total, "page": page, "size": size, "items": [member_record(row[0] if isinstance(row, Row) else row) for row in rows]}


def export_dataset(session, dataset_id, format="csv", artifact="commits", model_name=None, decision_threshold=None, **filters):
    if format not in ("csv", "xlsx") or artifact not in ("commits", "predictions"):
        fc.invalid("illegal dataset export format/artifact")
    snapshot(session)
    query = member_query(dataset_id, **filters)
    require_dataset(session, dataset_id)
    raw_members, total = bounded_rows(session, query)
    members = [row[0] if isinstance(row, Row) else row for row in raw_members]
    rows = []
    settings = {"dataset_id": dataset_id, "artifact": artifact, "format": format, "filters": filters, "label_method_source": "not_stored"}
    if artifact == "commits":
        if decision_threshold is not None or model_name is not None:
            fc.invalid("decision_threshold/model_name are only applicable to predictions exports")
        rows = [member_record(member) for member in members]
        columns = fc.COLLECTED_COMMITS_COLUMNS
    else:
        if not model_name:
            fc.invalid("predictions export requires model_name")
        model = session.get(Model, model_name)
        if model is None:
            raise AppError(40400, "model not found")
        text(model.feature_version, "registered Model.feature_version", 32)
        text(model.version_key, "registered Model.version_key", 64)
        threshold = parse_threshold(decision_threshold if decision_threshold is not None else config_store.get_value("decision_threshold", session))
        predictions = {row.commit_hash: row for row in session.scalars(select(Prediction).where(Prediction.model_name == model_name, Prediction.commit_hash.in_([m.commit_hash for m in members])))}
        for member in members:
            prediction = predictions.get(member.commit_hash)
            rows.append({"commit_hash": member.commit_hash, "model_name": model_name, "risk_score": prediction.risk_score if prediction else None,
                "predicted_label": int(prediction.risk_score >= threshold) if prediction else None, "decision_threshold": threshold,
                "model_version": prediction.model_version if prediction and prediction.model_version else model.version_key,
                "feature_version": prediction.feature_version if prediction and prediction.feature_version else model.feature_version,
                "predicted_at": prediction.predicted_at if prediction else None, "is_bug_inducing": member.is_bug_inducing})
        settings.update(model_name=model_name, decision_threshold=threshold, feature_version=model.feature_version,
                        predicted_label_source="stored probability >= export decision_threshold", missing_predictions=total - len(predictions))
        columns = fc.PREDICTIONS_COLUMNS
    return export_result("datasets", artifact, columns, rows, settings, total)
