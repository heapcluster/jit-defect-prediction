"""静态检查 MySQL 演示库建库脚本（Issue #142）。

只读文件、不连 MySQL：这些用例守的是**口径**，不是连通性。
连通性与行数验收走 `python -m scripts.demo_preflight`（Issue #138）。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
WRAPPER = REPO_ROOT / "backend" / "scripts" / "schema_mysql.sql"
INFRA_SCHEMA = REPO_ROOT / "infra" / "schema.sql"
SETUP_DOC = REPO_ROOT / "docs" / "backend" / "mysql-setup.md"
ACCEPTANCE_DOC = REPO_ROOT / "docs" / "backend" / "acceptance.md"
BACKEND_README = REPO_ROOT / "backend" / "README.md"

FORBIDDEN = ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "GRANT", "REVOKE", "CREATE USER")
PERSONAL_PATH = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]|(?<![A-Za-z0-9])/(?:Users|home)/")


def _statements(path: Path) -> list[str]:
    """去掉整行注释后按 `;` 切分，返回可执行语句（与 test_schema_sql.py 同一套口径）。"""
    text = "\n".join(
        line for line in path.read_text(encoding="utf-8").splitlines() if not line.lstrip().startswith("-- ")
    )
    return [" ".join(part.split()) for part in text.split(";") if part.strip()]


def _demo_db_name() -> str:
    match = re.search(r"CREATE DATABASE IF NOT EXISTS (\w+)", WRAPPER.read_text(encoding="utf-8"))
    assert match, "建库脚本必须用 CREATE DATABASE IF NOT EXISTS（幂等），否则重跑会报错"
    return match.group(1)


def test_wrapper_creates_demo_database_once_with_pinned_charset():
    creates = [s for s in _statements(WRAPPER) if s.upper().startswith("CREATE DATABASE")]
    assert len(creates) == 1, f"建库语句应恰好一条，实际 {len(creates)}"
    statement = creates[0].upper()
    assert "IF NOT EXISTS" in statement, "缺 IF NOT EXISTS → 重跑会报 1007，破坏幂等"
    assert _demo_db_name() == "jit_demo", "#142/#130 更正裁定：演示库名固定 jit_demo"
    assert "CHARACTER SET UTF8MB4" in statement, "缺显式字符集 → 各人本机默认值不同会建出不一致的库"
    assert "COLLATE UTF8MB4_UNICODE_CI" in statement, "缺显式排序规则（#142 裁定 utf8mb4_unicode_ci）"


def test_wrapper_switches_database_and_reuses_the_single_ddl_source():
    statements = _statements(WRAPPER)
    assert any(s.upper() == "USE JIT_DEMO" for s in statements), "缺 USE jit_demo → 四表会建到命令行指定的库里"
    sourced = [s for s in statements if s.upper().startswith("SOURCE")]
    assert len(sourced) == 1, f"应恰好 SOURCE 一次 infra/schema.sql，实际 {sourced}"
    assert sourced[0] == "SOURCE infra/schema.sql", (
        f"DDL 单一来源必须是 infra/schema.sql（相对仓库根），实际 {sourced[0]!r}"
    )
    assert (REPO_ROOT / sourced[0].split(maxsplit=1)[1]).is_file(), "SOURCE 指向的文件在仓库根下不存在"
    assert not [s for s in statements if "CREATE TABLE" in s.upper()], (
        "建库脚本里不许出现 CREATE TABLE：四表 DDL 只在 infra/schema.sql 一份，"
        "复制第二份必然与 Base.metadata 漂移（test_schema_sql.py 守的就是这份一致性）"
    )


@pytest.mark.parametrize("verb", FORBIDDEN)
def test_wrapper_carries_no_data_permission_or_destructive_statement(verb):
    for statement in _statements(WRAPPER):
        assert verb not in statement.upper(), f"建库脚本不应含 {verb}：{statement}"


def test_infra_schema_sql_stays_importable_into_any_database():
    """`infra/schema.sql` 必须保持「纯四表 DDL」。

    它同时服务三个调用方：`docs/backend/acceptance.md` 的导入命令、Issue #121 的两个探针库
    （jit_schema_probe / jit_orm_probe）、本建库脚本的 SOURCE。一旦里面出现 CREATE DATABASE
    或 USE，命令行指定的目标库会被静默改写 —— 验收会在错误的库上「通过」。
    """
    upper = "\n".join(
        line for line in INFRA_SCHEMA.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("-- ")
    ).upper()
    assert "CREATE DATABASE" not in upper, "建库头请放 backend/scripts/schema_mysql.sql，不要进 infra/schema.sql"
    assert not re.search(r"^\s*USE\s", upper, re.MULTILINE), "USE 会覆盖调用方指定的目标库"
    for verb in ("GRANT", "REVOKE", "CREATE USER", "DROP", "TRUNCATE"):
        assert verb not in upper, f"infra/schema.sql 不应含 {verb}"


def test_demo_db_name_is_the_single_caliber_across_backend_docs():
    db_name = _demo_db_name()
    setup = SETUP_DOC.read_text(encoding="utf-8")
    acceptance = ACCEPTANCE_DOC.read_text(encoding="utf-8")
    assert f"mysql+pymysql://<user>:<pwd>@127.0.0.1:3306/{db_name}" in setup, (
        "配置文档必须给出可直接照抄的 DATABASE_URL 形态（口令用占位符）"
    )
    assert "backend/scripts/schema_mysql.sql" in setup, "配置文档必须写明建库脚本路径与用法"
    assert db_name in acceptance, "验收文档的建表命令必须指向同一个库名"
    for path in (SETUP_DOC, ACCEPTANCE_DOC, BACKEND_README, WRAPPER):
        text = path.read_text(encoding="utf-8")
        assert "jit_defect" not in text, (
            f"{path.name} 仍在用旧库名 jit_defect —— 那是共享实例上的占位脏数据库，"
            "演示与验收一律 jit_demo（#130 更正裁定 / #142）"
        )


@pytest.mark.parametrize(
    "needle",
    [
        "8.0",                                     # 版本要求
        "pymysql",                                 # 驱动依赖确认
        "1044",                                    # CREATE DATABASE 权限不足的报错号
        "3306",                                    # 端口占用
        "utf8mb4",                                 # 字符集
        "time_zone",                               # 时区
        "python -m app.ingest",                    # 四份 CSV 灌库
        "python -m scripts.demo_preflight",        # 一条命令自检
        "84,461", "83,943", "14,596",              # 验收清单三个数
        "lr_v1", "rf_v1", "xgb_v1",                # 三模型全加载
        "load_dotenv",                             # 行内 DATABASE_URL 前缀压过 .env 的坑
        "docs/common/local-runbook.md",            # 步骤口径的指针（不复述）
    ],
)
def test_setup_doc_covers_every_item_issue_142_asked_for(needle):
    assert needle in SETUP_DOC.read_text(encoding="utf-8"), f"配置文档缺 #142 要求的项：{needle}"


def test_setup_doc_warns_about_the_raw_feature_table():
    """§4 那条警告是承重的：灌 raw 特征表会让在线预测静默算错，删掉它等于埋雷。"""
    text = SETUP_DOC.read_text(encoding="utf-8")
    for needle in ("commit_features_raw.csv", "dataset_szz.csv", "对数变换", "契约二 v1.2",
                   "0.82657", "0.79963", "MIN(la)"):
        assert needle in text, f"配置文档缺特征口径警告的关键项：{needle}"


@pytest.mark.parametrize(
    "index_doc",
    [
        REPO_ROOT / "backend" / "README.md",
        REPO_ROOT / "docs" / "backend" / "README.md",
        REPO_ROOT / "docs" / "README.md",
    ],
    ids=["backend/README.md", "docs/backend/README.md", "docs/README.md"],
)
def test_setup_doc_is_reachable_from_every_index(index_doc):
    """新文档必须能从三份索引点开。

    #142 要求「README 挂链接」；`openspec/specs/db-schema`「一条命令建库」还要求把该命令
    写进 `backend/README.md`。挂在索引外等于没有 —— 后面的人只会照 runbook 走。
    """
    text = index_doc.read_text(encoding="utf-8")
    assert "mysql-setup.md" in text, f"{index_doc.name} 没挂 docs/backend/mysql-setup.md 的入口"


def test_wrapper_and_docs_carry_no_personal_absolute_path():
    for path in (WRAPPER, SETUP_DOC, ACCEPTANCE_DOC, Path(__file__)):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            assert not PERSONAL_PATH.search(line), f"{path.name}:{lineno} 含个人绝对路径（§0 硬规矩 1）：{line}"


def test_wrapper_comments_use_the_mysql_safe_double_dash():
    """注释一律 `-- `（双横线 + 空格），不允许裸 `--`。

    MySQL 认裸 `--` 为注释（后面跟换行也算），但本文件与 test_schema_sql.py 都用
    「整行以 `-- ` 开头」来剥离注释再按 `;` 切分语句 —— 裸 `--` 会被当成语句的一部分，
    粘到下一条 CREATE DATABASE 上，让「恰好四条语句」这类断言静默失效。
    """
    for lineno, line in enumerate(WRAPPER.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.lstrip()
        if stripped.startswith("--"):
            assert stripped.startswith("-- "), f"schema_mysql.sql:{lineno} 注释必须是「-- 」开头：{line!r}"


def test_wrapper_is_a_four_statement_script():
    statements = _statements(WRAPPER)
    assert len(statements) == 4, f"建库 + USE + SOURCE + 自检 SELECT 共四条，实际 {len(statements)}：{statements}"
    assert statements[-1].upper().startswith("SELECT"), "末条应是自检 SELECT，跑完当场能看到建出的表"
