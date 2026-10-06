from engine.parser.intents import parse_input


def test_go():
    intent = parse_input("go forest")
    assert intent.action == "go" and intent.target == "forest"


def test_aliases_and_case():
    assert parse_input("L").action == "look"
    assert parse_input("INV").action == "inventory"
    assert parse_input("Walk Cave").action == "go"


def test_take_pickup_variant():
    assert parse_input("pick up rope").action == "take" and parse_input("pick up rope").target == "rope"
    assert parse_input("grab torch").target == "torch"


def test_talk_to():
    intent = parse_input("talk to elder")
    assert intent.action == "talk" and intent.target == "elder"


def test_unknown_is_free_text():
    intent = parse_input("sing a sad song")
    assert intent.action == "free" and intent.raw == "sing a sad song"


def test_empty_input():
    assert parse_input("").action == "free"
