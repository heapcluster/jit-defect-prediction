"""AI-generated offline public-data tests, not yet human-reviewed."""
import csv
import importlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def modules(tmp_path, monkeypatch):
    assert (ROOT / 'data_model/preparation/public_load.py').exists(), 'public loader must exist'
    assert (ROOT / 'data_model/preparation/public_quality.py').exists(), 'public quality tool must exist'
    loader = importlib.import_module('data_model.preparation.public_load')
    quality = importlib.import_module('data_model.preparation.public_quality')
    monkeypatch.setattr(loader.output_store, 'OUTPUT_ROOT', tmp_path / 'outputs')
    return loader, quality


def source(tmp_path, records, columns=None):
    path = tmp_path / 'public.csv'
    with path.open('w', encoding='utf-8-sig', newline='') as target:
        writer = csv.DictWriter(target, fieldnames=columns or list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    return path


def rows():
    return [
        {'commit_hash': 'a' * 40, 'committed_at': '2026-01-01T00:00:00Z', 'is_bug_inducing': '1', 'language': 'Python'},
        {'commit_hash': 'b' * 40, 'committed_at': '2026-01-02T00:00:00Z', 'is_bug_inducing': '0', 'language': 'C++'},
    ]


def test_load_preserves_records_and_metadata_without_business_db(tmp_path, monkeypatch):
    loader, quality = modules(tmp_path, monkeypatch)
    path = source(tmp_path, rows())
    monkeypatch.setenv('DATABASE_URL', 'mysql+pymysql://invalid:invalid@127.0.0.1:1/unavailable')
    result = loader.load_public(name='AI unreviewed', source=path, license_id='CC-BY-4.0', out=tmp_path / 'dataset')
    metadata = json.loads((tmp_path / 'dataset/metadata.json').read_bytes())
    assert metadata['source_sha256'] == loader.fc.sha256(path.read_bytes())
    assert metadata['license'] == 'CC-BY-4.0' and metadata['source_rows'] == metadata['rows'] == 2
    assert metadata['sampled'] is False
    assert metadata['acquired_at'].endswith('Z')
    report = quality.analyze(rows())
    assert report['label_granularity'] == '二值，无缺陷类型'
    assert report['languages'] == {'C++': {'count': 1, 'ratio': 0.5}, 'Python': {'count': 1, 'ratio': 0.5}}
    assert result['outputs']
    assert not any(key in metadata for key in ('dataset_id', 'model_name'))


@pytest.mark.parametrize('missing', ['commit_hash', 'committed_at', 'is_bug_inducing'])
def test_missing_required_column_has_no_half_finished_directory(tmp_path, monkeypatch, missing):
    loader, _ = modules(tmp_path, monkeypatch)
    records = [{key: value for key, value in row.items() if key != missing} for row in rows()]
    path = source(tmp_path, records)
    with pytest.raises(Exception, match=missing):
        loader.load_public(name='fixture', source=path, license_id='CC-BY-4.0', out=tmp_path / 'dataset')
    assert not (tmp_path / 'dataset').exists()
    assert not (tmp_path / 'outputs').exists()


def test_explicit_mapping_does_not_fill_missing_kamei_features(tmp_path, monkeypatch):
    loader, _ = modules(tmp_path, monkeypatch)
    path = source(tmp_path, [{'commit': 'a' * 40, 'date': '2026-01-01T00:00:00Z', 'defective': '1'}])
    loader.load_public(name='fixture', source=path, license_id='CC-BY-4.0', out=tmp_path / 'dataset',
        mapping={'commit_hash': 'commit', 'committed_at': 'date', 'is_bug_inducing': 'defective'})
    columns, values = loader.fc.read_table('normalized.csv', (tmp_path / 'dataset/normalized.csv').read_bytes())
    assert 'ns' not in columns and values[0]['is_bug_inducing'] == '1'


def test_conflicting_labels_and_bad_time_are_retained_and_reported(tmp_path, monkeypatch):
    loader, quality = modules(tmp_path, monkeypatch)
    records = rows() + [{**rows()[0], 'is_bug_inducing': '0', 'committed_at': 'bad-time'}]
    path = source(tmp_path, records)
    loader.load_public(name='fixture', source=path, license_id='CC-BY-4.0', out=tmp_path / 'dataset')
    report = quality.analyze(records)
    assert report['label_conflicts'] == [{'commit_hash': 'a' * 40, 'rows': [1, 3]}]
    assert report['duplicate_count'] == 1
    assert report['invalid_time_rows'] == [3]
    assert json.loads((tmp_path / 'dataset/metadata.json').read_bytes())['rows'] == 3


def test_deterministic_month_stratified_sample_is_conservative(tmp_path, monkeypatch):
    loader, quality = modules(tmp_path, monkeypatch)
    records = [{**rows()[index % 2], 'commit_hash': f'{index:040x}',
        'committed_at': f'2026-{1 + index // 10:02d}-{1 + index % 10:02d}T00:00:00Z'} for index in range(30)]
    selected, layers = loader.stratified_sample(records, 12)
    again, other_layers = loader.stratified_sample(list(reversed(records)), 12)
    assert selected == again and layers == other_layers
    assert len(selected) == sum(layer['selected'] for layer in layers) == 12
    assert sum(layer['source_rows'] for layer in layers) == 30
    assert [layer['selected'] for layer in layers] == [4, 4, 4]
    assert quality.analyze(selected)['time_order_rows'] == []


def test_quality_reports_type_language_missing_and_time_range(tmp_path, monkeypatch):
    _, quality = modules(tmp_path, monkeypatch)
    records = rows() + [{**rows()[0], 'commit_hash': 'c' * 40, 'language': '', 'defect_type': 'logic', 'committed_at': '2025-01-01T00:00:00Z'}]
    report = quality.analyze(records, start_time='2026-01-01T00:00:00Z')
    assert report['defect_types']['logic'] == 1
    assert report['time_order_rows'] == [3] and report['out_of_range_rows'] == [3]
    assert report['missing_rates']['language'] == pytest.approx(1 / 3)


def test_unknown_license_is_not_silently_declared_open(tmp_path, monkeypatch):
    loader, _ = modules(tmp_path, monkeypatch)
    path = source(tmp_path, rows())
    with pytest.raises(Exception, match='许可'):
        loader.load_public(name='fixture', source=path, license_id='', out=tmp_path / 'dataset')
    assert not (tmp_path / 'dataset').exists()


def test_existing_public_data_is_not_overwritten(tmp_path, monkeypatch):
    loader, _ = modules(tmp_path, monkeypatch)
    destination = tmp_path / 'dataset'
    destination.mkdir()
    (destination / 'keep.txt').write_text('user content')
    with pytest.raises(Exception, match='已存在'):
        loader.load_public(name='fixture', source=source(tmp_path, rows()), license_id='CC-BY-4.0', out=destination)
    assert (destination / 'keep.txt').read_text() == 'user content'


def test_zero_sample_is_rejected_instead_of_turning_into_full_load(tmp_path, monkeypatch):
    loader, _ = modules(tmp_path, monkeypatch)
    with pytest.raises(Exception, match='抽样'):
        loader.load_public(name='fixture', source=source(tmp_path, rows()), license_id='CC-BY-4.0',
                           out=tmp_path / 'dataset', sample_size=0)
    assert not (tmp_path / 'dataset').exists()


def test_quality_rejects_unparseable_boundary(tmp_path, monkeypatch):
    _, quality = modules(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match='start_time'):
        quality.analyze(rows(), start_time='not a UTC timestamp')


def test_quality_cli_malformed_record_shape_returns_error(tmp_path, monkeypatch):
    _, quality = modules(tmp_path, monkeypatch)
    path = tmp_path / 'input'
    path.mkdir()
    (path / 'records.json').write_text('{"records": "not a list"}')
    assert quality.main(['--name', 'fixture', '--input', str(path), '--out', str(tmp_path / 'quality')]) == 2
    assert not (tmp_path / 'quality').exists()


@pytest.mark.parametrize('raw', ['{"records": [], "records": []}', '{"other": []}'])
def test_quality_cli_uses_the_same_strict_json_contract(tmp_path, monkeypatch, raw):
    _, quality = modules(tmp_path, monkeypatch)
    path = tmp_path / 'input'
    path.mkdir()
    (path / 'records.json').write_text(raw)
    assert quality.main(['--name', 'fixture', '--input', str(path), '--out', str(tmp_path / 'quality')]) == 2
