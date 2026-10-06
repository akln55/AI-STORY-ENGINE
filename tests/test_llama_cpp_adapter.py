"""Tests for engine/ai/llama_cpp_adapter.py.

No real llama-cpp-python package or model file is required. When the
dependency genuinely isn't installed (the case in this sandbox / CI), those
tests exercise the real "not installed" path. The mocked-success/failure
tests monkeypatch the module's `_Llama` symbol with a small scripted stub --
same spirit as engine/ai/fake.py, no unittest.mock needed, no network calls
(CONVENTIONS §4).
"""

from __future__ import annotations

import tempfile
from contextlib import contextmanager
from pathlib import Path

import engine.ai.llama_cpp_adapter as lcp
from engine.ai.adapter_base import AIAdapter
from engine.ai.llama_cpp_adapter import (
    LlamaCppAdapter,
    LlamaCppConfig,
    LlamaCppInferenceError,
    LlamaCppModelError,
    LlamaCppNotInstalledError,
)
from engine.cli import build_session


@contextmanager
def raises(exc):
    try:
        yield
    except exc:
        return
    raise AssertionError(f"expected {exc.__name__} was not raised")


def _tmp_model_file() -> str:
    """A real (empty) file so the path-exists check passes; llama_cpp itself
    is stubbed out, so its content is never read."""
    fd, path = tempfile.mkstemp(suffix=".gguf")
    import os
    os.close(fd)
    return path


class _StubLlama:
    """Scripted stand-in for llama_cpp.Llama. Records constructor kwargs so
    tests can assert config was passed through, and returns/raises whatever
    the test configures."""

    last_init_kwargs: dict | None = None  # class-level, for assertion after construction

    def __init__(self, **kwargs):
        _StubLlama.last_init_kwargs = kwargs
        if kwargs.get("model_path") == "TRIGGER_INIT_FAILURE":
            raise RuntimeError("simulated llama.cpp load failure")
        self.completion_calls: list[dict] = []

    def create_completion(self, prompt, **kwargs):
        self.completion_calls.append({"prompt": prompt, **kwargs})
        if _StubLlama.script == "raise":
            raise RuntimeError("simulated inference crash")
        if _StubLlama.script == "bad_shape":
            return {"unexpected": "shape"}
        return {"choices": [{"text": _StubLlama.next_text}]}

    # Configured per-test via class attributes (simple, matches FakeAdapter's style)
    script = "ok"
    next_text = '{"narrative": "The torch flickers."}'


@contextmanager
def _stubbed_llama():
    """Swap in _StubLlama as the module's optional-dependency symbol for the
    duration of a test, then restore whatever was there before (None in this
    sandbox, since llama-cpp-python isn't installed)."""
    original = lcp._Llama
    lcp._Llama = _StubLlama
    try:
        yield
    finally:
        lcp._Llama = original


# ------------------------------------------------------------- adapter shape

def test_llama_cpp_adapter_implements_ai_adapter():
    assert issubclass(LlamaCppAdapter, AIAdapter)


# ----------------------------------------------------- missing dependency

def test_missing_dependency_raises_clear_error_and_does_not_break_import():
    """Exercises the real path in this sandbox: llama-cpp-python is not
    installed. `import engine` and this module must already have succeeded
    to reach this test at all; constructing the adapter must fail clearly."""
    original = lcp._Llama
    lcp._Llama = None  # explicit, in case another test's stub leaked
    try:
        with raises(LlamaCppNotInstalledError):
            LlamaCppAdapter(LlamaCppConfig(model_path=_tmp_model_file()))
    finally:
        lcp._Llama = original


def test_core_engine_import_does_not_require_llama_cpp():
    """This test module having already imported both engine.ai.llama_cpp_adapter
    and engine.cli without error (llama-cpp-python is absent in this sandbox)
    is itself the proof. Confirm core engine construction still works, without
    reloading the adapter module -- reload() would rebuild its exception
    classes with new identities and break every other test's `except <cls>`
    matching against the originally-imported class objects."""
    assert lcp.LlamaCppAdapter is LlamaCppAdapter  # same class object, no reload games
    build_session()  # core engine construction is unaffected by the optional adapter


# ----------------------------------------------------------- config

def test_empty_model_path_rejected_without_needing_the_dependency():
    with raises(LlamaCppModelError):
        LlamaCppConfig(model_path="")


def test_nonexistent_model_path_rejected():
    with _stubbed_llama():
        with raises(LlamaCppModelError):
            LlamaCppAdapter(LlamaCppConfig(model_path="/no/such/model.gguf"))


def test_model_init_failure_wrapped_as_model_error():
    with _stubbed_llama():
        with raises(LlamaCppModelError):
            LlamaCppAdapter(LlamaCppConfig(model_path="TRIGGER_INIT_FAILURE"))


def test_config_passed_through_to_underlying_runtime():
    with _stubbed_llama():
        cfg = LlamaCppConfig(model_path=_tmp_model_file(), n_ctx=2048,
                             n_gpu_layers=20, verbose=True)
        LlamaCppAdapter(cfg)
        kwargs = _StubLlama.last_init_kwargs
        assert kwargs["model_path"] == cfg.model_path
        assert kwargs["n_ctx"] == 2048
        assert kwargs["n_gpu_layers"] == 20
        assert kwargs["verbose"] is True


