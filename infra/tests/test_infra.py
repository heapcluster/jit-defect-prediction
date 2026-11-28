"""infra 目录自测：只校验工程化文件的静态契约，不连接数据库。"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INFRA = ROOT / "infra"


def test_schema_declares_fifteen_tables() -> None:
    sql = (INFRA / "schema.sql").read_text(encoding="utf-8")
    tables = re.findall(r"CREATE TABLE IF NOT EXISTS `?([a-z_]+)`?", sql)
    assert len(tables) == 15
    assert len(set(tables)) == 15


def test_setup_script_targets_both_databases() -> None:
    text = (INFRA / "setup_mysql.py").read_text(encoding="utf-8")
    assert "jit_demo" in text
    assert "jit_test" in text
    assert "schema.sql" in text
