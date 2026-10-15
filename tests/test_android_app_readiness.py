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
    assert '_install_imported_model(path, cleanup_source=False)' in source
    assert '_install_imported_model(path, cleanup_source=True)' in source
    assert 'def _install_imported_model(self, path, *, cleanup_source=False):' in source


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
    assert 'self.game.append(result, role="error" if error else "npc")' in finish


def test_gameplay_failures_are_separate_from_story_and_do_not_expose_raw_errors():
    source = (ROOT / "rpg_android_app.py").read_text()
    worker = source[source.index("    def _submit_worker"):source.index("    def _finish_submit")]
    finish = source[source.index("    def _finish_submit"):source.index("    def _initial_game")]
    bubble = source[source.index("class MessageBubble"):source.index("class GameplayScreen")]

    assert "self._record_gameplay_error(\"turn_submission\", exc)" in worker
    assert "API ayarlarını ve bağlantını kontrol edip tekrar dene." in worker
    assert "f\"[İşlem başarısız: {exc}]\"" not in worker
    assert 'self.game.append(result, role="error" if error else "npc")' in finish
    assert '"error": ("HATA", DANGER)' in bubble


def test_stage_four_version_is_consistent():
    assert "1.1.4" in (ROOT / "engine/__init__.py").read_text()
    assert "version = 1.1.4" in (ROOT / "buildozer.spec").read_text()


def test_bottom_navigation_has_only_three_text_tabs_and_recent_games_screen():
    source = (ROOT / "rpg_android_app.py").read_text()
    assert '("Oyun", "games"), ("Ana", "home"), ("Ayarlar", "settings")' in source
    assert 'class RecentGamesScreen(BaseScreen)' in source
    assert 'text="+ Senaryo"' in source
    assert 'class GameplayScreen(BaseScreen)' in source
    assert 'JsonStore(str(recent_path))' in source


def test_ai_settings_content_is_scrollable_on_small_android_screens():
    source = (ROOT / "rpg_android_app.py").read_text()
    ai = source[source.index("class AIScreen(BaseScreen):"):source.index("class SettingsScreen(BaseScreen):")]
    assert 'root = ScrollView(do_scroll_x=False' in ai
    assert 'content.bind(minimum_height=content.setter("height"))' in ai


def test_huggingface_catalog_is_available_from_ai_settings():
    source = (ROOT / "rpg_android_app.py").read_text()
    controller = (ROOT / "engine/app/controller.py").read_text()
    assert 'Hugging Face model kataloğu' in source
    assert 'def search_remote_models(self, query: str' in controller
    assert 'def remote_model_files(self, repo_id: str)' in controller
    assert 'def show_remote_model_files(self, repo_id)' in source
    assert 'def search_huggingface_models(' in (ROOT / "engine/ai/model_manager.py").read_text()


def test_mobile_ui_uses_void_black_theme_and_current_local_model_heading():
    source = (ROOT / "rpg_android_app.py").read_text()
    assert "BG = (0.0, 0.0, 0.0, 1)" in source
    assert "#111111" in source
    assert 'ColorProperty(TEXT)' in source
    assert 'radius = NumericProperty(dp(22))' in source
    assert 'class RecentGamesScreen(BaseScreen)' in source
    assert 'text="Yerel modeller · Local GGUF"' in source
    assert 'text="◇  Yerel modeller · Local GGUF"' not in source


def test_ai_forms_are_labelled_and_catalog_errors_are_user_friendly():
    source = (ROOT / "rpg_android_app.py").read_text()
    ai = source[source.index("class AIScreen(BaseScreen):"):source.index("class SettingsScreen(BaseScreen):")]
    assert '_field_group("Sağlayıcı", self.api_provider' in ai
    assert '_field_group("API endpoint", self.api_endpoint)' in ai
    assert '_field_group("Model adı", self.api_model)' in ai
    assert '_field_group("API anahtarı", self.api_key)' in ai
    assert 'def _friendly_catalog_error(self, error)' in ai
    assert 'text="Tekrar dene"' in ai
    assert 'text="Hugging Face model kataloğu"' in ai
    assert 'Arama başarısız: {error}' not in ai


