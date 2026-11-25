from __future__ import annotations

import argparse
import hashlib
import importlib
import ipaddress
import json
import math
import os
import socket
import sys
import tempfile
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit
from urllib.request import HTTPRedirectHandler, build_opener
from uuid import uuid4

from .public_quality import analyze, markdown, parse_time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
fc = importlib.import_module('app.services.file_contracts')
output_store = importlib.import_module('app.services.output_store')

REQUIRED = ('commit_hash', 'committed_at', 'is_bug_inducing')


def source_version():
    digest = hashlib.sha256()
    for path in sorted(Path(__file__).parent.glob('*.py')):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return output_store.backend_code_version() + '+public.' + digest.hexdigest()[:16]


def stratified_sample(rows, size):
    if type(size) is not int or size < 1:
        fc.invalid('抽样数必须为正整数')
    groups = defaultdict(list)
    for row in rows:
        timestamp = parse_time(row.get('committed_at'))
        groups[timestamp.strftime('%Y-%m') if timestamp else 'invalid-time'].append(row)
    target = min(size, len(rows))
    quotas = {key: int(len(values) * target / len(rows)) for key, values in groups.items()} if rows else {}
    remaining = target - sum(quotas.values())
    order = sorted(groups, key=lambda key: (-(len(groups[key]) * target / len(rows) - quotas[key]), key))
    for key in order[:remaining]:
        quotas[key] += 1
    selected, layers = [], []
    for key, values in sorted(groups.items()):
        ordered = sorted(values, key=lambda row: (str(row.get('committed_at', '')), str(row.get('commit_hash', '')), json.dumps(row, sort_keys=True)))
        count = quotas[key]
        indices = [math.floor(index * (len(ordered) - 1) / (count - 1)) for index in range(count)] if count > 1 else [len(ordered) // 2] if count else []
        selected.extend(ordered[index] for index in indices)
        layers.append({'layer': key, 'source_rows': len(values), 'selected': count,
                       'start': ordered[0].get('committed_at'), 'end': ordered[-1].get('committed_at')})
    return selected, layers


def _validate_url(url):
    parts = urlsplit(url)
    if parts.scheme != 'https' or not parts.hostname or parts.username or parts.password or parts.fragment:
        fc.invalid('公开来源只允许不含凭证的 HTTPS URL')
    try:
        addresses = socket.getaddrinfo(parts.hostname, parts.port or 443, type=socket.SOCK_STREAM)
        if any(not ipaddress.ip_address(address[4][0]).is_global for address in addresses):
            fc.invalid('公开来源不能指向本机或私有网络')
    except (ValueError, OSError) as error:
        raise fc.AppError(40001, '公开来源主机不可用') from error


class _SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _read_source(source):
    text = str(source)
    if '://' in text:
        _validate_url(text)
        with build_opener(_SafeRedirect()).open(text, timeout=30) as response:
            if int(response.headers.get('Content-Length', 0)) > fc.MAX_UPLOAD_BYTES:
                fc.invalid('公开来源超过 64MiB；先探测与抽样，未下载大文件')
            content = response.read(fc.MAX_UPLOAD_BYTES + 1)
        name = Path(unquote(urlsplit(text).path)).name
    else:
        path = Path(source)
        if path.stat().st_size > fc.MAX_UPLOAD_BYTES:
            fc.invalid('公开来源超过 64MiB；需先分批准备输入')
        content, name = path.read_bytes(), path.name
    if len(content) > fc.MAX_UPLOAD_BYTES:
        fc.invalid('公开来源超过上传大小限制')
    return name, content


def load_public(*, name, source, license_id, out, mapping=None, sample_size=None):
    if not isinstance(license_id, str) or not license_id.strip() or license_id.strip().lower() in {'other', 'other-open', 'unknown'}:
        fc.invalid('必须提供已确认的明确许可证，不能把 Other 当作授权')
    if not isinstance(name, str) or not name.strip():
        fc.invalid('数据集名称为空')
    destination = Path(out)
    if destination.exists() or destination.is_symlink():
        fc.invalid('公开数据目录已存在，不覆盖已有数据')
    filename, content = _read_source(source)
    columns, raw_rows = fc.read_table(filename, content)
    mapping = mapping or {column: column for column in columns}
    if not isinstance(mapping, dict) or any(not isinstance(key, str) or not isinstance(value, str) for key, value in mapping.items()):
        fc.invalid('字段映射必须为目标列到来源列的 JSON 对象')
    for key in REQUIRED:
        if key not in mapping or mapping[key] not in columns:
            fc.invalid(f'公开数据缺少必需字段：{key}')
    if any(value not in columns for value in mapping.values()):
        fc.invalid('映射引用不存在的来源列')
    records = []
    for index, row in enumerate(raw_rows, 1):
        record = {key: row[value] for key, value in mapping.items()}
        if not record['commit_hash'].strip():
            fc.invalid(f'第 {index} 行 commit_hash 为空')
        if record['is_bug_inducing'] not in ('0', '1', ''):
            fc.invalid(f'第 {index} 行 is_bug_inducing 不是二值标签；请核验语义')
        timestamp = parse_time(record['committed_at'])
        if timestamp:
            record['committed_at'] = timestamp.isoformat().replace('+00:00', 'Z')
        records.append(record)
    if not records:
        fc.invalid('公开数据为空')
    selected, layers = stratified_sample(records, len(records) if sample_size is None else sample_size)
    sampled = len(selected) < len(records)
    metadata = {'name': name, 'source': str(source), 'license': license_id.strip(),
                'acquired_at': datetime.now(UTC).isoformat().replace('+00:00', 'Z'),
                'source_bytes': len(content), 'source_sha256': fc.sha256(content), 'source_rows': len(records),
                'rows': len(selected), 'sampled': sampled, 'sampling_method': 'month-stratified-proportional-equidistant',
                'layers': layers, 'mapping': mapping, 'label_semantics': 'binary: 1=bug-inducing; 0=non-inducing; empty=unlabeled'}
    report = analyze(records)
    columns = list(fc.COLLECTED_COMMITS_COLUMNS)
    normalized_rows = []
    for row in selected:
        record = {column: '' for column in columns}
        record.update(row)
        record['label_method'] = record.get('label_method') or 'third_party'
        record['label_source'] = 'public_dataset'
        record['source_type'] = 'public_dataset'
        record['repo_name'] = record.get('repo_name') or name
        record['repo_url'] = record.get('repo_url') or str(source) if '://' in str(source) else record.get('repo_url', '')
        normalized_rows.append(record)
    normalized = fc.encode_table(columns, normalized_rows, 'csv')
    def encode(value):
        return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True).encode('utf-8')
    local_files = {'normalized.csv': normalized, 'records.json': encode({'records': records}),
                   'metadata.json': encode(metadata), 'field_mapping.json': encode(mapping),
                   'quality.json': encode(report), 'source_' + filename: content}
    destination.parent.mkdir(parents=True, exist_ok=True)
    job_id = 'j-' + uuid4().hex
    artifacts = {f'collected_commits_{job_id}.csv': normalized,
                 f'collect_public_metadata_{job_id}.json': encode(metadata),
                 f'collect_public_quality_{job_id}.json': encode(report),
                 f'collect_public_quality_{job_id}.md': markdown(name, report).encode('utf-8')}
    published = False
    try:
        with tempfile.TemporaryDirectory(prefix='.public-', dir=destination.parent) as temporary:
            for local_name, raw in local_files.items():
                (Path(temporary) / local_name).write_bytes(raw)
            result = output_store.publish_output('collect', artifacts, job_id=job_id,
                inputs=[{'name': filename, 'sha256': fc.sha256(content), 'rows': len(records)}],
                config={'name': name, 'license': license_id, 'mapping': mapping, 'sample_size': sample_size},
                code_version=source_version())
            published = True
            os.rename(temporary, destination)
    except Exception:
        if published:
            output_store.discard_output('collect', job_id)
        raise
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description='公开缺陷数据集离线加载，不写业务数据库')
    parser.add_argument('--name', required=True)
    parser.add_argument('--source', required=True)
    parser.add_argument('--license', required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--mapping', type=Path)
    parser.add_argument('--sample-size', type=int)
    args = parser.parse_args(argv)
    try:
        mapping = fc.read_json(args.mapping.read_bytes()) if args.mapping else None
        result = load_public(name=args.name, source=args.source, license_id=args.license, out=args.out,
                             mapping=mapping, sample_size=args.sample_size)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, OSError, fc.AppError) as error:
        print(f'公开数据加载失败：{error}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
