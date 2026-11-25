from __future__ import annotations

import csv
import hashlib
import io
import json
import lzma
import math
import re
import stat
import zipfile
import zlib
from datetime import datetime
from decimal import Decimal
from pathlib import PurePosixPath
from xml.etree.ElementTree import ParseError

from defusedxml.common import DefusedXmlException
from openpyxl import Workbook, load_workbook

from app.config import FEATURE_COLUMNS
from app.errors import AppError

MAX_UPLOAD_BYTES = 64 * 1024 * 1024
MAX_UNPACKED_BYTES = 512 * 1024 * 1024
MAX_ROWS = 100000
MAX_COLUMNS = 100
MAX_ZIP_FILES = 1000

# 外部交换文件（collect/clean/train 之间）：已打标二维表，不含 Kamei 14 维与 is_test。
COLLECTED_COMMITS_COLUMNS = (
    "commit_hash", "repo_name", "repo_url", "author_name", "author_email", "committed_at",
    "message", "parent_hash", "is_bug_inducing", "label_method", "label_source", "labeled_at",
    "fix_commit_hash", "source_type",
)
COLLECTED_COMMITS_REQUIRED = {"commit_hash", "repo_name", "is_bug_inducing", "label_source", "source_type"}
CLEAN_DATASET_COLUMNS = (*COLLECTED_COMMITS_COLUMNS, "message_length", "parent_count", "commit_hour")
CLEAN_DATASET_REQUIRED = COLLECTED_COMMITS_REQUIRED

# 内部特征表（训练/预测/解释内核之间）：含 Kamei 14 维与 is_test，不对外 handoff。
COMMITS_COLUMNS = ("commit_hash", "repo_name", "author_name", "author_email", "committed_at", "message",
                   "parent_hash", *FEATURE_COLUMNS, "is_bug_inducing", "labeled_at", "is_test", "label_method")
COMMITS_REQUIRED = {"commit_hash", "repo_name", "author_name", "committed_at", "message", "is_test", *FEATURE_COLUMNS}

PREDICTIONS_COLUMNS = ("commit_hash", "model_name", "risk_score", "predicted_label", "decision_threshold",
                       "model_version", "feature_version", "predicted_at", "is_bug_inducing")
# §3.4：is_bug_inducing 列必须存在（值在新提交预测场景允许为空），不能当作可选列漏掉。
PREDICTIONS_REQUIRED = set(PREDICTIONS_COLUMNS)


def invalid(message: str) -> None:
    raise AppError(40001, message)


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def validate_upload_name(name: str) -> None:
    if not name or len(name) > 255 or name in (".", "..") or any(ord(c) < 32 for c in name) or any(c in name for c in ("/", "\\", ":")):
        invalid("文件名非法")


def _bounded_upload(name: str, content: bytes) -> None:
    validate_upload_name(name)
    if not content or len(content) > MAX_UPLOAD_BYTES:
        invalid("文件为空或超过上传大小限制")


def _numeric_text(value: str) -> bool:
    try:
        return math.isfinite(float(value))
    except (ValueError, OverflowError):
        return False


def _formula(value: str) -> bool:
    stripped = value.lstrip(" \t\r\n")
    return bool(stripped) and stripped[0] in "=+-@" and not _numeric_text(stripped)


def _cell_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat() + ("Z" if value.tzinfo is None else "")
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _table(rows) -> tuple[list[str], list[dict]]:
    iterator = iter(rows)
    header = next(iterator, None)
    if not header:
        invalid("表格缺少列名")
    columns = [_cell_text(value) for value in header]
    if len(columns) > MAX_COLUMNS or len(set(columns)) != len(columns) or any(not re.fullmatch(r"[a-z][a-z0-9_]*", name) for name in columns):
        invalid("表格列名非法或重复")
    result = []
    for row in iterator:
        values = [_cell_text(value) for value in row]
        if not any(values):
            continue
        if len(values) != len(columns):
            invalid("表格行宽与列名不一致")
        if any(_formula(value) for value in values):
            invalid("检测到表格公式注入")
        result.append(dict(zip(columns, values, strict=True)))
        if len(result) > MAX_ROWS:
            invalid("表格超过行数限制")
    return columns, result


def read_zip(name: str, content: bytes) -> dict[str, bytes]:
    _bounded_upload(name, content)
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            infos = archive.infolist()
            names = [entry.filename for entry in infos]
            if len(infos) > MAX_ZIP_FILES or len(set(names)) != len(names) or sum(entry.file_size for entry in infos) > MAX_UNPACKED_BYTES:
                invalid("ZIP 包规模超限或存在重复条目")
            for entry in infos:
                path = PurePosixPath(entry.filename)
                if path.is_absolute() or ".." in path.parts or "\\" in entry.filename or ":" in entry.filename or any(ord(c) < 32 for c in entry.filename):
                    invalid("ZIP 包含不安全路径")
                if stat.S_ISLNK(entry.external_attr >> 16) or entry.flag_bits & 1:
                    invalid("ZIP 不允许符号链接或加密条目")
                if entry.file_size > max(entry.compress_size, 1) * 1000:
                    invalid("ZIP 压缩比超限")
            return {entry.filename: archive.read(entry) for entry in infos if not entry.is_dir()}
    except (zipfile.BadZipFile, zipfile.LargeZipFile, RuntimeError, OSError, ValueError, zlib.error, lzma.LZMAError, NotImplementedError) as error:
        raise AppError(40001, "ZIP 格式或 CRC 校验失败") from error