def test_notification_dialog_is_compact_and_wrapped():
    source = (ROOT / "rpg_android_app.py").read_text()
    start = source.index("    def notify(self, text):")
    end = source.index("    def _append", start)
    notify = source[start:end]
    assert '_aligned_label(' in notify
    assert 'size_hint=(0.90, None), height=dp(178)' in notify
    assert 'text="Tamam"' in notify


def test_android_declares_network_permissions_for_huggingface_and_api():
    spec = (ROOT / "buildozer.spec").read_text()
    assert "android.permissions = INTERNET, ACCESS_NETWORK_STATE" in spec


def test_first_gameplay_entry_initializes_the_world_log_and_lifecycle_state():
    source = (ROOT / "rpg_android_app.py").read_text()
    build = source[source.index("    def build(self):"):source.index("    def _bottom_nav(self):")]
    open_game = source[source.index("    def open_gameplay(self):"):source.index("    def open_scenarios(self):")]
    initial = source[source.index("    def _initial_game(self):"):source.index("    def save(self):")]
    assert "self._lifecycle_stopping = False" in build
    assert "self._gameplay_initialized = False" in build
    assert 'if not getattr(self, "_gameplay_initialized", False)' in open_game
    assert 'self._initial_game()' in open_game
    assert 'self.controller.submit("look")' in initial
    assert "def _record_gameplay_error(self, stage, exc)" in initial


def test_gameplay_does_not_force_android_soft_keyboard_on_navigation():
    source = (ROOT / "rpg_android_app.py").read_text()
    start = source.index("class GameplayScreen")
    end = source.index("class RecentGamesScreen")
    gameplay = source[start:end]
    assert "self.input.focus()" not in gameplay
    assert 'getattr(self.app_ref, "_lifecycle_stopping", False)' in gameplay


def test_api_provider_picker_exposes_openai_compatible_and_uses_custom_endpoint():
    source = (ROOT / "rpg_android_app.py").read_text()
    ai = source[source.index("class AIScreen(BaseScreen):"):source.index("class SettingsScreen(BaseScreen):")]
    assert 'values=("OpenAI", "Gemini", "OpenAI-compatible")' in ai
    assert 'self.api_endpoint.hint_text = "Örn. https://api.provider.com/v1"' in ai
    assert 'self.api_endpoint.text = ""' in ai
    assert 'self.hf_sort = Spinner(' in ai
    assert 'sort_by=sort_by' in ai


def test_api_settings_include_a_non_generation_connectivity_probe():
    source = (ROOT / "rpg_android_app.py").read_text()
    connectivity = (ROOT / "engine/ai/connectivity.py").read_text()
    ai = source[source.index("class AIScreen(BaseScreen):"):source.index("class SettingsScreen(BaseScreen):")]
    assert "from engine.ai.connectivity import APIConnectionError, check_api_connection" in source
    assert 'text="✓  Ayarları uygula ve test et"' in ai
    assert "check_api_connection(" in ai
    assert "Thread(target=worker, daemon=True).start()" in ai
    assert "does not generate text" in connectivity


def test_api_connection_test_exposes_discovered_models_for_selection():
    source = (ROOT / "rpg_android_app.py").read_text()
    ai = source[source.index("class AIScreen(BaseScreen):"):source.index("class SettingsScreen(BaseScreen):")]
    assert 'self.api_models_picker = Spinner(' in ai
    assert 'self.api_models_picker.values = model_ids[:30]' in ai
    assert 'self.api_model.text = selected' in ai
    assert 'self.api_model_filter = PillInput(' in ai
    assert 'def _filter_api_models(self):' in ai
    assert "fixed = dp(416)" in ai
    assert "self.api_panel.height = (" in ai
    assert "self._update_api_panel_height()" in ai


def test_selecting_discovered_api_model_updates_live_adapter():
    source = (ROOT / "rpg_android_app.py").read_text()
    ai = source[source.index("class AIScreen(BaseScreen):"):source.index("class SettingsScreen(BaseScreen):")]
    callback = ai[ai.index("    def _choose_api_model"):ai.index("    def refresh(self):")]
    assert 'adapter = getattr(self.app_ref.controller.session, "adapter", None)' in callback
    assert 'adapter.model = selected' in callback
    assert 'self.api_status.text = f"Model seçildi: {selected}"' in callback


