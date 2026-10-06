"""Installed scenario management for the application layer.

The manager owns installation metadata and filesystem operations. It never mutates
canonical scenario contents after installation and never mutates GameState.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from uuid import uuid4

from engine.scenario.errors import ScenarioError
from engine.scenario.loader import ScenarioPack, load_scenario

INDEX_NAME = "installed.json"


def default_scenario_dir() -> Path:
    if os.environ.get("ANDROID_ARGUMENT"):
        try:
            from android.storage import app_storage_path
        except ImportError:
            return Path.home() / ".rpg_engine" / "scenarios"
        return Path(app_storage_path()) / "scenarios"
    return Path(__file__).resolve().parents[2] / "scenarios" / "installed"


@dataclass(frozen=True)
class InstalledScenario:
    scenario_id: str
    name: str
    version: str
    path: str
    chapter_count: int


class ScenarioManager:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or default_scenario_dir()
        self.root.mkdir(parents=True, exist_ok=True)
        self._index_path = self.root / INDEX_NAME

    def list_installed(self) -> tuple[InstalledScenario, ...]:
        raw = self._read_index()
        result = []
        for item in raw:
            path = Path(item["path"])
            if not path.exists():
                continue
            result.append(InstalledScenario(
                str(item["scenario_id"]), str(item["name"]), str(item["version"]),
                str(path), int(item.get("chapter_count", 0)),
            ))
        return tuple(result)

    def install(self, archive: Path | str, *, replace: bool = False) -> ScenarioPack:
        archive = Path(archive)
        if not archive.is_file() or not zipfile.is_zipfile(archive):
            raise ScenarioError("scenario import requires a valid ZIP/.rpgscenario.zip archive")
        # Validate the archive before installing anything.
        pack = load_scenario(archive)
        existing = next((x for x in self.list_installed() if x.scenario_id == pack.scenario_id), None)
        if existing and not replace:
            raise ScenarioError(f"scenario already installed: {pack.scenario_id}")

        safe_id = _safe_id(pack.scenario_id)
        existing_path = Path(existing.path) if existing is not None else None
        temp_parent = self.root / ".installing"
        temp_parent.mkdir(exist_ok=True)
        temp_dir = Path(tempfile.mkdtemp(prefix=f"{safe_id}-", dir=temp_parent))
        destination = self.root / f"{safe_id}--{pack.version}-{uuid4().hex}"
        indexed = False
        try:
            _extract_secure(archive, temp_dir)
            installed_pack = load_scenario(temp_dir)
            if (installed_pack.scenario_id, installed_pack.version) != (pack.scenario_id, pack.version):
                raise ScenarioError("scenario changed while being imported")
            os.replace(temp_dir, destination)
            # The index is authoritative. Commit the new installation first;
            # only after that succeeds is it safe to delete the previous pack.
            self._write_index_entry(pack, destination)
            indexed = True
            if existing_path is not None and existing_path != destination and existing_path.exists():
                shutil.rmtree(existing_path)
            return load_scenario(destination)
        except Exception:
            if destination.exists() and not indexed:
                shutil.rmtree(destination, ignore_errors=True)
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            raise
        finally:
            try:
                if temp_parent.exists() and not any(temp_parent.iterdir()):
                    temp_parent.rmdir()
            except OSError:
                pass

    def load(self, scenario_id: str) -> ScenarioPack:
        entry = self._entry(scenario_id)
        if entry is None:
            raise ScenarioError(f"scenario is not installed: {scenario_id}")
        path = Path(entry["path"])
        pack = load_scenario(path)
        if pack.scenario_id != scenario_id:
            raise ScenarioError("installed scenario index does not match pack")
        return pack

    def remove(self, scenario_id: str) -> bool:
        entry = self._entry(scenario_id)
        if entry is None:
            return False
        path = Path(entry["path"])
        # Commit the index removal first so a deletion failure cannot leave an
        # index entry pointing at missing content. A failed cleanup may leave
        # an orphan directory, but the installed-state index stays correct.
        self._write_index([x for x in self._read_index() if x.get("scenario_id") != scenario_id])
        if path.exists():
            shutil.rmtree(path)
        return True

    def _entry(self, scenario_id: str) -> dict | None:
        for item in self._read_index():
            if item.get("scenario_id") == scenario_id:
                return item
        return None

    def _read_index(self) -> list[dict]:
        if not self._index_path.exists():
            return []
        try:
            value = json.loads(self._index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ScenarioError(f"corrupt installed scenario index: {exc}") from exc
        if not isinstance(value, list):
            raise ScenarioError("installed scenario index must be a list")
        return value

    def _write_index_entry(self, pack: ScenarioPack, destination: Path) -> None:
        entries = [x for x in self._read_index() if x.get("scenario_id") != pack.scenario_id]
        entries.append({
            "scenario_id": pack.scenario_id,
            "name": pack.name,
            "version": pack.version,
            "path": str(destination),
            "chapter_count": pack.chapter_manager.chapter_count if pack.chapter_manager else 0,
        })
        self._write_index(entries)

    def _write_index(self, entries: list[dict]) -> None:
        tmp = self._index_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self._index_path)


def _safe_id(value: str) -> str:
    if not value or value in {".", ".."} or any(ch in value for ch in "/\\"):
        raise ScenarioError("scenario_id contains an unsafe path")
    return value


MAX_SCENARIO_ENTRIES = 10_000
MAX_SCENARIO_FILE_BYTES = 32 * 1024 * 1024
MAX_SCENARIO_TOTAL_BYTES = 256 * 1024 * 1024


def _extract_secure(archive_path: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive_path) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_SCENARIO_ENTRIES:
            raise ScenarioError(f"scenario archive has too many entries (max {MAX_SCENARIO_ENTRIES})")
        total_size = 0
        for info in infos:
            if info.file_size > MAX_SCENARIO_FILE_BYTES:
                raise ScenarioError(f"scenario archive file is too large (max {MAX_SCENARIO_FILE_BYTES} bytes): {info.filename!r}")
            total_size += info.file_size
            if total_size > MAX_SCENARIO_TOTAL_BYTES:
                raise ScenarioError(f"scenario archive is too large when unpacked (max {MAX_SCENARIO_TOTAL_BYTES} bytes)")
        for info in infos:
            name = PurePosixPath(info.filename)
            if name.is_absolute() or ".." in name.parts:
                raise ScenarioError(f"unsafe path in scenario archive: {info.filename!r}")
            target = destination.joinpath(*name.parts)
            resolved = target.resolve()
            if destination.resolve() not in resolved.parents and resolved != destination.resolve():
                raise ScenarioError(f"archive extraction escaped destination: {info.filename!r}")
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)
