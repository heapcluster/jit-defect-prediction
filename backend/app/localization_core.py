"""Read-only, Git-object-backed source browsing and prediction localization.

No prediction, explanation, database, network suggestion, or artifact publishing
is performed here. Line scores are review heuristics, not line probabilities.
"""

from __future__ import annotations

import ast
import importlib
import json
import math
import re
import sys
import tempfile
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from app.diff import parse_unified_diff
from app.errors import AppError
from app.services.commits import _file_weight, _line_content_weight
from app.services.config_store import WEIGHT_DEFAULTS
from app.services.fix_suggestion import template_suggestions

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WEIGHTS = deepcopy(WEIGHT_DEFAULTS)
DEFAULT_TOP_N = {"files": 5, "lines": 30}
_HASH = re.compile(r"[0-9a-fA-F]{40}\Z")
_FILE_KIND = {
    "源码文件": "source",
    "普通文件": "other",
    "文档/配置": "document",
    "测试文件": "test",
    "生成物": "generated",
}
_LINE_KIND = {0.1: "empty", 0.15: "comment", 0.3: "import", 1.5: "suspicious", 1.0: "normal"}
_DIFF_MAX = 4 * 1024**2


def _invalid(message):
    raise AppError(40001, message)


def _hash(value):
    if not isinstance(value, str) or not _HASH.fullmatch(value):
        _invalid("commit_hash 必须是完整 40 位十六进制哈希")
    return value.lower()


def _number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _positive(value, maximum, name):
    if type(value) is not int or not 1 <= value <= maximum:
        _invalid(f"{name} 必须为 1..{maximum} 的整数")
    return value


def _weights(raw, defaults):
    if not isinstance(raw, dict) or set(raw) - set(defaults):
        _invalid("weights 包含未知字段或类型非法")
    result = deepcopy(defaults)
    for key, value in raw.items():
        if isinstance(defaults[key], dict):
            result[key] = _weights(value, defaults[key])
        elif not _number(value) or value < 0:
            _invalid("weights 必须是非负有限数值")
        else:
            result[key] = float(value)
    return result


def validate_config(raw: dict) -> dict:
    fields = {
        "weights",
        "top_n",
        "file_size_max",
        "suggestion_sources",
        "patch_preview",
        "format",
        "commit_hash",
        "model_name",
    }
    if not isinstance(raw, dict) or set(raw) - fields:
        _invalid("localization 配置类型非法或包含未知字段")
    result = {
        "weights": _weights(raw.get("weights", {}), DEFAULT_WEIGHTS),
        "top_n": deepcopy(DEFAULT_TOP_N),
        "file_size_max": _positive(
            raw.get("file_size_max", 1048576), 16 * 1024**2, "file_size_max"
        ),
        "suggestion_sources": deepcopy(raw.get("suggestion_sources", ["template"])),
        "patch_preview": raw.get("patch_preview", True),
        "format": raw.get("format", "csv"),
        "commit_hash": raw.get("commit_hash"),
        "model_name": raw.get("model_name"),
    }
    top = raw.get("top_n", {})
    if not isinstance(top, dict) or set(top) - set(DEFAULT_TOP_N):
        _invalid("top_n 包含未知字段或类型非法")
    for key, value in top.items():
        result["top_n"][key] = _positive(value, 1000, f"top_n.{key}")
    sources = result["suggestion_sources"]
    if (
        not isinstance(sources, list)
        or not sources
        or any(not isinstance(s, str) or s not in ("template", "llm", "history") for s in sources)
        or len(set(sources)) != len(sources)
    ):
        _invalid("suggestion_sources 必须是 template/llm/history 的非空唯一列表")
    if type(result["patch_preview"]) is not bool:
        _invalid("patch_preview 必须是 bool")
    if result["format"] not in ("csv", "xlsx"):
        _invalid("format 必须是 csv/xlsx")
    if result["commit_hash"] is not None:
        result["commit_hash"] = _hash(result["commit_hash"])
    if result["model_name"] is not None:
        _metadata_string(result["model_name"], "model_name")
    return result


