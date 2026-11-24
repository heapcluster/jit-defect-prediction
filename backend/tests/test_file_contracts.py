# 来源：[AI生成]；尚未人工审核，不作为课程审核完成证据。

import importlib
import importlib.util
import io
import json
import zipfile
from decimal import Decimal

import pytest
from app.errors import AppError
from openpyxl import Workbook, load_workbook


def contracts():
    assert importlib.util.find_spec("app.services.file_contracts") is not None, "File contract parser is missing"
    return importlib.import_module("app.services.file_contracts")


def xlsx_bytes(rows):
    book = Workbook()
    for row in rows:
        book.active.append(row)
    output = io.BytesIO()
    book.save(output)
    return output.getvalue()


def test_csv_reads_bom_unicode_and_empty_label():
    columns, rows = contracts().read_table("labels.csv", "\ufeffcommit_hash,is_bug_inducing,labeled_at\n".encode() + b"a" * 40 + b",,\n")
    assert columns == ["commit_hash", "is_bug_inducing", "labeled_at"]
    assert rows[0]["is_bug_inducing"] == ""


def test_xlsx_and_csv_normalize_to_the_same_rows():
    columns = ["commit_hash", "is_bug_inducing", "labeled_at"]
    rows = [["a" * 40, 1, "2026-11-22T00:00:00Z"], ["b" * 40, None, None]]
    from_csv = contracts().read_table("labels.csv", (','.join(columns) + '\n' + 'a' * 40 + ',1,2026-11-22T00:00:00Z\n' + 'b' * 40 + ',,\n').encode())
    from_xlsx = contracts().read_table("labels.xlsx", xlsx_bytes([columns, *rows]))
    assert from_csv == from_xlsx


@pytest.mark.parametrize("name,content", [
    ("../labels.csv", b"a\n1\n"), ("labels.exe", b"a\n1\n"),
    ("labels.xlsx", b"a\n1\n"), ("labels.csv", b"PK\x03\x04"),
    ("labels.csv", b"a,a\n1,2\n"), ("labels.csv", b"a,b\n1,2,3\n"),
    ("labels.csv", b"a\n=SUM(1)\n"), ("labels.csv", b"a\n +cmd\n"),
    ("labels.csv", b"a\n\xff\n"), ("labels.csv", b""),
])
def test_invalid_table_inputs_are_rejected(name, content):
    with pytest.raises(AppError) as rejected:
        contracts().read_table(name, content)
    assert rejected.value.code == 40001


def test_negative_numeric_features_are_not_formula_injection():
    _, rows = contracts().read_table("features.csv", b"la,ld\n-0.1234,-5.8\n")
    assert rows == [{"la": "-0.1234", "ld": "-5.8"}]


def test_xlsx_formula_is_rejected():
    content = xlsx_bytes([["commit_hash", "is_bug_inducing"], ["a" * 40, "=1+1"]])
    with pytest.raises(AppError) as rejected:
        contracts().read_table("labels.xlsx", content)
    assert rejected.value.code == 40001


def test_table_row_and_upload_size_limits_are_enforced(monkeypatch):
    module = contracts()
    monkeypatch.setattr(module, "MAX_ROWS", 1)
    with pytest.raises(AppError):
        module.read_table("rows.csv", b"a\n1\n2\n")
    monkeypatch.setattr(module, "MAX_UPLOAD_BYTES", 3)
    with pytest.raises(AppError):
        module.read_table("rows.csv", b"a\n1\n")


def test_encoder_protects_text_and_preserves_numbers_and_nulls():
    columns = ["message", "risk_score", "is_bug_inducing"]
    rows = [{"message": "=危险公式", "risk_score": Decimal("0.12345"), "is_bug_inducing": None}]
    csv = contracts().encode_table(columns, rows, "csv")
    assert csv.startswith(b"\xef\xbb\xbf")
    assert "'=危险公式" in csv.decode("utf-8-sig")
    assert "0.12345," in csv.decode("utf-8-sig")
    book = load_workbook(io.BytesIO(contracts().encode_table(columns, rows, "xlsx")))
    assert len(book.worksheets) == 1
    assert book.active.cell(2, 1).data_type != "f"
    assert book.active.cell(2, 3).value is None


