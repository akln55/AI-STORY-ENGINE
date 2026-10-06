from engine.core.invariants import check_invariants, InvariantError, DISPOSITION_MIN, DISPOSITION_MAX
from engine.demo import build_demo_state


def test_demo_state_satisfies_invariants():
    check_invariants(build_demo_state())


def test_unknown_character_location():
    s = build_demo_state()
    s.character.location_id = "nowhere"
    try:
        check_invariants(s)
        ok = False
    except InvariantError as e:
        ok = "location" in str(e)
    assert ok


def test_item_both_owner_and_location():
    s = build_demo_state()
    s.world.items["rope"].owner = "player"
    # location_id still set
    try:
        check_invariants(s)
        ok = False
    except InvariantError:
        ok = True
    assert ok


def test_item_neither_owner_nor_location():
    s = build_demo_state()
    s.world.items["rope"].location_id = None
    s.world.items["rope"].owner = None
    try:
        check_invariants(s)
        ok = False
    except InvariantError:
        ok = True
    assert ok


def test_dead_with_positive_hp():
    s = build_demo_state()
    s.world.npcs["wolf"].alive = False
    s.world.npcs["wolf"].hp = 5
    try:
        check_invariants(s)
        ok = False
    except InvariantError:
        ok = True
    assert ok


def test_disposition_bounds_constant():
    assert DISPOSITION_MIN == -100
    assert DISPOSITION_MAX == 100