def _collect():
    model_path = str(ROOT / "data_model")
    if model_path not in sys.path:
        sys.path.insert(0, model_path)
    return importlib.import_module("preparation.collect")


def _path(value, *, empty=False):
    if (
        not isinstance(value, str)
        or (not value and not empty)
        or value.startswith("/")
        or "\\" in value
        or any(ord(c) < 32 or ord(c) == 127 for c in value)
        or any(part in ("..", ".", "") for part in value.split("/") if value)
    ):
        _invalid("文件路径必须是安全的相对 POSIX 路径")
    return value


class SourceReader:
    def __init__(
        self,
        repo_source: str,
        *,
        allow_roots: list[str],
        protocol_whitelist: list[str],
        file_size_max: int = 1048576,
    ):
        self.repo_source = repo_source
        self.allow_roots = allow_roots
        self.protocol_whitelist = protocol_whitelist
        self.file_size_max = _positive(file_size_max, 16 * 1024**2, "file_size_max")
        self._temporary = None
        self._repo = None
        self._runner = None
        self._collect = None

    def __enter__(self):
        if self._repo is not None:
            _invalid("SourceReader 已打开")
        collect = self._collect = _collect()
        try:
            cfg = collect.validate_config(
                {"repo_source": self.repo_source, "dataset_name": "source", "fetch_remote": False},
                allow_roots=self.allow_roots,
                protocol_whitelist=self.protocol_whitelist,
            )
            roots = collect._roots(self.allow_roots)
            source = cfg["repo_source"]
            if "://" in source:
                controlled = [
                    root
                    for root in roots
                    if not any(
                        (p / ".git").exists()
                        or ((p / "HEAD").is_file() and (p / "objects").is_dir())
                        for p in (root, *root.parents)
                    )
                ]
                if not controlled:
                    _invalid("远程源码需要用户仓库之外的受控允许根目录")
                url, pins = collect._url(source, self.protocol_whitelist)
                self._temporary = tempfile.TemporaryDirectory(
                    prefix=".localization-source-", dir=controlled[0]
                )
                directory = Path(self._temporary.name)
                repo = directory / "repository.git"
                runner = collect.GitRunner(self.protocol_whitelist, None, size_directory=repo)
                runner.network_config = pins
                runner(
                    directory, "clone", "--bare", "--no-local", "--template=", "--", url, str(repo)
                )
                runner.size_directory = None
            else:
                repo = Path(source)
            # Local reads and all post-clone reads have no permitted network protocols.
            runner = collect.GitRunner([], None)
            if (repo / ".git").is_symlink():
                _invalid("Git 存储不允许符号链接")
            collect._repository(repo, roots, runner)
            self._repo, self._runner = repo, runner
            return self
        except collect.CollectError as exc:
            self.__exit__(None, None, None)
            raise AppError(exc.code, "源码仓库验证或读取失败") from None
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, exc_type, exc, traceback):
        self._repo = self._runner = None
        if self._temporary is not None:
            self._temporary.cleanup()
            self._temporary = None
        return False

    def _git(self, *args, **kwargs):
        if self._repo is None or self._runner is None:
            _invalid("SourceReader 尚未打开")
        try:
            return self._runner(self._repo, *args, **kwargs)
        except self._collect.CollectError as exc:
            raise AppError(exc.code, "源码 Git 对象读取失败") from None

    def resolve(self, commit_hash) -> str:
        commit_hash = _hash(commit_hash)
        try:
            result = self._git(
                "rev-parse", "--verify", "--end-of-options", commit_hash + "^{commit}"
            ).strip()
        except AppError as exc:
            if exc.code == 50000:
                raise AppError(40400, "提交不存在") from None
            raise
        return _hash(result)

    @staticmethod
    def _entries(raw: bytes, prefix=""):
        entries = []
        for item in raw.split(b"\x00"):
            if not item:
                continue
            header, name = item.split(b"\t", 1)
            mode, kind, object_id, size = header.split()
            path = name.decode("utf-8", "surrogateescape")
            entries.append(
                {
                    "name": PurePosixPath(path).name,
                    "path": prefix + path,
                    "type": kind.decode("ascii"),
                    "size": int(size) if size != b"-" else None,
                    "mode": mode.decode("ascii"),
                    "object_id": object_id.decode("ascii"),
                }
            )
        return entries

    def _entry(self, commit_hash, path):
        entries = self._entries(self._git("ls-tree", "-lz", commit_hash, "--", path, binary=True))
        return next((e for e in entries if e["path"] == path), None)

    def tree(self, commit_hash, path="", search=None) -> dict:
        commit_hash = self.resolve(commit_hash)
        path = _path(path, empty=True)
        if search is not None and (
            not isinstance(search, str)
            or not search
            or len(search) > 4096
            or any(ord(c) < 32 or ord(c) == 127 for c in search)
        ):
            _invalid("search 必须是非空路径子串")
        if path:
            entry = self._entry(commit_hash, path)
            if entry is None:
                raise AppError(40400, "目录不存在")
            if entry["type"] != "tree":
                _invalid("tree 路径不是目录")
        spec = commit_hash + (":" + path if path else "")
        raw = self._git("ls-tree", "-rlz" if search is not None else "-lz", spec, binary=True)
        entries = self._entries(raw, path + "/" if path else "")
        unsupported = [e["path"] for e in entries if e["type"] not in ("tree", "blob")]
        entries = [
            e
            for e in entries
            if e["type"] in ("tree", "blob") and (search is None or search in e["path"])
        ]
        for entry in entries:
            entry.pop("object_id")
        return {
            "commit_hash": commit_hash,
            "path": path,
            "entries": entries[:1000],
            "truncated": len(entries) > 1000,
            "skipped": [{"path": p, "reason": "unsupported_gitlink"} for p in unsupported[:1000]],
        }

    def file(self, commit_hash, path, start_line=1, end_line=None) -> dict:
        commit_hash = self.resolve(commit_hash)
        path = _path(path)
        if type(start_line) is not int or start_line < 1:
            _invalid("start_line 必须是正整数")
        if end_line is not None and (type(end_line) is not int or end_line < start_line):
            _invalid("end_line 必须是大于等于 start_line 的整数")
        result = {
            "commit_hash": commit_hash,
            "path": path,
            "status": "not_found",
            "content": None,
            "start_line": start_line,
            "end_line": None,
            "total_lines": None,
            "size_bytes": None,
            "encoding": None,
            "reason": "not_found",
        }
        entry = self._entry(commit_hash, path)
        if entry is None:
            return result
        if entry["type"] != "blob" or entry["mode"] not in ("100644", "100755"):
            result["reason"] = "not_regular_blob"
            return result
        size = int(self._git("cat-file", "-s", entry["object_id"]).strip())
        result["size_bytes"] = size
        if size > self.file_size_max:
            result.update(status="too_large", reason="file_size_max")
            return result
        body = self._git("cat-file", "blob", entry["object_id"], binary=True)
        try:
            if b"\x00" in body:
                raise UnicodeError
            text = body.decode("utf-8")
        except UnicodeError:
            result.update(status="binary", reason="nul_or_non_utf8")
            return result
        lines = text.split('\n') if text else []
        if text.endswith('\n'):
            lines.pop()
        total = len(lines)
        if (
            (total and start_line > total)
            or (not total and start_line != 1)
        ):
            _invalid("请求行范围超过文件末尾")
        end = min(total, end_line if end_line is not None else start_line + 1999, start_line + 1999)
        result.update(
            status="ok",
            content='\n'.join(lines[start_line - 1 : end]) + ('\n' if end >= start_line and (end < total or text.endswith('\n')) else ''),
            end_line=end,
            total_lines=total,
            encoding="utf-8",
            reason=None,
        )
        return result

    def diff(self, commit_hash) -> str:
        commit_hash = self.resolve(commit_hash)
        raw = self._git(
            "show", "--format=", "--unified=0", "--no-renames", commit_hash, "--", binary=True
        )
        if len(raw) > _DIFF_MAX:
            _invalid("提交 diff 超过 4 MiB 限制")
        return raw.decode("utf-8", "replace")

    def history(self, commit_hash) -> list[dict]:
        commit_hash = self.resolve(commit_hash)
        classifier = importlib.import_module("preparation.02_szz_labeling").is_fix_commit
        raw = self._git(
            "log",
            "--no-merges",
            "--max-count=200",
            "--format=%H%x00%ct%x00%B%x00",
            commit_hash,
            "--",
            binary=True,
        )
        parts = raw.decode("utf-8", "replace").split("\x00")
        result = []
        for i in range(0, len(parts) - 2, 3):
            hash_value, timestamp, message = parts[i : i + 3]
            message = message.strip()
            if hash_value.strip() != commit_hash and classifier(message):
                result.append(
                    {
                        "commit_hash": _hash(hash_value.strip()),
                        "message": message,
                        "committed_at": datetime.fromtimestamp(int(timestamp), UTC)
                        .isoformat()
                        .replace("+00:00", "Z"),
                    }
                )
                if len(result) == 3:
                    break
        return result


