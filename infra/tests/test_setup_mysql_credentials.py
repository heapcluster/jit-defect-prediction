"""`infra/setup_mysql.py` 的连接配置解析：分字段 / 整段 DSN / 优先级 / .env 读取。

只测纯函数（不连库），因此可以在没有 MySQL 的机器上跑；真建库的路径由
`docs/backend/mysql-setup.md` 的手工步骤与 CI 的「准备测试库」步骤覆盖。
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import setup_mysql  # noqa: E402


def make_args(**overrides) -> argparse.Namespace:
    base = {
        "database_url": None,
        "db_host": None,
        "db_port": None,
        "db_user": None,
        "db_password": None,
        "db_name": None,
    }
    base.update(overrides)
    return argparse.Namespace(**base)


class ResolveCredentialsTest(unittest.TestCase):
    def test_fields_from_env(self) -> None:
        creds = setup_mysql.resolve_credentials(
            make_args(),
            {
                "DB_HOST": "127.0.0.1",
                "DB_USER": "jit",
                "DB_PASSWORD": "p@ss:w/rd",
                "DB_NAME": "jit_demo",
            },
        )
        self.assertEqual(creds["host"], "127.0.0.1")
        self.assertEqual(creds["user"], "jit")
        self.assertEqual(creds["port"], 3306)
        self.assertEqual(creds["password"], "p@ss:w/rd", "口令原样传给驱动，不做二次编码")
        self.assertEqual(creds["database"], "jit_demo")

    def test_cli_flags_override_env(self) -> None:
        creds = setup_mysql.resolve_credentials(
            make_args(
                db_host="db.internal",
                db_port="3307",
                db_user="root",
                db_password="x",
                db_name="other",
            ),
            {"DB_HOST": "127.0.0.1", "DB_USER": "jit", "DB_PASSWORD": "p", "DB_NAME": "jit_demo"},
        )
        self.assertEqual(creds["host"], "db.internal")
        self.assertEqual(creds["port"], 3307)
        self.assertEqual(creds["user"], "root")
        self.assertEqual(creds["database"], "other")

    def test_database_url_wins_over_fields(self) -> None:
        creds = setup_mysql.resolve_credentials(
            make_args(
                database_url="mysql+pymysql://root:root@127.0.0.1:3306/jit_demo?charset=utf8mb4"
            ),
            {"DB_HOST": "ignored", "DB_USER": "ignored"},
        )
        self.assertEqual(creds["user"], "root")
        self.assertEqual(creds["password"], "root")

    def test_legacy_env_database_url_is_still_accepted(self) -> None:
        creds = setup_mysql.resolve_credentials(
            make_args(), {"DATABASE_URL": "mysql+pymysql://jit:old@127.0.0.1:3306/jit_demo"}
        )
        self.assertEqual(creds["user"], "jit")
        self.assertEqual(creds["password"], "old")

    def test_missing_config_exits_with_guidance(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            setup_mysql.resolve_credentials(make_args(), {})
        self.assertIn("DB_HOST", str(ctx.exception))

    def test_invalid_port_exits(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            setup_mysql.resolve_credentials(
                make_args(), {"DB_HOST": "h", "DB_USER": "u", "DB_PORT": "not-a-port"}
            )
        self.assertIn("DB_PORT", str(ctx.exception))


class ReadBackendEnvTest(unittest.TestCase):
    def test_parses_fields_and_ignores_noise(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text(
                "# 注释行\n"
                "\n"
                "DB_HOST=127.0.0.1\n"
                "DB_PORT = 3306 \n"
                "DB_USER=jit\n"
                'DB_PASSWORD="quoted#pwd"\n'
                "UNRELATED=1\n"
                "DATABASE_URL=mysql+pymysql://u:p@h:3306/db\n",
                encoding="utf-8",
            )
            env = setup_mysql.read_backend_env(env_file)
        self.assertEqual(env["DB_HOST"], "127.0.0.1")
        self.assertEqual(env["DB_PORT"], "3306")
        self.assertEqual(
            env["DB_PASSWORD"], "quoted#pwd", "整段被引号包住时剥一层（与 dotenv 同口径）"
        )
        self.assertNotIn("UNRELATED", env, "只收连接相关的键")
        self.assertIn("DATABASE_URL", env, "老配置仍要能读到")

    def test_missing_file_returns_empty(self) -> None:
        self.assertEqual(setup_mysql.read_backend_env(Path("no-such-dir") / ".env"), {})


if __name__ == "__main__":
    unittest.main()
