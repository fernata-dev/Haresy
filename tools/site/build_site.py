"""Build the Bawwab website from site/template.html and tools/site/content.py.

  python tools/site/build_site.py              regenerate site/index.html, site/en/index.html,
                                              site/assets/demo-data.js and site/assets/img/*
  python tools/site/build_site.py --check      fail if the committed pages are stale
  python tools/site/build_site.py --out DIR    also assemble a deployable folder: the site at DIR/,
                                              the phone/desktop app (src/bawwab/web) at DIR/app/

Every decision shown in the demo is computed here by Bawwab's own policy code
(bawwab.policy.evaluate) and the frozen text scanner (D2); nothing is typed by hand.
"""
from __future__ import annotations

import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import content as C  # noqa: E402
from bawwab.policy import DEFAULT_POLICY, evaluate, hosts_from_content  # noqa: E402
from hares.defenses.d2_scanner import D2Scanner  # noqa: E402

SITE = ROOT / "site"
DEMO_HOME = Path("/home/demo")          # fixed, so the build is reproducible on any machine


def demo_data() -> dict:
    d2 = D2Scanner()
    out = []
    for sc in C.SCENARIOS:
        pol = dict(DEFAULT_POLICY, **sc["policy"])
        variants = []
        for code, text in sc["variants"]:
            tainted = hosts_from_content(text) if pol["destination_mode"] == "taint" else set()
            tool, args = sc["call"]
            dec = evaluate(tool, args, pol, DEMO_HOME, tainted).to_dict()
            v = d2.screen(text, sc["source"]).to_dict()
            variants.append({"code": code, "text": text, "tainted": sorted(tainted), "decision": dec,
                             "d2": {"flagged": v["flagged"], "score": v["score"],
                                    "rules": sorted({r["rule"] for r in v["reasons"]})}})
        item = {"id": sc["id"], "source": sc["source"], "mode": pol["destination_mode"],
                "call": {"tool": sc["call"][0], "args": sc["call"][1]}, "variants": variants}
        if "also" in sc:
            tool, args = sc["also"]
            item["also"] = {"tool": tool, "args": args, "decision": evaluate(tool, args, pol, DEMO_HOME, set()).to_dict()}
        out.append(item)
    return {"scenarios": out, "policy_default": {k: DEFAULT_POLICY[k] for k in ("allowed_hosts", "secret_paths")}}


def ledger_lines(data: dict) -> list[str]:
    """The hero's decision log: one line per scenario/variant, from the same computed data."""
    lines = []
    for sc in data["scenarios"]:
        for v in sc["variants"][:2]:
            d = v["decision"]
            target = ", ".join(d["hosts"]) or next(iter(sc["call"]["args"].values()))
            mark = "ALLOW" if d["allowed"] else "BLOCK"
            lines.append(f"{mark} {sc['call']['tool']} → {target} · {d['rule'] or 'ok'} [{v['code']}]")
    return lines


def _os_blocks(t: dict) -> tuple[str, str]:
    tabs, panels = [], []
    for i, os_id in enumerate(("arch", "debian", "mac", "win")):
        sel = "true" if i == 0 else "false"
        tabs.append(f'<button type="button" role="tab" id="tab-{os_id}" aria-controls="os-{os_id}" aria-selected="{sel}" '
                    f'tabindex="{0 if i == 0 else -1}">{html.escape(t["os_" + os_id])}</button>')
        cmds = C.INSTALL[os_id] + ["bawwab"]
        body = "\n".join(f'<span class="c">$</span> {html.escape(c)}' for c in cmds)
        hidden = "" if i == 0 else " hidden"
        panels.append(f'<div class="os-panel" role="tabpanel" id="os-{os_id}" aria-labelledby="tab-{os_id}"{hidden}>'
                      f'<pre class="term ltr" data-copy="{html.escape(chr(10).join(cmds))}">{body}</pre>'
                      f'<button class="copy on-term" type="button" data-copy-target data-label="{html.escape(t["copy"])}" '
                      f'data-done="{html.escape(t["copied"])}">{html.escape(t["copy"])}</button></div>')
    return "".join(tabs), "\n      ".join(panels)