def test_api_adapter_is_replaced_only_after_successful_connection_probe():
    source = (ROOT / "rpg_android_app.py").read_text()
    ai = source[source.index("class AIScreen(BaseScreen):"):source.index("class SettingsScreen(BaseScreen):")]
    connect = ai[ai.index("    def connect_api(self):"):]
    probe_result = connect.index("result = check_api_connection(")
    configure = connect.index("self.app_ref.controller.set_gemini(api_key, model_name)")
    success_guard = connect.rfind("if apply_success:", 0, configure)
    assert probe_result < success_guard < configure
    assert "preserves the" in connect and "current adapter" in connect

def test_scenario_studio_exposes_ordered_source_queue_checkpoints_candidates_and_export():
    source = (ROOT / "rpg_android_app.py").read_text()
    studio = source[source.index("class SourceWorkspaceScreen"):source.index("class AIScreen(BaseScreen):")]
    manager = (ROOT / "engine/scenario/source_workspace.py").read_text()
    assert 'text="Senaryo Atölyesi"' in studio
    assert 'text="Kaynak ekle"' in studio
    assert 'text="İşlemeyi başlat / devam et"' in studio
    assert 'text="Çıkarılan adayları incele"' in studio
    assert 'text="İncelenmiş veriden senaryo ZIP\'i oluştur"' in studio
    assert 'text="↑"' in studio and 'text="↓"' in studio
    assert "def next_batch(" in manager
    assert "def complete_batch(" in manager
    assert "chunks_completed" in manager
    assert "source_sha256" in manager
    assert "def export_scenario_archive(" in manager


def test_scenario_export_uses_android_save_picker_and_preserves_cancellation_state():
    source = (ROOT / "rpg_android_app.py").read_text()
    picker = (ROOT / "rpg_android_file_picker.py").read_text()
    assert "save_scenario_document" in source
    assert "ACTION_CREATE_DOCUMENT" in picker
    assert "application/zip" in picker
    assert "on_cancel" in picker
    assert "def _finish_scenario_export(self, uri, error)" in source


def test_installed_scenario_removal_is_confirmed_and_demo_is_not_pinned():
    source = (ROOT / "rpg_android_app.py").read_text()
    controller = (ROOT / "engine/app/controller.py").read_text()
    assert source.count("def confirm_remove_scenario(self, item):") == 1
    assert "remove_installed_scenario" in source
    assert '"demo-bootstrap"' in source and "recent_scenarios" in source
    assert 'self.recent_scenarios = [' in source
    assert "Aktif kampanya senaryosu kaldırılamaz" in controller
    assert "Oyun kayıtları silinmez" in source


def test_test_runner_delegates_full_project_suite_and_never_claims_partial_passes():
    source = (ROOT / "tools/run_tests.py").read_text()
    assert "if tests_dir == DEFAULT_TESTS_DIR:" in source
    assert '"-m", "pytest", "-q", str(tests_dir)' in source
    assert "the full project suite requires pytest" in source
    assert "isolated smoke directories only" in source

def test_scenario_studio_exposes_candidate_identity_resolution():
    source = (ROOT / "rpg_android_app.py").read_text()
    studio = source[source.index("class SourceWorkspaceScreen"):source.index("class AIScreen(BaseScreen):")]
    manager = (ROOT / "engine/scenario/source_workspace.py").read_text()
    assert 'text="Kimlik çakışmalarını çöz"' in studio
    assert "def _resolve_identity_dialog(self):" in studio
    assert "resolve_candidate_identity(" in studio
    assert "def _record_identity_decision(" in manager
    assert "identity_decisions.json" in manager
    assert "resolve possible duplicate identities before export" in manager

def test_settings_exposes_safe_partial_model_resume_with_saved_revision():
    app = (ROOT / "rpg_android_app.py").read_text()
    manager = (ROOT / "engine/ai/model_manager.py").read_text()
    controller = (ROOT / "engine/app/controller.py").read_text()
    assert "partial_local_model_downloads()" in app
    assert 'text="Yarım kalan indirmeler"' in app
    assert 'text="Devam et"' in app
    assert "revision=item.spec.revision" in app
    assert "expected_sha256=item.spec.expected_sha256" in app
    assert "def list_partial_model_downloads(" in manager
    assert "_download_fingerprint(spec) != fingerprint" in manager
    assert "list_partial_model_downloads(default_model_storage_dir())" in controller



