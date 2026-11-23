"""Standalone W1 migration: empty / canonical five / legacy four -> schema.sql.

CLI is read-only unless --apply is supplied. Legacy cleanup additionally needs
--allow-legacy-cleanup --backup-dir EXISTING_DIRECTORY; mysqldump must succeed
before any database writes. Stop application writers for the entire migration:
MySQL DDL auto-commits, so backups, not transactions, provide DDL recovery.

migrate_connection uses an already selected, committed, dedicated connection.
Its caller owns backup/recovery and must explicitly authorize legacy cleanup.
Partial/unrecognized schemas are refused rather than guessed or repaired.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pymysql

try:
    from .setup_mysql import resolve_credentials
except ImportError:  # Direct standalone execution, without backend/Web imports.
    from setup_mysql import resolve_credentials

SCHEMA = Path(__file__).with_name("schema.sql")
LEGACY = {"commit", "commit_feature", "commit_label", "prediction"}
EXPERT_ALGOS = "lr|rf|xgb|lgbm|et|svm|mlp_deep|tabnet"


class MigrationError(ValueError):
    """A predictable unsafe migration, detected before DDL."""


def _query(conn, sql, args=None):
    with conn.cursor(pymysql.cursors.Cursor) as cursor:
        cursor.execute(sql, args)
        return cursor.fetchall()


def _canonical():
    sql = re.sub(r"--[^\n]*", "", SCHEMA.read_text(encoding="utf-8"))
    specs = {}
    for statement in sql.split(";"):
        match = re.search(r"CREATE TABLE IF NOT EXISTS `?(\w+)`?\s*\(([\s\S]*)\)", statement)
        if not match:
            continue
        columns, indexes, foreign = {}, {}, []
        for raw in match[2].splitlines():
            line = raw.strip().rstrip(",")
            column = re.match(r"(\w+)\s+((?:CHAR|VARCHAR|DECIMAL|TINYINT)\([\d, ]+\)|DATETIME|TEXT|BIGINT|INT)(.*)$", line)
            if column:
                name, kind, rest = column.groups()
                default = re.search(r"DEFAULT ('[^']*'|\d+)", rest)
                columns[name] = (re.sub(r"\s+", "", kind.lower()), "NO" if "NOT NULL" in rest else "YES",
                                 default[1].strip("'") if default else None, line)
            key = re.match(r"(PRIMARY KEY|INDEX \w+|UNIQUE KEY \w+)\s*\(([^)]+)\)", line)
            if key:
                name = "PRIMARY" if key[1] == "PRIMARY KEY" else key[1].split()[-1]
                indexes[name] = (0 if key[1].startswith(("PRIMARY", "UNIQUE")) else 1,
                                 tuple(item.strip() for item in key[2].split(",")))
            fk = re.match(r"FOREIGN KEY\((\w+)\) REFERENCES `?(\w+)`? \((\w+)\)", line)
            if fk:
                foreign.append((*fk.groups(), line))
        for column, _, _, _ in foreign:
            if not any(cols[0] == column for _, cols in indexes.values()):
                indexes[column] = (1, (column,))  # MySQL's implicit FK supporting index.
        specs[match[1]] = (statement.strip(), columns, indexes, foreign)
    return specs


def _metadata(conn, table):
    columns = _query(conn, """SELECT COLUMN_NAME,COLUMN_TYPE,IS_NULLABLE,COLUMN_DEFAULT,EXTRA,COLLATION_NAME
        FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s
        ORDER BY ORDINAL_POSITION""", (table,))
    indexes = {}
    for name, unique, column in _query(conn, """SELECT INDEX_NAME,NON_UNIQUE,COLUMN_NAME
        FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s
        ORDER BY INDEX_NAME,SEQ_IN_INDEX""", (table,)):
        indexes.setdefault(name, (unique, []))[1].append(column)
    foreign = _query(conn, """SELECT k.COLUMN_NAME,k.REFERENCED_TABLE_NAME,k.REFERENCED_COLUMN_NAME,
        k.REFERENCED_TABLE_SCHEMA,r.UPDATE_RULE,r.DELETE_RULE FROM information_schema.KEY_COLUMN_USAGE k
        JOIN information_schema.REFERENTIAL_CONSTRAINTS r ON r.CONSTRAINT_SCHEMA=k.CONSTRAINT_SCHEMA
        AND r.TABLE_NAME=k.TABLE_NAME AND r.CONSTRAINT_NAME=k.CONSTRAINT_NAME
        WHERE k.TABLE_SCHEMA=DATABASE() AND k.TABLE_NAME=%s
        AND k.REFERENCED_TABLE_NAME IS NOT NULL ORDER BY k.ORDINAL_POSITION""", (table,))
    return columns, {name: (unique, tuple(cols)) for name, (unique, cols) in indexes.items()}, foreign


def _lineage(name):
    match = re.fullmatch(rf"(?:{EXPERT_ALGOS})(?:_(semantic|fused))?_v\d+", name)
    if match:
        return match[1] or "expert"
    if re.fullmatch(r"codebert_e2e_v\d+", name):
        return "e2e"
    raise MigrationError(f"Unknown model lineage: {name!r}; provide authoritative metadata first")


def _prepare(conn):
    if _query(conn, "SELECT @@FOREIGN_KEY_CHECKS")[0][0] != 1:
        raise MigrationError("FOREIGN_KEY_CHECKS must be enabled")
    database, collation = _query(conn, """SELECT SCHEMA_NAME,DEFAULT_COLLATION_NAME
        FROM information_schema.SCHEMATA WHERE SCHEMA_NAME=DATABASE()""")[0]
    specs = _canonical()
    present = {name for name, kind in _query(conn, "SHOW FULL TABLES") if kind == "BASE TABLE"}
    if len(present) != len(_query(conn, "SHOW FULL TABLES")):
        raise MigrationError("Views are not a supported migration source")
    proper5 = set(list(specs)[:5])
    source = {frozenset(): "empty", frozenset(proper5): "proper5",
              frozenset(LEGACY): "legacy4", frozenset(specs): "current12"}.get(frozenset(present))
    if source is None:
        raise MigrationError("Unsupported partial/unrecognized schema; no DDL performed")
    if _query(conn, "SELECT 1 FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA=DATABASE() LIMIT 1"):
        raise MigrationError("Custom triggers require a separately reviewed migration")
    if _query(conn, "SELECT 1 FROM information_schema.TABLE_CONSTRAINTS WHERE CONSTRAINT_SCHEMA=DATABASE() AND CONSTRAINT_TYPE='CHECK' LIMIT 1"):
        raise MigrationError("Custom CHECK constraints require a separately reviewed migration")
    if _query(conn, "SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() AND ENGINE<>'InnoDB' LIMIT 1"):
        raise MigrationError("Only InnoDB tables are supported")
    if _query(conn, "SELECT 1 FROM information_schema.KEY_COLUMN_USAGE WHERE REFERENCED_TABLE_SCHEMA=DATABASE() AND TABLE_SCHEMA<>DATABASE() LIMIT 1"):
        raise MigrationError("External inbound foreign keys require a separately reviewed migration")
    metadata = {table: _metadata(conn, table) for table in present}
    upgrades = {}
    legacy_columns = {
        "commit": set(specs["commit"][1]) | {"id"},
        "commit_feature": (set(specs["commit_feature"][1]) - {"is_test", "is_bug_inducing", "labeled_at"}) | {"committed_at"},
        "prediction": (set(specs["prediction"][1]) - {"model_version", "feature_version"}) | {"id", "feature_version"},
        "commit_label": {"id", "commit_hash", "is_bug_inducing", "label_method", "bug_fix_hash", "labeled_at"},
    }
    legacy_extra = {
        "id": ("bigint", "NO"), "committed_at": ("datetime", "NO"),
        "feature_version": ("varchar(32)", "NO"), "commit_hash": ("char(40)", "NO"),
        "is_bug_inducing": ("tinyint(1)", "NO"), "label_method": ("varchar(32)", "NO"),
        "bug_fix_hash": ("char(40)", "YES"), "labeled_at": ("datetime", "NO"),
    }
    for table, (columns, indexes, foreign) in metadata.items():
        if source == "legacy4":
            if {row[0] for row in columns} != legacy_columns[table]:
                raise MigrationError(f"Unsupported legacy columns in {table}")
            targets = specs[table][1] if table in specs else {}
            for name, kind, _nullable, _default, extra, _coll in columns:
                definition = targets[name] if name in targets else legacy_extra[name]
                if kind != definition[0] or extra not in ("", "auto_increment"):
                    raise MigrationError(f"Unsupported legacy type: {table}.{name}")
                if definition[1] == "NO" and _query(conn, f"SELECT 1 FROM `{table}` WHERE `{name}` IS NULL LIMIT 1"):
                    raise MigrationError(f"Required NULL in {table}.{name}")
        else:
            expected = [(name, *definition[:3], "") for name, definition in specs[table][1].items()]
            actual = [row[:5] for row in columns]
            added = []
            if table == "prediction" and actual != expected:
                # 旧 current12/proper5 的 prediction 缺两个可空版本列；只接受整组缺失，部分缺失仍拒绝。
                previous = [row for row in expected if row[0] not in ("model_version", "feature_version")]
                if actual == previous:
                    added = ["model_version", "feature_version"]
            if (actual != expected and not added) or indexes != specs[table][2]:
                raise MigrationError(f"Noncanonical columns/PK/indexes in {table}")
            if added:
                upgrades[table] = added
            if sorted(row[:3] for row in foreign) != sorted(row[:3] for row in specs[table][3]):
                raise MigrationError(f"Noncanonical foreign keys in {table}")
        if any(row[5] and row[5] != collation for row in columns):
            raise MigrationError(f"{table}: column/database collations differ; resolve before migration")
        for column, parent, parent_column, parent_db, *rules in foreign:
            allowed = {row[:3] for row in specs[table][3]} if table in specs else {
                ("commit_hash", "commit", "commit_hash"), ("commit_hash", "commit_feature", "commit_hash"),
                ("bug_fix_hash", "commit", "commit_hash"),
            }
            if parent_db != database or parent not in present or (column, parent, parent_column) not in allowed or rules != ["NO ACTION", "NO ACTION"]:
                raise MigrationError("External/unrecognized foreign key or cascading rule")
            if _query(conn, f"SELECT 1 FROM `{table}` c LEFT JOIN `{parent}` p ON c.`{column}`=p.`{parent_column}` WHERE c.`{column}` IS NOT NULL AND p.`{parent_column}` IS NULL LIMIT 1"):
                raise MigrationError(f"Orphan foreign key in {table}.{column}")
    models = []
    if source == "legacy4":
        for table, keys in (("commit", "commit_hash"), ("commit_feature", "commit_hash"),
                            ("prediction", "commit_hash,model_name"), ("commit_label", "commit_hash,label_method")):
            if _query(conn, f"SELECT 1 FROM `{table}` GROUP BY {keys} HAVING COUNT(*)>1 LIMIT 1"):
                raise MigrationError(f"Duplicate target key in {table}")
        for table, parent in (("commit_feature", "commit"), ("prediction", "commit"), ("commit_label", "commit_feature")):
            if _query(conn, f"SELECT 1 FROM `{table}` c LEFT JOIN `{parent}` p USING(commit_hash) WHERE p.commit_hash IS NULL LIMIT 1"):
                raise MigrationError(f"Orphan {table} row")
        if _query(conn, "SELECT 1 FROM commit_label WHERE is_bug_inducing IS NULL OR is_bug_inducing NOT IN (0,1) OR labeled_at IS NULL LIMIT 1"):
            raise MigrationError("Invalid label or missing labeled_at")
        if _query(conn, "SELECT 1 FROM commit_label GROUP BY commit_hash HAVING MIN(is_bug_inducing)<>MAX(is_bug_inducing) LIMIT 1"):
            raise MigrationError("Conflicting labels across methods; reconcile explicitly before migration")
        if _query(conn, "SELECT 1 FROM prediction WHERE risk_score IS NULL OR risk_score<0 OR risk_score>1 OR model_name IS NULL LIMIT 1"):
            raise MigrationError("Invalid prediction probability/model")
        models = [(name, _lineage(name)) for (name,) in _query(conn, "SELECT DISTINCT model_name FROM prediction")]
    missing = [table for table in specs if table not in present]
    operations = [f"CREATE TABLE {table}" for table in missing]
    operations += [f"ALTER TABLE {table} ADD nullable columns {', '.join(names)}" for table, names in upgrades.items()]
    warnings = []
    if source == "legacy4":
        operations = ["Normalize commit/prediction PKs; remove redundant id/committed_at columns; prediction version columns become nullable provenance",
                      "Backfill consistent labels with latest labeled_at; DROP TABLE commit_label", *operations]
        warnings = ["Historical train/test split is missing: is_test=0 for all legacy features; no random split was invented.",
                    "Only model name/known lineage registered; historical metadata/artifacts remain absent.",
                    "Consistent multi-method labels use latest labeled_at; method/fix links and redundant columns remain in backup only."]
    seed = "user" not in present or not _query(conn, "SELECT 1 FROM `user` WHERE user_id='global'")
    if seed:
        operations.append("INSERT missing global user (never overwrite edits/config)")
    report = {"source": source, "operations": operations, "warnings": warnings, "destructive": source == "legacy4"}
    return report, specs, metadata, models, seed, upgrades


def migrate_connection(conn, allow_legacy_cleanup=False):
    """Apply a fully preflighted migration; caller must back up before legacy opt-in."""
    report, specs, metadata, models, seed, upgrades = _prepare(conn)
    if report["destructive"] and not allow_legacy_cleanup:
        raise MigrationError("Legacy removal requires allow_legacy_cleanup=True and a caller-owned backup")
    if report["destructive"]:
        _query(conn, specs["model"][0])
        saved = []
        for table in metadata:
            ddl = _query(conn, f"SHOW CREATE TABLE `{table}`")[0][1]
            for clause in re.findall(r"^\s*(CONSTRAINT .*FOREIGN KEY.*)$", ddl, re.MULTILINE):
                clause = clause.rstrip(",")
                name = re.search(r"CONSTRAINT `([^`]+)`", clause)[1]
                saved.append((table, name, clause))
        try:
            for table, name, _ in saved:
                _query(conn, f"ALTER TABLE `{table}` DROP FOREIGN KEY `{name}`")
            for table in ("commit", "commit_feature", "prediction"):
                columns, indexes, _ = metadata[table]
                target = specs[table][1]
                changes = ["DROP PRIMARY KEY"] if "PRIMARY" in indexes else []
                changes += [f"DROP INDEX `{name}`" for name in indexes if name != "PRIMARY"]
                existing = {row[0] for row in columns}
                changes += [f"DROP COLUMN `{name}`" for name in existing - set(target)]
                previous = None
                for name, definition in target.items():
                    position = f"AFTER `{previous}`" if previous else "FIRST"
                    changes.append(f"{'MODIFY' if name in existing else 'ADD'} COLUMN {definition[3]} {position}")
                    previous = name
                for name, (unique, cols) in specs[table][2].items():
                    key = "PRIMARY KEY" if name == "PRIMARY" else f"{'UNIQUE ' if unique == 0 else ''}INDEX `{name}`"
                    changes.append(f"ADD {key} ({','.join(f'`{col}`' for col in cols)})")
                _query(conn, f"ALTER TABLE `{table}` " + ", ".join(changes))
        finally:
            # Reattach original constraints even if an unexpected ALTER failure occurs.
            for table, name, clause in saved:
                if not _query(conn, "SELECT 1 FROM information_schema.TABLE_CONSTRAINTS WHERE CONSTRAINT_SCHEMA=DATABASE() AND TABLE_NAME=%s AND CONSTRAINT_NAME=%s", (table, name)):
                    _query(conn, f"ALTER TABLE `{table}` ADD {clause}")
        for name, line in models:
            _query(conn, "INSERT INTO model (model_name,line) VALUES (%s,%s)", (name, line))
        _query(conn, """UPDATE commit_feature f JOIN
            (SELECT commit_hash,MIN(is_bug_inducing) label,MAX(labeled_at) labeled_at
             FROM commit_label GROUP BY commit_hash) l USING(commit_hash)
            SET f.is_bug_inducing=l.label,f.labeled_at=l.labeled_at""")
        conn.commit()
        for table in ("commit_feature", "prediction"):
            foreign = {row[:3] for row in _metadata(conn, table)[2]}
            for column, parent, parent_column, clause in specs[table][3]:
                if (column, parent, parent_column) not in foreign:
                    _query(conn, f"ALTER TABLE `{table}` ADD {clause}")
        _query(conn, "DROP TABLE commit_label")
    for table, spec in specs.items():
        if table not in metadata and not (report["destructive"] and table == "model"):
            _query(conn, spec[0])
    for table, names in upgrades.items():
        for name in names:
            _query(conn, f"ALTER TABLE `{table}` ADD COLUMN {specs[table][1][name][3]}")
    if seed:
        _query(conn, """INSERT INTO `user` (user_id,display_name,role,status,created_at)
            VALUES ('global','全局默认','system','active',UTC_TIMESTAMP())""")
    conn.commit()
    return report


def _backup(creds, directory):
    directory = Path(directory).resolve()
    if not directory.is_dir():
        raise MigrationError("--backup-dir must be an existing writable directory")
    path = directory / f"migration-{datetime.now(UTC):%Y%m%dT%H%M%S}-{uuid4().hex}.sql"
    args = ["mysqldump", "--single-transaction", "--skip-lock-tables", "--no-tablespaces",
            "--set-gtid-purged=OFF", "--default-character-set=utf8mb4", "--host", creds["host"],
            "--port", str(creds["port"]), "--user", creds["user"], creds["database"], *sorted(LEGACY)]
    try:
        with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as output:
            subprocess.run(args, env={**os.environ, "MYSQL_PWD": creds["password"]},
                           stdout=output, stderr=subprocess.PIPE, check=True)
        if path.stat().st_size == 0:
            raise MigrationError("mysqldump produced an empty backup")
    except (OSError, subprocess.CalledProcessError, MigrationError) as exc:
        path.unlink(missing_ok=True)
        raise MigrationError("mysqldump backup failed; install/configure MySQL client and check backup-dir; no database writes performed") from exc
    return str(path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("database-url", "db-host", "db-port", "db-user", "db-password", "db-name"):
        parser.add_argument(f"--{flag}")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default: dry-run)")
    parser.add_argument("--allow-legacy-cleanup", action="store_true")
    parser.add_argument("--backup-dir", help="Existing directory for mandatory pre-cleanup mysqldump")
    args = parser.parse_args(argv)
    creds = resolve_credentials(args)
    conn = pymysql.connect(**creds, charset="utf8mb4", autocommit=True)
    try:
        report = _prepare(conn)[0]
        report["mode"] = "apply" if args.apply else "dry-run"
        if args.apply:
            if report["destructive"]:
                if not args.allow_legacy_cleanup or not args.backup_dir:
                    raise MigrationError("Legacy --apply requires --allow-legacy-cleanup and --backup-dir")
                report["backup"] = _backup(creds, args.backup_dir)
            result = migrate_connection(conn, allow_legacy_cleanup=args.allow_legacy_cleanup)
            report.update(result)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except MigrationError as exc:
        raise SystemExit(str(exc)) from exc
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
