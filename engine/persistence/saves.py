"""Save slots (Phase 2 scope: single-slot API, slot parameter ready for Phase 8).

Scenario isolation: the slot records its scenario_id; loading into a session
with a different scenario_id is an explicit SaveError, never a silent merge.
"""

from __future__ import annotations

import os
import json
import shutil
from pathlib import Path

from engine.ai.adapter_base import AIAdapter
from engine.core.game import GameSession
from engine.core.invariants import check_invariants
from engine.persistence.db import SaveError, SaveSlotMetadata, read_save, read_slot_metadata, write_save
from engine.scenario.configuration import ScenarioConfiguration
from engine.scenario.context import ScenarioContext

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def default_save_dir() -> Path:
    """Return a writable default save directory on desktop and Android.

    Packaged Android applications must not write beside bundled Python source.
    python-for-android exposes ``android.storage.app_storage_path`` for the
    app-private writable directory.  The import stays lazy so desktop/Termux
    development has no Android dependency.
    """
    if os.environ.get("ANDROID_ARGUMENT"):
        try:
            from android.storage import app_storage_path
        except ImportError:
            # Keep the engine importable in Android-like test environments
            # where the p4a runtime module is not installed.
            return Path.home() / ".rpg_engine" / "saves"
        return Path(app_storage_path()) / "saves"
    return PROJECT_ROOT / "saves"

DEMO_SCENARIO_ID = "demo-bootstrap"


def slot_path(slot: str, save_dir: Path | None = None) -> Path:
    if (not slot or slot.startswith(".") or ".." in slot
            or any(ch in slot for ch in "/\\:")):
        raise SaveError(f"invalid save slot name: {slot!r}")
    return (save_dir or default_save_dir()) / f"{slot}.db"


def backup_path(slot: str, save_dir: Path | None = None) -> Path:
    """Return the explicit recovery backup path for a save slot."""
    return slot_path(slot, save_dir).with_suffix(".db.bak")


def save_session(session: GameSession, slot: str = "slot1",
                 save_dir: Path | None = None,
                 scenario_id: str | None = None,
                 scenario_config: ScenarioConfiguration | None = None,
                 campaign_id: str | None = None, campaign_name: str | None = None) -> Path:
    path = slot_path(slot, save_dir)
    runtime_config = scenario_config or session.scenario_configuration
    if scenario_id is None:
        scenario_id = runtime_config.scenario_id if runtime_config is not None else DEMO_SCENARIO_ID
    if runtime_config is not None and runtime_config.scenario_id != scenario_id:
        raise SaveError("scenario_id does not match session scenario configuration")
    write_save(
        path, session.state, session.clock.turn,
        session.recent_turns, scenario_id,
        memory=session.memory,
        scenario_config=runtime_config.to_dict() if runtime_config is not None else None,
        campaign_id=campaign_id, campaign_name=campaign_name,
        recovery_checkpoint=session.export_recovery_checkpoint(),
    )
    return path


def list_save_slots(save_dir: Path | None = None) -> list[SaveSlotMetadata]:
    """List campaign slots without recovering, deleting, or mutating any save."""
    directory = save_dir or default_save_dir()
    if not directory.exists():
        return []
    slots = []
    for path in sorted(directory.glob("*.db")):
        slots.append(read_slot_metadata(path))
    return slots


def load_session(slot: str = "slot1", save_dir: Path | None = None,
                 adapter: AIAdapter | None = None,
                 scenario_id: str = DEMO_SCENARIO_ID,
                 expected_config: ScenarioConfiguration | None = None,
                 scenario_registry=None, scenario_retriever=None,
                 scenario_context: ScenarioContext | None = None,
                 recover: bool = False) -> GameSession:
    path = slot_path(slot, save_dir)
    try:
        state, turn, recent, header, memory = read_save(path)
    except SaveError:
        if not recover or not backup_path(slot, save_dir).exists():
            raise
        restore_backup(slot, save_dir)
        state, turn, recent, header, memory = read_save(path)
    if header["scenario_id"] != scenario_id:
        raise SaveError(
            f"save belongs to scenario '{header['scenario_id']}', "
            f"not '{scenario_id}' — refusing to mix scenarios")
    saved_config = None
    raw_config = header.get("scenario_config", "")
    if raw_config:
        try:
            saved_config = ScenarioConfiguration.from_dict(json.loads(raw_config))
        except Exception as exc:
            raise SaveError(f"corrupt scenario configuration: {exc}") from exc
    if scenario_context is not None:
        if any(x is not None for x in (expected_config, scenario_registry, scenario_retriever)):
            raise SaveError("scenario_context cannot be combined with individual scenario wiring")
        if scenario_context.pack.scenario_id != scenario_id:
            raise SaveError("scenario context belongs to a different scenario")
        expected_config = scenario_context.configuration
        scenario_registry = scenario_context.registry
        scenario_retriever = scenario_context.retriever
    elif (scenario_registry is None) != (scenario_retriever is None):
        raise SaveError("scenario_registry and scenario_retriever must be supplied together")

    if expected_config is not None:
        if saved_config is None:
            raise SaveError("save has no scenario configuration")
        if saved_config != expected_config:
            raise SaveError("save scenario configuration does not match requested configuration")
    elif saved_config is not None and scenario_retriever is not None:
        try:
            saved_config.validate_against(scenario_retriever.scenario_pack)
        except Exception as exc:
            raise SaveError(f"save scenario configuration is invalid for loaded scenario: {exc}") from exc
    runtime_config = expected_config if expected_config is not None else saved_config
    check_invariants(state)
    if runtime_config is not None and scenario_registry is not None and scenario_retriever is not None:
        context = ScenarioContext(
            scenario_retriever.scenario_pack, runtime_config
        )
        session = GameSession(
            state=state, adapter=adapter, memory=memory, scenario_context=context
        )
    else:
        session = GameSession(state=state, adapter=adapter, memory=memory)
    session.clock.turn = turn
    session.recent_turns = recent
    raw_checkpoint = header.get("recovery_checkpoint", "")
    if raw_checkpoint:
        try:
            session.import_recovery_checkpoint(json.loads(raw_checkpoint))
        except Exception as exc:
            raise SaveError(f"corrupt recovery checkpoint: {exc}") from exc
    return session


def restore_backup(slot: str = "slot1", save_dir: Path | None = None) -> Path:
    """Restore the last known-good backup over the primary save.

    Recovery is explicit: callers must opt in with ``recover=True`` on load or
    call this function directly. The backup is never silently selected.
    """
    primary = slot_path(slot, save_dir)
    backup = backup_path(slot, save_dir)
    if not backup.exists():
        raise SaveError(f"no recovery backup at {backup}")
    tmp = primary.with_suffix(".db.recovery")
    try:
        shutil.copy2(backup, tmp)
        # Verify the copied database before replacing the primary.
        read_save(tmp)
        os.replace(tmp, primary)
    except Exception as exc:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        if isinstance(exc, SaveError):
            raise
        raise SaveError(f"failed to restore save backup: {exc}") from exc
    return primary


def delete_slot(slot: str = "slot1", save_dir: Path | None = None) -> bool:
    """Delete a complete campaign slot, including its recovery backup."""
    path = slot_path(slot, save_dir)
    backup = backup_path(slot, save_dir)
    deleted = False
    for candidate in (path, backup):
        if candidate.exists():
            candidate.unlink()
            deleted = True
    return deleted