def test_zip_validation_rejects_traversal_and_symlinks():
    for name, mode in [("../weights.pkl", None), ("weights.pkl", 0o120777)]:
        raw = io.BytesIO()
        with zipfile.ZipFile(raw, "w") as archive:
            info = zipfile.ZipInfo(name)
            if mode:
                info.create_system = 3
                info.external_attr = mode << 16
            archive.writestr(info, b"opaque weights")
        with pytest.raises(AppError) as rejected:
            contracts().read_zip("model_package.zip", raw.getvalue())
        assert rejected.value.code == 40001


def test_zip_checks_crc_and_uncompressed_limits(monkeypatch):
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("weight.pkl", b"0" * 100)
    module = contracts()
    monkeypatch.setattr(module, "MAX_UNPACKED_BYTES", 20)
    with pytest.raises(AppError):
        module.read_zip("model_package.zip", raw.getvalue())


def test_malformed_deflate_returns_400_not_an_internal_error():
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("weights.pkl", b"opaque" * 20)
        offset = archive.getinfo("weights.pkl").header_offset + 30 + len("weights.pkl")
    broken = bytearray(raw.getvalue())
    broken[offset] = 7
    with pytest.raises(AppError) as rejected:
        contracts().read_zip("model_package.zip", bytes(broken))
    assert rejected.value.code == 40001


def test_malformed_xlsx_xml_returns_400():
    members = contracts().read_zip("data.xlsx", xlsx_bytes([["a"], [1]]))
    members["xl/workbook.xml"] = b"<workbook>"
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name, content in members.items():
            archive.writestr(name, content)
    with pytest.raises(AppError) as rejected:
        contracts().read_table("data.xlsx", output.getvalue())
    assert rejected.value.code == 40001


def test_xlsx_dtd_entities_are_not_expanded():
    members = contracts().read_zip("data.xlsx", xlsx_bytes([["a"], [1]]))
    members["xl/workbook.xml"] = b'<!DOCTYPE workbook [<!ENTITY entity "data">]>' + members["xl/workbook.xml"].replace(b'name="Sheet"', b'name="&entity;"')
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name, content in members.items():
            archive.writestr(name, content)
    with pytest.raises(AppError) as rejected:
        contracts().read_table("data.xlsx", output.getvalue())
    assert rejected.value.code == 40001


def test_invalid_lzma_properties_are_a_client_error():
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, "w", compression=zipfile.ZIP_LZMA) as archive:
        archive.writestr("weights.pkl", b"opaque" * 20)
        offset = archive.getinfo("weights.pkl").header_offset + 30 + len("weights.pkl")
    broken = bytearray(raw.getvalue())
    broken[offset + 4] = 255
    with pytest.raises(AppError) as rejected:
        contracts().read_zip("model_package.zip", bytes(broken))
    assert rejected.value.code == 40001


def test_invalid_xlsx_shared_string_reference_is_a_client_error():
    members = contracts().read_zip("data.xlsx", xlsx_bytes([["a"], [1]]))
    members["xl/worksheets/sheet1.xml"] = b'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="s"><v>9999</v></c></row></sheetData></worksheet>'
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name, content in members.items():
            archive.writestr(name, content)
    with pytest.raises(AppError) as rejected:
        contracts().read_table("data.xlsx", output.getvalue())
    assert rejected.value.code == 40001


def test_manifest_checksum_must_match_and_feature_version_is_not_invented():
    module = contracts()
    payload = b"a\n1\n"
    manifest = {"schema_version": "1.0", "module": "collect", "job_id": "j-source", "inputs": [],
                "config": {"feature_version": "v1"}, "outputs": [{"name": "commits.csv", "sha256": module.sha256(payload)}],
                "code_version": "verified-test", "created_at": "2026-11-22T00:00:00Z"}
    result = module.verify_manifest("commits.csv", payload, json.dumps(manifest).encode())
    assert result["config"]["feature_version"] == "v1"
    manifest["outputs"][0]["sha256"] = "0" * 64
    with pytest.raises(AppError):
        module.verify_manifest("commits.csv", payload, json.dumps(manifest).encode())
