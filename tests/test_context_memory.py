from engine.ai.context import assemble_context
from engine.demo import build_demo_state
from engine.memory.system import MemorySystem


def test_player_visible_memory_included():
    state = build_demo_state()
    ms = MemorySystem()
    ms.add("location", "The well is dry", visibility="player",
           importance=40, created_turn=1, location_id="village")
    ctx = assemble_context(state, [], "look around", memory=ms, viewer="player")
    assert "well is dry" in ctx
    assert "RELEVANT MEMORY" in ctx


def test_system_memory_excluded_from_player_context():
    state = build_demo_state()
    ms = MemorySystem()
    ms.add("secret", "GM only fact about dragon", visibility="system",
           importance=99, created_turn=1)
    ctx = assemble_context(state, [], "ask about dragons", memory=ms, viewer="player")
    assert "GM only fact" not in ctx


def test_npc_memory_excluded_from_player_context():
    state = build_demo_state()
    ms = MemorySystem()
    ms.add("knowledge", "elder private plan", visibility="npc:elder",
           importance=80, created_turn=1)
    ctx = assemble_context(state, [], "talk to elder", memory=ms, viewer="player")
    assert "private plan" not in ctx


def test_context_bounded_with_many_memories():
    state = build_demo_state()
    ms = MemorySystem()
    for i in range(200):
        ms.add("recent", f"memory entry number {i} " + ("x" * 80),
               visibility="player", importance=i % 50, created_turn=i)
    ctx = assemble_context(state, [f"T{i} player: act" for i in range(40)],
                           "do something elaborate", memory=ms, viewer="player")
    assert len(ctx) <= 12000


def test_scenario_canon_is_included_in_context_when_configured():
    from engine.scenario.configuration import ScenarioConfiguration
    from engine.scenario.loader import load_scenario

    pack = load_scenario(__import__('pathlib').Path(__file__).resolve().parent.parent / 'scenarios' / 'demo-bootstrap')
    config = ScenarioConfiguration.from_pack(pack, start_chapter=1)
    state = pack.build_state()
    ctx = assemble_context(
        state, [], "ask about the elder", scenario_retriever=pack.retriever,
        scenario_configuration=config,
    )
    assert "RELEVANT SCENARIO CANON" in ctx
    assert "elder" in ctx.lower()
    assert "active chapter: 1" in ctx


def test_scenario_canon_does_not_replace_runtime_npc_truth():
    from engine.scenario.configuration import ScenarioConfiguration
    from engine.scenario.loader import load_scenario

    pack = load_scenario(__import__('pathlib').Path(__file__).resolve().parent.parent / 'scenarios' / 'demo-bootstrap')
    config = ScenarioConfiguration.from_pack(pack, start_chapter=1)
    state = pack.build_state()
    state.world.npcs["elder"].location_id = "road"
    ctx = assemble_context(
        state, [], "talk to elder", scenario_retriever=pack.retriever,
        scenario_configuration=config,
    )
    assert "CORE SYSTEM" in ctx
    assert "You narrate a text RPG" in ctx
    assert "active chapter: 1" in ctx


def test_context_diagnostics_report_truncation_without_exposing_context():
    from engine.ai.context import ContextDiagnostics, assemble_context
    state = build_demo_state()
    memory = MemorySystem()
    for turn in range(30):
        memory.add("recent", f"remembered event {turn} " + ("x" * 180), visibility="player", created_turn=turn)
    diagnostics = ContextDiagnostics()
    context = assemble_context(state, ["scene " + ("y" * 150)] * 10, "look", memory,
                                max_context_chars=1800, diagnostics=diagnostics)
    assert len(context) <= 1800
    assert diagnostics.initial_chars >= diagnostics.final_chars
    assert (diagnostics.memory_lines_dropped + diagnostics.scenario_lines_dropped + diagnostics.recent_turns_dropped) > 0
    assert diagnostics.final_chars == len(context)


def test_context_respects_provider_specific_budget():
    from engine.ai.context import assemble_context
    state = build_demo_state()
    try:
        assemble_context(state, ["scene " + ("x" * 200)] * 10, "look", max_context_chars=50)
    except RuntimeError as exc:
        assert "context budget exceeded" in str(exc)
    else:
        raise AssertionError("irreducible context must reject an impossibly small provider budget")
