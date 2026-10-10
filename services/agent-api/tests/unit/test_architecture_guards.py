"""The layering and ambient-state guards must actually fire (spine AD-1, AD-2, AD-10).

Each case builds a throwaway package, so a green ``lint-imports`` on the real tree can
never be a guard that silently stopped working.
"""

import subprocess
import sys
from pathlib import Path

import pytest

SERVICE_ROOT = Path(__file__).resolve().parents[2]
BIN = Path(sys.executable).parent
PACKAGES = [
    "app",
    "app/api",
    "app/orchestration",
    "app/tools",
    "app/ports",
    "app/providers",
    "app/clients",
    "app/schemas",
]
ROOT_MODULES = ("settings", "main", "container")


def _make_tree(root: Path, extra: dict[str, str]) -> None:
    for package in PACKAGES:
        (root / package).mkdir(parents=True, exist_ok=True)
        (root / package / "__init__.py").touch()
    for module in ROOT_MODULES:
        (root / "app" / f"{module}.py").touch()
    for relative, body in extra.items():
        (root / relative).write_text(body)
    (root / ".importlinter").write_text((SERVICE_ROOT / ".importlinter").read_text())


def _lint_imports(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [str(BIN / "lint-imports")], cwd=root, capture_output=True, text=True, check=False
    )


def test_clean_tree_is_accepted(tmp_path: Path) -> None:
    _make_tree(tmp_path, {})
    result = _lint_imports(tmp_path)
    assert result.returncode == 0, result.stdout


@pytest.mark.parametrize(
    ("file", "source"),
    [
        ("app/ports/bad.py", "import httpx\n"),
        ("app/ports/bad.py", "import app.tools\n"),
        ("app/tools/bad.py", "import httpx\n"),
        ("app/tools/bad.py", "import app.clients\n"),
        ("app/tools/bad.py", "import app.orchestration\n"),
        ("app/orchestration/bad.py", "import app.providers\n"),
        ("app/orchestration/bad.py", "import fastapi\n"),
        ("app/orchestration/bad.py", "import app.api\n"),
        ("app/api/bad.py", "import app.clients\n"),
        ("app/api/bad.py", "import app.providers\n"),
        ("app/clients/bad.py", "import app.orchestration\n"),
        ("app/providers/bad.py", "import app.tools\n"),
        ("app/schemas/bad.py", "import app.ports\n"),
        ("app/api/bad.py", "import app.settings\n"),
        ("app/orchestration/bad.py", "import app.settings\n"),
        ("app/clients/bad.py", "import app.settings\n"),
        ("app/clients/bad.py", "import app.main\n"),
        ("app/api/bad.py", "import app.container\n"),
        # AD-1: the Agent never reaches Core's database. AD-10: it never decodes tokens.
        ("app/clients/bad.py", "import sqlalchemy\n"),
        ("app/clients/bad.py", "import psycopg\n"),
        ("app/clients/bad.py", "import asyncpg\n"),
        ("app/api/bad.py", "import jwt\n"),
        ("app/tools/bad.py", "import jwt\n"),
    ],
)
def test_forbidden_import_is_rejected(tmp_path: Path, file: str, source: str) -> None:
    _make_tree(tmp_path, {file: source})
    result = _lint_imports(tmp_path)
    assert result.returncode != 0, f"{file}: {source!r} was accepted\n{result.stdout}"
    assert "BROKEN" in result.stdout


def _ruff(filename: str, source: str) -> str:
    result = subprocess.run(  # noqa: S603
        [str(BIN / "ruff"), "check", "--stdin-filename", filename, "-"],
        cwd=SERVICE_ROOT,
        input=source,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout


@pytest.mark.parametrize("layer", ["orchestration", "tools", "ports"])
@pytest.mark.parametrize(
    "source",
    [
        "import datetime\nvalue = datetime.datetime.now()\n",
        "from datetime import datetime\nvalue = datetime.now()\n",
        "import os\nvalue = os.environ\n",
        "import os\nvalue = os.getenv('A')\n",
        "import uuid\nvalue = uuid.uuid4()\n",
        "import time\nvalue = time.time()\n",
        "import time\nvalue = time.monotonic()\n",
        "import random\nvalue = random.random()\n",
    ],
)
def test_ambient_state_is_banned_in_deterministic_layers(layer: str, source: str) -> None:
    assert "TID251" in _ruff(f"app/{layer}/probe.py", source)


@pytest.mark.parametrize("layer", ["clients", "providers", "api"])
def test_ambient_state_is_allowed_in_adapters_and_transport(layer: str) -> None:
    source = "import datetime\nvalue = datetime.datetime.now()\n"
    assert "TID251" not in _ruff(f"app/{layer}/probe.py", source)
