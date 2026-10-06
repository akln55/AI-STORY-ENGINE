"""Scenario data-pack loading and validation.

Scenario distribution contract:
- JSON is authoritative machine-readable data.
- Markdown is human-readable research/lore documentation.
- A complete installable scenario is distributed as a ZIP archive.
- ``world.json`` is the initial runtime bootstrap; ``data/`` and ``chapters/``
  hold canonical scenario knowledge and are immutable during a save.
"""
from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, Mapping

from engine.scenario.errors import ScenarioError
from engine.scenario.registry import ScenarioRegistry
from engine.scenario.chapters import ChapterManager
from engine.scenario.documents import ScenarioDocument
from engine.scenario.retrieval import ScenarioRetriever

from engine.core.invariants import check_invariants
from engine.core.state import (
    CharacterState, EventState, GameState, ItemState, NPCGoal, NPCPersonality,
    NPCState, QuestObjective, QuestState, RelationshipState, TechniqueState, WorldState,
)

PACK_FORMAT_VERSION = 2
_REQUIRED_MANIFEST = ("scenario_id", "name", "version")
_DATA_JSON_FILES = {
    "characters.json", "locations.json", "factions.json", "items.json",
    "techniques.json", "realms.json", "creatures.json", "events.json",
    "relationships.json", "timeline.json", "knowledge.json",
}


@dataclass(frozen=True)
class ChapterPack:
    pack_id: str
    chapter_start: int
    chapter_end: int
    sequence: int
    previous_pack: str | None = None
    next_pack: str | None = None


@dataclass(frozen=True)
class ScenarioPack:
    scenario_id: str
    name: str
    version: str
    engine_min_version: str | None
    manifest: Mapping[str, Any]
    world_payload: Mapping[str, Any]
    lore_documents: tuple[str, ...] = ()
    data_documents: tuple[str, ...] = ()
    chapter_packs: tuple[ChapterPack, ...] = ()
    registry: ScenarioRegistry | None = None
    chapter_manager: ChapterManager | None = None
    documents: tuple[ScenarioDocument, ...] = ()
    retriever: ScenarioRetriever | None = None

    def build_state(self) -> GameState:
        state = _state_from_payload(self.world_payload)
        check_invariants(state)
        return state


def load_scenario(path: str | Path) -> ScenarioPack:
    """Load a directory pack or a .zip/.rpgscenario.zip pack."""
    path = Path(path)
    if path.is_dir():
        return _load_directory(path)
    if path.is_file() and zipfile.is_zipfile(path):
        return _load_zip(path)
    raise ScenarioError(f"scenario path is neither a directory nor a zip: {path}")


def validate_scenario(path: str | Path) -> ScenarioPack:
    return load_scenario(path)


def _load_directory(root: Path) -> ScenarioPack:
    manifest_path = root / "manifest.json"
    world_path = root / "world.json"
    if not manifest_path.is_file():
        raise ScenarioError("scenario pack is missing manifest.json")
    if not world_path.is_file():
        raise ScenarioError("scenario pack is missing world.json")
    manifest = _read_json(manifest_path, "manifest.json")
    world = _read_json(world_path, "world.json")
    lore = tuple(str(p.relative_to(root)).replace("\\", "/") for p in sorted((root / "lore").rglob("*.md")) if p.is_file()) if (root / "lore").exists() else ()
    data, payloads = _read_data_documents_directory(root)
    chapters = _read_chapter_manifests_directory(root)
    chapter_docs = _read_markdown_documents_directory(root, chapters)
    return _make_pack(manifest, world, lore, data, chapters, payloads, chapter_docs)