def _metadata_string(value, name):
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > 4096
        or any(ord(c) < 32 or ord(c) == 127 for c in value)
    ):
        _invalid(f"{name} 必须是非空字符串")
    return value


def _identity(row):
    if not isinstance(row, dict):
        _invalid("预测或解释行必须是对象")
    return (
        _hash(row.get("commit_hash")),
        *(
            _metadata_string(row.get(key), key)
            for key in ("model_name", "model_version", "feature_version")
        ),
    )


def _prediction(row):
    identity = _identity(row)
    risk = row.get("risk_score")
    if not _number(risk) or not 0 <= risk <= 1:
        _invalid("预测风险必须是 0..1 的有限数值")
    return {
        "commit_hash": identity[0],
        "model_name": identity[1],
        "model_version": identity[2],
        "feature_version": identity[3],
        "risk_score": float(risk),
    }


def _explanations(rows, identities):
    if rows is not None and not isinstance(rows, list):
        _invalid("解释必须是行列表")
    grouped = {}
    for row in rows or []:
        identity = _identity(row)
        if identity not in identities:
            _invalid("解释提交、模型或版本与预测不一致")
        grouped.setdefault(identity, []).append(row)
    return grouped


def _explanation_context(rows):
    contributions, reasons = [], []
    for row in rows:
        if row.get("reason_code"):
            reasons.append(str(row["reason_code"])[:1000])
            continue
        value = row.get("contribution")
        if not _number(value):
            _invalid("解释贡献必须是有限有符号数值")
        feature = _metadata_string(row.get("feature"), "feature")
        if value != 0:
            contributions.append(
                {
                    "feature": feature,
                    "raw_value": row.get("raw_value"),
                    "contribution": float(value),
                }
            )
    missing = []
    if not rows or reasons:
        missing.append("missing_explanation")
    if rows and not reasons and not contributions:
        missing.append("zero_explanation")
    return {
        "contributions": contributions,
        "reasons": reasons,
        "mapping_note": "提交级有符号贡献仅作为审查背景，不证明任何文件或行的特征归因。",
    }, missing


