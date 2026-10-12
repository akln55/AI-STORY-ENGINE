from pathlib import Path
import ast


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = ROOT / "rpg_android_app.py"


def test_pill_input_sets_mutable_padding_on_instance_not_class():
    source = APP_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    pill_input = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "PillInput"
    )

    class_padding_assignments = [
        node for node in pill_input.body
        if isinstance(node, (ast.Assign, ast.AnnAssign))
        and (
            any(isinstance(target, ast.Name) and target.id == "padding"
                for target in (node.targets if isinstance(node, ast.Assign) else [node.target]))
        )
    ]
    assert not class_padding_assignments, (
        "Kivy's inherited padding property must not be replaced by a list "
        "at class definition time."
    )

    init = next(
        node for node in pill_input.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    assert any(
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Attribute)
        and node.value.func.attr == "setdefault"
        and len(node.value.args) >= 2
        and isinstance(node.value.args[0], ast.Constant)
        and node.value.args[0].value == "padding"
        and isinstance(node.value.args[1], ast.List)
        for node in ast.walk(init)
    ), "PillInput should preserve its padding defaults via instance kwargs."
