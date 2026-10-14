"""Thin application controller shared by Android and future desktop UI.

UI code never mutates GameState directly. All gameplay goes through GameSession.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:
    from kivy.utils import platform as _kivy_platform
except Exception:  # pragma: no cover - controller remains importable in minimal tooling
    _kivy_platform = "unknown"

from engine.ai.gemini_adapter import GeminiAdapter
from engine.ai.llama_cpp_adapter import LlamaCppAdapter, LlamaCppConfig
from engine.ai.llama_cpp_process_adapter import LlamaCppProcessAdapter, LlamaCppProcessConfig
from engine.ai.llama_native_runtime import (
    NativeLlamaRuntimeStartError,
    NativeLlamaRuntimeConfig,
    NativeLlamaServer,
    default_runtime_dir,
    packaged_llama_server_path,
    pick_free_local_port,
)
from engine.ai.model_manager import (
    ModelSpec,
    default_model_storage_dir,
    download_huggingface_model,
    install_imported_model,
    list_installed_models,
    list_huggingface_gguf_files,
    search_huggingface_models,
    validate_model_file,
)
from engine.ai.openai_compatible_adapter import OpenAICompatibleAdapter
from engine.core.game import GameSession
from engine.demo import build_demo_state
from engine.scenario.configuration import ScenarioConfiguration
from engine.scenario.loader import ScenarioPack
from engine.scenario.manager import ScenarioManager
from engine.scenario.source_workspace import SourceBatch, SourceWorkspaceManager
from engine.persistence.saves import load_session, save_session


@dataclass
class AppController:
    session: GameSession
    scenario_id: str = "demo-bootstrap"
    scenario_pack: ScenarioPack | None = None
    scenario_config: ScenarioConfiguration | None = None
    local_runtime: NativeLlamaServer | None = None
    _dirty: bool = False
    _source_workspaces: SourceWorkspaceManager | None = None

    @classmethod
    def demo(cls, adapter=None) -> "AppController":
        return cls(GameSession(build_demo_state(), adapter=adapter))

    @property
    def turn(self) -> int:
        return self.session.clock.turn

    @property
    def location_name(self) -> str:
        location = self.session.state.character.location_id
        return self.session.state.world.locations.get(location, location)

    def installed_scenarios(self):
        return ScenarioManager().list_installed()

    def load_installed_scenario(self, scenario_id: str) -> ScenarioPack:
        return ScenarioManager().load(scenario_id)

    def install_scenario(self, archive: Path | str, *, replace: bool = False) -> ScenarioPack:
        manager = ScenarioManager()
        pack = manager.install(archive, replace=replace)
        return pack

    def source_workspace_manager(self) -> SourceWorkspaceManager:
        """Return the persistent workspace manager used by the scenario studio."""
        if self._source_workspaces is None:
            self._source_workspaces = SourceWorkspaceManager()
        return self._source_workspaces

    def list_source_workspaces(self):
        return self.source_workspace_manager().list_workspaces()

    def create_source_workspace(self, name: str, description: str = "") -> str:
        return self.source_workspace_manager().create(name, description)

    def add_source_to_workspace(self, workspace_id: str, path: str | Path, *, chapter_hint: int | None = None):
        return self.source_workspace_manager().add_source(workspace_id, path, chapter_hint=chapter_hint)

    def reorder_workspace_source(self, workspace_id: str, source_id: str, delta: int):
        return self.source_workspace_manager().reorder_source(workspace_id, source_id, delta)

    def remove_workspace_source(self, workspace_id: str, source_id: str) -> bool:
        return self.source_workspace_manager().remove_source(workspace_id, source_id)

    def process_source_queue(self, workspace_id: str, *, progress_callback=None, max_batches: int | None = None) -> int:
        """Extract and checkpoint source batches through the currently selected AI adapter.

        Extraction results remain intermediate candidates. This method never mutates
        the installed scenario registry, active GameState, or gameplay save slots.
        """
        manager = self.source_workspace_manager()
        adapter = getattr(self.session, "adapter", None)
        if adapter is None or not callable(getattr(adapter, "generate", None)):
            raise RuntimeError("Etkin bir AI modeli yok. Önce AI ayarlarından model veya API sağlayıcısı bağla.")

        known = []
        registry = getattr(self.session, "scenario_registry", None)
        if registry is not None:
            for category in registry.categories():
                for record in registry.all(category):
                    known.append({"category": record.category, "id": record.id,
                                  "name": str(record.data.get("name") or record.id)})
        for saved in manager.read_batch_results(workspace_id):
            extraction = saved.get("extraction", {})
            for entity in extraction.get("entities", []):
                if isinstance(entity, dict):
                    known.append({
                        "category": entity.get("category"),
                        "id": entity.get("canonical_id") or entity.get("id_candidate"),
                        "name": entity.get("name"),
                    })
        # Stable dedup keeps the prompt index bounded and ordered.
        seen = set()
        known_index = []
        for entity in known:
            key = (entity.get("category"), entity.get("id"), entity.get("name"))
            if key in seen or not all(isinstance(value, str) and value for value in key):
                continue
            seen.add(key)
            known_index.append(entity)

        completed = 0
        while max_batches is None or completed < max_batches:
            batch = manager.next_batch(workspace_id)
            if batch is None:
                break
            try:
                prompt = manager.build_extraction_prompt(batch, existing_entities=known_index)
                response = adapter.generate(prompt)
                narrative = response if isinstance(response, str) else getattr(response, "narrative", None)
                if not isinstance(narrative, str) or not narrative.strip():
                    raise ValueError("model returned no extraction JSON")
                extraction = manager.parse_extraction_response(narrative)
                manager.complete_batch(batch, extraction)
                for entity in extraction.get("entities", []):
                    known_index.append({
                        "category": entity["category"],
                        "id": entity.get("canonical_id") or entity["id_candidate"],
                        "name": entity["name"],
                    })
                completed += 1
                if progress_callback is not None:
                    progress_callback(batch, None)
            except Exception as exc:
                manager.fail_batch(batch, f"AI extraction failed ({type(exc).__name__}); check provider output and retry")
                if progress_callback is not None:
                    progress_callback(batch, type(exc).__name__)
                raise RuntimeError(
                    f"Kaynak işleme durdu: {batch.source_name}, parça {batch.chunk_index + 1}. "
                    "Hata durumu kaydedildi; sağlayıcıyı kontrol edip devam edebilirsin."
                ) from None
        return completed

    @property
    def dirty(self) -> bool:
        """Whether the current campaign has unsaved gameplay changes."""
        return self._dirty

    def start_scenario(self, pack: ScenarioPack, *, mode="sequential", selected_pack_ids=None, start_chapter=None, adapter=None) -> None:
        self.session = GameSession.from_scenario_pack(
            pack, adapter=adapter, mode=mode, selected_pack_ids=selected_pack_ids, start_chapter=start_chapter
        )
        config = self.session.scenario_configuration
        self.scenario_id = pack.scenario_id
        self.scenario_pack = pack
        self.scenario_config = config
        self._dirty = True

    @property
    def is_android(self) -> bool:
        return _kivy_platform == "android"

    def shutdown(self) -> None:
        self._stop_local_runtime()

    def _stop_local_runtime(self) -> None:
        if self.local_runtime is not None:
            self.local_runtime.stop()
            self.local_runtime = None

    def set_gemini(self, api_key: str, model: str = "") -> None:
        self._stop_local_runtime()
        self.session.adapter = GeminiAdapter(api_key, model=model or "gemini-3.6-flash")

    def installed_local_models(self, *, verify_integrity: bool = False):
        # UI listings use cheap GGUF header/size checks. Full SHA-256 is
        # performed immediately before model execution instead of blocking the
        # Kivy thread on multi-GB files.
        return list_installed_models(
            default_model_storage_dir(), verify_integrity=verify_integrity
        )

    def install_local_model(self, source: str | Path):
        return install_imported_model(source, default_model_storage_dir())

    def download_local_model(self, spec: ModelSpec, progress_callback=None):
        return download_huggingface_model(
            spec, default_model_storage_dir(), progress_callback=progress_callback
        )

    def search_remote_models(self, query: str, *, limit: int = 12, sort_by: str = "downloads"):
        return search_huggingface_models(query, limit=limit, sort_by=sort_by)

    def remote_model_files(self, repo_id: str):
        return list_huggingface_gguf_files(repo_id)

    def set_local_model(self, model_path: str, *, n_ctx: int = 4096, max_tokens: int = 512,
                        temperature: float = 0.7, n_gpu_layers: int = 0) -> None:
        # Android must use the native llama.cpp server. The Python llama-cpp
        # adapter remains available for desktop/development environments only.
        packaged = packaged_llama_server_path()
        if packaged.is_file():
            # Validate the complete GGUF before touching the currently running
            # model. A bad replacement must not take down a healthy session.
            validated = validate_model_file(model_path)
            runtime = NativeLlamaServer(NativeLlamaRuntimeConfig(
                binary_source=packaged,
                runtime_dir=default_runtime_dir(),
                model_path=validated.path,
                port=pick_free_local_port(),
                ctx_size=n_ctx,
                max_tokens=max_tokens,
            ))
            try:
                base_url = runtime.start()
            except Exception as exc:
                runtime.stop()
                raise NativeLlamaRuntimeStartError(
                    f"Android local AI runtime could not start: {exc}"
                ) from exc

            # The new server is healthy before the old one is stopped. This
            # makes model switching transactional from the gameplay side.
            previous_runtime = self.local_runtime
            self.local_runtime = runtime
            self.session.adapter = LlamaCppProcessAdapter(LlamaCppProcessConfig(
                server_url=base_url,
                max_tokens=max_tokens,
                temperature=temperature,
            ))
            if previous_runtime is not None:
                previous_runtime.stop()
            return

        if self.is_android:
            raise NativeLlamaRuntimeStartError(
                "Android local AI runtime binary is not packaged yet; build the pinned llama.cpp ARM64 runtime first."
            )
        self._stop_local_runtime()
        self.session.adapter = LlamaCppAdapter(LlamaCppConfig(
            model_path=model_path, n_ctx=n_ctx, max_tokens=max_tokens,
            temperature=temperature, n_gpu_layers=n_gpu_layers,
        ))

    def set_openai_compatible(self, endpoint: str, api_key: str, model: str = "") -> None:
        self._stop_local_runtime()
        self.session.adapter = OpenAICompatibleAdapter(endpoint, api_key, model)

    @property
    def provider_name(self) -> str:
        adapter = self.session.adapter
        if adapter is None:
            return "Demo / AI kapalı"
        name = adapter.__class__.__name__
        return {
            "GeminiAdapter": "Gemini",
            "LlamaCppAdapter": "Local GGUF",
            "LlamaCppProcessAdapter": "Local GGUF",
            "OpenAICompatibleAdapter": "OpenAI-compatible API",
        }.get(name, name)

    def submit(self, text: str) -> str:
        text = text.strip()
        if not text:
            return ""
        before_turn = self.session.clock.turn
        result = self.session.handle_input(text)
        if self.session.clock.turn != before_turn:
            self._dirty = True
        return result

    def save(self, slot: str = "slot1", save_dir: Path | None = None) -> Path:
        path = save_session(self.session, slot=slot, save_dir=save_dir)
        self._dirty = False
        return path

    def load(self, slot: str = "slot1", save_dir: Path | None = None, adapter=None) -> None:
        context = None
        if self.scenario_pack is not None:
            from engine.scenario.context import ScenarioContext
            context = ScenarioContext(self.scenario_pack, self.scenario_config) if self.scenario_config is not None else None
        self.session = load_session(
            slot=slot, save_dir=save_dir, adapter=adapter, scenario_id=self.scenario_id,
            scenario_context=context,
        )
        self._dirty = False
