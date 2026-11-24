"""Real MySQL W1 smoke tests; never use backend fixtures or shared databases."""

from __future__ import annotations

import importlib
import importlib.util
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

import pymysql
import pytest

INFRA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(INFRA))
from setup_mysql import read_backend_env  # noqa: E402

TEST_DB = "jit_test_w1_migration"
DDL = re.sub(r"--[^\n]*", "", (INFRA / "schema.sql").read_text(encoding="utf-8"))
STATEMENTS = [part.strip() for part in DDL.split(";") if part.strip()]
TABLES = [re.search(r"EXISTS\s+`?(\w+)", sql).group(1) for sql in STATEMENTS[:-1]]
DROP_ORDER = [
    "dataset_commit", "dataset", "model_artifact", "user_config", "algorithm", "job",
    "user", "model_figure", "prediction", "commit_label", "commit_feature", "model", "commit",
]
HASHES = [character * 40 for character in "abcd"]
TIME = datetime(2026, 10, 1, 12, 34, 56)
METRICS = "ns nd nf entropy la ld lt fix ndev age nuc exp rexp sexp".split()


def guard_database(name):
    if not (name.startswith("jit_test") and name.endswith("_migration") and name == TEST_DB):
        raise RuntimeError("Destructive fixtures require the named disposable jit_test*_migration DB")


def execute(conn, sql, args=None):
    with conn.cursor() as cursor:
        cursor.execute(sql, args)
        return cursor.fetchall()


def clear_tables(conn):
    guard_database(execute(conn, "SELECT DATABASE()")[0][0])
    existing = {row[0] for row in execute(conn, "SHOW TABLES")}
    assert existing <= set(DROP_ORDER), "Refuse to remove unfamiliar tables"
    for table in DROP_ORDER:
        if table in existing:
            execute(conn, f"DROP TABLE `{table}`")


def schema_signature(conn):
    columns = execute(conn, """
        SELECT TABLE_NAME,COLUMN_NAME,COLUMN_TYPE,IS_NULLABLE,COLUMN_DEFAULT,EXTRA
        FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE()
        ORDER BY TABLE_NAME,ORDINAL_POSITION
    """)
    indexes = execute(conn, """
        SELECT TABLE_NAME,INDEX_NAME,NON_UNIQUE,SEQ_IN_INDEX,COLUMN_NAME,INDEX_TYPE
        FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE()
        ORDER BY TABLE_NAME,INDEX_NAME,SEQ_IN_INDEX
    """)
    # MySQL generates FK names; compare the complete relationship and rules, not names.
    foreign_keys = execute(conn, """
        SELECT k.TABLE_NAME,k.COLUMN_NAME,k.REFERENCED_TABLE_NAME,k.REFERENCED_COLUMN_NAME,
               r.UPDATE_RULE,r.DELETE_RULE
        FROM information_schema.KEY_COLUMN_USAGE k
        JOIN information_schema.REFERENTIAL_CONSTRAINTS r
          ON r.CONSTRAINT_SCHEMA=k.CONSTRAINT_SCHEMA AND r.CONSTRAINT_NAME=k.CONSTRAINT_NAME
         AND r.TABLE_NAME=k.TABLE_NAME
        WHERE k.TABLE_SCHEMA=DATABASE() AND k.REFERENCED_TABLE_NAME IS NOT NULL
        ORDER BY k.TABLE_NAME,k.COLUMN_NAME
    """)
    return columns, indexes, foreign_keys


def snapshot(conn):
    return {
        name: (execute(conn, f"SHOW CREATE TABLE `{name}`")[0][1],
               sorted(execute(conn, f"SELECT * FROM `{name}`"), key=repr))
        for (name,) in execute(conn, "SHOW TABLES")
    }


def migration():
    assert importlib.util.find_spec("migrate_mysql") is not None, "Standalone migration is missing"
    return importlib.import_module("migrate_mysql")


@pytest.fixture(scope="session")
def session_connection():
    # The database is explicitly created/granted via docker exec in this session, not here.
    guard_database(TEST_DB)
    env = read_backend_env()
    conn = pymysql.connect(
        host=os.environ.get("W1_MYSQL_HOST", "127.0.0.1"),
        port=int(os.environ.get("W1_MYSQL_PORT", "3306")), user="jit",
        password=os.environ.get("W1_MYSQL_PASSWORD", env.get("DB_PASSWORD", "")),
        database=TEST_DB, charset="utf8mb4", autocommit=True,
    )
    clear_tables(conn)
    yield conn
    clear_tables(conn)
    conn.close()


