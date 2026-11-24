from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path


def parse_time(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return parsed.astimezone(UTC) if parsed.tzinfo else None
    except (TypeError, ValueError):
        return None


def analyze(rows, *, start_time=None, end_time=None):
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError('records 必须为记录对象列表')
    if start_time is not None and parse_time(start_time) is None:
        raise ValueError('start_time 必须为带时区的 ISO 时间')
    if end_time is not None and parse_time(end_time) is None:
        raise ValueError('end_time 必须为带时区的 ISO 时间')
    if start_time and end_time and parse_time(start_time) > parse_time(end_time):
        raise ValueError('start_time 不能晚于 end_time')
    total = len(rows)
    fields = sorted({key for row in rows for key in row})
    missing = {key: sum(row.get(key) in ('', None) for row in rows) / total if total else 0 for key in fields}
    languages = Counter(row.get('language') or 'unknown' for row in rows)
    types = Counter(row['defect_type'] for row in rows if row.get('defect_type'))
    by_hash = defaultdict(list)
    invalid, unordered, outside, invalid_labels = [], [], [], []
    previous = None
    start, end = parse_time(start_time), parse_time(end_time)
    for index, row in enumerate(rows, 1):
        by_hash[row.get('commit_hash')].append((index, str(row.get('is_bug_inducing', ''))))
        if str(row.get('is_bug_inducing', '')) not in ('0', '1', '', 'None'):
            invalid_labels.append(index)
        timestamp = parse_time(row.get('committed_at'))
        if timestamp is None:
            invalid.append(index)
            continue
        if previous is not None and timestamp < previous:
            unordered.append(index)
        previous = timestamp
        if (start and timestamp < start) or (end and timestamp > end):
            outside.append(index)
    conflicts = [{'commit_hash': key, 'rows': [index for index, _ in values]}
                 for key, values in sorted(by_hash.items(), key=lambda item: str(item[0]))
                 if {'0', '1'} <= {label for _, label in values}]
    duplicate_count = sum(max(0, len(values) - 1) for values in by_hash.values())
    return {'rows': total, 'label_granularity': '含缺陷类型' if types else '二值，无缺陷类型',
            'defect_types': dict(sorted(types.items())),
            'languages': {key: {'count': count, 'ratio': count / total if total else 0}
                          for key, count in sorted(languages.items())},
            'missing_rates': missing, 'duplicate_count': duplicate_count,
            'duplicate_rate': duplicate_count / total if total else 0, 'label_conflicts': conflicts,
            'invalid_time_rows': invalid, 'time_order_rows': unordered, 'out_of_range_rows': outside,
            'invalid_label_rows': invalid_labels}


def markdown(name, report):
    return (f'# 公开数据质量报告：{name}\n\n'
            f'基于公开数据集 {name}，与 Apache Camel 基线并列对照；本报告不登记模型，不做文献性能对照。\n\n'
            f'标签粒度：{report["label_granularity"]}。记录数：{report["rows"]}。\n\n'
            '| 语言 | 提交数 | 占比 |\n|---|---:|---:|\n'
            + ''.join(f'| {language} | {item["count"]} | {item["ratio"]:.6f} |\n' for language, item in report['languages'].items())
            + '\n## 质量明细\n\n```json\n' + json.dumps(report, ensure_ascii=False, indent=2) + '\n```\n\n'
            '建议：核验缺失字段与标签语义；逐记录处理冲突和非法时间，不静默删除或补零。\n')


def main(argv=None):
    from .public_load import fc, output_store, source_version
    parser = argparse.ArgumentParser(description='公开缺陷数据集离线质量治理，不写业务数据库')
    parser.add_argument('--name', required=True)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--start-time')
    parser.add_argument('--end-time')
    args = parser.parse_args(argv)
    try:
        path = args.input / 'records.json'
        if path.stat().st_size > fc.MAX_UPLOAD_BYTES:
            fc.invalid('质量输入超过大小限制')
        raw = path.read_bytes()
        records = fc.read_json(raw).get('records')
        report = analyze(records, start_time=args.start_time, end_time=args.end_time)
        from uuid import uuid4
        job_id = 'j-' + uuid4().hex
        artifacts = {f'collect_public_quality_{job_id}.json': json.dumps(report, ensure_ascii=False).encode(),
                     f'collect_public_quality_{job_id}.md': markdown(args.name, report).encode()}
        old_root = output_store.OUTPUT_ROOT
        output_store.OUTPUT_ROOT = args.out
        try:
            result = output_store.publish_output('collect', artifacts, job_id=job_id,
                inputs=[{'name': 'records.json', 'sha256': fc.sha256(raw), 'rows': len(records)}],
                config={'name': args.name, 'start_time': args.start_time, 'end_time': args.end_time}, code_version=source_version())
        finally:
            output_store.OUTPUT_ROOT = old_root
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, OSError, fc.AppError) as error:
        print(f'公开数据质量检查失败：{error}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
