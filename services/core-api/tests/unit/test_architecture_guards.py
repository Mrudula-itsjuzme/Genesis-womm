"""The layering and ambient-state guards must actually fire (spine AD-2).

Each case builds a throwaway package, so a green ``lint-imports`` on the real tree can
never be a guard that silently stopped working.
"""

import subprocess
import sys
from pathlib import Path

import pytest

SERVICE_ROOT = Path(__file__).resolve().parents[2]
BIN = Path(sys.executable).parent
LAYER_PACKAGES = [
    "app",
    "app/api",
    "app/services",
    "app/domain",
    "app/schemas",
    "app/repositories",
    "app/models",
    "app/clients",
    "app/ingestion",
]


def _make_tree(root: Path, extra: dict[str, str]) -> None:
    for package in LAYER_PACKAGES:
        (root / package).mkdir(parents=True, exist_ok=True)
        (root / package / "__init__.py").touch()
    for module in ("settings", "main", "container"):
        (root / "app" / f"{module}.py").touch()
    (root / "app" / "services" / "schedule_store.py").touch()
    # The one module allowed to import the event writers.
    (root / "app" / "services" / "schedule_write.py").write_text(
        "import app.services.schedule_store\n"
    )
    for relative, body in extra.items():
        (root / relative).write_text(body)
    (root / ".importlinter").write_text((SERVICE_ROOT / ".importlinter").read_text())


def _lint_imports(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [str(BIN / "lint-imports")],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def test_clean_tree_is_accepted(tmp_path: Path) -> None:
    _make_tree(tmp_path, {})
    result = _lint_imports(tmp_path)
    assert result.returncode == 0, result.stdout


@pytest.mark.parametrize(
    ("file", "source"),
    [
        ("app/domain/bad.py", "import fastapi\n"),
        ("app/domain/bad.py", "import app.services\n"),
        ("app/services/bad.py", "import sqlalchemy\n"),
        ("app/services/bad.py", "import app.repositories\n"),
        ("app/services/bad.py", "import app.api\n"),
        ("app/api/bad.py", "import app.repositories\n"),
        ("app/api/bad.py", "import app.clients\n"),
        ("app/repositories/bad.py", "import app.api\n"),
        ("app/schemas/bad.py", "import app.services\n"),
        ("app/api/bad.py", "import app.settings\n"),
        ("app/services/bad.py", "import app.settings\n"),
        ("app/clients/bad.py", "import app.settings\n"),
        ("app/api/bad.py", "import app.container\n"),
        # Spine AD-4: nothing else may write an event around the engine and the lock.
        ("app/services/bad.py", "import app.services.schedule_store\n"),
        ("app/services/bad.py", "from app.services.schedule_store import EventWriter\n"),
        ("app/api/bad.py", "import app.services.schedule_store\n"),
        ("app/repositories/bad.py", "import app.services.schedule_store\n"),
        ("app/repositories/bad.py", "import app.main\n"),
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


@pytest.mark.parametrize("layer", ["domain", "services"])
@pytest.mark.parametrize(
    "source",
    [
        "import datetime\nvalue = datetime.datetime.now()\n",
        "from datetime import datetime\nvalue = datetime.now()\n",
        "import os\nvalue = os.environ\n",
        "import os\nvalue = os.getenv('A')\n",
        "import uuid\nvalue = uuid.uuid4()\n",
        "import time\nvalue = time.time()\n",
    ],
)
def test_ambient_state_is_banned_in_pure_layers(layer: str, source: str) -> None:
    assert "TID251" in _ruff(f"app/{layer}/probe.py", source)


def test_ambient_state_is_allowed_in_adapters() -> None:
    source = "import datetime\nvalue = datetime.datetime.now()\n"
    assert "TID251" not in _ruff("app/clients/probe.py", source)
