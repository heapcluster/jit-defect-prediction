"""创建 jit_demo / jit_test 两个库并执行 infra/schema.sql。

用法（仓库根目录）：
    python infra/setup_mysql.py

连接参数：
- 建库账号：DB_ROOT_USER / DB_ROOT_PASSWORD，默认 root / 空口令；
- 服务器：DB_HOST / DB_PORT，默认 127.0.0.1:3306；
- 业务库名：DB_NAME / DB_TEST_NAME，默认 jit_demo / jit_test。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pymysql

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = Path(__file__).with_name("schema.sql")


def read_statements() -> list[str]:
    lines = []
    for line in SCHEMA.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        lines.append(line)
    statements = []
    for chunk in "\n".join(lines).split(";"):
        if chunk.strip():
            statements.append(chunk.strip())
    return statements


def main() -> int:
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = int(os.getenv("DB_PORT", "3306"))
    user = os.getenv("DB_ROOT_USER", "root")
    password = os.getenv("DB_ROOT_PASSWORD", "")
    databases = [
        os.getenv("DB_NAME", "jit_demo").strip() or "jit_demo",
        os.getenv("DB_TEST_NAME", "jit_test").strip() or "jit_test",
    ]

    statements = read_statements()
    connection = pymysql.connect(host=host, port=port, user=user, password=password, autocommit=True)
    try:
        with connection.cursor() as cursor:
            for database in databases:
                cursor.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{database}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
                cursor.execute(f"USE `{database}`")
                for statement in statements:
                    cursor.execute(statement)
                print(f"initialized {database}: {len(statements)} statements")
    finally:
        connection.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
