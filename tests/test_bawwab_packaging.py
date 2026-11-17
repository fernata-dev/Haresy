import subprocess
import sys
import tomllib
from pathlib import Path

from bawwab_helpers import env_with_src

ROOT = Path(__file__).resolve().parents[1]


def test_pyproject_exposes_cli_and_ships_agent_list():
    py = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert py["project"]["name"] == "bawwab"
    assert py["project"]["scripts"]["bawwab"] == "bawwab.cli:main"
    assert "_data/*.json" in py["tool"]["setuptools"]["package-data"]["bawwab"]
    assert py["project"]["dependencies"] == []          # stdlib only


def test_module_entry_point_and_version():
    from bawwab import __version__
    r = subprocess.run([sys.executable, "-m", "bawwab", "--version"], capture_output=True, text=True,
                       env=env_with_src(), timeout=60)
    assert r.returncode == 0 and r.stdout.strip() == f"bawwab {__version__}"


def test_readme_keeps_required_sentence_and_install_command():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Hares reduces the damage an injected instruction can cause; it does not stop a model from following it." in text
    assert "pipx install" in text and "does **not** support \"any AI\"" in text
