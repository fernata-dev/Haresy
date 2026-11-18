import http.client
import json
import threading
from pathlib import Path

import pytest

from bawwab.testing.fake_home import build
from bawwab.ui.server import App, Refused, make_server
from bawwab_helpers import SECRETS, tree_digest

WEB = Path(__file__).resolve().parents[1] / "src" / "bawwab" / "web"


@pytest.fixture
def fake(tmp_path):
    home, project = build(tmp_path)
    return tmp_path, home, project


@pytest.fixture
def served(fake):
    root, home, project = fake
    app = App(home, project)
    srv = make_server(app, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield app, srv.server_address[1], root, home
    srv.shutdown()


def req(port, method, path, body=None, headers=None):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=20)
    h = {"Host": f"127.0.0.1:{port}"}
    h.update(headers or {})
    data = json.dumps(body).encode() if body is not None else None
    if data is not None:
        h["Content-Type"] = "application/json"
    c.request(method, path, body=data, headers=h)
    r = c.getresponse()
    raw = r.read()
    return r.status, dict(r.getheaders()), raw


def test_static_page_has_strict_csp_and_no_inline_code(served):
    app, port, *_ = served
    code, headers, body = req(port, "GET", "/")
    html = body.decode("utf-8")
    csp = headers["Content-Security-Policy"]
    assert code == 200 and "script-src 'self'" in csp and "'unsafe-inline'" not in csp and "frame-ancestors 'none'" in csp
    assert 'dir="rtl"' in html and '<script type="module" src="app/main.js"></script>' in html
    assert "style=" not in html and "onclick=" not in html
    for path in ("/app/main.js", "/engine/check.js", "/engine/worker.js", "/sw.js", "/manifest.webmanifest",
                 "/fonts/plex-arabic-arabic-400.woff2", "/samples/hidden.docx"):
        assert req(port, "GET", path)[0] == 200, path
    for bad in ("/../server.py", "/app/../../ui/server.py", "/%2e%2e/server.py", "/web/index.html", "/fonts/OFL.txt/x"):
        assert req(port, "GET", bad)[0] == 404, bad


def test_api_needs_token_right_host_and_no_foreign_origin(served):
    app, port, *_ = served
    tok = {"X-Bawwab-Token": app.token}
    assert req(port, "GET", "/api/status")[0] == 403                                   # no token
    assert req(port, "GET", "/api/status", headers={"X-Bawwab-Token": "wrong"})[0] == 403
    assert req(port, "GET", "/api/status", headers={**tok, "Host": "evil.example:80"})[0] == 403   # DNS rebinding
    assert req(port, "POST", "/api/policy/check", {"tool": "x"},
               headers={**tok, "Origin": "https://evil.example"})[0] == 403
    code, _, body = req(port, "GET", "/api/status", headers=tok)
    st = json.loads(body)
    assert code == 200 and st["discover"]["summary"]["skills_high_risk"] == 1
    for s in SECRETS:
        assert s not in body.decode("utf-8")
    assert req(port, "POST", "/api/scan", headers=tok, body={"text": "x" * 10})[0] == 200
    # declare an oversized body but send a small one: the server must refuse from the header alone
    # (sending 2 MB races with the server closing early: BrokenPipe on some OSes, found by CI)
    assert req(port, "POST", "/api/scan", {"text": "x"}, headers={**tok, "Content-Length": "2100000"})[0] == 413