def _finite_score(value):
    if not math.isfinite(value):
        _invalid("权重组合导致分数溢出")
    return value


def _parse_diff(text):
    # Git adds a TAB delimiter to space-containing paths and C-quotes some
    # names. Normalize metadata only; the shared parser owns all hunk logic.
    normalized = []
    for raw in text.split('\n'):
        if raw.startswith("+++ "):
            name = raw[4:]
            if name.startswith('"'):
                token = name.split("\t", 1)[0]
                escaped = "".join(
                    chr(b) if b < 128 else f"\\x{b:02x}" for b in token.encode("utf-8")
                )
                try:
                    name = ast.literal_eval("b" + escaped).decode("utf-8")
                except (ValueError, SyntaxError, UnicodeError):
                    _invalid("diff 路径编码非法")
            else:
                name = name.removesuffix("\t")
            raw = "+++ " + name
        normalized.append(raw)
    return parse_unified_diff("\n".join(normalized))


def _score_files(files, weights):
    scored = []
    for file in files:
        path = file["path"]
        _, label = _file_weight(path)
        kind = _FILE_KIND[label]
        added, deleted = len(file["added_lines"]), file["deleted_count"]
        hunks = file["hunks"]
        raw = added + weights["change"]["deleted"] * deleted
        raw *= weights["change"]["modified"] if added and deleted else 1
        raw *= weights["file_types"][kind] * (1 + weights["hunk"] * min(max(len(hunks) - 1, 0), 4))
        scored.append({**file, "kind": kind, "category": label, "file_raw": _finite_score(raw)})
    maximum = max((f["file_raw"] for f in scored), default=0)
    for file in scored:
        file["file_norm"] = file["file_raw"] / maximum if maximum else 0
        for hunk in file["hunks"]:
            hunk["raw"] = _finite_score(
                sum(
                    weights["line_content"][_LINE_KIND[_line_content_weight(line)]]
                    for line in hunk["added_lines"]
                )
                + weights["change"]["deleted"] * hunk["deleted_count"]
                + int(bool(hunk["added_lines"] and hunk["deleted_count"]))
            )
        hmax = max((h["raw"] for h in file["hunks"]), default=0)
        for hunk in file["hunks"]:
            hunk["norm"] = hunk["raw"] / hmax if hmax else 0
    return sorted(scored, key=lambda f: (-f["file_raw"], f["path"]))


