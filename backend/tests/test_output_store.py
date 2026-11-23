# 来源：[AI生成]；尚未人工审核，不作为课程审核完成证据。

import importlib
import importlib.util
import json

import pytest
from app.errors import AppError


def store(tmp_path, monkeypatch):
    assert importlib.util.find_spec("app.services.output_store") is not None, "Output store is missing"
    module = importlib.import_module("app.services.output_store")
    monkeypatch.setattr(module, "OUTPUT_ROOT", tmp_path / "outputs")
    return module


def test_published_files_have_manifest_checksums_and_survive_new_reader(tmp_path, monkeypatch):
    module = store(tmp_path, monkeypatch)
    result = module.publish_output("storage", {"storage_commit_j-test.csv": b"\xef\xbb\xbfcommit_hash\r\n"},
                                   inputs=[], config={"table": "commit", "format": "csv"},
                                   job_id="j-test", code_version="verified-test")
    assert result["job_id"] == "j-test"
    assert len(result["outputs"]) == 2
    manifest = json.loads(module.read_output("storage", "j-test", result["manifest_name"]).read_bytes())
    assert manifest["schema_version"] == "1.0"
    assert manifest["code_version"] == "verified-test"
    assert manifest["outputs"][0]["sha256"] == module.sha256(b"\xef\xbb\xbfcommit_hash\r\n")
    assert module.read_output("storage", "j-test", "storage_commit_j-test.csv").read_bytes().startswith(b"\xef\xbb\xbf")


@pytest.mark.parametrize("module_name,job_id,name", [
    ("unknown", "j-test", "file.csv"), ("storage", "../x", "file.csv"),
    ("storage", "j-test", "../file.csv"), ("storage", "j-test", "file.exe"),
])
def test_unsafe_publication_never_leaves_final_output(tmp_path, monkeypatch, module_name, job_id, name):
    module = store(tmp_path, monkeypatch)
    with pytest.raises(AppError) as error:
        module.publish_output(module_name, {name: b"bytes"}, inputs=[], config={}, job_id=job_id, code_version="test")
    assert error.value.code == 40001
    assert not (tmp_path / "x").exists()


def test_every_artifact_has_same_stem_manifest_and_shared_table_formats(tmp_path, monkeypatch):
    module = store(tmp_path, monkeypatch)
    artifacts = {'collect_commits_batch.csv': b'csv', 'collect_commits_batch.xlsx': b'xlsx',
                 'collect_summary_batch.json': b'{}'}
    result = module.publish_output('collect', artifacts, inputs=[], config={},
                                   job_id='batch', code_version='test')
    names = {item['name'] for item in result['outputs']}
    assert names == set(artifacts) | {'collect_commits_batch.manifest.json', 'collect_summary_batch.manifest.json'}
    for name, content in artifacts.items():
        manifest_name = name.rsplit('.', 1)[0] + '.manifest.json'
        raw_manifest = module.read_output('collect', 'batch', manifest_name).read_bytes()
        manifest = json.loads(raw_manifest)
        assert any(item['name'] == name and item['sha256'] == module.sha256(content) for item in manifest['outputs'])
    assert result['manifest_name'] == 'collect_commits_batch.manifest.json'


def test_existing_output_is_immutable(tmp_path, monkeypatch):
    module = store(tmp_path, monkeypatch)
    args = {"inputs": [], "config": {}, "job_id": "j-test", "code_version": "test"}
    module.publish_output("storage", {"file.csv": b"original"}, **args)
    with pytest.raises(AppError):
        module.publish_output("storage", {"file.csv": b"replacement"}, **args)
    assert module.read_output("storage", "j-test", "file.csv").read_bytes() == b"original"


def test_download_refuses_unknown_module_file_and_changed_content(tmp_path, monkeypatch):
    module = store(tmp_path, monkeypatch)
    module.publish_output("storage", {"file.csv": b"original"}, inputs=[], config={}, job_id="j-test", code_version="test")
    for owner, name in [("collect", "file.csv"), ("storage", ".index.json"), ("storage", "unknown.csv")]:
        with pytest.raises(AppError) as error:
            module.read_output(owner, "j-test", name)
        assert error.value.code == 40400
    path = module.OUTPUT_ROOT / "j-test" / "file.csv"
    path.write_bytes(b"tampered")
    with pytest.raises(AppError):
        module.read_output("storage", "j-test", "file.csv")


def test_download_refuses_symlink_escape(tmp_path, monkeypatch):
    module = store(tmp_path, monkeypatch)
    module.publish_output("storage", {"file.csv": b"original"}, inputs=[], config={}, job_id="j-test", code_version="test")
    outside = tmp_path / "outside.csv"
    outside.write_bytes(b"original")
    artifact = module.OUTPUT_ROOT / "j-test" / "file.csv"
    artifact.unlink()
    artifact.symlink_to(outside)
    with pytest.raises(AppError):
        module.read_output("storage", "j-test", "file.csv")


def test_nonbytes_artifact_is_rejected_before_publication(tmp_path, monkeypatch):
    module = store(tmp_path, monkeypatch)
    with pytest.raises(AppError):
        module.publish_output("storage", {"file.csv": "not bytes"}, inputs=[], config={}, job_id="j-test", code_version="test")
    assert not (module.OUTPUT_ROOT / "j-test").exists()