def test_protect_apply_needs_word_and_matching_preview_then_restore(fake):
    root, home, project = fake
    app = App(home, project)
    plan = app.plan({})
    assert plan["changes"] and plan["plan_hash"]
    assert all(s not in json.dumps(plan) for s in SECRETS)
    with pytest.raises(Refused):
        app.apply({"confirm": "apply", "plan_hash": plan["plan_hash"]})
    (home / ".gemini" / "settings.json").write_text('{"mcpServers": {}}\n', encoding="utf-8")
    with pytest.raises(Refused) as e:
        app.apply({"confirm": "APPLY", "plan_hash": plan["plan_hash"]})     # files changed since preview
    assert e.value.code == 409
    before = {k: v[0] for k, v in tree_digest(root, exclude=".bawwab").items()}   # state the user approved
    plan = app.plan({})
    res = app.apply({"confirm": "APPLY", "plan_hash": plan["plan_hash"]})
    assert res["applied"] >= 3
    assert app.status()["discover"]["summary"]["stdio_servers_unprotected"] == 0
    rp = app.restore_plan({})
    assert rp["problems"] == [] and rp["files"] == res["applied"]
    with pytest.raises(Refused):
        app.restore({"confirm": "restore"})
    app.restore({"confirm": "RESTORE"})
    assert {k: v[0] for k, v in tree_digest(root, exclude=".bawwab").items()} == before   # byte-identical


def test_policy_save_validates_and_backs_up(fake):
    root, home, project = fake
    app = App(home, project)
    with pytest.raises(Refused):
        app.save_policy({"policy": {"version": 1, "destination_mode": "everything"}})
    pol = app.status()["policy"]
    pol["destination_mode"] = "taint"
    assert app.save_policy({"policy": pol})["previous_backup"] is None
    pol["allowed_hosts"].append("github.com")
    r = app.save_policy({"policy": pol})
    assert r["previous_backup"] and Path(r["previous_backup"]).exists()
    assert app.status()["policy"]["allowed_hosts"][-1] == "github.com"


def test_check_scan_and_activity(fake):
    root, home, project = fake
    app = App(home, project)
    d = app.check({"tool": "fetch", "args": {"url": "https://gіthub.com/login"}})
    assert not d["allowed"] and d["hosts"] == ["xn--gthub-n2e.com"]
    d = app.check({"tool": "fetch", "args": {"url": "https://collector.test.local"},
                   "policy": {"version": 1, "destination_mode": "taint"}, "tainted": ["collector.test.local"]})
    assert d["rule"] == "tainted_destination"
    rep = app.scan({"path": str(home / ".claude" / "skills" / "pdf-helper" / "SKILL.md")})
    assert rep["verdict"] == "high-risk"
    assert app.scan({"path": "~/.claude/skills/pdf-helper/SKILL.md"})["verdict"] == "high-risk"   # ~ = app home
    with pytest.raises(Refused):
        app.scan({"path": str(home / "missing.md")})
    with pytest.raises(Refused):
        app.check({"tool": "x", "args": [1, 2]})
    assert app.activity() == {"rows": []}


@pytest.mark.skipif(not __import__("sys").platform.startswith("linux"), reason="launcher is Linux-only")
def test_linux_launcher_is_opt_in_and_only_touches_its_own_files(tmp_path, monkeypatch, capsys):
    from bawwab.cli import main
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    home = tmp_path / "h"
    home.mkdir()
    assert main(["shortcut", "--home", str(home), "--dry-run"]) == 0
    assert "Exec=" in capsys.readouterr().out and not (home / ".local").exists()
    assert main(["shortcut", "--home", str(home)]) == 0
    desk = home / ".local/share/applications/bawwab.desktop"
    text = desk.read_text(encoding="utf-8")
    assert "-m bawwab ui" in text and "Name[ar]=بوّاب" in text and (home / ".local/share/icons/hicolor/scalable/apps/bawwab.svg").exists()
    other = home / ".local/share/applications/other.desktop"
    other.write_text("[Desktop Entry]\nName=Other\n", encoding="utf-8")
    assert main(["shortcut", "--home", str(home), "--remove"]) == 0
    assert not desk.exists() and other.exists()
    desk.write_text("[Desktop Entry]\nName=Mine\n", encoding="utf-8")        # not ours: never overwritten
    assert main(["shortcut", "--home", str(home)]) == 1 and "Mine" in desk.read_text(encoding="utf-8")