def _verified_candidates(reader, commit, file, risk, cfg):
    path = file["path"]
    payload = reader.file(commit, path)
    if payload["status"] != "ok":
        return [], [payload["status"]]
    if payload["size_bytes"] > cfg["file_size_max"]:
        return [], ["too_large"]
    cached = {
        i: text.removesuffix('\r') for i, text in enumerate(payload['content'].split('\n')[:payload['end_line'] - payload['start_line'] + 1], payload['start_line'])
    }
    total = payload["total_lines"]
    candidates, issues = [], []
    weights = cfg["weights"]
    for hunk_index, hunk in enumerate(file["hunks"], 1):
        for line in hunk["added_lines"]:
            number = line["number"]
            if not 1 <= number <= total:
                issues.append("blob_line_mismatch")
                continue
            start, end = max(1, number - 2), min(total, number + 2)
            if any(n not in cached for n in range(start, end + 1)):
                window = reader.file(commit, path, start, min(total, start + 1999))
                if window["status"] != "ok":
                    issues.append(window["status"])
                    continue
                cached.update(enumerate((text.removesuffix('\r') for text in window['content'].split('\n')[:window['end_line'] - window['start_line'] + 1]), window['start_line']))
            if cached[number] != line["content"]:
                issues.append("blob_line_mismatch")
                continue
            line_kind = _LINE_KIND[_line_content_weight(line)]
            mix = weights["mix"]
            suspicion = risk * (
                mix["base"] + mix["file"] * file["file_norm"] + mix["hunk"] * hunk["norm"]
            )
            suspicion *= weights["line_content"][line_kind] * weights["line_path"][file["kind"]]
            candidates.append(
                {
                    "number": number,
                    "content": line["content"],
                    "suspicion": max(0.0, min(1.0, _finite_score(suspicion))),
                    "line_kind": line_kind,
                    "hunk": {
                        "index": hunk_index,
                        "raw": hunk["raw"],
                        "norm": hunk["norm"],
                        "deleted_count": hunk["deleted_count"],
                    },
                    "context": [{"number": n, "content": cached[n]} for n in range(start, end + 1)],
                }
            )
    candidates.sort(key=lambda line: (-line["suspicion"], path, line["number"]))
    return candidates, sorted(set(issues))


def _json(value):
    try:
        return json.dumps(value, ensure_ascii=False, allow_nan=False)
    except (ValueError, TypeError, OverflowError):
        _invalid("输入证据不能编码为有限 JSON 数据")