def test_android_llama_server_is_packaged_in_native_library_directory():
    spec = (ROOT / "buildozer.spec").read_text()
    runtime = (ROOT / "engine/ai/llama_native_runtime.py").read_text()
    native_build = (ROOT / "tools/build_llama_server_android.sh").read_text()
    apk_verifier = (ROOT / "tools/verify_android_apk.py").read_text()

    assert "android.add_libs_arm64_v8a = android_native/arm64-v8a/libllama-server.so" in spec
    assert "NATIVE_SERVER_FILENAME = \"libllama-server.so\"" in runtime
    assert "nativeLibraryDir" in runtime
    assert "install_runtime_binary" not in runtime
    assert "android_native/arm64-v8a/libllama-server.so" in native_build
    assert "NATIVE_LIBRARY_APK_PATH" in apk_verifier
    apk_contents = (ROOT / "tools/android_apk_contents.py").read_text()
    assert "NATIVE_LIBRARY_APK_PATH = " + chr(34) + "lib/arm64-v8a/libllama-server.so" + chr(34) in apk_contents


def test_android_build_verifies_native_pie_and_starts_on_pull_request():
    workflow = (ROOT / ".github/workflows/android-build.yml").read_text()
    assert "pull_request:" in workflow
    assert "Type:.*DYN" in workflow
    assert "android_native/arm64-v8a/libllama-server.so" in workflow



def test_gguf_import_picker_runs_file_copy_off_ui_thread_and_handles_completion():
    picker = (ROOT / "rpg_android_file_picker.py").read_text()
    app = (ROOT / "rpg_android_app.py").read_text()
    picker_method = picker[picker.index("def open_model_document("):]
    import_flow = app[app.index("    def import_model(self):"):app.index("    def on_start(self):")]

    assert "on_error: Callable[[str], None] | None = None" in picker_method
    assert "on_cancel: Callable[[], None] | None = None" in picker_method
    assert 'Thread(target=copy_worker, name="gguf-import-copy", daemon=True).start()' in picker_method
    assert 'temporary.replace(target)' in picker
    assert 'intent.setType("*/*")' in picker_method
    assert "on_error=self._on_model_import_error" in import_flow
    assert "on_cancel=self._on_model_import_cancel" in import_flow
    assert "def _finish_model_import_error(self, message):" in import_flow
    assert "def _finish_model_import_cancel(self):" in import_flow
    assert "def _install_imported_model(self, path, *, cleanup_source=False):" in import_flow
    assert "GGUF dosyası doğrulanıyor ve içe aktarılıyor" in import_flow


def test_hidden_api_text_inputs_cannot_capture_taps_and_focused_inputs_scroll_into_view():
    app = (ROOT / "rpg_android_app.py").read_text()
    ai = app[app.index("class AIScreen(BaseScreen):"):app.index("class SettingsScreen(BaseScreen):")]
    build = app[app.index("class RPGEngineApp(App):"):]
    pill = app[app.index("class PillInput(TextInput):"):app.index("class BodyLabel(Label):")]

    visibility = ai[ai.index("    def _update_api_advanced_visibility(self):"):ai.index("    def _update_api_panel_height(self):")]
    assert "self.api_endpoint.disabled = not show_endpoint" in visibility
    assert "self.api_endpoint.height = dp(44) if show_endpoint else 0" in visibility
    assert "self.api_model.disabled = not show_model" in visibility
    assert "self.api_model.height = dp(44) if show_model else 0" in visibility
    assert "self.api_model.opacity = 1 if show_model else 0" in visibility
    assert "self.api_model_filter.disabled = not show_model_picker" in visibility
    assert "def _input_focus_changed(self, widget, focused):" in ai
    assert "scroll.scroll_to(widget, padding=dp(18), animate=False)" in ai
    assert 'Window.softinput_mode = "pan"' in build
    assert 'kwargs.setdefault("background_disabled_normal", "")' in pill
    assert 'kwargs.setdefault("cursor_width", dp(2))' in pill
    gameplay = app[app.index("class GameplayScreen(BaseScreen):"):app.index("class RecentGamesScreen(BaseScreen):")]
    assert 'multiline=True' in gameplay
    assert "self.input.bind(text=self._resize_composer, width=self._resize_composer)" in gameplay