def _load_zip(path: Path) -> ScenarioPack:
    with zipfile.ZipFile(path) as archive:
        raw_names = [n for n in archive.namelist() if not n.endswith("/")]
        names_list = [_safe_zip_name(n) for n in raw_names]
        if len(names_list) != len(set(names_list)):
            raise ScenarioError("scenario zip contains duplicate file names")
        names = set(names_list)
        if "manifest.json" not in names:
            raise ScenarioError("scenario zip is missing manifest.json")
        if "world.json" not in names:
            raise ScenarioError("scenario zip is missing world.json")
        manifest = _json_bytes(archive.read("manifest.json"), "manifest.json")
        world = _json_bytes(archive.read("world.json"), "world.json")
        data = {}
        payloads = {}
        for name in sorted(n for n in names if n.startswith("data/") and n.endswith(".json")):
            if name.count("/") != 1 or PurePosixPath(name).name not in _DATA_JSON_FILES:
                raise ScenarioError(f"unsupported canonical scenario data path: {name}")
            payload = _json_bytes(archive.read(name), name)
            data[name] = payload
            payloads[PurePosixPath(name).name] = payload
        lore = tuple(sorted(n for n in names if n.startswith("lore/") and n.endswith(".md")))
        chapters = _read_chapter_manifests_zip(archive, names)
        chapter_docs = _read_markdown_documents_zip(archive, names, chapters)
    return _make_pack(manifest, world, lore, tuple(data), chapters, payloads, chapter_docs)


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({str(k): _freeze(v) for k, v in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(v) for v in value)
    return value


def _safe_zip_name(name: str) -> str:
    normalized = str(PurePosixPath(name))
    if normalized.startswith("/") or ".." in PurePosixPath(normalized).parts:
        raise ScenarioError(f"unsafe path in scenario zip: {name!r}")
    return normalized


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        return _json_bytes(path.read_bytes(), label)
    except OSError as exc:
        raise ScenarioError(f"cannot read {label}: {exc}") from exc


def _json_bytes(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ScenarioError(f"invalid JSON in {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ScenarioError(f"{label} root must be an object")
    return value


def _read_data_documents_directory(root: Path) -> tuple[tuple[str, ...], dict[str, dict[str, Any]]]:
    data_root = root / "data"
    if not data_root.exists():
        return (), {}
    if not data_root.is_dir():
        raise ScenarioError("scenario data path 'data' must be a directory")
    found = []
    payloads: dict[str, dict[str, Any]] = {}
    for path in sorted(data_root.rglob("*.json")):
        if path.is_file():
            relative = str(path.relative_to(root)).replace("\\", "/")
            if relative.count("/") != 1 or path.name not in _DATA_JSON_FILES:
                raise ScenarioError(f"unsupported canonical scenario data path: {relative}")
            payload = _json_bytes(path.read_bytes(), relative)
            found.append(relative)
            payloads[path.name] = payload
    return tuple(found), payloads


def _read_chapter_manifests_directory(root: Path) -> tuple[ChapterPack, ...]:
    chapter_root = root / "chapters"
    if not chapter_root.exists():
        return ()
    if not chapter_root.is_dir():
        raise ScenarioError("scenario path 'chapters' must be a directory")
    packs = []
    for path in sorted(chapter_root.rglob("chapter_manifest.json")):
        packs.append(_chapter_from_dict(_read_json(path, str(path.relative_to(root))), str(path)))
    return _validate_chapter_sequence(packs)


def _read_chapter_manifests_zip(archive: zipfile.ZipFile, names: set[str]) -> tuple[ChapterPack, ...]:
    packs = []
    for name in sorted(n for n in names if n.startswith("chapters/") and n.endswith("/chapter_manifest.json")):
        packs.append(_chapter_from_dict(_json_bytes(archive.read(name), name), name))
    return _validate_chapter_sequence(packs)


def _chapter_from_dict(value: dict[str, Any], label: str) -> ChapterPack:
    required = ("pack_id", "chapter_start", "chapter_end", "sequence")
    missing = [k for k in required if k not in value]
    if missing:
        raise ScenarioError(f"{label} missing required fields: {', '.join(missing)}")
    try:
        start = int(value["chapter_start"])
        end = int(value["chapter_end"])
        sequence = int(value["sequence"])
    except (TypeError, ValueError) as exc:
        raise ScenarioError(f"invalid chapter metadata in {label}") from exc
    pack_id = str(value["pack_id"]).strip()
    if not pack_id or start < 1 or end < start or sequence < 1:
        raise ScenarioError(f"invalid chapter range/sequence in {label}")
    return ChapterPack(pack_id, start, end, sequence, value.get("previous_pack"), value.get("next_pack"))


def _validate_chapter_sequence(packs: list[ChapterPack]) -> tuple[ChapterPack, ...]:
    ordered = sorted(packs, key=lambda p: p.sequence)
    ids = [p.pack_id for p in ordered]
    if len(ids) != len(set(ids)):
        raise ScenarioError("duplicate chapter pack_id")
    sequences = [p.sequence for p in ordered]
    if sequences != list(range(1, len(sequences) + 1)):
        raise ScenarioError("chapter pack sequences must be contiguous starting at 1")
    previous_end = None
    for pack in ordered:
        if previous_end is not None and pack.chapter_start != previous_end + 1:
            raise ScenarioError("chapter pack ranges must be contiguous and non-overlapping")
        previous_end = pack.chapter_end
    for i, pack in enumerate(ordered):
        expected_prev = ordered[i - 1].pack_id if i else None
        expected_next = ordered[i + 1].pack_id if i + 1 < len(ordered) else None
        if pack.previous_pack not in (None, expected_prev) or pack.next_pack not in (None, expected_next):
            raise ScenarioError(f"invalid previous/next chapter links for {pack.pack_id}")
    return tuple(ordered)



def _document_kind(path: str) -> str:
    name = PurePosixPath(path).name.lower()
    if name.endswith(".md"):
        return name[:-3] or "document"
    return name


def _document_title(content: str, fallback: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or fallback
    return fallback


def _read_markdown_documents_directory(root: Path, chapters: tuple[ChapterPack, ...]) -> tuple[ScenarioDocument, ...]:
    docs: list[ScenarioDocument] = []
    lore_root = root / "lore"
    if lore_root.exists():
        for path in sorted(lore_root.rglob("*.md")):
            if path.is_file():
                rel = str(path.relative_to(root)).replace("\\", "/")
                try:
                    content = path.read_text(encoding="utf-8")
                except UnicodeDecodeError as exc:
                    raise ScenarioError(f"invalid UTF-8 in {rel}") from exc
                docs.append(ScenarioDocument(rel, "lore", None, None, None, _document_kind(rel), _document_title(content, path.stem), content))
    chapter_root = root / "chapters"
    if chapter_root.exists():
        declared_dirs: set[Path] = set()
        for pack in chapters:
            for manifest_path in chapter_root.rglob("chapter_manifest.json"):
                try:
                    payload = _read_json(manifest_path, str(manifest_path.relative_to(root)))
                except ScenarioError:
                    raise
                if payload.get("pack_id") == pack.pack_id:
                    declared_dirs.add(manifest_path.parent)
        for path in chapter_root.rglob("*.md"):
            if path.is_file() and path.parent not in declared_dirs:
                rel = str(path.relative_to(root)).replace("\\", "/")
                raise ScenarioError(f"chapter Markdown is outside a declared chapter pack: {rel}")
        for pack in chapters:
            pack_dir = next((p for p in chapter_root.iterdir() if p.is_dir() and (p / "chapter_manifest.json").is_file() and _read_json(p / "chapter_manifest.json", str(p / "chapter_manifest.json")).get("pack_id") == pack.pack_id), None)
            if pack_dir is None:
                continue
            for path in sorted(pack_dir.rglob("*.md")):
                rel = str(path.relative_to(root)).replace("\\", "/")
                try:
                    content = path.read_text(encoding="utf-8")
                except UnicodeDecodeError as exc:
                    raise ScenarioError(f"invalid UTF-8 in {rel}") from exc
                docs.append(ScenarioDocument(rel, "chapter", pack.pack_id, pack.chapter_start, pack.chapter_end, _document_kind(rel), _document_title(content, path.stem), content))
    return tuple(docs)


def _read_markdown_documents_zip(archive: zipfile.ZipFile, names: set[str], chapters: tuple[ChapterPack, ...]) -> tuple[ScenarioDocument, ...]:
    docs: list[ScenarioDocument] = []
    pack_by_dir = {}
    for pack in chapters:
        prefix = f"chapters/"
        for name in names:
            if name.startswith(prefix) and name.endswith("/chapter_manifest.json"):
                payload = _json_bytes(archive.read(name), name)
                if payload.get("pack_id") == pack.pack_id:
                    pack_by_dir[name.rsplit("/", 1)[0]] = pack
    for name in sorted(n for n in names if n.startswith("lore/") and n.endswith(".md")):
        try:
            content = archive.read(name).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ScenarioError(f"invalid UTF-8 in {name}") from exc
        docs.append(ScenarioDocument(name, "lore", None, None, None, _document_kind(name), _document_title(content, PurePosixPath(name).stem), content))
    for name in sorted(n for n in names if n.startswith("chapters/") and n.endswith(".md")):
        pack_dir = name.rsplit("/", 1)[0]
        pack = pack_by_dir.get(pack_dir)
        if pack is None:
            raise ScenarioError(f"chapter Markdown is outside a declared chapter pack: {name}")
        try:
            content = archive.read(name).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ScenarioError(f"invalid UTF-8 in {name}") from exc
        docs.append(ScenarioDocument(name, "chapter", pack.pack_id, pack.chapter_start, pack.chapter_end, _document_kind(name), _document_title(content, PurePosixPath(name).stem), content))
    return tuple(docs)


def _make_pack(manifest: dict[str, Any], world: dict[str, Any], lore: tuple[str, ...], data: tuple[str, ...], chapters: tuple[ChapterPack, ...], payloads: dict[str, dict[str, Any]] | None = None, documents: tuple[ScenarioDocument, ...] = ()) -> ScenarioPack:
    missing = [k for k in _REQUIRED_MANIFEST if not isinstance(manifest.get(k), str) or not manifest[k].strip()]
    if missing:
        raise ScenarioError(f"manifest missing required fields: {', '.join(missing)}")
    fmt = manifest.get("pack_format", 1)
    if fmt not in (1, PACK_FORMAT_VERSION):
        raise ScenarioError(f"unsupported scenario pack format {fmt!r}")
    scenario_id = manifest["scenario_id"]
    if scenario_id != _clean_id(scenario_id):
        raise ScenarioError(f"invalid scenario_id {scenario_id!r}")
    if not isinstance(manifest.get("version"), str):
        raise ScenarioError("manifest.version must be a string")
    if not isinstance(world.get("character", {}), dict) or not isinstance(world.get("locations", {}), dict):
        raise ScenarioError("world.json must contain object fields character and locations")
    if fmt >= 2:
        declared_size = manifest.get("chapter_pack_size")
        if declared_size is not None and (not isinstance(declared_size, int) or isinstance(declared_size, bool) or declared_size < 1):
            raise ScenarioError("manifest.chapter_pack_size must be a positive integer")
        _validate_manifest_chapter_declarations(manifest, chapters, declared_size)
    registry = ScenarioRegistry.from_documents(payloads or {})
    _validate_event_definitions(registry)
    pack = ScenarioPack(
        scenario_id, manifest["name"], manifest["version"], manifest.get("engine_min_version"),
        _freeze(manifest), _freeze(world), lore, data, chapters, registry, ChapterManager(chapters), documents, None
    )
    retriever = ScenarioRetriever(registry, documents)
    retriever.scenario_pack = pack
    object.__setattr__(pack, "retriever", retriever)
    pack.build_state()
    return pack


def _validate_manifest_chapter_declarations(
    manifest: dict[str, Any],
    chapters: tuple[ChapterPack, ...],
    declared_size: int | None,
) -> None:
    """Cross-check optional manifest chapter metadata against actual manifests."""
    declared_count = manifest.get("chapter_count")
    if declared_count is not None:
        if not isinstance(declared_count, int) or isinstance(declared_count, bool) or declared_count < 0:
            raise ScenarioError("manifest.chapter_count must be a non-negative integer")
        actual_count = sum(p.chapter_end - p.chapter_start + 1 for p in chapters)
        if declared_count != actual_count:
            raise ScenarioError(
                f"manifest.chapter_count={declared_count} does not match actual chapter count {actual_count}"
            )

    declared_packs = manifest.get("chapter_packs")
    if declared_packs is not None:
        if not isinstance(declared_packs, list) or any(not isinstance(x, str) or not x.strip() for x in declared_packs):
            raise ScenarioError("manifest.chapter_packs must be a list of non-empty strings")
        actual_ids = [p.pack_id for p in chapters]
        if declared_packs != actual_ids:
            raise ScenarioError(
                "manifest.chapter_packs must exactly match chapter manifest order"
            )

    if declared_size is not None:
        for pack in chapters:
            size = pack.chapter_end - pack.chapter_start + 1
            if size > declared_size:
                raise ScenarioError(
                    f"chapter pack {pack.pack_id!r} contains {size} chapters, "
                    f"exceeding manifest.chapter_pack_size={declared_size}"
                )


_EVENT_CONDITIONS = {
    "turn", "chapter", "location", "level", "realm", "popularity",
    "reputation", "relationship_affinity", "relationship_trust",
    "inventory", "quest", "event", "npc_present", "npc_absent",
}
_EFFECT_KINDS = {"resource", "inventory", "location", "npc", "relationship", "event", "progression", "quest"}

def _validate_event_definitions(registry: ScenarioRegistry) -> None:
    for record in registry.all("events"):
        data = record.data
        conditions = data.get("trigger_conditions", ())
        if not isinstance(conditions, (list, tuple)):
            raise ScenarioError(f"event {record.id}: trigger_conditions must be a list")
        for condition in conditions:
            if not isinstance(condition, Mapping) or condition.get("type") not in _EVENT_CONDITIONS:
                raise ScenarioError(f"event {record.id}: unsupported trigger condition")
        effects = data.get("effects", ())
        if not isinstance(effects, (list, tuple)):
            raise ScenarioError(f"event {record.id}: effects must be a list")
        for effect in effects:
            if not isinstance(effect, Mapping) or effect.get("kind") not in _EFFECT_KINDS:
                raise ScenarioError(f"event {record.id}: unsupported effect kind")
        advance = data.get("advance_chapter_to")
        if advance is not None and (not isinstance(advance, int) or isinstance(advance, bool) or advance < 1):
            raise ScenarioError(f"event {record.id}: advance_chapter_to must be a positive integer")


def _clean_id(value: str) -> str:
    return value.strip() and value.strip().replace("_", "").replace("-", "").isalnum() and value.strip()


def _state_from_payload(w: dict[str, Any]) -> GameState:
    character_raw = w.get("character") or {}
    character = CharacterState(name=character_raw.get("name", "Player"), hp=int(character_raw.get("hp", 100)), max_hp=int(character_raw.get("max_hp", 100)), stamina=int(character_raw.get("stamina", 100)), max_stamina=int(character_raw.get("max_stamina", 100)), location_id=str(character_raw.get("location_id", "")), inventory=list(character_raw.get("inventory") or []), attack_power=int(character_raw.get("attack_power", 15)), defense=int(character_raw.get("defense", 0)), level=int(character_raw.get("level", 1)), xp=int(character_raw.get("xp", 0)), xp_to_next=int(character_raw.get("xp_to_next", 100)), realm_id=str(character_raw.get("realm_id", "base")), realm_stage=int(character_raw.get("realm_stage", 0)), techniques=list(character_raw.get("techniques") or []), popularity=int(character_raw.get("popularity", 0)), reputation={str(k): int(v) for k, v in (character_raw.get("reputation") or {}).items()})
    locations = {str(k): str(v) for k, v in (w.get("locations") or {}).items()}
    exits = {str(k): [str(x) for x in v] for k, v in (w.get("exits") or {}).items()}
    items = {str(k): ItemState(id=v["id"], name=v["name"], location_id=v.get("location_id"), owner=v.get("owner")) for k, v in (w.get("items") or {}).items()}
    npcs = {str(k): _npc_from_dict(v) for k, v in (w.get("npcs") or {}).items()}
    relationships = {str(k): RelationshipState(party_a=v["party_a"], party_b=v["party_b"], affinity=int(v.get("affinity", 0)), trust=int(v.get("trust", 0)), flags=list(v.get("flags") or [])) for k, v in (w.get("relationships") or {}).items()}
    events = {str(k): EventState(id=v["id"], type=v["type"], status=v.get("status", "inactive"), start_turn=v.get("start_turn"), resolved_turn=v.get("resolved_turn"), location_id=v.get("location_id"), participants=list(v.get("participants") or []), metadata=dict(v.get("metadata") or {})) for k, v in (w.get("events") or {}).items()}
    techniques = {str(k): TechniqueState(id=v["id"], name=v["name"], power=int(v.get("power", 0)), stamina_cost=int(v.get("stamina_cost", 10)), description=v.get("description", "")) for k, v in (w.get("techniques") or {}).items()}
    quests = {}
    for k, v in (w.get("quests") or {}).items():
        objectives = [QuestObjective(id=o["id"], description=o["description"], type=o["type"], target_id=o["target_id"], required_count=int(o.get("required_count", 1)), current_count=int(o.get("current_count", 0)), completed=bool(o.get("completed", False))) for o in (v.get("objectives") or [])]
        quests[str(k)] = QuestState(
            id=v["id"], title=v["title"], description=v.get("description", ""),
            status=v.get("status", "available"), giver=v.get("giver"),
            participants=list(v.get("participants") or []), objectives=objectives,
            rewards=[dict(r) for r in (v.get("rewards") or [])],
            prerequisites=[dict(r) for r in (v.get("prerequisites") or [])],
            rewards_claimed=bool(v.get("rewards_claimed", False)),
            hidden=bool(v.get("hidden", False)),
            expires_turn=(int(v["expires_turn"]) if v.get("expires_turn") is not None else None),
            started_turn=(int(v["started_turn"]) if v.get("started_turn") is not None else None),
            completed_turn=(int(v["completed_turn"]) if v.get("completed_turn") is not None else None),
            failed_turn=(int(v["failed_turn"]) if v.get("failed_turn") is not None else None),
            unlocks_on_complete=list(v.get("unlocks_on_complete") or []),
            unlocks_on_fail=list(v.get("unlocks_on_fail") or []),
        )
    world = WorldState(locations=locations, exits=exits, items=items, npcs=npcs, relationships=relationships, events=events, quests=quests, techniques=techniques)
    return GameState(character=character, world=world)


def _npc_from_dict(v: dict[str, Any]) -> NPCState:
    p = v.get("personality") or {}
    personality = NPCPersonality(courage=int(p.get("courage", 50)), aggression=int(p.get("aggression", 50)), sociability=int(p.get("sociability", 50)), honesty=int(p.get("honesty", 50)), greed=int(p.get("greed", 50)), curiosity=int(p.get("curiosity", 50)), loyalty=int(p.get("loyalty", 50)), patience=int(p.get("patience", 50)))
    goals = [NPCGoal(
        id=g["id"], description=g["description"], priority=int(g["priority"]),
        status=g.get("status", "active"), kind=str(g.get("kind", "passive")),
        target_id=(str(g["target_id"]) if g.get("target_id") is not None else None),
        target_location=(str(g["target_location"]) if g.get("target_location") is not None else None),
        required_progress=max(1, int(g.get("required_progress", 1))),
        progress=max(0, int(g.get("progress", 0))), data=dict(g.get("data") or {}),
    ) for g in (v.get("goals") or [])]
    return NPCState(id=v["id"], name=v["name"], location_id=v["location_id"], hp=int(v.get("hp", 50)), max_hp=int(v.get("max_hp", 50)), attack_power=int(v.get("attack_power", 5)), defense=int(v.get("defense", 0)), xp_reward=int(v.get("xp_reward", 25)), disposition=int(v.get("disposition", 0)), alive=bool(v.get("alive", True)), traits=list(v.get("traits") or []), personality=personality, goals=goals, fears=list(v.get("fears") or []), preferences=list(v.get("preferences") or []))
