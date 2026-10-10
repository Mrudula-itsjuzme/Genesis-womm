"""Migrations form one linear chain of NNNN_slug.py files (spine AD-20)."""

import re
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

SERVICE_ROOT = Path(__file__).resolve().parents[2]


def _script_directory() -> ScriptDirectory:
    return ScriptDirectory.from_config(Config(str(SERVICE_ROOT / "alembic.ini")))


def test_there_is_exactly_one_head() -> None:
    assert len(_script_directory().get_heads()) == 1


def test_revisions_form_a_single_linear_chain_from_0001() -> None:
    revisions = list(_script_directory().walk_revisions(base="base", head="heads"))
    assert revisions, "no migrations found"
    assert all(len(r.nextrev) <= 1 for r in revisions), "branching detected"
    assert revisions[-1].down_revision is None
    assert revisions[-1].revision == "0001"


def test_file_names_are_sequential_nnnn_slug() -> None:
    names = sorted(p.name for p in (SERVICE_ROOT / "migrations" / "versions").glob("*.py"))
    assert names, "no migration files"
    for index, name in enumerate(names, start=1):
        assert re.fullmatch(rf"{index:04d}_[a-z0-9_]+\.py", name), name


def test_revision_id_matches_the_file_prefix() -> None:
    for script in _script_directory().walk_revisions():
        assert script.path is not None
        assert Path(script.path).name.startswith(f"{script.revision}_")
