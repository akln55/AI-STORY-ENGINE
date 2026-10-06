"""LlamaCppAdapter: local-first AIAdapter backend over llama.cpp.

Per docs/TECH_STACK.md ("Local AI: llama.cpp (via local server or
llama-cpp-python)") and ADR-0003, this backend uses the `llama-cpp-python`
bindings so the engine keeps running fully offline on Android/Termux with no
network calls and no paid service.

Responsibility boundary (ARCHITECTURE.md §3, this task's brief):

    GameSession -> AIAdapter -> LlamaCppAdapter -> llama.cpp -> raw text
        -> parse_structured_response_json() -> StructuredResponse
        -> (back in GameSession) effect conversion -> validation gate -> GameState

This module does exactly one job: turn an assembled context string into a
StructuredResponse. It never touches GameState, never applies Effects, never
runs RPG rules, and never writes persistence -- same contract FakeAdapter
already satisfies. Nothing here is a second mutation path.

Optional dependency: `llama-cpp-python` is NOT required to import this module
or the rest of the engine (CONVENTIONS §1, TECH_STACK.md dependency policy).
Importing this file always succeeds; only constructing or using
LlamaCppAdapter without the package raises LlamaCppNotInstalledError. Nothing
here silently falls back to FakeAdapter -- that decision belongs to whoever
wires up GameSession, not to this adapter.

No model path is hardcoded, no model is bundled or auto-downloaded, and no
model file lives in this repository (CONVENTIONS §5: adapters read config
from a caller-supplied, git-ignored local file -- LlamaCppConfig is that
config's shape, not a place to put actual paths/secrets).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from engine.ai.adapter_base import AIAdapter
from engine.ai.reliability import AIProviderError, AICapabilities
from engine.ai.schema import StructuredResponse, parse_structured_response_json

# Optional dependency: import lazily-tolerant so `import engine` and the rest
# of the deterministic engine (and `python tools/run_tests.py`) work whether
# or not llama-cpp-python is installed. Only instantiating/using
# LlamaCppAdapter requires it.
try:
    from llama_cpp import Llama as _Llama
except ImportError:  # pragma: no cover - exercised via _Llama monkeypatching in tests
    _Llama = None


# --------------------------------------------------------------- exceptions

class LlamaCppError(AIProviderError):
    """Base class for every LlamaCppAdapter provider-specific failure.

    Deliberately NOT a subclass of ValueError: ValueError is reserved for
    "this is malformed structured output" (engine/ai/schema.py), which the
    existing GameSession._generate_with_retry loop already catches and
    retries. A provider failure (missing dependency, bad model path, a crash
    inside llama.cpp) is a different kind of problem and must not be silently
    treated as "try again with feedback" by that loop.
    """


class LlamaCppNotInstalledError(LlamaCppError):
    """Raised when `llama-cpp-python` is not installed."""


class LlamaCppModelError(LlamaCppError):
    """Raised for a bad/missing model path or a failure loading the model."""


class LlamaCppInferenceError(LlamaCppError):
    """Raised when the underlying llama.cpp call itself fails, or returns a
    response shape this adapter does not recognize."""


# ----------------------------------------------------------------- config

@dataclass
class LlamaCppConfig:
    """Explicit runtime configuration for LlamaCppAdapter.

    No field has a default model path -- `model_path` is required and there
    is no bundled/auto-downloaded model. Callers are expected to load these
    values from their own git-ignored local config file (CONVENTIONS §5);
    this dataclass only defines the shape.
    """

    model_path: str
    n_ctx: int = 4096              # context window, tokens
    temperature: float = 0.7
    max_tokens: int = 512          # max tokens in the completion
    n_gpu_layers: int = 0          # 0 = CPU-only; >0 offloads layers if the
                                    # installed llama-cpp-python build supports it
    stop: list[str] = field(default_factory=list)
    verbose: bool = False

    def __post_init__(self) -> None:
        if not self.model_path:
            raise LlamaCppModelError("LlamaCppConfig.model_path must be set; "
                                      "no default or bundled model exists")
        if self.n_ctx < 512:
            raise LlamaCppModelError("LlamaCppConfig.n_ctx must be at least 512")
        if self.max_tokens < 1 or self.max_tokens > 4096:
            raise LlamaCppModelError("LlamaCppConfig.max_tokens must be between 1 and 4096")
        if not 0.0 <= self.temperature <= 2.0:
            raise LlamaCppModelError("LlamaCppConfig.temperature must be between 0 and 2")
        if self.n_gpu_layers < 0:
            raise LlamaCppModelError("LlamaCppConfig.n_gpu_layers cannot be negative")


# ----------------------------------------------------------------- adapter

class LlamaCppAdapter(AIAdapter):
    """AIAdapter backend that runs a local GGUF model via llama-cpp-python."""

    def __init__(self, config: LlamaCppConfig):
        if _Llama is None:
            raise LlamaCppNotInstalledError(
                "llama-cpp-python is not installed. Install it with "
                "`pip install llama-cpp-python` (see docs/TECH_STACK.md) to use "
                "LlamaCppAdapter. The rest of the engine, including FakeAdapter, "
                "works without this dependency."
            )
        self.config = config
        model_path = Path(config.model_path)
        if not model_path.is_file():
            raise LlamaCppModelError(f"model file not found: {model_path}")
        try:
            self._llm = _Llama(
                model_path=str(model_path),
                n_ctx=config.n_ctx,
                n_gpu_layers=config.n_gpu_layers,
                verbose=config.verbose,
            )
        except LlamaCppError:
            raise
        except Exception as err:  # llama_cpp itself raises varied exception types
            raise LlamaCppModelError(f"failed to load model {model_path}: {err}") from err

    # --------------------------------------------------------- AIAdapter

    @property
    def capabilities(self) -> AICapabilities:
        return AICapabilities(structured_json=True, streaming=False, cancellation=False, local=True)

    def generate(self, context: str) -> StructuredResponse:
        """Assembled context in -> StructuredResponse out.

        This is the whole job: build the model prompt from the context the
        engine already assembled (engine/ai/context.py; not redesigned here),
        run inference, and hand the raw text to the shared JSON boundary
        (parse_structured_response_json). Any malformed output raises
        ValueError there -- unchanged, un-duplicated -- so GameSession's
        existing retry loop keeps working exactly as it does for any other
        adapter.
        """
        prompt = self._build_prompt(context)
        raw = self._run_inference(prompt)
        text = self._extract_text(raw)
        text = _strip_code_fence(text)
        return parse_structured_response_json(text)

    # ------------------------------------------------------------ helpers

    @staticmethod
    def _build_prompt(context: str) -> str:
        """Context (system+rules+state+recent+action, per ARCHITECTURE.md §5)
        plus the one instruction the model needs to hit the output contract.
        Does not add memory/retrieval/hidden state -- only what
        assemble_context already produced, unchanged."""
        return (
            context
            + "\n\nRespond with ONLY a single JSON object matching the "
              "structured response contract above. No prose, no markdown "
              "code fences, no commentary before or after the JSON."
        )

    def _run_inference(self, prompt: str) -> dict:
        try:
            return self._llm.create_completion(
                prompt,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                stop=self.config.stop or None,
            )
        except LlamaCppError:
            raise
        except Exception as err:
            raise LlamaCppInferenceError(f"llama.cpp inference failed: {err}") from err

    @staticmethod
    def _extract_text(raw: dict) -> str:
        try:
            return raw["choices"][0]["text"]
        except (KeyError, IndexError, TypeError) as err:
            raise LlamaCppInferenceError(
                f"unexpected llama.cpp response shape: {raw!r}"
            ) from err


def _strip_code_fence(text: str) -> str:
    """Strip a single leading/trailing markdown code fence, if present.

    Local models sometimes wrap JSON in ```/```json fences despite the
    prompt instruction not to. This handles exactly that one known quirk --
    it is not a prose parser. Anything else (extra commentary, multiple JSON
    objects, non-JSON text) is left untouched for
    parse_structured_response_json to reject as invalid JSON, per this
    task's "do not create a huge permissive parser" constraint.
    """
    stripped = text.strip()
    if stripped.startswith("```"):
        first_newline = stripped.find("\n")
        body = stripped[first_newline + 1:] if first_newline != -1 else ""
        if body.rstrip().endswith("```"):
            body = body.rstrip()[: -3]
        return body.strip()
    return stripped