def _suggestions(pred, selected, explanation, history, sources, llm):
    # At most 5 files / 30 lines each; no whole diff or unbounded source for callbacks.
    facts = {
        "prediction": pred,
        "top_files": [
            {
                "path": file["path"],
                "score": file["file_norm"],
                "lines": [
                    {
                        "number": line["number"],
                        "content": line["content"][:500],
                        "score": line["suspicion"],
                    }
                    for line in file["selected_lines"][:30]
                ],
            }
            for file in selected[:5]
        ],
        "top_factors": [row["feature"][:100] for row in explanation["contributions"][:20]],
        "historical_fixes": [{**ref, "message": ref["message"][:1000]} for ref in history[:3]],
        "mapping_note": explanation["mapping_note"],
    }
    actual, issues, instructions = [], [], []
    if "template" in sources:
        instructions.extend(template_suggestions(facts))
        actual.append("template")
    if "llm" in sources:
        try:
            response = llm(deepcopy(facts)) if llm is not None else None
            valid = (
                isinstance(response, list)
                and 1 <= len(response) <= 3
                and all(isinstance(s, str) and s.strip() and len(s) <= 1000 for s in response)
            )
        except Exception:
            valid = False
        if valid:
            instructions.extend(response)
            actual.append("llm")
        else:
            if not instructions:
                instructions.extend(template_suggestions(facts))
            actual.append("template_fallback")
            issues.append("llm_unavailable")
    if "history" in sources:
        actual.append("history")
    if not instructions:
        instructions.append("根据下列真实版本证据复核改动；没有可靠证据时不自动修改代码。")
    cites = [f"{f['path']}:{line['number']}" for f in selected for line in f["selected_lines"]]
    references = cites + [f"{h['commit_hash']} {h['message']}" for h in history]
    references = references or [pred["commit_hash"] + "（无可验证新增文本行）"]
    title = f"# {pred['commit_hash']} / {pred['model_name']} / {pred['model_version']} / {pred['feature_version']}"
    text = "\n".join(
        [
            title,
            "## 问题说明",
            f"提交风险 {pred['risk_score']:g}；以下定位仅为启发式审查线索，不断言存在缺陷。",
            "## 建议修改",
            *(f"- {s}" for s in instructions),
            "## 风险提示",
            "提交级解释不等于行级归因；仅复核，不自动应用补丁。"
            + (" LLM 不可用，使用 template_fallback。" if issues else ""),
            "## 参考依据",
            *(f"- {r}" for r in references),
        ]
    )
    return text, actual, issues


