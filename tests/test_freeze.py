from hares.eval.freeze import FROZEN_FILES, freeze_status
from hares.util import project_root


def test_frozen_files_exist():
    for rel in FROZEN_FILES:
        assert (project_root() / rel).exists(), rel


def test_freeze_status_shape():
    st = freeze_status()
    assert set(st) >= {"tag", "tag_exists", "files", "ok"}
    if st["tag_exists"]:
        assert set(st["files"]) == set(FROZEN_FILES)


def test_unrecorded_change_is_refused_and_recorded_change_is_listed(tmp_path, monkeypatch):
    import shutil
    import subprocess
    from hares.eval import freeze as F

    st = freeze_status()
    if not st["tag_exists"]:
        return
    assert st["ok"]
    for rec in st["post_freeze_changes"]:
        assert rec["reason"] and rec["sha256"] and "affects_results" in rec
    # simulate an unrecorded edit of a frozen file in a scratch copy of the repo
    repo = tmp_path / "repo"
    subprocess.run(["git", "clone", "-q", str(project_root()), str(repo)], check=True)
    for rel in FROZEN_FILES + (F.RECORDED_CHANGES,):
        src = project_root() / rel
        if src.exists():
            (repo / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, repo / rel)
    monkeypatch.setenv("HARES_ROOT", str(repo))
    assert F.freeze_status()["ok"]
    target = repo / "src/hares/defenses/d2_lexicon.py"
    target.write_text(target.read_text(encoding="utf-8") + "\n# tuned on test\n", encoding="utf-8")
    bad = F.freeze_status()
    assert not bad["ok"] and "not recorded" in bad["reason"]


def test_default_pipeline_makes_no_network_connections(monkeypatch):
    """HARD RULE 2: D4 must not try to download its vocabulary; the simulator touches no network."""
    import socket
    from hares.defenses import d4_cpt, registry
    from hares.agents.obedient_mock import ObedientMock
    from hares.eval import runner
    attempts = []
    real_connect = socket.socket.connect

    def guard(self, addr):
        attempts.append(addr)
        raise OSError("network disabled in test")
    monkeypatch.setattr(socket.socket, "connect", guard)
    monkeypatch.setenv("TIKTOKEN_CACHE_DIR", "/nonexistent-hares-cache")
    d4_cpt._encoding.cache_clear()
    ok, why = registry.availability("D4")
    cases = runner.build_cases("dev", langs=("arz",), encodings=("none",))
    runner.run_matrix(cases, ["D0", "D1", "D2", "D4", "D5"], ObedientMock())
    d4_cpt._encoding.cache_clear()
    monkeypatch.setattr(socket.socket, "connect", real_connect)
    assert attempts == []
    assert not ok and ("not in the local tiktoken cache" in why or "not installed" in why)


def test_freeze_check_falls_back_to_pinned_commit_when_tag_is_missing(tmp_path, monkeypatch):
    import subprocess
    from hares.eval import freeze as F
    if not freeze_status()["tag_exists"]:
        return
    repo = tmp_path / "r"
    subprocess.run(["git", "clone", "-q", str(project_root()), str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "checkout", "-q", "HEAD"], check=True)
    for t in subprocess.run(["git", "-C", str(repo), "tag"], capture_output=True, text=True).stdout.split():
        subprocess.run(["git", "-C", str(repo), "tag", "-d", t], capture_output=True, check=True)
    import shutil
    for rel in FROZEN_FILES + (F.RECORDED_CHANGES, F.PINNED_TAGS):
        if (project_root() / rel).exists():
            shutil.copy(project_root() / rel, repo / rel)
    monkeypatch.setenv("HARES_ROOT", str(repo))
    st = F.freeze_status()
    assert not st["tag_exists"] and st["ok"] and st["resolved_via"] == F.PINNED_TAGS
    assert F.restore_tags() == 0
    st2 = F.freeze_status()
    assert st2["tag_exists"] and st2["ok"]
