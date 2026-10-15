from __future__ import annotations

import stat
import zipfile
from pathlib import Path

import pytest

from tools.release_verify import (
    MAX_RELEASE_TOTAL_BYTES,
    _extract_release_archive,
)


def _archive(path: Path, entries: list[tuple[str, bytes]]) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in entries:
            archive.writestr(name, data)
    return path


def test_release_archive_extracts_normal_project_files(tmp_path):
    archive = _archive(
        tmp_path / "release.zip",
        [
            ("AI-STORY-ENGINE/engine/__init__.py", b"__version__ = '1.1.4'"),
            ("AI-STORY-ENGINE/tests/test_example.py", b"def test_ok(): pass"),
        ],
    )
    destination = tmp_path / "extract"
    _extract_release_archive(archive, destination)
    assert (destination / "AI-STORY-ENGINE/engine/__init__.py").read_bytes() == b"__version__ = '1.1.4'"
    assert (destination / "AI-STORY-ENGINE/tests/test_example.py").is_file()


@pytest.mark.parametrize("name", [
    "../outside.txt",
    "..\\outside.txt",
    "/absolute.txt",
    "C:\\outside.txt",
    "folder/../../outside.txt",
])
def test_release_archive_rejects_unsafe_paths(tmp_path, name):
    archive = _archive(tmp_path / "unsafe.zip", [(name, b"bad")])
    destination = tmp_path / "extract"
    with pytest.raises(ValueError, match="unsafe|traversal"):
        _extract_release_archive(archive, destination)
    assert not (tmp_path / "outside.txt").exists()


def test_release_archive_rejects_duplicate_casefolded_paths(tmp_path):
    archive = _archive(tmp_path / "duplicate.zip", [
        ("project/README.md", b"one"),
        ("project/readme.md", b"two"),
    ])
    with pytest.raises(ValueError, match="duplicate"):
        _extract_release_archive(archive, tmp_path / "extract")


def test_release_archive_rejects_symlink_members(tmp_path):
    archive_path = tmp_path / "symlink.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        info = zipfile.ZipInfo("project/link")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(info, b"../outside.txt")
    with pytest.raises(ValueError, match="non-regular"):
        _extract_release_archive(archive_path, tmp_path / "extract")


def test_release_archive_rejects_expansion_above_total_limit(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.release_verify.MAX_RELEASE_TOTAL_BYTES", 10)
    archive = _archive(tmp_path / "large.zip", [("project/file.bin", b"x" * 11)])
    with pytest.raises(ValueError, match="expands beyond"):
        _extract_release_archive(archive, tmp_path / "extract")
