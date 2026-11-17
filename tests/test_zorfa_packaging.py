import subprocess
import sys
import tomllib
from pathlib import Path

from zorfa_helpers import env_with_src

ROOT = Path(__file__).resolve().parents[1]


def test_pyproject_exposes_cli_and_ships_agent_list():
    py = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert py["project"]["name"] == "zorfa"
    assert py["project"]["scripts"]["zorfa"] == "zorfa.cli:main"
    assert "_data/*.json" in py["tool"]["setuptools"]["package-data"]["zorfa"]
    assert py["project"]["dependencies"] == []          # stdlib only


def test_module_entry_point_and_version():
    from zorfa import __version__
    r = subprocess.run([sys.executable, "-m", "zorfa", "--version"], capture_output=True, text=True,
                       env=env_with_src(), timeout=60)
    assert r.returncode == 0 and r.stdout.strip() == f"zorfa {__version__}"


def test_readme_keeps_required_sentence_and_install_command():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Hares reduces the damage an injected instruction can cause; it does not stop a model from following it." in text
    assert "pipx install" in text and "does **not** support \"any AI\"" in text