def read_table(name: str, content: bytes) -> tuple[list[str], list[dict]]:
    _bounded_upload(name, content)
    extension = name.rsplit(".", 1)[-1].lower()
    if extension == "csv":
        try:
            text = content.decode("utf-8-sig")
            if "\x00" in text or text.startswith("PK\x03\x04"):
                invalid("CSV 编码或文件格式非法")
            return _table(csv.reader(io.StringIO(text, newline=""), strict=True))
        except (UnicodeDecodeError, csv.Error) as error:
            raise AppError(40001, "CSV 编码或文件格式非法") from error
    if extension == "xlsx":
        members = read_zip(name, content)
        if "[Content_Types].xml" not in members or "xl/workbook.xml" not in members or any("externalLinks/" in key or key.endswith("vbaProject.bin") for key in members):
            invalid("XLSX 格式非法或含外部链接/宏")
        try:
            book = load_workbook(io.BytesIO(content), read_only=True, data_only=False, keep_links=False)
            try:
                if len(book.worksheets) != 1:
                    invalid("XLSX 必须只有一个主表")
                sheet = book.worksheets[0]
                if sheet.max_row and sheet.max_row > MAX_ROWS + 1 or sheet.max_column and sheet.max_column > MAX_COLUMNS:
                    invalid("XLSX 行列数超限")
                def values():
                    for row in sheet.iter_rows():
                        if any(cell.data_type == "f" for cell in row):
                            invalid("XLSX 不允许公式单元格")
                        yield [cell.value for cell in row]
                return _table(values())
            finally:
                book.close()
        except (ValueError, KeyError, IndexError, OSError, zipfile.BadZipFile, ParseError, DefusedXmlException) as error:
            raise AppError(40001, "XLSX 解析失败") from error
    invalid("仅支持 CSV/XLSX 表格")


def _export_cell(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z") + ("Z" if value.tzinfo is None else "")
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, str) and _formula(value):
        return "'" + value
    return value


def encode_table(columns: list[str] | tuple[str, ...], rows: list[dict], format: str) -> bytes:
    if format not in ("csv", "xlsx"):
        invalid("导出格式只支持 CSV/XLSX")
    if format == "csv":
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(columns)
        for row in rows:
            writer.writerow([_export_cell(row.get(column)) for column in columns])
        return output.getvalue().encode("utf-8-sig")
    book = Workbook(write_only=True)
    sheet = book.create_sheet("data")
    sheet.append(list(columns))
    for row in rows:
        sheet.append([_export_cell(row.get(column)) for column in columns])
    output = io.BytesIO()
    book.save(output)
    return output.getvalue()


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            invalid("JSON 存在重复键")
        result[key] = value
    return result


def read_json(content: bytes) -> dict:
    if len(content) > MAX_UPLOAD_BYTES:
        invalid("JSON 文件超限")
    try:
        value = json.loads(content.decode("utf-8-sig"), object_pairs_hook=_unique_object,
                           parse_constant=lambda _: invalid("JSON 不允许非有限数值"))
        if not isinstance(value, dict):
            invalid("JSON 主结构须为对象")
        return value
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as error:
        raise AppError(40001, "JSON 格式非法") from error


def verify_manifest(name: str, content: bytes, raw_manifest: bytes) -> dict:
    manifest = read_json(raw_manifest)
    required = {"schema_version", "module", "job_id", "inputs", "config", "outputs", "code_version", "created_at"}
    if not required <= set(manifest) or manifest["schema_version"] != "1.0" or not isinstance(manifest["config"], dict):
        invalid("manifest 缺少契约字段或版本不支持")
    if not isinstance(manifest["outputs"], list) or not isinstance(manifest["inputs"], list):
        invalid("manifest 输入/输出索引非法")
    for key in ("module", "job_id", "code_version", "created_at"):
        if not isinstance(manifest[key], str) or not manifest[key]:
            invalid("manifest 元信息非法")
    found = []
    for item in manifest["outputs"]:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str) or not re.fullmatch(r"[0-9a-f]{64}", str(item.get("sha256", ""))):
            invalid("manifest 输出条目非法")
        validate_upload_name(item["name"])
        if item["name"] == name:
            found.append(item)
    if len(found) != 1 or found[0]["sha256"] != sha256(content):
        invalid("manifest 与上传文件 checksum 不一致")
    return manifest
