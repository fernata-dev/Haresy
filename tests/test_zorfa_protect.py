import io
import json

import pytest

from zorfa import protect as P
from zorfa.cli import main
from zorfa.discover import discover
from zorfa.testing.fake_home import build
from zorfa_helpers import SECRETS, tree_digest


@pytest.fixture
def fake(tmp_path):
    home, project = build(tmp_path)
    return tmp_path, home, project


def _files(root):
    return tree_digest(root, exclude=".zorfa")


def test_dry_run_changes_nothing_and_shows_exact_diff_without_secrets(fake, capsys):
    root, home, project = fake
    before = tree_digest(root)
    assert main(["protect", "--dry-run", "--home", str(home), "--project", str(project), "--no-color"]) == 0
    out = capsys.readouterr().out
    assert tree_digest(root) == before
    assert "DRY RUN" in out and "+++ b/~/.claude.json" in out and "+++ b/~/.gemini/settings.json" in out
    assert "mcp-proxy" in out and "hook claude-code" in out
    for s in SECRETS:
        assert s not in out
    assert ".cursor" not in out


def test_diff_masking_of_secret_values():
    from zorfa.redact import mask_diff_line
    st = {"masked": 0}
    assert "ghp_" not in mask_diff_line('       "GITHUB_TOKEN": "ghp_FAKEFAKEFAKEFAKEFAKEFAKEFAKE00",', st)
    assert "$KEY" in mask_diff_line('   "API_KEY": "$KEY"', st)               # a reference, not a secret
    assert "sk-" not in mask_diff_line('+        "sk-FAKEFAKEFAKEFAKEFAKEFAKE",', st)
    mask_diff_line('   "--api-key",', st)
    assert "hunter2" not in mask_diff_line('   "hunter2",', st)                # value after a secret flag
    assert mask_diff_line('   "-y",', st) == '   "-y",'
    assert st["masked"] == 3


def test_apply_requires_confirmation(fake, monkeypatch, capsys):
    root, home, project = fake
    before = tree_digest(root)
    monkeypatch.setattr("sys.stdin", io.StringIO("APPLY\n"))       # not a TTY: typed input is ignored
    assert main(["protect", "--apply", "--home", str(home), "--project", str(project)]) == 3
    assert main(["protect", "--apply", "--confirm", "yes", "--home", str(home), "--project", str(project)]) == 3
    assert tree_digest(root) == before
    with pytest.raises(PermissionError):
        P.apply_plan(P.make_plan(home, project), "apply")


def test_apply_backup_validate_idempotent_and_unprotect_restores_exactly(fake):
    root, home, project = fake
    before = _files(root)
    plan = P.make_plan(home, project)
    assert {c.mechanism for c in plan.changes} == {"policy-file", "pretooluse-hook", "mcp-stdio-proxy"}
    res = P.apply_plan(plan, P.APPLY_WORD)
    man = json.loads((P.backups_dir(home) / res["backup_id"] / "manifest.json").read_text(encoding="utf-8"))
    assert len(man["files"]) == len(plan.changes) and all("sha256_after" in f for f in man["files"])
    cj = json.loads((home / ".claude.json").read_text(encoding="utf-8"))
    gh = cj["mcpServers"]["github"]
    assert gh["args"][-3:] == ["npx", "-y", "@modelcontextprotocol/server-github"]
    assert gh["env"]["GITHUB_PERSONAL_ACCESS_TOKEN"].startswith("ghp_")           # env kept as is
    assert cj["mcpServers"]["docs"]["type"] == "http" and "args" not in cj["mcpServers"]["docs"]
    assert cj["numStartups"] == 12
    assert discover(home, project)["summary"]["stdio_servers_unprotected"] == 0
    assert P.make_plan(home, project).changes == []                                 # idempotent
    bdir, actions, problems = P.plan_restore(home, None)
    assert problems == []
    P.apply_restore(home, actions, problems, P.RESTORE_WORD, False)
    assert {k: v[0] for k, v in _files(root).items()} == {k: v[0] for k, v in before.items()}  # same bytes
    assert not (home / ".zorfa" / "policy.json").exists()


def test_unprotect_refuses_after_user_edits_unless_forced(fake):
    root, home, project = fake
    P.apply_plan(P.make_plan(home, project), P.APPLY_WORD)
    s = home / ".gemini" / "settings.json"
    s.write_text(s.read_text(encoding="utf-8").replace("Default", "Dark"), encoding="utf-8")
    bdir, actions, problems = P.plan_restore(home, None)
    assert any("changed after Zorfa wrote it" in p for p in problems)
    with pytest.raises(RuntimeError):
        P.apply_restore(home, actions, problems, P.RESTORE_WORD, False)
    bdir, actions, problems = P.plan_restore(home, None, force=True)
    P.apply_restore(home, actions, problems, P.RESTORE_WORD, True)
    assert "Default" in s.read_text(encoding="utf-8")


def test_unparseable_and_unsupported_files_are_never_modified(fake):
    root, home, project = fake
    g = home / ".gemini" / "settings.json"
    g.write_text('{"mcpServers": {"w": {"command": "node"}}, // comment\n}', encoding="utf-8")
    cursor_before = (home / ".cursor" / "mcp.json").read_bytes()
    plan = P.make_plan(home, project)
    assert all(c.path != g for c in plan.changes)
    assert any("not valid JSON" in n for n in plan.notes)
    P.apply_plan(plan, P.APPLY_WORD)
    assert g.read_text(encoding="utf-8").startswith('{"mcpServers": {"w": {"command": "node"}}, // comment')
    assert (home / ".cursor" / "mcp.json").read_bytes() == cursor_before


def test_apply_rolls_back_on_failure(fake, monkeypatch):
    root, home, project = fake
    before = _files(root)
    calls = {"n": 0}
    real = P._atomic_write

    def flaky(path, text, mode):
        calls["n"] += 1
        if calls["n"] == 3:
            raise OSError("disk full (simulated)")
        return real(path, text, mode)
    monkeypatch.setattr(P, "_atomic_write", flaky)
    with pytest.raises(OSError):
        P.apply_plan(P.make_plan(home, project), P.APPLY_WORD)
    assert {k: v[0] for k, v in _files(root).items()} == {k: v[0] for k, v in before.items()}


def test_apply_refuses_if_file_changed_after_planning(fake):
    root, home, project = fake
    plan = P.make_plan(home, project)
    (home / ".claude.json").write_text('{"mcpServers": {}}\n', encoding="utf-8")
    with pytest.raises(RuntimeError, match="changed after the plan"):
        P.apply_plan(plan, P.APPLY_WORD)
    assert (home / ".claude.json").read_text(encoding="utf-8") == '{"mcpServers": {}}\n'


def test_hook_only_when_agent_installed_and_not_duplicated(tmp_path):
    home = tmp_path / "h"
    home.mkdir()
    assert P.make_plan(home, None).changes == []                  # no agent installed: nothing to do
    (home / ".claude").mkdir()
    plan = P.make_plan(home, None, mechs=("pretooluse-hook",))
    assert [c.mechanism for c in plan.changes] == ["policy-file", "pretooluse-hook"]
    P.apply_plan(plan, P.APPLY_WORD)
    settings = json.loads((home / ".claude" / "settings.json").read_text(encoding="utf-8"))
    hook = settings["hooks"]["PreToolUse"][0]
    assert hook["matcher"] == "*" and hook["hooks"][0]["type"] == "command"
    assert "zorfa hook claude-code --policy" in hook["hooks"][0]["command"]
    assert P.make_plan(home, None, mechs=("pretooluse-hook",)).changes == []