@pytest.fixture(scope="session")
def canonical_signature(session_connection):
    for sql in STATEMENTS:
        execute(session_connection, sql)
    result = schema_signature(session_connection)
    clear_tables(session_connection)
    return result


@pytest.fixture
def db(session_connection, canonical_signature):
    clear_tables(session_connection)
    yield session_connection
    clear_tables(session_connection)


@pytest.fixture(scope="session")
def backup_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("w1-migration-backups")


def backup_fixture(conn, directory):
    """Explicit test-only backup before opting into destructive library migration."""
    guard_database(execute(conn, "SELECT DATABASE()")[0][0])
    path = directory / f"legacy-{len(list(directory.iterdir()))}.sql"
    parts = ["SET NAMES utf8mb4; SET SQL_MODE='';"]
    with conn.cursor() as cursor:
        for table in ("commit", "commit_feature", "commit_label", "prediction"):
            parts.append(execute(conn, f"SHOW CREATE TABLE `{table}`")[0][1] + ";")
            for row in execute(conn, f"SELECT * FROM `{table}`"):
                parts.append(cursor.mogrify(
                    f"INSERT INTO `{table}` VALUES ({','.join(['%s'] * len(row))})", row
                ) + ";")
    path.write_text("\n".join(parts), encoding="utf-8")
    assert path.stat().st_size > 0
    return path


def create_legacy(conn):
    # Use the actual backup's four DDL statements, never its INSERT/USE/DROP statements.
    sql = (INFRA.parent / "backend" / "jit_demo_backup_20261101_195117.sql").read_text(
        encoding="utf-8"
    )
    tables = re.findall(r"CREATE TABLE `\w+` \([\s\S]*?\) ENGINE=[^;]+;", sql)
    assert len(tables) == 4
    for statement in tables:
        execute(conn, statement)
    for number, commit_hash in enumerate(HASHES[:3]):
        execute(conn, """
            INSERT INTO `commit` (repo_name,commit_hash,author_name,author_email,
                                  committed_at,message,parent_hash)
            VALUES ('camel',%s,'Author',%s,%s,'preserve message',%s)
        """, (commit_hash, None if number == 0 else "author@example.test", TIME,
              None if number == 0 else HASHES[0]))
        values = ["1.1234567890" if metric != "fix" else 1 for metric in METRICS]
        execute(conn, f"""
            INSERT INTO commit_feature (commit_hash,committed_at,feature_version,{','.join(METRICS)})
            VALUES ({','.join(['%s'] * (3 + len(METRICS)))})
        """, [commit_hash, TIME, "legacy-v1", *values])
    for commit_hash, label in zip(HASHES[:2], (1, 0), strict=True):
        execute(conn, """
            INSERT INTO commit_label (commit_hash,is_bug_inducing,label_method,bug_fix_hash,labeled_at)
            VALUES (%s,%s,'szz',NULL,%s)
        """, (commit_hash, label, TIME))
    execute(conn, """
        INSERT INTO commit_label (commit_hash,is_bug_inducing,label_method,labeled_at)
        VALUES (%s,1,'szz_lite',%s)
    """, (HASHES[0], datetime(2026, 10, 2)))
    for commit_hash, model_name in zip(HASHES[:3], ("rf_v1", "lr_semantic_v1", "xgb_v1"), strict=True):
        execute(conn, """
            INSERT INTO prediction (commit_hash,model_name,risk_score,predicted_at,feature_version)
            VALUES (%s,%s,0.12345,%s,'legacy-v1')
        """, (commit_hash, model_name, TIME))


def create_proper5(conn):
    for sql in STATEMENTS[:5]:
        execute(conn, sql)
    execute(conn, """INSERT INTO `commit` VALUES (%s,'camel','Author',NULL,%s,'message',NULL)""",
            (HASHES[0], TIME))
    execute(conn, """INSERT INTO model VALUES ('rf_v1','expert','rf','v1',%s,'real-v1')""", (TIME,))
    execute(conn, f"""
        INSERT INTO commit_feature VALUES ({','.join(['%s'] * (2 + len(METRICS) + 3))})
    """, [HASHES[0], "real-v1", *([1] * len(METRICS)), 1, None, None])
    execute(conn, "INSERT INTO prediction (commit_hash,model_name,risk_score,predicted_at) VALUES (%s,'rf_v1',0.98765,%s)", (HASHES[0], TIME))
    execute(conn, "INSERT INTO model_figure VALUES ('rf_v1','roc','ROC','real.png',%s)", (TIME,))


