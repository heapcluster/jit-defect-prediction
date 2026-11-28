"""命令行入口：建表与创建账号。"""

from __future__ import annotations

import argparse
import getpass
import sys

from app import auth, db
from app.constants import ALGORITHMS, FEATURE_VERSION, LINES
from app.models import Algorithm, User
from app.utils import new_id, now


def seed_algorithms() -> None:
    from sqlalchemy import select

    canonical = {(line, item["algo"]) for line in LINES for item in ALGORITHMS}
    with db.SessionLocal() as session:
        for row in session.scalars(select(Algorithm)).all():
            if (row.line, row.algo) not in canonical:
                session.delete(row)
        for line in LINES:
            for item in ALGORITHMS:
                existing = session.get(Algorithm, (line, item["algo"]))
                payload = {
                    "defaults": item["defaults"],
                    "types": item["types"],
                }
                import json

                hyper = json.dumps(payload, ensure_ascii=False, sort_keys=True)
                if existing is None:
                    session.add(
                        Algorithm(
                            line=line,
                            algo=item["algo"],
                            family=item["family"],
                            hyperparams_json=hyper,
                            enabled=1,
                            description=item["name"],
                        )
                    )
                elif existing.hyperparams_json != hyper:
                    existing.hyperparams_json = hyper
        session.commit()


def init_db() -> None:
    db.init_db()
    seed_algorithms()
    print("建表完成：15 张表；算法清单已写入（26 行）")


def create_user() -> None:
    username = input("用户名: ").strip()
    if not username:
        print("用户名不能为空", file=sys.stderr)
        raise SystemExit(2)
    display = input("显示名（回车同用户名）: ").strip() or username
    password = getpass.getpass("口令: ")
    if not password:
        print("口令不能为空", file=sys.stderr)
        raise SystemExit(2)
    with db.SessionLocal() as session:
        from sqlalchemy import select

        if session.scalar(select(User).where(User.username == username)):
            print("用户名已存在", file=sys.stderr)
            raise SystemExit(2)
        session.add(
            User(
                user_id=new_id("user"),
                username=username,
                password=password,
                display_name=display,
                status="active",
                created_at=now(),
            )
        )
        session.commit()
    print(f"账号已创建：{username}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="JIT 缺陷预测系统命令行")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init-db", help="建表并写入算法清单")
    sub.add_parser("create-user", help="交互式创建账号")
    args = parser.parse_args(argv)
    if args.command == "init-db":
        init_db()
        return 0
    create_user()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
