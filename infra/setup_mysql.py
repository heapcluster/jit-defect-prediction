"""一键建库脚本（非 docker）。

在「已安装 MySQL 的本机」上把 jit-defect-prediction 跑起来所需的库一次性备好：

  1. 检测并（在需要时）尝试启动本机 MySQL 服务（Windows / Linux / macOS 各自一行命令）；
  2. 建两份库：jit_demo（联调 / 演示 / 验收共用）与 jit_test（pytest 用）；
  3. 确保应用用户 jit 存在并拥有两份库的权限；
  4. 在两份库上执行 infra/schema.sql 建四张表；
  5. 可选：--seed 灌入起步种子数据。

设计前提（与「全部按 MySQL」一致）：你已经在本机装好 MySQL，并在 backend/.env
里按分字段填好连接（DB_HOST / DB_PORT / DB_USER / DB_PASSWORD / DB_NAME）。脚本按这份配置
连库、建库（演示库 + 测试库）、建表。

连接配置优先级（高 → 低）：
    1. --database-url 整段 DSN（CI / 容器用）
    2. --db-host / --db-port / --db-user / --db-password / --db-name
    3. backend/.env 的分字段
    4. backend/.env 里遗留的 DATABASE_URL（老配置仍可跑）

最常见用法：
    python infra/setup_mysql.py            # 读 backend/.env，建 jit_demo + jit_test
    python infra/setup_mysql.py --seed     # 额外灌 seed 起步数据
    python infra/setup_mysql.py --root-password <pwd>   # jit 无建库权限时，用 root 代建并授权

注意：MySQL 没装时脚本不会偷偷改系统，只会给出各平台一行安装命令后退出。
"""

from __future__ import annotations

import argparse
import platform
import re
import socket
import subprocess
import sys
from pathlib import Path

import pymysql

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
SCHEMA_PATH = REPO_ROOT / "infra" / "schema.sql"


# ───────────────────────────── 解析与读取 ─────────────────────────────


def parse_database_url(url: str) -> dict:
    """mysql+pymysql://user:pwd@host:port/db?query → 字段。"""
    m = re.match(
        r"mysql\+pymysql://(?P<user>[^:]+):(?P<pwd>[^@]+)@(?P<host>[^:/]+)"
        r"(?::(?P<port>\d+))?/(?P<db>[^?]+)",
        url.strip(),
    )
    if not m:
        raise SystemExit(
            f"[setup] 无法解析整段 DSN：{url}\n"
            "期望形如 mysql+pymysql://jit:<pwd>@127.0.0.1:3306/jit_demo?charset=utf8mb4"
        )
    port = int(m.group("port") or 3306)
    return {
        "user": m.group("user"),
        "password": m.group("pwd"),
        "host": m.group("host"),
        "port": port,
        "database": m.group("db"),
    }


ENV_KEYS = (
    "DB_HOST",
    "DB_PORT",
    "DB_USER",
    "DB_PASSWORD",
    "DB_NAME",
    "DB_TEST_NAME",
    "DATABASE_URL",
)


def read_backend_env(path: Path | None = None) -> dict[str, str]:
    """读 backend/.env 里连接相关的键（手写解析，不给 infra 引入 dotenv 依赖）。"""
    env_file = path or (BACKEND_DIR / ".env")
    if not env_file.exists():
        return {}
    values: dict[str, str] = {}
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key in ENV_KEYS:
            value = value.strip()
            # 与 dotenv 同口径：整段被引号包住时剥一层，口令本身带引号也不会被吃掉
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            values[key] = value
    return values


def resolve_credentials(args: argparse.Namespace, env: dict[str, str] | None = None) -> dict:
    """按「命令行 > .env 分字段 > .env 的旧 DATABASE_URL」取连接字段。"""
    if args.database_url:
        return parse_database_url(args.database_url)
    env = read_backend_env() if env is None else env
    host = (args.db_host or env.get("DB_HOST", "")).strip()
    user = (args.db_user or env.get("DB_USER", "")).strip()
    if host and user:
        port_raw = str(args.db_port or env.get("DB_PORT") or 3306).strip()
        try:
            port = int(port_raw)
        except ValueError:
            raise SystemExit(f"[setup] DB_PORT 不是整数：{port_raw}") from None
        password = args.db_password if args.db_password is not None else env.get("DB_PASSWORD", "")
        return {
            "user": user,
            "password": password,
            "host": host,
            "port": port,
            "database": (args.db_name or env.get("DB_NAME") or "jit_demo").strip(),
        }
    legacy = env.get("DATABASE_URL", "").strip()
    if legacy:
        return parse_database_url(legacy)
    raise SystemExit(
        "[setup] 未找到数据库连接配置。请在 backend/.env 填这五项（口令原样写，不用转义）：\n"
        "        DB_HOST=127.0.0.1\n"
        "        DB_PORT=3306\n"
        "        DB_USER=jit\n"
        "        DB_PASSWORD=<你的口令>\n"
        "        DB_NAME=jit_demo\n"
        "        模板见 backend/.env.example，引导见 docs/backend/mysql-setup.md。"
    )


