from engine.core.state import CharacterState, GameState, NPCState, TechniqueState, WorldState
from engine.core.validation import apply_effects
from engine.parser.intents import parse_input
from engine.rules.base import Effect
from engine.rules.basic import AttackRule, TechniqueRule

def state():
    npc = NPCState(id="goblin", name="Goblin", location_id="camp", hp=12, max_hp=12, attack_power=4, defense=2, xp_reward=120)
    return GameState(
        character=CharacterState(location_id="camp", stamina=100, max_stamina=100, attack_power=15, defense=1),
        world=WorldState(locations={"camp":"Camp"}, exits={}, npcs={"goblin":npc}, techniques={
            "slash": TechniqueState(id="slash", name="Slash", power=8, stamina_cost=20),
        })
    )

def test_attack_uses_combat_stats_and_awards_xp_on_defeat():
    s=state(); r=AttackRule().resolve(parse_input("attack goblin"),s)
    assert r is not None
    assert apply_effects(r.effects,s).clean
    assert not s.world.npcs["goblin"].alive
    assert s.character.level == 2
    assert s.character.xp == 20

def test_attack_cannot_deal_less_than_one_damage():
    s=state(); s.world.npcs["goblin"].defense=999
    r=AttackRule().resolve(parse_input("attack goblin"),s); assert r is not None
    assert apply_effects(r.effects,s).clean
    assert s.world.npcs["goblin"].hp == 11

def test_technique_requires_known_technique_and_stamina():
    s=state(); r=TechniqueRule().resolve(parse_input("use slash goblin"),s)
    assert r is not None and "do not know" in r.narration_hint
    s.character.techniques=["slash"]
    s.character.stamina=10
    r=TechniqueRule().resolve(parse_input("use slash goblin"),s)
    assert "exhausted" in r.narration_hint

def test_technique_deals_power_plus_attack_minus_defense():
    s=state(); s.character.techniques=["slash"]; s.world.npcs["goblin"].hp=30
    r=TechniqueRule().resolve(parse_input("use slash goblin"),s); assert r is not None
    assert apply_effects(r.effects,s).clean
    assert s.world.npcs["goblin"].hp == 9


def test_hostile_npc_retaliates_when_surviving_attack():
    s=state(); s.character.defense=1; s.world.npcs["goblin"].hp=30; s.world.npcs["goblin"].disposition=-50
    r=AttackRule().resolve(parse_input("attack goblin"),s)
    assert r is not None
    report=apply_effects(r.effects,s)
    assert report.clean
    assert s.character.hp == 97


def test_non_hostile_npc_does_not_retaliate():
    s=state(); s.world.npcs["goblin"].hp=30; s.world.npcs["goblin"].disposition=-10
    r=AttackRule().resolve(parse_input("attack goblin"),s)
    assert r is not None
    assert apply_effects(r.effects,s).clean
    assert s.character.hp == 100


def test_technique_retaliation_is_atomic():
    s=state(); s.character.techniques=["slash"]; s.world.npcs["goblin"].hp=30
    s.world.npcs["goblin"].disposition=-100
    r=TechniqueRule().resolve(parse_input("use slash goblin"),s)
    assert r is not None
    assert apply_effects(r.effects,s).clean
    assert s.world.npcs["goblin"].hp == 9
    assert s.character.hp == 97
