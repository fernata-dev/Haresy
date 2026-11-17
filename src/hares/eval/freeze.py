"""Check that the content scanners are byte-identical to git tag `freeze-scanner`.

HARD RULE 4: scanners are developed on the dev split only and frozen before
any run on the test split.  This module makes that checkable by a machine.
"""
from __future__ import annotations

import hashlib
import json
import subprocess

from hares.util import project_root

RECORDED_CHANGES = "docs/post_freeze_changes.json"


def recorded_changes() -> list[dict]:
    p = project_root() / RECORDED_CHANGES
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))

FREEZE_TAG = "freeze-scanner"
FROZEN_FILES = (
    "src/hares/attacks/encoders.py",       # removing an encoding a scanner fails on would also be rigging
    "src/hares/defenses/d1_keyword.py",
    "src/hares/defenses/d2_normalizer.py",
    "src/hares/defenses/d2_lexicon.py",
    "src/hares/defenses/d2_scanner.py",
    "src/hares/defenses/d3_llm_judge.py",
    "src/hares/defenses/d4_cpt.py",
)


def _git(*args: str) -> tuple[int, bytes]:
    try:
        p = subprocess.run(["git", *args], cwd=project_root(), capture_output=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return 1, b""
    return p.returncode, p.stdout


def freeze_status() -> dict:
    root = project_root()
    code, out = _git("rev-parse", "--verify", "--quiet", f"refs/tags/{FREEZE_TAG}^{{commit}}")
    status: dict = {"tag": FREEZE_TAG, "tag_exists": code == 0,
                    "tag_commit": out.decode().strip() if code == 0 else None,
                    "files": {}, "ok": False}
    if code != 0:
        status["reason"] = "freeze tag not found"
        return status
    all_same = True
    recorded = {(c["file"], c["sha256"]): c for c in recorded_changes()}
    status["post_freeze_changes"] = []
    for rel in FROZEN_FILES:
        c, blob = _git("show", f"{FREEZE_TAG}:{rel}")
        path = root / rel
        if c != 0:
            same = False
            note = "not present at freeze tag"
        elif not path.exists():
            same = False
            note = "missing in working tree"
        else:
            data = path.read_bytes()
            same = data == blob
            note = "identical" if same else "CHANGED since freeze"
            if not same:
                rec = recorded.get((rel, hashlib.sha256(data).hexdigest()))
                if rec:
                    note = "changed after freeze (recorded: " + rec["reason"][:60] + "...)"
                    status["post_freeze_changes"].append(rec)
                    status["files"][rel] = {"same": False, "recorded": True, "note": note}
                    continue
        status["files"][rel] = {"same": same, "note": note}
        all_same = all_same and same
    status["ok"] = all_same
    status["identical_to_tag"] = all_same and not status["post_freeze_changes"]
    if not all_same:
        status["reason"] = ("frozen files differ from the freeze tag and the change is not recorded in "
                            f"{RECORDED_CHANGES}; see CHANGELOG.md")
    return status
