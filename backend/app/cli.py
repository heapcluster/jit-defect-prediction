"""独立 CLI：python -m app.cli predict run/one、models load/unload/reload/set-default/status。

predict run 仅凭模型包 + 特征文件即可批量产出 §3.4 predictions（不依赖业务库/在线服务）；
predict one 与 models 管理命令使用配置/任务库。与 API 共用同一预测/加载实现。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from uuid import uuid4

from app import model_registry
from app.errors import AppError
from app.services import file_contracts as fc
from app.services import output_store


def _bounded(path: Path) -> bytes:
    if path.stat().st_size > fc.MAX_UPLOAD_BYTES:
        raise AppError(40001, "文件超过大小限制")
    return path.read_bytes()


def _predict_run(args) -> int:
    from app.services import predict_run, storage
    if not args.model_package and not args.model:
        raise AppError(40001, "需要 --model-package 或 --model")
    text_rows = None
    if args.text:
        columns, raw_text = fc.read_table(Path(args.text).name, _bounded(Path(args.text)))
        if columns != ["commit_hash", "text"]:
            raise AppError(40001, "--text 须为 commit_hash,text 表格")
        text_rows = {row["commit_hash"]: row["text"] for row in raw_text}
    if args.model_package:
        raw = _bounded(Path(args.model_package))
        meta = storage.model_package(Path(args.model_package).name, raw)
        line = meta["line"]
        if line == "e2e":
            raise AppError(40001, "e2e 批量暂不支持上传模型包，请使用 --model codebert_e2e_v1 与文本输入")
        model_registry.load_artifact_package(meta["model_name"], raw, line=line)
        model_name = meta["model_name"]
        feature_version = meta.get("feature_version")
        model_version = meta.get("version_key") or model_name
    else:
        model_name = args.model
        line = model_registry.line_of(model_name)
        if line != "e2e":
            model_registry.get_model(model_name)
        feature_version = None
        model_version = model_name
    rows, metadata = [], {}
    if args.input:
        table = _bounded(Path(args.input))
        manifest = Path(args.manifest).read_bytes() if args.manifest else None
        rows, metadata = predict_run._parse_table(Path(args.input).name, table, manifest)
    if line == "expert":
        if text_rows is not None:
            raise AppError(40001, "expert 线不接受文本表")
        if not rows:
            raise AppError(40001, "预测输入为空")
    elif line in ("semantic", "fused"):
        if not rows:
            raise AppError(40001, f"{line} 线需要 --input 特征表提供提交哈希与 Kamei 特征")
    elif line == "e2e":
        if not rows and not text_rows:
            raise AppError(40001, "e2e 线需要 --input 特征表或 --text 文本表")
        if not rows:
            rows = [{"commit_hash": commit_hash, "is_bug_inducing": None} for commit_hash in text_rows]
    feature_version = feature_version or metadata.get("feature_version")
    job_id = str(uuid4())
    cfg = {"model_name": model_name, "line": line, "decision_threshold": args.threshold,
           "model_version": model_version, "feature_version": feature_version}
    out, failed, _ = predict_run._predict_rows(rows, cfg, None, job_id, 0, len(rows), text_map=text_rows)
    summary = {"input_rows": len(rows), "success_count": len(out), "failed_count": len(failed),
               "model_name": model_name, "model_version": model_version, "feature_version": feature_version,
               "decision_threshold": args.threshold, "failed_samples": failed[:100]}
    primary = args.format
    artifacts = {f"predict_predictions_{job_id}.{primary}": fc.encode_table(fc.PREDICTIONS_COLUMNS, out, primary),
                 f"predict_predictions_{job_id}.{'xlsx' if primary == 'csv' else 'csv'}": fc.encode_table(fc.PREDICTIONS_COLUMNS, out, "xlsx" if primary == "csv" else "csv"),
                 f"predict_summary_{job_id}.json": json.dumps(summary, ensure_ascii=False).encode()}
    output_store.OUTPUT_ROOT = Path(args.out).resolve()
    inputs = []
    if args.input:
        inputs.append({"name": Path(args.input).name, "sha256": fc.sha256(table), "rows": len(rows)})
    if args.model_package:
        inputs.append({"name": Path(args.model_package).name, "sha256": fc.sha256(raw)})
    if args.text:
        inputs.append({"name": Path(args.text).name, "sha256": fc.sha256(_bounded(Path(args.text)))})
    published = output_store.publish_output("predict", artifacts, inputs=inputs,
        config={"model_name": model_name, "line": line, "decision_threshold": args.threshold,
                "model_version": model_version, "feature_version": feature_version},
        job_id=job_id, code_version=output_store.backend_code_version())
    print(json.dumps({**published, "summary": summary}, ensure_ascii=False))
    return 0


def _predict_one(args) -> int:
    from app.services.predict import predict_single
    print(json.dumps(predict_single(args.commit, args.model, force_recompute=args.force), ensure_ascii=False, default=str))
    return 0


def _models(args) -> int:
    from app.db import SessionLocal
    from app.services import model_manage
    with SessionLocal() as session:
        if args.action == "status":
            result = model_manage.status(session, line=args.line)
        elif args.action == "set-default":
            result = model_manage.set_default(session, args.name)
        elif args.action == "load":
            result = model_manage.load(session, args.name)
        elif args.action == "unload":
            result = model_manage.unload(session, args.name)
        elif args.action == "reload":
            result = model_manage.reload(session, args.name)
        else:
            raise AppError(40001, "未知 models 操作")
    print(json.dumps(result, ensure_ascii=False, default=str))
    return 0


def _explain(args):
    from app import explain_core
    from app.services import explain_run
    if args.action == 'techniques':
        print(json.dumps({'techniques': explain_core.techniques(), 'compatibility': explain_core.compatibility()}, ensure_ascii=False))
        return 0
    files = []
    for path in (args.input, args.model_package, args.predictions):
        if path:
            source = Path(path)
            files.append((source.name, _bounded(source)))
            manifest = source.with_suffix('.manifest.json')
            if manifest.is_file():
                files.append((manifest.name, _bounded(manifest)))
    selected = [args.technique]
    if args.compare:
        selected.append(args.compare)
    params = fc.read_json(_bounded(Path(args.params))) if args.params else {}
    prepared = explain_run.prepare_files({'techniques': selected, 'params': {args.technique: params},
        'top_n': args.top_n, 'cache_ttl': 0, 'format': args.format}, files)
    result = explain_run.run_files(prepared)
    output_store.OUTPUT_ROOT = Path(args.out).resolve()
    job_id = str(uuid4())
    reference = output_store.publish_output('explain', explain_run.artifacts(result, job_id), inputs=prepared['inputs'],
        config=result['config'], job_id=job_id, code_version=explain_run.code_version())
    print(json.dumps({**reference, 'summary': result['summary']}, ensure_ascii=False))
    return 0


def _source_or_localize(args):
    from app import localization_core
    from app.services import localize_run
    policy = {'allow_roots': args.allow_root or [], 'protocol_whitelist': args.protocol or []}
    if args.group == 'source':
        with localization_core.SourceReader(args.repo, **policy, file_size_max=1048576 if args.file_size_max is None else args.file_size_max) as reader:
            if args.action == 'tree':
                result = reader.tree(args.commit, args.path or '', args.search)
            else:
                result = reader.file(args.commit, args.path, args.start_line, args.end_line)
    else:
        files = []
        for path in (args.predictions, args.explanations):
            if path:
                source = Path(path)
                files.append((source.name, _bounded(source)))
                manifest = source.with_suffix('.manifest.json')
                if manifest.is_file():
                    files.append((manifest.name, _bounded(manifest)))
        raw = fc.read_json(_bounded(Path(args.config))) if args.config else {}
        localization_core.validate_config(raw)
        top = dict(raw.get('top_n', {}))
        if args.top_files is not None:
            top['files'] = args.top_files
        if args.top_n is not None:
            top['lines'] = args.top_n
        raw['top_n'] = top
        for key, value in (('commit_hash', args.commit), ('file_size_max', args.file_size_max), ('patch_preview', args.patch_preview), ('format', args.format)):
            if value is not None:
                raw[key] = value
        result, inputs = localize_run.run_files(args.repo, files, raw, policy=policy)
        output_store.OUTPUT_ROOT = Path(args.out).resolve()
        result = localize_run.publish(result, inputs, args.repo)
    print(json.dumps(result, ensure_ascii=False))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="JIT 预测与模型管理 CLI")
    sub = parser.add_subparsers(dest="group", required=True)
    predict = sub.add_parser("predict").add_subparsers(dest="action", required=True)
    run = predict.add_parser("run")
    run.add_argument("--model-package")
    run.add_argument("--model")
    run.add_argument("--input")
    run.add_argument("--text")
    run.add_argument("--threshold", type=float, default=0.5)
    run.add_argument("--format", choices=("csv", "xlsx"), default="csv")
    run.add_argument("--manifest")
    run.add_argument("--out", required=True)
    one = predict.add_parser("one")
    one.add_argument("--commit", required=True)
    one.add_argument("--model")
    one.add_argument("--force", action="store_true")
    models = sub.add_parser("models").add_subparsers(dest="action", required=True)
    for action in ("load", "unload", "reload", "set-default"):
        models.add_parser(action).add_argument("--name", required=True)
    status = models.add_parser("status")
    status.add_argument("--line")
    explanation = sub.add_parser('explain').add_subparsers(dest='action', required=True)
    explanation.add_parser('techniques')
    explain_run = explanation.add_parser('run')
    explain_run.add_argument('--model-package', required=True)
    explain_run.add_argument('--input', required=True)
    explain_run.add_argument('--predictions')
    explain_run.add_argument('--technique', choices=('shap', 'lime'), default='shap')
    explain_run.add_argument('--compare', choices=('shap', 'lime'))
    explain_run.add_argument('--params')
    explain_run.add_argument('--top-n', type=int, default=8)
    explain_run.add_argument('--format', choices=('csv', 'xlsx'), default='csv')
    explain_run.add_argument('--out', required=True)
    source = sub.add_parser('source').add_subparsers(dest='action', required=True)
    tree = source.add_parser('tree')
    file = source.add_parser('file')
    localize = sub.add_parser('localize').add_subparsers(dest='action', required=True).add_parser('run')
    for command in (tree, file, localize):
        command.add_argument('--repo', required=True)
        command.add_argument('--allow-root', action='append')
        command.add_argument('--protocol', action='append', choices=('https', 'git'))
        command.add_argument('--file-size-max', type=int)
    tree.add_argument('--commit', required=True)
    tree.add_argument('--path', default='')
    tree.add_argument('--search')
    file.add_argument('--commit', required=True)
    file.add_argument('--path', required=True)
    file.add_argument('--start-line', type=int, default=1)
    file.add_argument('--end-line', type=int)
    localize.add_argument('--commit')
    localize.add_argument('--predictions', required=True)
    localize.add_argument('--explanations')
    localize.add_argument('--config')
    localize.add_argument('--top-files', type=int)
    localize.add_argument('--top-n', type=int)
    localize.add_argument('--patch-preview', action=argparse.BooleanOptionalAction, default=None)
    localize.add_argument('--format', choices=('csv', 'xlsx'))
    localize.add_argument('--out', required=True)
    args = parser.parse_args(argv)
    try:
        if args.group in ('source', 'localize'):
            return _source_or_localize(args)
        if args.group == 'explain':
            return _explain(args)
        if args.group == "predict":
            return _predict_run(args) if args.action == "run" else _predict_one(args)
        return _models(args)
    except (AppError, ValueError, OSError) as error:
        print(json.dumps({"code": getattr(error, "code", 40001),
                          "message": getattr(error, "message", str(error))}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