def test_empty_to_exact_canonical12(db, canonical_signature):
    report = migration().migrate_connection(db)
    assert report["source"] == "empty"
    assert schema_signature(db) == canonical_signature
    assert len(execute(db, "SHOW TABLES")) == 12
    assert execute(db, "SELECT user_id,role FROM `user`") == (("global", "system"),)


def test_proper5_is_additive_and_preserves_all_rows(db, canonical_signature):
    create_proper5(db)
    before = snapshot(db)
    report = migration().migrate_connection(db)
    assert report["source"] == "proper5"
    assert schema_signature(db) == canonical_signature
    after = snapshot(db)
    assert all(after[table] == contents for table, contents in before.items())


def test_old_current12_prediction_gains_nullable_versions(db, canonical_signature):
    for sql in STATEMENTS:
        execute(db, sql)
    execute(db, "ALTER TABLE prediction DROP COLUMN model_version, DROP COLUMN feature_version")
    create_proper5(db)
    before = execute(db, "SELECT commit_hash,model_name,risk_score,predicted_at FROM prediction")
    report = migration().migrate_connection(db)
    assert any("ADD nullable columns" in op for op in report["operations"])
    assert schema_signature(db) == canonical_signature
    assert execute(db, "SELECT commit_hash,model_name,risk_score,predicted_at FROM prediction") == before
    assert execute(db, "SELECT model_version,feature_version FROM prediction") == ((None, None),)
    assert migration().migrate_connection(db)["operations"] == []


def test_partial_prediction_version_columns_refuse_before_ddl(db):
    for sql in STATEMENTS:
        execute(db, sql)
    execute(db, "ALTER TABLE prediction DROP COLUMN feature_version")
    create_proper5(db)
    before = snapshot(db)
    with pytest.raises(migration().MigrationError, match="Noncanonical"):
        migration().migrate_connection(db)
    assert snapshot(db) == before


def test_legacy4_preserves_values_nulls_and_exact_schema(db, canonical_signature, backup_dir):
    create_legacy(db)
    before_commit = execute(db, "SELECT commit_hash,repo_name,author_name,author_email,committed_at,message,parent_hash FROM `commit` ORDER BY commit_hash")
    before_features = execute(db, f"SELECT commit_hash,feature_version,{','.join(METRICS)} FROM commit_feature ORDER BY commit_hash")
    before_predictions = execute(db, "SELECT commit_hash,model_name,risk_score,predicted_at FROM prediction ORDER BY commit_hash")
    backup_fixture(db, backup_dir)
    report = migration().migrate_connection(db, allow_legacy_cleanup=True)
    assert schema_signature(db) == canonical_signature
    assert execute(db, "SELECT * FROM `commit` ORDER BY commit_hash") == before_commit
    assert execute(db, f"SELECT commit_hash,feature_version,{','.join(METRICS)} FROM commit_feature ORDER BY commit_hash") == before_features
    assert execute(db, "SELECT commit_hash,model_name,risk_score,predicted_at FROM prediction ORDER BY commit_hash") == before_predictions
    assert execute(db, "SELECT model_version,feature_version FROM prediction ORDER BY commit_hash") == (
        (None, "legacy-v1"), (None, "legacy-v1"), (None, "legacy-v1"),
    )
    assert execute(db, "SELECT is_test,is_bug_inducing,labeled_at FROM commit_feature ORDER BY commit_hash") == (
        (0, 1, datetime(2026, 10, 2)), (0, 0, TIME), (0, None, None),
    )
    assert execute(db, "SELECT model_name,line,algo,version_key,trained_at,feature_version FROM model ORDER BY model_name") == (
        ("lr_semantic_v1", "semantic", None, "", None, None),
        ("rf_v1", "expert", None, "", None, None),
        ("xgb_v1", "expert", None, "", None, None),
    )
    assert execute(db, "SELECT COUNT(*) FROM model_artifact") == ((0,),)
    assert any("split" in warning.lower() and "is_test=0" in warning for warning in report["warnings"])


