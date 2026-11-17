"""`bawwab ui`: a local, bilingual (Arabic/English) app in your browser.

Security (the UI can change agent configs, so a random website must not be able to drive it):
  * binds to 127.0.0.1 only;
  * a fresh random token per launch; every /api call must send it in the X-Bawwab-Token header
    (custom headers cannot be sent cross-site without a CORS preflight, which this server never allows);
  * the Host header must be 127.0.0.1:<port> or localhost:<port> (DNS-rebinding defence);
  * a request with a foreign Origin header is refused;
  * strict Content-Security-Policy; static files come from a fixed whitelist.
Every action calls the same functions as the CLI (discover, scan, protect, unprotect, policy).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import threading
import time
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from bawwab import __version__

STATIC = Path(__file__).parent / "static"
FILES = {"/": ("index.html", "text/html; charset=utf-8"), "/index.html": ("index.html", "text/html; charset=utf-8"),
         "/app.js": ("app.js", "text/javascript; charset=utf-8"), "/app.css": ("app.css", "text/css; charset=utf-8"),
         "/logo.svg": ("logo.svg", "image/svg+xml")}
MAX_BODY = 2_000_000
CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; "
       "base-uri 'none'; form-action 'none'; frame-ancestors 'none'")


class Refused(Exception):
    def __init__(self, code: int, msg: str):
        super().__init__(msg)
        self.code = code


class App:
    """State + actions behind the HTTP API (kept separate so it can be tested directly)."""

    def __init__(self, home: Path, project: Path | None, policy_path: Path | None = None) -> None:
        self.home = Path(home)
        self.project = project
        self.policy_path = Path(policy_path or self.home / ".bawwab" / "policy.json")
        self.token = secrets.token_urlsafe(32)

    # -- helpers ----------------------------------------------------------
    def _plan(self, body: dict):
        from bawwab import protect as P
        mechs = tuple(body.get("mechanisms") or ()) or None
        agents = tuple(body.get("agents") or ()) or None
        return P.make_plan(self.home, self.project, agents, mechs, self.policy_path)

    @staticmethod
    def plan_hash(plan) -> str:
        h = hashlib.sha256()
        for c in plan.changes:
            for part in (str(c.path), c.before or "\0", c.after):
                h.update(hashlib.sha256(part.encode("utf-8")).digest())
        return h.hexdigest()

    def _render_plan(self, plan) -> dict:
        from bawwab.redact import display_path, mask_diff_line
        mask = {"masked": 0}
        changes = []
        for c in plan.changes:
            diff = [mask_diff_line(l, mask) for l in c.diff(self.home).splitlines()]
            changes.append({"path": display_path(c.path, self.home), "agent": c.agent, "mechanism": c.mechanism,
                            "summary": c.summary, "diff": diff, "new_file": c.before is None})
        return {"changes": changes, "notes": plan.notes, "masked": mask["masked"], "plan_hash": self.plan_hash(plan)}

    def _policy(self) -> tuple[dict, bool, str | None]:
        from bawwab.policy import DEFAULT_POLICY, PolicyError, load_policy
        if not self.policy_path.exists():
            return dict(DEFAULT_POLICY), False, None
        try:
            return load_policy(self.policy_path), True, None
        except PolicyError as exc:
            return dict(DEFAULT_POLICY), True, str(exc)

    # -- actions ----------------------------------------------------------
    def status(self) -> dict:
        from bawwab.discover import discover
        from bawwab.protect import list_backups
        from bawwab.registry import current_os, load_registry
        from bawwab.redact import display_path
        res = discover(self.home, self.project)
        pol, exists, err = self._policy()
        reg = load_registry()
        return {"version": __version__, "os": current_os(), "home": str(self.home),
                "project": str(self.project) if self.project else None,
                "discover": res, "policy": pol, "policy_exists": exists, "policy_error": err,
                "policy_path": display_path(self.policy_path, self.home), "backups": list_backups(self.home),
                "registry": {"agents": [{k: a[k] for k in ("id", "name", "support", "docs", "mechanisms")}
                                        | {"real_cli_check": a.get("real_cli_check", {})} for a in reg["agents"]],
                             "not_supported": reg["not_supported"], "verified_on": reg["verified_on"]}}

    def scan(self, body: dict) -> dict:
        from hares.skillscan.scanner import scan_path, scan_text
        allow = tuple(a.strip().lower() for a in str(body.get("allow", "")).split(",") if a.strip())
        if body.get("path"):
            p = Path(os.path.expanduser(str(body["path"])))
            if not p.exists():
                raise Refused(400, "path not found")
            return scan_path(p, allow)
        text = str(body.get("text", ""))[:MAX_BODY]
        if not text.strip():
            raise Refused(400, "nothing to scan")
        return scan_text(text, str(body.get("name") or "pasted text")[:120], allow)

    def plan(self, body: dict) -> dict:
        return self._render_plan(self._plan(body))

    def apply(self, body: dict) -> dict:
        from bawwab import protect as P
        if body.get("confirm") != P.APPLY_WORD:
            raise Refused(400, f"type {P.APPLY_WORD} to confirm")
        plan = self._plan(body)
        if self.plan_hash(plan) != body.get("plan_hash"):
            raise Refused(409, "the files changed since the preview; preview again")
        return P.apply_plan(plan, P.APPLY_WORD)

    def restore_plan(self, body: dict) -> dict:
        from bawwab import protect as P
        from bawwab.redact import mask_diff_line
        bdir, actions, problems = P.plan_restore(self.home, body.get("backup"), bool(body.get("force")))
        mask = {"masked": 0}
        diff = [mask_diff_line(l, mask) for l in P.render_restore(self.home, actions).splitlines()]
        return {"backup": bdir.name, "diff": diff, "problems": problems, "files": len(actions)}

    def restore(self, body: dict) -> dict:
        from bawwab import protect as P
        if body.get("confirm") != P.RESTORE_WORD:
            raise Refused(400, f"type {P.RESTORE_WORD} to confirm")
        bdir, actions, problems = P.plan_restore(self.home, body.get("backup"), bool(body.get("force")))
        try:
            n = P.apply_restore(self.home, actions, problems, P.RESTORE_WORD, bool(body.get("force")))
        except RuntimeError as exc:
            raise Refused(409, str(exc)) from exc
        return {"restored": n, "backup": bdir.name}

    def save_policy(self, body: dict) -> dict:
        from bawwab.policy import PolicyError, validate_policy
        try:
            pol = validate_policy(body.get("policy"))
        except PolicyError as exc:
            raise Refused(400, str(exc)) from exc
        backup = None
        if self.policy_path.exists():
            bdir = self.home / ".bawwab" / "backups"
            bdir.mkdir(parents=True, exist_ok=True)
            backup = bdir / f"policy-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}.json"
            backup.write_bytes(self.policy_path.read_bytes())
        self.policy_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.policy_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(pol, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, self.policy_path)
        return {"saved": True, "previous_backup": str(backup) if backup else None}

    def check(self, body: dict) -> dict:
        from bawwab.policy import evaluate
        pol = self._policy()[0] if body.get("policy") is None else body["policy"]
        from bawwab.policy import validate_policy
        pol = validate_policy(pol)
        tainted = set(body.get("tainted") or [])
        args = body.get("args") or {}
        if not isinstance(args, dict):
            raise Refused(400, "args must be an object")
        return evaluate(str(body.get("tool", "")), args, pol, self.home, tainted).to_dict()

    def activity(self) -> dict:
        pol = self._policy()[0]
        lf = pol.get("log_file") or ""
        p = Path(str(self.home) + lf[1:]) if lf.startswith("~") else Path(lf) if lf else None
        rows = []
        if p and p.exists():
            for line in p.read_text(encoding="utf-8", errors="replace").splitlines()[-300:]:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return {"rows": list(reversed(rows))}


ROUTES_GET = {"/api/status": "status", "/api/activity": "activity"}
ROUTES_POST = {"/api/scan": "scan", "/api/protect/plan": "plan", "/api/protect/apply": "apply",
               "/api/restore/plan": "restore_plan", "/api/restore/apply": "restore", "/api/policy": "save_policy",
               "/api/policy/check": "check"}


def make_handler(app: App, port_ref: dict):
    class Handler(BaseHTTPRequestHandler):
        server_version = "bawwab-ui"

        def log_message(self, *a):
            pass

        def _send(self, code, body: bytes, ctype: str):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Content-Security-Policy", CSP)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code, obj):
            self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def _guard(self, api: bool):
            port = port_ref["port"]
            host = (self.headers.get("Host") or "").lower()
            if host not in (f"127.0.0.1:{port}", f"localhost:{port}"):
                raise Refused(403, "bad Host header")
            origin = self.headers.get("Origin")
            if origin and origin not in (f"http://127.0.0.1:{port}", f"http://localhost:{port}"):
                raise Refused(403, "foreign origin")
            if api and not hmac.compare_digest(self.headers.get("X-Bawwab-Token", ""), app.token):
                raise Refused(403, "missing or wrong token")

        def _dispatch(self, method: str):
            path = self.path.split("?")[0].split("#")[0]
            try:
                if path in FILES and method == "GET":
                    self._guard(api=False)
                    name, ctype = FILES[path]
                    return self._send(200, (STATIC / name).read_bytes(), ctype)
                routes = ROUTES_GET if method == "GET" else ROUTES_POST
                if path not in routes:
                    return self._json(404, {"error": "not found"})
                self._guard(api=True)
                body = {}
                if method == "POST":
                    n = int(self.headers.get("Content-Length", "0") or 0)
                    if n > MAX_BODY:
                        raise Refused(413, "request too large")
                    try:
                        body = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        raise Refused(400, "invalid JSON")
                    if not isinstance(body, dict):
                        raise Refused(400, "JSON object expected")
                fn = getattr(app, routes[path])
                return self._json(200, fn(body) if method == "POST" else fn())
            except Refused as exc:
                return self._json(exc.code, {"error": str(exc)})
            except (PermissionError, FileNotFoundError) as exc:
                return self._json(400, {"error": str(exc)})
            except Exception as exc:  # pragma: no cover - surfaced to the UI
                traceback.print_exc()
                return self._json(500, {"error": f"{type(exc).__name__}: {exc}"})

        def do_GET(self):
            self._dispatch("GET")

        def do_POST(self):
            self._dispatch("POST")

    return Handler


def make_server(app: App, port: int = 0) -> ThreadingHTTPServer:
    ref = {"port": port}
    srv = ThreadingHTTPServer(("127.0.0.1", port), make_handler(app, ref))
    ref["port"] = srv.server_address[1]
    return srv


def serve(home: Path, project: Path | None, port: int = 8777, open_browser: bool = True) -> int:
    app = App(home, project)
    try:
        srv = make_server(app, port)
    except OSError:
        srv = make_server(app, 0)          # port busy: pick a free one
    url = f"http://127.0.0.1:{srv.server_address[1]}/#token={app.token}"
    print("Bawwab UI is running on this computer only.")
    print(f"Open: {url}")
    print("Press Ctrl+C to stop. (The link contains a one-time secret; do not share it.)")
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0
