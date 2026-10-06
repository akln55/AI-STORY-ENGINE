from engine.ai.fake import FakeAdapter
from engine.core.game import GameSession
from engine.core.state import CharacterState, GameState, NPCState, QuestObjective, QuestState, WorldState
from engine.npc.dialogue import build_dialogue_context, resolve_dialogue_target
from engine.npc.encounter import EncounterResolver
from engine.scenario.registry import ScenarioRegistry


def _state():
    return GameState(
        character=CharacterState(name="Player", location_id="inn"),
        world=WorldState(
            locations={"inn": "Inn", "street": "Street"},
            exits={"inn": ["street"], "street": ["inn"]},
            npcs={"elder": NPCState("elder", "Elder", "inn", disposition=20)},
            quests={
                "meet": QuestState(
                    id="meet", title="Meet the Elder", status="active",
                    objectives=[QuestObjective("talk", "Speak to the elder", "talk", "elder")],
                )
            },
        ),
    )


def test_dialogue_target_resolves_id_and_name():
    state = _state()
    resolver = EncounterResolver()
    assert resolve_dialogue_target(state, "elder", resolver).npc.id == "elder"
    assert resolve_dialogue_target(state, "Elder", resolver).npc.id == "elder"


def test_dialogue_target_cannot_bypass_location_gate():
    state = _state()
    state.world.npcs["elder"].location_id = "street"
    target = resolve_dialogue_target(state, "elder", EncounterResolver())
    assert target is not None and not target.encounterable


def test_dialogue_uses_ai_and_completes_talk_objective():
    state = _state()
    fake = FakeAdapter(handlers={
        "talk to elder": {
            "narrative": "The elder greets you cautiously.",
            "state_changes": [],
            "memory_updates": [],
            "npc_changes": [],
            "events_triggered": [],
            "available_actions": ["ask about the village"],
        }
    })
    session = GameSession(state, adapter=fake)
    out = session.handle_input("talk to elder")
    assert "greets" in out
    assert state.world.quests["meet"].status == "completed"
    assert state.world.quests["meet"].objectives[0].completed
    assert len(fake.calls) == 1


def test_dialogue_rejected_when_npc_is_blocked():
    state = _state()
    state.world.npcs["guard"] = NPCState("guard", "Guard", "inn")
    registry = ScenarioRegistry.from_documents({
        "characters.json": {
            "elder": {
                "id": "elder",
                "encounter_conditions": [{"type": "npc_absent", "npc_id": "guard"}],
            },
            "guard": {"id": "guard"},
        }
    })
    fake = FakeAdapter(handlers={"talk to elder": {"narrative": "should not run"}})
    session = GameSession(state, adapter=fake, scenario_registry=registry)
    out = session.handle_input("talk to elder")
    assert "cannot reach" in out
    assert len(fake.calls) == 0


def test_dialogue_context_includes_canonical_speech_rules():
    state = _state()
    registry = ScenarioRegistry.from_documents({
        "characters.json": {
            "elder": {
                "id": "elder",
                "speech_style": {"tone": "measured", "formality": "high"},
                "dialogue_rules": ["never reveal the sealed archive"],
                "knowledge_boundary": ["knows village history"],
            }
        }
    })
    target = resolve_dialogue_target(state, "elder", EncounterResolver())
    text = build_dialogue_context(state, target, registry=registry)
    assert "canonical_speech_style" in text
    assert "canonical_dialogue_rules" in text
    assert "canonical_knowledge_boundary" in text


def test_dialogue_topic_is_parsed_and_added_to_context():
    from engine.parser.intents import parse_input
    intent = parse_input("talk to elder about the village")
    assert intent.action == "talk"
    assert intent.target == "elder"
    assert intent.topic == "the village"
    state = _state()
    registry = ScenarioRegistry.from_documents({
        "characters.json": {"elder": {"id": "elder", "dialogue_topics": ["the village", "the archive"]}}
    })
    target = resolve_dialogue_target(state, "elder", EncounterResolver())
    text = build_dialogue_context(state, target, registry=registry, topic=intent.topic)
    assert "requested_topic: 'the village'" in text
    assert "canonical_dialogue_topics" in text
