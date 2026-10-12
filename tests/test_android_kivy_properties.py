from pathlib import Path
import ast


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = ROOT / "rpg_android_app.py"


def _class_node(name: str) -> ast.ClassDef:
    tree = ast.parse(APP_SOURCE.read_text(encoding="utf-8"))
    return next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == name
    )


def _class_assignment_names(node: ast.ClassDef) -> set[str]:
    names = set()
    for statement in node.body:
        if isinstance(statement, ast.Assign):
            names.update(
                target.id for target in statement.targets
                if isinstance(target, ast.Name)
            )
        elif isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
            names.add(statement.target.id)
    return names


def _init_method(node: ast.ClassDef) -> ast.FunctionDef:
    return next(
        statement for statement in node.body
        if isinstance(statement, ast.FunctionDef) and statement.name == "__init__"
    )


def _has_kwargs_default(init: ast.FunctionDef, name: str) -> bool:
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "setdefault"
        and len(node.args) >= 2
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == name
        for node in ast.walk(init)
    )


def test_pill_input_sets_mutable_padding_on_instance_not_class():
    pill_input = _class_node("PillInput")
    class_names = _class_assignment_names(pill_input)

    assert "padding" not in class_names, (
        "Kivy's inherited padding property must not be replaced by a list "
        "at class definition time."
    )
    assert "font_size" not in class_names, (
        "Inherited Kivy font_size is a Property descriptor; a float class "
        "attribute breaks Kivy widget initialization."
    )
    assert "multiline" not in class_names, (
        "Inherited Kivy multiline must be configured per instance."
    )

    init = _init_method(pill_input)
    for name in ("padding", "font_size", "multiline"):
        assert _has_kwargs_default(init, name), (
            f"PillInput should configure {name} via instance kwargs."
        )


def test_body_label_does_not_replace_inherited_kivy_property_descriptors():
    body_label = _class_node("BodyLabel")
    class_names = _class_assignment_names(body_label)

    for name in ("font_size", "halign", "valign", "text_size"):
        assert name not in class_names, (
            f"BodyLabel must not replace inherited Kivy property {name!r} "
            "with a plain class attribute."
        )

    init = _init_method(body_label)
    for name in ("font_size", "halign", "valign", "text_size"):
        assert _has_kwargs_default(init, name), (
            f"BodyLabel should configure {name} via instance kwargs."
        )



def test_soft_button_updates_pressed_and_disabled_visual_states():
    soft_button = _class_node("SoftButton")
    init = _init_method(soft_button)
    init_source = ast.get_source_segment(APP_SOURCE.read_text(encoding="utf-8"), init) or ""

    assert _has_kwargs_default(init, "color"), (
        "SoftButton must set a readable text color on the instance."
    )
    assert _has_kwargs_default(init, "disabled_color"), (
        "Disabled button text must use an explicit accessible color."
    )
    assert "state=self._sync" in init_source, (
        "The button background must refresh when its pressed state changes."
    )
    assert "disabled=self._sync" in init_source, (
        "The button background must refresh when it becomes disabled."
    )


def test_accent_button_has_explicit_contrasting_text_color():
    accent_button = _class_node("AccentButton")
    class_names = _class_assignment_names(accent_button)

    assert "color" in class_names, (
        "Primary action buttons must define their own text color rather than "
        "inherit a potentially conflicting default."
    )
    init = _init_method(accent_button)
    assert _has_kwargs_default(init, "color"), (
        "Primary action text color must also be set explicitly per instance."
    )
