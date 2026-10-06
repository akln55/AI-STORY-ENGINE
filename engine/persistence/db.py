"""SQLite persistence layer (contract: docs/DATA_MODELS.md §4).

Save format v5 carries the authoritative game state and memories JSON alongside it.
v1 saves (no memories key) load with an empty MemorySystem.
"""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4
from pathlib import Path

from engine import __version__ as ENGINE_VERSION

from engine.core.state import (
    CharacterState, EventState, GameState, ItemState, NPCGoal, NPCPersonality, NPCState,
    QuestObjective, QuestState, RelationshipState, WorldState,
)
from engine.memory.system import MemorySystem

SAVE_FORMAT_VERSION = 5
# v1 is still readable: missing memories → empty MemorySystem
# v1.3 engine change (NPC personality/goals/fears/preferences): additive only.
# NPCState.personality/goals/fears/preferences are new dict/list keys under
# world.npcs.<id>; a save written by the v1.2 engine simply lacks these keys,
# and state_from_dict() above defaults them (personality=all 50, goals=[],
# fears=[], preferences=[]). No new required key, no changed meaning of any
# existing key -> schema stays backward-compatible. Verified by
# tests/test_persistence.py::test_v1_2_save_loads_with_npc_defaults.
_SUPPORTED_LOAD_VERSIONS = frozenset({1, 2, 3, 4, 5})


class SaveError(Exception):
    """Explicit save/load failure — never a silent merge."""


def _status_to_dict(status):
    return {
        "effect_type": status.effect_type,
        "remaining_turns": status.remaining_turns,
        "potency": status.potency,
        "stacks": status.stacks,
        "max_stacks": status.max_stacks,
        "source_id": status.source_id,
    }


