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
