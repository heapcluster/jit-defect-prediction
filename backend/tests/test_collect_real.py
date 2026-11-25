"""AI-generated W3 real Git integration tests, not human-reviewed."""
import csv
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from app import config, db
from app.models import Commit, Dataset
from app.services import collect_run, output_store
from app.services import file_contracts as fc
from sqlalchemy import func, select

from tests.conftest import HEADERS


@pytest.fixture
def real_collect(client, tmp_path, monkeypatch):
    monkeypatch.setattr(collect_run, 'REQUEST_ROOT', tmp_path / 'requests')
    monkeypatch.setattr(collect_run, 'CACHE_ROOT', tmp_path / 'cache')
    monkeypatch.setattr(collect_run, 'dispatch', lambda: None)
    monkeypatch.setattr(output_store, 'OUTPUT_ROOT', tmp_path / 'outputs')
    repo = tmp_path / 'source'
    repo.mkdir()
    monkeypatch.setattr(config, 'SOURCE_REPO', repo)
    subprocess.run(['git', 'init', '-q', str(repo)], check=True)
    commits = []
    for index, (message, text) in enumerate([
        ('AI unreviewed initial', 'class Main {\n int wrong = 1;\n}\n'),
        ('AI unreviewed change', 'class Main {\n int wrong = 2;\n}\n'),
        ('CAMEL-123 fix wrong value AI unreviewed', 'class Main {\n int right = 3;\n}\n'),
        ('AI unreviewed final', 'class Main {\n int right = 3;\n int extra = 1;\n}\n'),
    ], 1):
        (repo / 'Main.java').write_text(text)
        subprocess.run(['git', '-C', str(repo), 'add', '--', 'Main.java'], check=True)
        env = {**os.environ, 'GIT_AUTHOR_DATE': f'2026-01-0{index}T00:00:00Z', 'GIT_COMMITTER_DATE': f'2026-01-0{index}T00:00:00Z'}
        subprocess.run(['git', '-C', str(repo), '-c', 'user.name=AI unreviewed fixture', '-c', 'user.email=fixture@example.test', 'commit', '-qm', message], check=True, env=env)
        commits.append(subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip())
    return client, repo, commits


def run(client, repo, **settings):
    response = client.post('/api/collect/run', data={'config': json.dumps({
        'repo_source': str(repo), 'dataset_name': 'AI real Git fixture',
        'fetch_remote': False, **settings,
    })}, headers=HEADERS)
    assert response.status_code == 200, response.text
    job_id = response.json()['data']['job_id']
    collect_run._execute(job_id, 0)
    job = client.get('/api/jobs/' + job_id, headers=HEADERS).json()['data']
    assert job['status'] == 'success', job['error_log']
    result = job['output_ref_json']
    csv_name = next(item['name'] for item in result['outputs'] if item['name'].endswith('.csv'))
    raw = client.get(f'/api/collect/outputs/{job_id}/{csv_name}', headers=HEADERS).content
    return job_id, result, list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))), raw


@pytest.mark.parametrize('method', ['szz_v1', 'szz_lite'])
def test_real_git_szz_range_and_feature_history(real_collect, method):
    client, repo, hashes = real_collect
    job_id, result, rows, raw = run(client, repo, szz_method=method)
    assert len(rows) == len({row['commit_hash'] for row in rows}) == 4
    assert next(row for row in rows if row['commit_hash'] == hashes[1])['is_bug_inducing'] == '1'
    assert all(row['label_source'] == 'git_szz' and row['source_type'] == 'git_repo' for row in rows)
    assert 'is_test' not in rows[0] and 'fix' not in rows[0]
    _, _, window, _ = run(client, repo, szz_method=method, start_time='2026-01-02T00:00:00Z')
    full = {row['commit_hash']: row for row in rows}
    for row in window:
        assert all(row[field] == full[row['commit_hash']][field] for field in fc.COLLECTED_COMMITS_COLUMNS)
    _, _, again, repeat_raw = run(client, repo, szz_method=method)
    assert rows == again and raw == repeat_raw