def _status_from_dict(value):
    from engine.core.state import StatusEffectState
    if not isinstance(value, dict):
        raise SaveError("invalid status effect record")
    try:
        return StatusEffectState(
            effect_type=str(value["effect_type"]),
            remaining_turns=int(value["remaining_turns"]),
            potency=int(value.get("potency", 1)),
            stacks=int(value.get("stacks", 1)),
            max_stacks=int(value.get("max_stacks", 1)),
            source_id=(str(value["source_id"]) if value.get("source_id") is not None else None),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise SaveError(f"invalid status effect record: {exc}") from exc


_SCHEMA = """
CREATE TABLE IF NOT EXISTS header (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS game_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    json TEXT NOT NULL
);
"""

_HEADER_KEYS = ("engine_version", "save_format_version", "scenario_id",
                "created", "modified")


@dataclass(frozen=True)
class SaveSlotMetadata:
    """Safe-to-display metadata for one campaign save slot."""

    slot: str
    campaign_id: str | None
    campaign_name: str | None
    scenario_id: str | None
    created: str | None
    modified: str | None
    engine_version: str | None
    save_format_version: int | None
    valid: bool
    error: str | None = None



def _connect(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(str(path))


def state_to_dict(
    state: GameState,
    turn: int,
    recent_turns: list[str],
    memory: MemorySystem | None = None,
) -> dict:
    return {
        "schema": SAVE_FORMAT_VERSION,
        "turn": turn,
        "recent_turns": list(recent_turns),
        "character": {
            "name": state.character.name,
            "hp": state.character.hp,
            "max_hp": state.character.max_hp,
            "stamina": state.character.stamina,
            "max_stamina": state.character.max_stamina,
            "location_id": state.character.location_id,
            "inventory": list(state.character.inventory),
            "attack_power": state.character.attack_power,
            "defense": state.character.defense,
            "level": state.character.level,
            "xp": state.character.xp,
            "xp_to_next": state.character.xp_to_next,
            "realm_id": state.character.realm_id,
            "realm_stage": state.character.realm_stage,
            "techniques": list(state.character.techniques),
            "popularity": state.character.popularity,
            "reputation": dict(state.character.reputation),
            "status_effects": [_status_to_dict(x) for x in state.character.status_effects],
        },
        "world": {
            "locations": dict(state.world.locations),
            "exits": {k: list(v) for k, v in state.world.exits.items()},
            "items": {
                k: {"id": v.id, "name": v.name,
                    "location_id": v.location_id, "owner": v.owner}
                for k, v in state.world.items.items()
            },
            "npcs": {
                k: {"id": v.id, "name": v.name, "location_id": v.location_id,
                    "hp": v.hp, "max_hp": v.max_hp,
                    "attack_power": v.attack_power, "defense": v.defense,
                    "xp_reward": v.xp_reward,
                    "disposition": v.disposition, "alive": v.alive,
                    "traits": list(v.traits),
                    "personality": {
                        "courage": v.personality.courage,
                        "aggression": v.personality.aggression,
                        "sociability": v.personality.sociability,
                        "honesty": v.personality.honesty,
                        "greed": v.personality.greed,
                        "curiosity": v.personality.curiosity,
                        "loyalty": v.personality.loyalty,
                        "patience": v.personality.patience,
                    },
                    "goals": [
                        {"id": g.id, "description": g.description,
                         "priority": g.priority, "status": g.status,
                         "kind": g.kind, "target_id": g.target_id,
                         "target_location": g.target_location,
                         "required_progress": g.required_progress, "progress": g.progress,
                         "data": dict(g.data)}
                        for g in v.goals
                    ],
                    "fears": list(v.fears),
                    "preferences": list(v.preferences),
                    "status_effects": [_status_to_dict(x) for x in v.status_effects]}
                for k, v in state.world.npcs.items()
            },
            "relationships": {
                k: {"party_a": v.party_a, "party_b": v.party_b,
                    "affinity": v.affinity, "trust": v.trust,
                    "flags": list(v.flags)}
                for k, v in state.world.relationships.items()
            },
            "events": {
                k: {
                    "id": v.id,
                    "type": v.type,
                    "status": v.status,
                    "start_turn": v.start_turn,
                    "resolved_turn": v.resolved_turn,
                    "location_id": v.location_id,
                    "participants": list(v.participants),
                    "metadata": dict(v.metadata),
                }
                for k, v in state.world.events.items()
            },
            "techniques": {
                k: {"id": v.id, "name": v.name, "power": v.power,
                    "stamina_cost": v.stamina_cost, "description": v.description}
                for k, v in state.world.techniques.items()
            },
            "quests": {
                k: {
                    "id": v.id,
                    "title": v.title,
                    "description": v.description,
                    "status": v.status,
                    "giver": v.giver,
                    "participants": list(v.participants),
                    "objectives": [
                        {
                            "id": o.id, "description": o.description,
                            "type": o.type, "target_id": o.target_id,
                            "required_count": o.required_count,
                            "current_count": o.current_count,
                            "completed": o.completed,
                        }
                        for o in v.objectives
                    ],
                    "rewards": [dict(r) for r in v.rewards],
                    "rewards_claimed": v.rewards_claimed,
                    "prerequisites": [dict(r) for r in v.prerequisites],
                    "hidden": v.hidden,
                    "expires_turn": v.expires_turn,
                    "started_turn": v.started_turn,
                    "completed_turn": v.completed_turn,
                    "failed_turn": v.failed_turn,
                    "unlocks_on_complete": list(v.unlocks_on_complete),
                    "unlocks_on_fail": list(v.unlocks_on_fail),
                }
                for k, v in state.world.quests.items()
            },
        },
        "memories": (memory.to_list() if memory is not None else []),
    }


def state_from_dict(data: dict) -> tuple[GameState, int, list[str], MemorySystem]:
    try:
        schema = data["schema"]
        if schema not in _SUPPORTED_LOAD_VERSIONS:
            raise SaveError(
                f"unsupported save schema {schema} "
                f"(engine supports {sorted(_SUPPORTED_LOAD_VERSIONS)})")
        c = data["character"]
        character = CharacterState(
            name=c.get("name", "Player"), hp=int(c.get("hp", 100)), max_hp=int(c.get("max_hp", 100)),
            stamina=int(c.get("stamina", 100)), max_stamina=int(c.get("max_stamina", 100)),
            attack_power=int(c.get("attack_power", 15)), defense=int(c.get("defense", 0)),
            level=int(c.get("level", 1)), xp=int(c.get("xp", 0)), xp_to_next=int(c.get("xp_to_next", 100)),
            realm_id=str(c.get("realm_id", "base")), realm_stage=int(c.get("realm_stage", 0)),
            location_id=str(c.get("location_id", "")), inventory=list(c.get("inventory") or []),
            techniques=list(c.get("techniques") or []),
            popularity=int(c.get("popularity", 0)),
            reputation={str(k): int(v) for k, v in (c.get("reputation") or {}).items()},
            status_effects=[_status_from_dict(x) for x in (c.get("status_effects") or [])],
        )
        w = data["world"]
        npcs = {}
        for k, v in w["npcs"].items():
            traits = list(v.get("traits") or [])
            # Additive backward compatibility: v1.2 saves (schema 3, pre-v1.3
            # engine) have no 'personality'/'goals'/'fears'/'preferences' keys
            # at all. Missing keys -> engine defaults, not a schema bump.
            personality_raw = v.get("personality") or {}
            personality = NPCPersonality(
                courage=personality_raw.get("courage", 50),
                aggression=personality_raw.get("aggression", 50),
                sociability=personality_raw.get("sociability", 50),
                honesty=personality_raw.get("honesty", 50),
                greed=personality_raw.get("greed", 50),
                curiosity=personality_raw.get("curiosity", 50),
                loyalty=personality_raw.get("loyalty", 50),
                patience=personality_raw.get("patience", 50),
            )
            goals = [
                NPCGoal(
                    id=g["id"], description=g["description"],
                    priority=int(g["priority"]), status=g.get("status", "active"),
                    kind=str(g.get("kind", "passive")),
                    target_id=(str(g["target_id"]) if g.get("target_id") is not None else None),
                    target_location=(str(g["target_location"]) if g.get("target_location") is not None else None),
                    required_progress=max(1, int(g.get("required_progress", 1))),
                    progress=max(0, int(g.get("progress", 0))), data=dict(g.get("data") or {}),
                )
                for g in (v.get("goals") or [])
            ]
            fears = list(v.get("fears") or [])
            preferences = list(v.get("preferences") or [])
            npcs[k] = NPCState(
                id=v["id"], name=v["name"], location_id=v["location_id"],
                hp=v.get("hp", 50), max_hp=v.get("max_hp", 50),
                attack_power=int(v.get("attack_power", 5)), defense=int(v.get("defense", 0)),
                xp_reward=int(v.get("xp_reward", 25)), disposition=v.get("disposition", 0), alive=v.get("alive", True),
                traits=traits, personality=personality, goals=goals,
                fears=fears, preferences=preferences,
                status_effects=[_status_from_dict(x) for x in (v.get("status_effects") or [])],
            )
        relationships = {}
        for k, v in (w.get("relationships") or {}).items():
            relationships[k] = RelationshipState(
                party_a=v["party_a"], party_b=v["party_b"],
                affinity=int(v.get("affinity", 0)),
                trust=int(v.get("trust", 0)),
                flags=list(v.get("flags") or []),
            )
        events = {}
        for k, v in (w.get("events") or {}).items():
            events[k] = EventState(
                id=v["id"], type=v["type"],
                status=v.get("status", "inactive"),
                start_turn=v.get("start_turn"),
                resolved_turn=v.get("resolved_turn"),
                location_id=v.get("location_id"),
                participants=list(v.get("participants") or []),
                metadata=dict(v.get("metadata") or {}),
            )
        techniques = {}
        for k, v in (w.get("techniques") or {}).items():
            techniques[k] = TechniqueState(
                id=v["id"], name=v["name"], power=int(v.get("power", 0)),
                stamina_cost=int(v.get("stamina_cost", 10)), description=v.get("description", ""),
            )
        quests = {}
        for k, v in (w.get("quests") or {}).items():
            objectives = [
                QuestObjective(
                    id=o["id"], description=o["description"],
                    type=o["type"], target_id=o["target_id"],
                    required_count=int(o.get("required_count", 1)),
                    current_count=int(o.get("current_count", 0)),
                    completed=bool(o.get("completed", False)),
                )
                for o in (v.get("objectives") or [])
            ]
            quests[k] = QuestState(
                id=v["id"], title=v["title"],
                description=v.get("description", ""),
                status=v.get("status", "available"),
                giver=v.get("giver"),
                participants=list(v.get("participants") or []),
                objectives=objectives,
                rewards=[dict(r) for r in (v.get("rewards") or [])],
                rewards_claimed=bool(v.get("rewards_claimed", False)),
                prerequisites=[dict(r) for r in (v.get("prerequisites") or [])],
                hidden=bool(v.get("hidden", False)),
                expires_turn=(int(v["expires_turn"]) if v.get("expires_turn") is not None else None),
                started_turn=(int(v["started_turn"]) if v.get("started_turn") is not None else None),
                completed_turn=(int(v["completed_turn"]) if v.get("completed_turn") is not None else None),
                failed_turn=(int(v["failed_turn"]) if v.get("failed_turn") is not None else None),
                unlocks_on_complete=list(v.get("unlocks_on_complete") or []),
                unlocks_on_fail=list(v.get("unlocks_on_fail") or []),
            )
        world = WorldState(
            locations=dict(w["locations"]),
            exits={k: list(v) for k, v in w["exits"].items()},
            items={k: ItemState(**v) for k, v in w["items"].items()},
            npcs=npcs,
            relationships=relationships,
            events=events,
            quests=quests,
            techniques=techniques,
        )
        memories_raw = data.get("memories", [])
        if not isinstance(memories_raw, list):
            raise SaveError("memories must be a list")
        memory = MemorySystem.from_list(memories_raw)
        return (
            GameState(character=character, world=world),
            int(data["turn"]),
            list(data["recent_turns"]),
            memory,
        )
    except SaveError:
        raise
    except (KeyError, TypeError, ValueError) as err:
        raise SaveError(f"corrupt save payload: {err}") from err


def write_save(
    path: Path,
    state: GameState,
    turn: int,
    recent_turns: list[str],
    scenario_id: str,
    memory: MemorySystem | None = None,
    scenario_config: dict | None = None,
    campaign_id: str | None = None,
    campaign_name: str | None = None,
    recovery_checkpoint: dict | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(state_to_dict(state, turn, recent_turns, memory))
    now = datetime.now(timezone.utc).isoformat()
    tmp = path.with_suffix(path.suffix + ".tmp")
    backup = path.with_suffix(path.suffix + ".bak")
    existing_created = None
    existing_campaign_id = None
    existing_campaign_name = None
    if path.exists():
        try:
            existing = _connect(path)
            existing_header = dict(existing.execute("SELECT key, value FROM header").fetchall())
            existing_created = (existing_header.get("created"),) if existing_header.get("created") else None
            existing_campaign_id = existing_header.get("campaign_id")
            existing_campaign_name = existing_header.get("campaign_name")
        except sqlite3.DatabaseError:
            # A corrupt primary must never be promoted to the recovery copy.
            existing_created = None
        finally:
            try:
                existing.close()
            except UnboundLocalError:
                pass
    created = existing_created[0] if existing_created else now
    campaign_id = campaign_id or existing_campaign_id or str(uuid4())
    campaign_name = campaign_name or existing_campaign_name or state.character.name or "Campaign"
    conn = _connect(tmp)
    try:
        with conn:
            conn.executescript(_SCHEMA)
            for key, value in (
                ("engine_version", ENGINE_VERSION),
                ("save_format_version", str(SAVE_FORMAT_VERSION)),
                ("scenario_id", scenario_id),
                ("created", created),
                ("modified", now),
                ("scenario_config", json.dumps(scenario_config) if scenario_config is not None else ""),
                ("campaign_id", campaign_id),
                ("campaign_name", campaign_name),
                ("recovery_checkpoint", json.dumps(recovery_checkpoint) if recovery_checkpoint is not None else ""),
            ):
                conn.execute("INSERT INTO header VALUES (?, ?)", (key, value))
            conn.execute("INSERT INTO game_state (id, json) VALUES (1, ?)", (payload,))
    finally:
        conn.close()

    try:
        # Validate the new database before it can replace the live save.
        read_save(tmp)
        if path.exists():
            os.replace(path, backup)
        os.replace(tmp, path)
    except Exception as exc:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        # If promotion failed after moving the primary, restore the previous copy.
        if not path.exists() and backup.exists():
            os.replace(backup, path)
        if isinstance(exc, SaveError):
            raise
        raise SaveError(f"failed to commit save atomically: {exc}") from exc


def read_slot_metadata(path: Path) -> SaveSlotMetadata:
    """Read lightweight slot metadata without mutating or recovering the save."""
    slot = path.stem if path.suffix == ".db" else path.name
    try:
        conn = _connect(path)
        try:
            header = dict(conn.execute("SELECT key, value FROM header").fetchall())
        finally:
            conn.close()
        if not header:
            raise SaveError("empty header")
        raw_version = header.get("save_format_version")
        try:
            format_version = int(raw_version) if raw_version is not None else None
        except (TypeError, ValueError):
            format_version = None
        # Optional campaign fields keep pre-v1.19.2 saves readable.
        return SaveSlotMetadata(
            slot=slot, campaign_id=header.get("campaign_id"),
            campaign_name=header.get("campaign_name"),
            scenario_id=header.get("scenario_id"), created=header.get("created"),
            modified=header.get("modified"), engine_version=header.get("engine_version"),
            save_format_version=format_version, valid=True,
        )
    except (sqlite3.DatabaseError, OSError, SaveError) as exc:
        return SaveSlotMetadata(
            slot=slot, campaign_id=None, campaign_name=None, scenario_id=None,
            created=None, modified=None, engine_version=None, save_format_version=None,
            valid=False, error=str(exc),
        )


def read_save(path: Path) -> tuple[GameState, int, list[str], dict, MemorySystem]:
    if not path.exists():
        raise SaveError(f"no save file at {path}")
    conn = _connect(path)
    try:
        header = dict(conn.execute("SELECT key, value FROM header").fetchall())
        if not header:
            raise SaveError(f"{path} is not an RPG engine save (empty header)")
        missing = [k for k in _HEADER_KEYS if k not in header]
        if missing:
            raise SaveError(f"corrupt save header, missing: {missing}")
        hdr_ver = int(header["save_format_version"])
        if hdr_ver not in _SUPPORTED_LOAD_VERSIONS:
            raise SaveError(
                f"save format v{header['save_format_version']} not supported "
                f"by this engine (supports {sorted(_SUPPORTED_LOAD_VERSIONS)})")
        row = conn.execute("SELECT json FROM game_state WHERE id=1").fetchone()
        if row is None:
            raise SaveError("save file has no game_state payload")
        data = json.loads(row[0])
        state, turn, recent, memory = state_from_dict(data)
        return state, turn, recent, header, memory
    except (sqlite3.DatabaseError, json.JSONDecodeError) as err:
        raise SaveError(f"corrupt save file: {err}") from err
    finally:
        conn.close()
