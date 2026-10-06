from pathlib import Path


from contextlib import contextmanager

@contextmanager
def raises(exc, match=None):
    try:
        yield
    except exc as caught:
        if match is not None and match not in str(caught):
            raise AssertionError(f"expected exception message to contain {match!r}, got {caught!r}")
        return
    raise AssertionError(f"expected {exc!r} to be raised")

from engine.ai.adapter_base import AIAdapter
from engine.ai.security import (
    AI_RULES,
    DEFAULT_AI_ACCESS_POLICY,
    DENIED_CAPABILITIES,
    protected_path,
    rules_text,
)


def test_ai_policy_allows_only_declared_proposal_capabilities():
    assert DEFAULT_AI_ACCESS_POLICY.can("read_context")
    assert DEFAULT_AI_ACCESS_POLICY.can("narrate")
    assert DEFAULT_AI_ACCESS_POLICY.can("propose_state_changes")
    assert DEFAULT_AI_ACCESS_POLICY.can("propose_memory_updates")
    for capability in DENIED_CAPABILITIES:
        assert not DEFAULT_AI_ACCESS_POLICY.can(capability)


def test_ai_policy_rules_explicitly_deny_filesystem_and_state_ownership():
    text = rules_text()
    assert "cannot create, delete, edit, or overwrite scenario files" in text
    assert "cannot create, delete, edit, or overwrite save files or databases" in text
    assert "cannot execute code" in text
    assert len(AI_RULES) >= 8


def test_protected_path_rejects_traversal(tmp_path: Path):
    root = tmp_path / "models"
    root.mkdir()
    allowed = root / "model.gguf"
    assert protected_path(allowed, root) == allowed.resolve()
    with raises(PermissionError):
        protected_path(root / ".." / "saves" / "save.db", root)


def test_ai_adapter_interface_exposes_only_generation_boundary():
    public = {
        name for name in dir(AIAdapter)
        if not name.startswith("_")
    }
    assert public == {"generate"}


def test_context_contains_ai_security_rules_and_not_tool_capabilities():
    from engine.ai.context import assemble_context
    from engine.demo import build_demo_state

    ctx = assemble_context(build_demo_state(), [], "look")
    assert "AI ACCESS / AUTHORITY RULES:" in ctx
    assert "cannot create, delete, edit, or overwrite scenario files" in ctx
    assert "cannot execute code" in ctx
    assert "filesystem_read" not in ctx


def test_context_exposes_only_encounterable_npcs_when_registry_is_available():
    from engine.ai.context import assemble_context
    from engine.core.state import CharacterState, GameState, NPCState, WorldState
    from engine.scenario.registry import ScenarioRegistry

    state = GameState(
        character=CharacterState(location_id="palace"),
        world=WorldState(
            locations={"palace": "Palace"},
            npcs={
                "king": NPCState("king", "King", "palace"),
                "guard": NPCState("guard", "Guard", "palace"),
            },
        ),
    )
    registry = ScenarioRegistry.from_documents({
        "characters.json": {
            "king": {"id": "king", "encounter_conditions": [
                {"type": "npc_absent", "npc_id": "guard"}
            ]},
            "guard": {"id": "guard"},
        }
    })
    ctx = assemble_context(state, [], "look", scenario_registry=registry)
    assert "Guard" in ctx
    assert "King" not in ctx