@pytest.mark.parametrize("source", ["empty", "proper5", "legacy4"])
def test_repeat_is_identical_including_edited_global_and_config(db, backup_dir, source):
    if source == "proper5":
        create_proper5(db)
    elif source == "legacy4":
        create_legacy(db)
        backup_fixture(db, backup_dir)
    migration().migrate_connection(db, allow_legacy_cleanup=source == "legacy4")
    execute(db, "UPDATE `user` SET display_name='User edit',status='disabled' WHERE user_id='global'")
    execute(db, "INSERT INTO user_config VALUES ('global','decision_threshold','0.73','float',%s)", (TIME,))
    before = snapshot(db)
    assert migration().migrate_connection(db)["operations"] == []
    assert snapshot(db) == before


def test_legacy_cleanup_requires_explicit_opt_in_before_any_mutation(db):
    create_legacy(db)
    before = snapshot(db)
    with pytest.raises(migration().MigrationError, match="allow_legacy_cleanup"):
        migration().migrate_connection(db)
    assert snapshot(db) == before


@pytest.mark.parametrize("problem,sql,args", [
    ("conflicting labels", "UPDATE commit_label SET is_bug_inducing=0 WHERE label_method='szz_lite'", None),
    ("unknown lineage", "UPDATE prediction SET model_name='unidentified_model' WHERE model_name='rf_v1'", None),
    ("orphan feature", "UPDATE commit_feature SET commit_hash=%s WHERE commit_hash=%s", (HASHES[3], HASHES[2])),
    ("orphan prediction", "UPDATE prediction SET commit_hash=%s WHERE commit_hash=%s", (HASHES[3], HASHES[2])),
    ("orphan label", "UPDATE commit_label SET commit_hash=%s WHERE commit_hash=%s", (HASHES[3], HASHES[1])),
    ("invalid label", "UPDATE commit_label SET is_bug_inducing=2 WHERE commit_hash=%s", (HASHES[1],)),
    ("invalid probability", "UPDATE prediction SET risk_score=1.2 WHERE model_name='rf_v1'", None),
])
def test_predictable_legacy_data_errors_refuse_before_ddl(db, problem, sql, args):
    create_legacy(db)
    execute(db, sql, args)
    before = snapshot(db)
    with pytest.raises(migration().MigrationError):
        migration().migrate_connection(db, allow_legacy_cleanup=True)
    assert snapshot(db) == before, problem


def test_required_null_refuses_before_ddl(db):
    create_legacy(db)
    execute(db, "ALTER TABLE commit_feature MODIFY ns DECIMAL(20,10) NULL")
    execute(db, "UPDATE commit_feature SET ns=NULL WHERE commit_hash=%s", (HASHES[0],))
    before = snapshot(db)
    with pytest.raises(migration().MigrationError):
        migration().migrate_connection(db, allow_legacy_cleanup=True)
    assert snapshot(db) == before


def test_duplicate_prediction_refuses_before_ddl(db):
    create_legacy(db)
    execute(db, "ALTER TABLE prediction DROP INDEX uq_prediction_hash_model")
    execute(db, """INSERT INTO prediction (commit_hash,model_name,risk_score,predicted_at,feature_version)
                   SELECT commit_hash,model_name,risk_score,predicted_at,feature_version FROM prediction LIMIT 1""")
    before = snapshot(db)
    with pytest.raises(migration().MigrationError):
        migration().migrate_connection(db, allow_legacy_cleanup=True)
    assert snapshot(db) == before


def test_legacy_existing_foreign_keys_are_restored(db, canonical_signature, backup_dir):
    create_legacy(db)
    execute(db, "ALTER TABLE commit_feature ADD CONSTRAINT old_feature_fk FOREIGN KEY (commit_hash) REFERENCES `commit`(commit_hash)")
    execute(db, "ALTER TABLE prediction ADD CONSTRAINT old_prediction_fk FOREIGN KEY (commit_hash) REFERENCES `commit`(commit_hash)")
    backup_fixture(db, backup_dir)
    migration().migrate_connection(db, allow_legacy_cleanup=True)
    assert schema_signature(db) == canonical_signature
    assert execute(db, "SELECT @@FOREIGN_KEY_CHECKS") == ((1,),)
    with pytest.raises(pymysql.IntegrityError):
        execute(db, "INSERT INTO prediction (commit_hash,model_name,risk_score,predicted_at) VALUES (%s,'rf_v1',0.1,%s)", (HASHES[3], TIME))