def test_real_collected_output_can_be_explicitly_imported(real_collect):
    client, repo, _ = real_collect
    job_id, result, rows, raw = run(client, repo)
    with db.SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(Commit)) == 3
        assert session.scalar(select(func.count()).select_from(Dataset)) == 0
    manifest = client.get(f'/api/collect/outputs/{job_id}/' + result['manifest_name'], headers=HEADERS).content
    name = next(item['name'] for item in result['outputs'] if item['name'].endswith('.csv'))
    response = client.post('/api/storage/import', data={'config': json.dumps({'create_dataset': {
        'name': 'AI unreviewed collected dataset', 'source_type': 'git_repo',
        'source_url': str(repo), 'head_hash': result['summary']['head_hash']}})},
        files=[('files[]', (name, raw)), ('files[]', (result['manifest_name'], manifest))], headers=HEADERS)
    assert response.status_code == 200, response.text
    assert response.json()['data']['summary']['inserted'] == len(rows)


def test_cli_and_api_files_are_identical_for_the_same_real_repository(real_collect, tmp_path):
    client, repo, _ = real_collect
    _, _, rows, _ = run(client, repo)
    root = Path(config.REPO_ROOT)
    process = subprocess.run([sys.executable, '-m', 'preparation.collect', 'run',
        '--repo', str(repo), '--name', 'AI real Git fixture', '--fetch-remote', 'false',
        '--allow-root', str(repo.parent), '--out', str(tmp_path / 'cli')],
        cwd=root, env={**os.environ, 'PYTHONPATH': str(root / 'data_model')}, text=True, capture_output=True)
    assert process.returncode == 0, process.stdout + process.stderr
    csv_path = next((tmp_path / 'cli').rglob('collect_commits_*.csv'))
    with csv_path.open(encoding='utf-8-sig', newline='') as source:
        assert list(csv.DictReader(source)) == rows


def test_repository_input_snapshot_is_downloadable_without_private_path_leak(real_collect):
    from app.services import file_contracts as fc
    client, repo, _ = real_collect
    job_id, result, _, _ = run(client, repo)
    manifest = client.get(f'/api/collect/outputs/{job_id}/' + result['manifest_name'], headers=HEADERS).json()
    assert all('path' not in item for item in manifest['inputs'])
    name = f'collect_repository_snapshot_{job_id}.json'
    response = client.get(f'/api/collect/outputs/{job_id}/{name}', headers=HEADERS)
    assert response.status_code == 200
    item = next(item for item in manifest['inputs'] if item['name'] == 'repository_snapshot.json')
    assert fc.sha256(response.content) == item['sha256']
    assert response.json()['head_hash'] == result['summary']['head_hash']


def test_production_import_path_does_not_depend_on_pytest(real_collect):
    _, repo, _ = real_collect
    root = Path(config.REPO_ROOT)
    code = (
        'import sys, json; sys.path.insert(0, sys.argv[1]); '
        'from app.services import collect_run; '
        'result=collect_run._call("run", json.loads(sys.argv[2]), '
        'allow_roots=[sys.argv[3]], protocol_whitelist=[]); '
        'assert result["summary"]["rows"] == 4'
    )
    settings = {'repo_source': str(repo), 'dataset_name': 'isolated runtime', 'fetch_remote': False}
    result = subprocess.run([sys.executable, '-I', '-c', code,
                             str(root / 'backend'), json.dumps(settings), str(repo.parent)],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_real_xlsx_output_keeps_trailing_null_cells(real_collect):
    from app.services import file_contracts as fc
    client, repo, hashes = real_collect
    job_id, result, _, _ = run(client, repo, branch=hashes[0])
    name = next(item['name'] for item in result['outputs'] if item['name'].endswith('.xlsx'))
    response = client.get(f'/api/collect/outputs/{job_id}/{name}', headers=HEADERS)
    columns, rows = fc.read_table(name, response.content)
    assert columns == list(fc.COLLECTED_COMMITS_COLUMNS)
    assert rows[0]['is_bug_inducing'] == rows[0]['labeled_at'] == rows[0]['label_method'] == ''


def test_unreachable_hash_is_rejected_without_success_output(real_collect):
    client, repo, _ = real_collect
    response = client.post('/api/collect/run', data={'config': json.dumps({
        'repo_source': str(repo), 'dataset_name': 'fixture', 'fetch_remote': False,
        'head_expect': 'f' * 40})}, headers=HEADERS)
    if response.status_code == 200:
        job_id = response.json()['data']['job_id']
        collect_run._execute(job_id, 0)
        job = client.get('/api/jobs/' + job_id, headers=HEADERS).json()['data']
        assert job['status'] == 'failed' and not job['output_ref_json']
    else:
        assert response.status_code == 400