# ───────────────────────────── 服务可用性 ─────────────────────────────


def mysql_listening(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def try_start_service() -> None:
    """按平台尝试启动 MySQL 服务；失败只提示，不强制。"""
    system = platform.system()
    print("[setup] 尝试启动本机 MySQL 服务 …")
    try:
        if system == "Windows":
            for svc in ("MySQL80", "MySQL57", "MySQL"):
                rc = subprocess.run(
                    ["net", "start", svc], capture_output=True, text=True, check=False
                )
                if rc.returncode == 0:
                    print(f"[setup] 已启动服务 {svc}")
                    return
            print(
                "[setup] 未能通过 net start 启动（服务名可能不同）。请手动启动 MySQL 后再跑本脚本。"
            )
        elif system == "Darwin":  # macOS
            subprocess.run(
                ["brew", "services", "start", "mysql"], capture_output=True, text=True, check=False
            )
            print("[setup] 已执行 brew services start mysql")
        else:  # Linux
            for cmd in (
                ["sudo", "systemctl", "start", "mysql"],
                ["sudo", "service", "mysql", "start"],
                ["sudo", "systemctl", "start", "mysqld"],
            ):
                rc = subprocess.run(cmd, capture_output=True, text=True, check=False)
                if rc.returncode == 0:
                    print(f"[setup] 已执行：{' '.join(cmd)}")
                    return
            print("[setup] 未能启动 MySQL 服务，请手动启动后重试。")
    except Exception as exc:  # noqa: BLE001
        print(f"[setup] 启动服务时出错：{exc}（可忽略，请手动启动 MySQL）")


def ensure_reachable(creds: dict, skip_start: bool) -> None:
    if mysql_listening(creds["host"], creds["port"]):
        print(f"[setup] MySQL 已在 {creds['host']}:{creds['port']} 监听")
        return
    if not skip_start:
        try_start_service()
    # 再等一会儿
    for _ in range(10):
        if mysql_listening(creds["host"], creds["port"]):
            print(f"[setup] MySQL 已在 {creds['host']}:{creds['port']} 监听")
            return
    print(f"[setup] 连不上 {creds['host']}:{creds['port']}。请确认 MySQL 已安装并启动。")
    print(
        "        Windows: net start MySQL80    Linux: sudo systemctl start mysql"
        "    macOS: brew services start mysql"
    )
    raise SystemExit(1) from None


# ───────────────────────────── 建库 / 授权 / 建表 ─────────────────────────────


def split_statements(sql: str) -> list[str]:
    return [s.strip() for s in sql.split(";") if s.strip()]


def connect(
    creds: dict, user: str, password: str, database: str | None = None
) -> pymysql.Connection:
    return pymysql.connect(
        host=creds["host"],
        port=creds["port"],
        user=user,
        password=password,
        database=database,
        autocommit=True,
    )


def run_schema_on(conn: pymysql.Connection, database: str) -> None:
    conn.select_db(database)
    statements = split_statements(SCHEMA_PATH.read_text(encoding="utf-8"))
    with conn.cursor() as cur:
        for stmt in statements:
            cur.execute(stmt)
    print(f"[setup] 已在 {database} 执行 schema.sql（四张表就绪）")


def build_databases(creds: dict, test_db: str, root_password: str | None) -> None:
    demo_db = creds["database"]
    app_user, app_pwd = creds["user"], creds["password"]

    if root_password is not None:
        # 用 root 建库 + 建应用用户 + 授权（jit 自身无需建库权限）
        print("[setup] 以 root 连接，建库并授权应用用户 …")
        root = connect(creds, "root", root_password)
        try:
            with root.cursor() as cur:
                for db in (demo_db, test_db):
                    cur.execute(
                        f"CREATE DATABASE IF NOT EXISTS `{db}` "
                        f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                    )
                cur.execute(f"CREATE USER IF NOT EXISTS '{app_user}'@'%' IDENTIFIED BY '{app_pwd}'")
                cur.execute(
                    f"CREATE USER IF NOT EXISTS '{app_user}'@'localhost' IDENTIFIED BY '{app_pwd}'"
                )
                for host_spec in ("%", "localhost"):
                    cur.execute(
                        f"GRANT ALL PRIVILEGES ON `{demo_db}`.* TO '{app_user}'@'{host_spec}'"
                    )
                    cur.execute(
                        f"GRANT ALL PRIVILEGES ON `{test_db}`.* TO '{app_user}'@'{host_spec}'"
                    )
                cur.execute("FLUSH PRIVILEGES")
            print(f"[setup] 已建库 {demo_db} / {test_db}，并授权 {app_user}")
        finally:
            root.close()
        # 后续建表用应用用户自己执行
        app = connect(creds, app_user, app_pwd)
        try:
            run_schema_on(app, demo_db)
            run_schema_on(app, test_db)
        finally:
            app.close()
        return

    # 无 root 密码：直接用应用用户建库（需要该用户有建库权限）
    print(f"[setup] 以应用用户 {app_user} 连接，尝试直接建库 …")
    try:
        app = connect(creds, app_user, app_pwd)
    except pymysql.err.OperationalError as exc:
        print(
            f"[setup] 连接失败：{exc}\n"
            f"        若 jit 无建库权限，请加 --root-password <pwd> 由 root 代建并授权。"
        )
        raise SystemExit(1) from None
    try:
        with app.cursor() as cur:
            for db in (demo_db, test_db):
                cur.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{db}` "
                    f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
        run_schema_on(app, demo_db)
        run_schema_on(app, test_db)
    except pymysql.err.OperationalError as exc:
        print(
            f"[setup] 建库/建表失败（多半是 jit 没有 CREATE DATABASE 权限）：{exc}\n"
            f"        请用 root 执行：GRANT CREATE, DROP ON *.* TO '{app_user}'@'%';\n"
            f"        或改用 --root-password <pwd> 由 root 代建并授权。"
        )
        raise SystemExit(1) from None
    finally:
        app.close()


def run_seed() -> None:
    print("[setup] 灌入种子数据（seed_dev_data.py）…")
    rc = subprocess.run(
        [sys.executable, "-m", "scripts.seed_dev_data"],
        cwd=str(BACKEND_DIR),
        check=False,
    )
    if rc.returncode != 0:
        print("[setup] 种子数据写入失败，请检查 backend/.env 的连接字段与库连接。")
        raise SystemExit(1) from None
    print("[setup] 种子数据写入完成")


# ───────────────────────────── 入口 ─────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="一键建库（非 docker）：建 jit_demo / jit_test 并执行 schema.sql"
    )
    parser.add_argument(
        "--database-url", help="整段 DSN，优先级最高（CI / 容器用；覆盖下面的分字段）"
    )
    parser.add_argument("--db-host", help="覆盖 backend/.env 的 DB_HOST")
    parser.add_argument("--db-port", help="覆盖 DB_PORT（默认 3306）")
    parser.add_argument("--db-user", help="覆盖 DB_USER")
    parser.add_argument("--db-password", help="覆盖 DB_PASSWORD")
    parser.add_argument("--db-name", help="覆盖 DB_NAME（演示库，默认 jit_demo）")
    parser.add_argument(
        "--test-db", default=None, help="pytest 用测试库名（默认取 DB_TEST_NAME，否则 jit_test）"
    )
    parser.add_argument("--seed", action="store_true", help="额外灌入起步种子数据")
    parser.add_argument(
        "--root-password", default=None, help="用 root 代建库并授权（jit 无建库权限时）"
    )
    parser.add_argument("--skip-start", action="store_true", help="跳过启动 MySQL 服务尝试")
    args = parser.parse_args()

    env = read_backend_env()
    creds = resolve_credentials(args, env)
    test_db = args.test_db or env.get("DB_TEST_NAME") or "jit_test"
    print(
        f"[setup] 目标：{creds['user']}@{creds['host']}:{creds['port']}  "
        f"演示库={creds['database']} 测试库={test_db}"
    )

    ensure_reachable(creds, args.skip_start)
    build_databases(creds, test_db, args.root_password)
    if args.seed:
        run_seed()

    print("[setup] 完成。下一步：")
    print("        cd backend && uvicorn app.main:app --reload   # 起后端")
    print(f"        （pytest 会自动连测试库 {test_db}，不需要改 .env）")


if __name__ == "__main__":
    main()
