"""Static/runtime-safe checks for the Android packaging contract."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_buildozer_targets_current_play_api():
    spec = (ROOT / "buildozer.spec").read_text()
    assert "version = 1.1.4" in spec
    assert "android.api = 36" in spec
    assert "READ_EXTERNAL_STORAGE" not in spec


def test_root_entrypoint_is_android_app():
    main = (ROOT / "main.py").read_text()
    assert "from rpg_android_app import RPGEngineApp" in main
    assert "app.run()" in main


def test_android_uses_saf_picker():
    source = (ROOT / "rpg_android_app.py").read_text()
    picker = (ROOT / "rpg_android_file_picker.py").read_text()
    assert "open_scenario_document" in source
    assert "ACTION_OPEN_DOCUMENT" in picker
    assert "_saf_import" in source


def test_android_import_does_not_request_legacy_storage_permission():
    spec = (ROOT / "buildozer.spec").read_text()
    assert "WRITE_EXTERNAL_STORAGE" not in spec
    assert "READ_EXTERNAL_STORAGE" not in spec


def test_android_ui_has_model_manager_and_provider_screens():
    source = (ROOT / "rpg_android_app.py").read_text()
    assert "class AIScreen" in source
    assert "import_model" in source
    assert "set_openai_compatible" in source
    assert "Local GGUF" in source

def test_generic_api_adapter_imports_without_optional_dependencies():
    from engine.ai.openai_compatible_adapter import OpenAICompatibleAdapter
    adapter = OpenAICompatibleAdapter("https://example.com/v1", "key", "model")
    assert adapter.capabilities.structured_json is True


def test_android_uses_model_saf_picker():
    source = (ROOT / "rpg_android_app.py").read_text()
    picker = (ROOT / "rpg_android_file_picker.py").read_text()
    assert "open_model_document" in source
    assert ".gguf" in picker
    assert 'subdir="imports"' in picker


def test_desktop_model_selection_does_not_delete_user_source():
    source = (ROOT / "rpg_android_app.py").read_text()
    assert '_activate_local_model(chooser.selection[0], cleanup_source=False)' in source
    assert '_activate_local_model(path, cleanup_source=True)' in source
    assert 'def _activate_local_model(self, path, *, cleanup_source=False):' in source


def test_entrypoint_has_startup_failure_logging():
    source = (ROOT / "main.py").read_text()
    assert "startup_error.log" in source
    assert "android_entrypoint_import" in source
    assert "application_runtime" in source


def test_android_app_build_has_visible_failure_path():
    source = (ROOT / "rpg_android_app.py").read_text()
    assert "RPG Engine başlatılamadı" in source
    assert "build_error.log" in source


def test_game_ui_uses_role_bubbles_and_presentation_animation():
    source = (ROOT / "rpg_android_app.py").read_text()
    assert "class MessageBubble" in source
    assert 'role="player"' in source
    assert 'role="npc"' in source
    assert "Clock.schedule_interval" in source
    assert "show_typing" in source
    assert "remove_typing" in source


def test_presentation_animation_is_not_the_persistence_gate():
    source = (ROOT / "rpg_android_app.py").read_text()
    finish = source[source.index("    def _finish_submit"):source.index("    def _initial_game")]
    assert 'self._autosave("turn")' in finish
    assert "self.game.remove_typing()" in finish
    assert "self.game.append(result)" in finish


def test_stage_four_version_is_consistent():
    assert "1.1.4" in (ROOT / "engine/__init__.py").read_text()
    assert "version = 1.1.4" in (ROOT / "buildozer.spec").read_text()