def test_generation_config_passed_through_to_completion_call():
    with _stubbed_llama():
        cfg = LlamaCppConfig(model_path=_tmp_model_file(), temperature=0.2,
                             max_tokens=64, stop=["STOP"])
        adapter = LlamaCppAdapter(cfg)
        _StubLlama.script = "ok"
        _StubLlama.next_text = '{"narrative": "ok"}'
        adapter.generate("PLAYER ACTION: look")
        call = adapter._llm.completion_calls[-1]
        assert call["temperature"] == 0.2
        assert call["max_tokens"] == 64
        assert call["stop"] == ["STOP"]


# -------------------------------------------------------- successful output

def test_mocked_valid_json_becomes_structured_response():
    with _stubbed_llama():
        adapter = LlamaCppAdapter(LlamaCppConfig(model_path=_tmp_model_file()))
        _StubLlama.script = "ok"
        _StubLlama.next_text = (
            '{"narrative": "You find a rusty key.", '
            '"state_changes": [{"type": "inventory", "target": "key", '
            '"operation": "take", "value": "player"}]}'
        )
        resp = adapter.generate("PLAYER ACTION: search the drawer")
        assert resp.narrative == "You find a rusty key."
        assert resp.state_changes[0].target == "key"


def test_mocked_fenced_json_is_stripped_and_parsed():
    with _stubbed_llama():
        adapter = LlamaCppAdapter(LlamaCppConfig(model_path=_tmp_model_file()))
        _StubLlama.script = "ok"
        _StubLlama.next_text = '```json\n{"narrative": "Fenced but valid."}\n```'
        resp = adapter.generate("PLAYER ACTION: look")
        assert resp.narrative == "Fenced but valid."


# ---------------------------------------------------------- malformed output

def test_malformed_json_text_reaches_shared_boundary_and_is_rejected():
    with _stubbed_llama():
        adapter = LlamaCppAdapter(LlamaCppConfig(model_path=_tmp_model_file()))
        _StubLlama.script = "ok"
        _StubLlama.next_text = "I think the player should find a key here."  # not JSON at all
        with raises(ValueError):
            adapter.generate("PLAYER ACTION: search the drawer")


def test_json_missing_required_field_rejected():
    with _stubbed_llama():
        adapter = LlamaCppAdapter(LlamaCppConfig(model_path=_tmp_model_file()))
        _StubLlama.script = "ok"
        _StubLlama.next_text = '{"state_changes": []}'  # missing 'narrative'
        with raises(ValueError):
            adapter.generate("PLAYER ACTION: look")


def test_unexpected_response_shape_raises_inference_error():
    with _stubbed_llama():
        adapter = LlamaCppAdapter(LlamaCppConfig(model_path=_tmp_model_file()))
        _StubLlama.script = "bad_shape"
        with raises(LlamaCppInferenceError):
            adapter.generate("PLAYER ACTION: look")


# --------------------------------------------------------- provider failures

def test_inference_crash_propagates_as_inference_error():
    with _stubbed_llama():
        adapter = LlamaCppAdapter(LlamaCppConfig(model_path=_tmp_model_file()))
        _StubLlama.script = "raise"
        with raises(LlamaCppInferenceError):
            adapter.generate("PLAYER ACTION: look")


# -------------------------------------------------- does not touch GameState

def test_adapter_never_mutates_state_directly_only_through_validation_gate():
    """Wire a stubbed LlamaCppAdapter into a real GameSession and prove the
    normal path still applies: proposal -> Effect -> validation -> GameState.
    An invalid proposal must be rejected exactly like FakeAdapter's."""
    with _stubbed_llama():
        adapter = LlamaCppAdapter(LlamaCppConfig(model_path=_tmp_model_file()))
        session = build_session(adapter=adapter)

        _StubLlama.script = "ok"
        _StubLlama.next_text = (
            '{"narrative": "A sword materializes!", '
            '"state_changes": [{"type": "inventory", "target": "excalibur", '
            '"operation": "take", "value": "player"}]}'
        )
        out = session.handle_input("wish for a sword")
        # 'excalibur' is not a real item in the demo world -> validation rejects it
        assert "excalibur" not in session.state.character.inventory
        assert session.last_report is not None and len(session.last_report.rejected) == 1
        assert ("could not apply" in out or "does not fully succeed" in out or "attempt" in out.lower())

        _StubLlama.next_text = '{"narrative": "Nothing happens."}'
        hp_before = session.state.character.hp
        session.handle_input("do nothing")
        assert session.state.character.hp == hp_before  # narration-only, no mutation


def test_llama_cpp_adapter_has_no_state_or_apply_or_persistence_attributes():
    """Cheap structural guard against scope creep: the adapter class must not
    grow a second mutation path (no apply_effects/validate/save/etc.)."""
    forbidden = {"apply_effects", "validate_effect", "validate_effects",
                 "save_session", "load_session", "mutate_state", "state"}
    present = forbidden & set(dir(LlamaCppAdapter))
    assert not present, f"LlamaCppAdapter must not define: {present}"

def test_llama_config_rejects_unsafe_runtime_bounds():
    from engine.ai.llama_cpp_adapter import LlamaCppConfig, LlamaCppModelError
    for kwargs in (
        {"n_ctx": 256},
        {"max_tokens": 5000},
        {"temperature": -0.1},
        {"temperature": 2.1},
        {"n_gpu_layers": -1},
    ):
        try:
            LlamaCppConfig(model_path="model.gguf", **kwargs)
        except LlamaCppModelError:
            pass
        else:
            raise AssertionError(f"expected config rejection: {kwargs}")