def render(lang: str, data: dict) -> str:
    t = dict(C.T[lang])
    tpl = (SITE / "template.html").read_text(encoding="utf-8")
    tabs, panels = _os_blocks(t)
    lines = ledger_lines(data)
    shown = [l for l in lines if l.startswith("BLOCK")][:6] + [l for l in lines if l.startswith("ALLOW")][:1]   # the door also opens
    ledger = "".join(f'<p class="{"ok" if l.startswith("ALLOW") else "no"}"><b>{l[:5]}</b>{html.escape(l[5:])}</p>' for l in shown)
    values = {
        **{k: html.escape(v) for k, v in t.items()},
        "lang": lang, "dir": "rtl" if lang == "ar" else "ltr", "alt_lang": "en" if lang == "ar" else "ar",
        "root": "" if lang == "ar" else "../", "brand": "بوّاب" if lang == "ar" else "Bawwab",
        "pipx": html.escape(C.PIPX), "pipx_short": html.escape(C.PIPX), "repo": C.REPO,
        "src_owasp": C.SOURCES["owasp"], "src_willison": C.SOURCES["willison"],
        "doc_limits": f"{C.DOC}/docs/LIMITATIONS.md", "doc_install": f"{C.DOC}/docs/INSTALL.md",
        "doc_integrations": f"{C.DOC}/docs/INTEGRATIONS.md", "doc_ai": f"{C.DOC}/docs/AI_PROVENANCE.md",
        "doc_readme": f"{C.DOC}/README.md", "os_tabs": tabs, "os_panels": panels, "ledger_static": ledger,
    }
    out = re.sub(r"\{\{(\w+)\}\}", lambda m: values[m.group(1)], tpl)
    assert "{{" not in out, "unresolved placeholder"
    return "<!-- GENERATED by tools/site/build_site.py from site/template.html. Do not edit. -->\n" + out


def demo_module(data: dict) -> str:
    texts = {lang: {k: v for k, v in C.T[lang].items()
                    if k.startswith(("demo_", "dec_", "src_", "scn_", "v_", "rule_", "mode_", "copy", "copied"))}
             for lang in ("ar", "en")}
    body = json.dumps({"data": data, "text": texts}, ensure_ascii=True, indent=1, sort_keys=True)
    return f"// GENERATED by tools/site/build_site.py (decisions computed by bawwab.policy). Do not edit.\nexport default {body};\n"


def outputs() -> dict[Path, str]:
    data = demo_data()
    return {SITE / "index.html": render("ar", data), SITE / "en" / "index.html": render("en", data),
            SITE / "assets" / "demo-data.js": demo_module(data)}


def images() -> None:
    """Real recordings / app screenshots, resized for the web (proof, not illustration)."""
    from PIL import Image
    dst = SITE / "assets" / "img"
    dst.mkdir(parents=True, exist_ok=True)
    for src, name, width in ((ROOT / "docs/media/08-mcp-proxy-taint.png", "proxy-taint.png", 2056),
                             (ROOT / "docs/media/app/desktop-2-result.png", "desktop-result.png", 1440),
                             (ROOT / "docs/media/app/phone-2-result-ar.png", "phone-result.png", 585)):
        im = Image.open(src).convert("RGB")
        if im.width > width:
            im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
        im.save(dst / name, optimize=True)


def assemble(out: Path) -> None:
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SITE, out, ignore=shutil.ignore_patterns("template.html"))
    shutil.copytree(ROOT / "src" / "bawwab" / "web", out / "app")
    print(f"assembled {out} (site + app/)")


def main(argv: list[str]) -> int:
    outs = outputs()
    if "--check" in argv:
        stale = [str(p.relative_to(ROOT)) for p, text in outs.items()
                 if not p.exists() or p.read_text(encoding="utf-8") != text]
        print("site up to date" if not stale else "site STALE: " + ", ".join(stale))
        return 1 if stale else 0
    for p, text in outs.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    if "--no-images" not in argv:
        images()
    print("wrote site/index.html, site/en/index.html, site/assets/demo-data.js")
    if "--out" in argv:
        assemble(Path(argv[argv.index("--out") + 1]).resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