@pytest.mark.parametrize("ddl", [
    "ALTER TABLE `commit` ADD CONSTRAINT custom_parent_fk FOREIGN KEY(parent_hash) REFERENCES `commit`(commit_hash)",
    "ALTER TABLE commit_feature ADD CONSTRAINT custom_time_check CHECK(committed_at > '2000-01-01')",
])
def test_unrecognized_legacy_constraints_refuse_before_any_ddl(db, ddl):
    create_legacy(db)
    execute(db, ddl)
    before = snapshot(db)
    with pytest.raises(migration().MigrationError):
        migration().migrate_connection(db, allow_legacy_cleanup=True)
    assert snapshot(db) == before


def test_null_legacy_label_method_refuses_before_any_ddl(db):
    create_legacy(db)
    execute(db, "ALTER TABLE commit_label MODIFY label_method VARCHAR(32) NULL")
    execute(db, "UPDATE commit_label SET label_method=NULL WHERE commit_hash=%s", (HASHES[1],))
    before = snapshot(db)
    with pytest.raises(migration().MigrationError):
        migration().migrate_connection(db, allow_legacy_cleanup=True)
    assert snapshot(db) == before


def cli_args():
    env = read_backend_env()
    return ["--db-host", os.environ.get("W1_MYSQL_HOST", "127.0.0.1"),
            "--db-port", os.environ.get("W1_MYSQL_PORT", "3306"), "--db-user", "jit",
            "--db-password", os.environ.get("W1_MYSQL_PASSWORD", env.get("DB_PASSWORD", "")),
            "--db-name", TEST_DB]


def test_cli_default_dry_run_lists_cleanup_without_mutation(db, capsys):
    create_legacy(db)
    before = snapshot(db)
    assert migration().main(cli_args()) == 0
    output = capsys.readouterr().out
    assert "commit_label" in output and "dry" in output.lower()
    assert snapshot(db) == before


def test_cli_apply_requires_backup_directory_before_mutation(db):
    create_legacy(db)
    before = snapshot(db)
    with pytest.raises(SystemExit, match="backup-dir"):
        migration().main([*cli_args(), "--apply", "--allow-legacy-cleanup"])
    assert snapshot(db) == before


def test_cli_backup_failure_does_not_mutate(db, tmp_path, monkeypatch):
    create_legacy(db)
    before = snapshot(db)
    module = migration()
    def unavailable(*args, **kwargs):
        raise FileNotFoundError("mysqldump unavailable")
    monkeypatch.setattr(module.subprocess, "run", unavailable)
    with pytest.raises(SystemExit, match="mysqldump"):
        module.main([*cli_args(), "--apply", "--allow-legacy-cleanup", "--backup-dir", str(tmp_path)])
    assert snapshot(db) == before


def test_cli_real_backup_precedes_cleanup_and_restores_legacy(db, canonical_signature, tmp_path, monkeypatch):
    create_legacy(db)
    before = snapshot(db)
    module = migration()
    real_run = module.subprocess.run

    def container_mysqldump(command, **kwargs):
        # macOS host has no mysql client: exercise the real dump binary inside jit-mysql.
        # Windows host ships mysqldump on PATH: run it directly.
        assert command[0] == "mysqldump" and TEST_DB in command
        assert "--password" not in command and "MYSQL_PWD" in kwargs["env"]
        assert snapshot(db) == before, "Backup must precede all destructive writes"
        if shutil.which("mysqldump"):
            return real_run(command, **kwargs)
        return real_run(["docker", "exec", "--env", "MYSQL_PWD", "jit-mysql", *command], **kwargs)

    monkeypatch.setattr(module.subprocess, "run", container_mysqldump)
    assert module.main([*cli_args(), "--apply", "--allow-legacy-cleanup", "--backup-dir", str(tmp_path)]) == 0
    assert schema_signature(db) == canonical_signature
    backups = list(tmp_path.glob("*.sql"))
    assert len(backups) == 1 and backups[0].stat().st_mode & 0o777 == (0o666 if os.name == "nt" else 0o600)
    clear_tables(db)
    sql = re.sub(r"--[^\n]*", "", backups[0].read_text(encoding="utf-8"))
    for statement in sql.split(";"):
        if statement.strip():
            execute(db, statement)
    assert snapshot(db) == before
    assert execute(db, "SELECT @@FOREIGN_KEY_CHECKS") == ((1,),)


@pytest.mark.parametrize("name", ["jit_demo", "jit_test", "other_migration", "jit_test_unsafe", "jit_test_other_migration"])
def test_fixture_guard_refuses_shared_or_unapproved_databases(name):
    with pytest.raises(RuntimeError):
        guard_database(name)