def localize(
    reader,
    predictions: list[dict],
    config: dict,
    *,
    explanations: list[dict] | None = None,
    llm=None,
) -> dict:
    cfg = validate_config(config)
    if not isinstance(predictions, list) or not predictions:
        _invalid("必须提供非空预测行列表")
    normalized = [_prediction(row) for row in predictions]
    identities = {_identity(p) for p in normalized}
    grouped = _explanations(explanations, identities)
    targets = [
        p
        for p in normalized
        if (cfg["commit_hash"] is None or cfg["commit_hash"] == p["commit_hash"])
        and (cfg["model_name"] is None or cfg["model_name"] == p["model_name"])
    ]
    if not targets:
        _invalid("筛选后没有目标预测")
    rows, evidence, suggestions, actual_sources = [], {}, [], []
    insufficient_count, truncated = 0, False
    # Enforce the caller's configured cap before blob reads, without increasing the reader cap.
    original_limit = reader.file_size_max
    reader.file_size_max = min(original_limit, cfg["file_size_max"])
    try:
        for pred in targets:
            commit = reader.resolve(pred["commit_hash"])
            pred["commit_hash"] = commit
            if commit not in evidence:
                diff = reader.diff(commit)
                evidence[commit] = {
                    "diff": diff,
                    "files": [],
                    "scores": [],
                    "predictions": [],
                    "insufficiencies": [],
                    "meta": {"source": "immutable_git_objects"},
                }
            aggregate = evidence[commit]
            explanation, issues = _explanation_context(grouped.get(_identity(pred), []))
            history = reader.history(commit) if "history" in cfg["suggestion_sources"] else []
            scored = _score_files(_parse_diff(aggregate["diff"]), cfg["weights"])
            if len(scored) > cfg["top_n"]["files"]:
                truncated = True
            selected = []
            for file in scored[: cfg["top_n"]["files"]]:
                candidates, file_issues = _verified_candidates(
                    reader, commit, file, pred["risk_score"], cfg
                )
                issues.extend(file_issues)
                if len(candidates) > cfg["top_n"]["lines"]:
                    truncated = True
                file["selected_lines"] = candidates[: cfg["top_n"]["lines"]]
                file["insufficiencies"] = file_issues
                if file["selected_lines"]:
                    selected.append(file)
            if not selected:
                issues.append("no_added_text_lines")
            suggestion, used, suggestion_issues = _suggestions(
                pred, selected, explanation, history, cfg["suggestion_sources"], llm
            )
            suggestions.append(suggestion)
            actual_sources.extend(used)
            issues = sorted(set(issues + suggestion_issues))
            insufficient_count += bool(issues)
            aggregate["insufficiencies"] = sorted(set(aggregate["insufficiencies"] + issues))
            file_evidence = [
                {
                    "path": f["path"],
                    "category": f["category"],
                    "file_raw": f["file_raw"],
                    "file_norm": f["file_norm"],
                    "added_count": len(f["added_lines"]),
                    "deleted_count": f["deleted_count"],
                    "hunks": f["hunks"],
                    "selected_lines": f.get("selected_lines", []),
                    "insufficiencies": f.get("insufficiencies", []),
                }
                for f in scored
            ]
            aggregate["files"] = file_evidence
            aggregate["scores"] = [
                {"path": f["path"], "raw": f["file_raw"], "norm": f["file_norm"]} for f in scored
            ]
            aggregate["predictions"].append(
                {
                    "prediction": pred,
                    "files": file_evidence,
                    "explanation": explanation,
                    "history": history,
                    "insufficiencies": issues,
                }
            )
            base = {
                "prediction": pred,
                "explanation": explanation,
                "history": history,
                "insufficiencies": issues,
                "signal_weights": cfg["weights"],
                "diff_meta": {
                    "bytes": len(aggregate["diff"].encode("utf-8")),
                    "files": len(scored),
                    "format": "unified=0",
                    "source": "immutable_git_objects",
                },
            }
            candidates = [(file, line) for file in selected for line in file["selected_lines"]]
            candidates.sort(
                key=lambda pair: (-pair[1]["suspicion"], pair[0]["path"], pair[1]["number"])
            )
            for rank, (file, line) in enumerate(candidates, 1):
                detail = {
                    **base,
                    "line": {
                        "number": line["number"],
                        "content": line["content"],
                        "kind": line["line_kind"],
                    },
                    "context": line["context"],
                    "file": {
                        "path": file["path"],
                        "category": file["category"],
                        "file_raw": file["file_raw"],
                        "file_norm": file["file_norm"],
                    },
                    "hunk": line["hunk"],
                }
                rows.append(
                    {
                        "commit_hash": commit,
                        "file_path": file["path"],
                        "line_number": line["number"],
                        "suspicion": line["suspicion"],
                        "rank": rank,
                        "evidence_json": _json(detail),
                        "level": "line",
                    }
                )
            if not candidates:
                rows.append(
                    {
                        "commit_hash": commit,
                        "file_path": None,
                        "line_number": None,
                        "suspicion": pred["risk_score"],
                        "rank": 1,
                        "evidence_json": _json(base),
                        "level": "commit",
                    }
                )
    finally:
        reader.file_size_max = original_limit
    result = {
        "rows": rows,
        "evidence": evidence,
        "suggestions": "\n\n".join(suggestions),
        "config": cfg,
        "summary": {
            "commits": len(evidence),
            "localized_rows": len(rows),
            "insufficient_count": insufficient_count,
            "truncated": truncated,
            "suggestion_sources": list(dict.fromkeys(actual_sources)),
            "patch_reason": "no_reliable_patch" if cfg["patch_preview"] else None,
        },
    }
    _json(result)
    return result
