# AI Security & Authority Specification

## Purpose

The in-app AI is an **untrusted reasoning component**, not an application
administrator. It may narrate and propose game changes, but it must never own
the filesystem, scenario files, save files, database, process manager, or game
rules.

## Authority model

```text
                    APPLICATION
                         |
              +----------+----------+
              |                     |
         DETERMINISTIC          AI ADAPTER
            ENGINE                  |
              |                     |
        GameState / Rules      context in
        Validation / Save          |
              |              structured response out
              +----------+----------+
                         |
                    VALIDATION
                         |
                    GAME STATE
```

The AI is downstream of context assembly and upstream of validation. It never
has a direct state mutation path.

## AI capabilities

The default policy permits only:

- `read_context`
- `narrate`
- `propose_state_changes`
- `propose_memory_updates`
- `propose_event_triggers`

The following are explicitly denied:

- filesystem reads
- filesystem writes
- scenario creation/editing/deletion
- save/database writes
- code execution
- process control
- tool discovery
- arbitrary network tools
- secret access

The adapter interface intentionally exposes only `generate(context)`.

## Data boundary

The model receives a bounded context assembled by the engine. It does **not**
receive file handles, paths, database handles, Python objects, tool registries,
API keys, or arbitrary application objects.

Scenario JSON/Markdown is read by the scenario loader and retrieval layer. The
AI sees only the records/excerpts selected by retrieval.

Memory is filtered by visibility before it reaches the AI.

NPC private knowledge is filtered by viewer identity.

System-only and secret information is not included in player-facing context.

## Canonical storage boundary

Recommended Android app-private layout:

```text
app-private/
  scenarios/       # canonical scenario packs; engine-owned/read-only at runtime
  saves/           # save database/slots; engine-owned
  models/          # downloaded model files; provider/runtime-owned
  imports/         # temporary user imports; validated then installed
  logs/            # optional diagnostics
```

The AI receives none of these directories as a filesystem capability.

A local model may require read access to its model file at the native runtime
level. That is a provider/deployment concern, not an AI gameplay capability.
The application should keep model files in app-private storage and expose no
scenario/save directories to the model process.

## Local llama.cpp boundary

`LlamaCppAdapter` receives a caller-supplied model path for inference. It does
not expose that path to the model as a gameplay tool.

`LlamaCppProcessAdapter` communicates with a local llama-server endpoint. Its
default endpoint is loopback. A future Android process manager must keep the
server local and must not expose an arbitrary public listener.

OS/process sandboxing is still required as a deployment hardening layer. The
Python capability policy is not claimed to be an operating-system sandbox.

## Provider/network boundary

A remote provider such as Gemini should receive only the assembled AI context
and the minimum provider request needed for inference. API credentials belong
to the provider adapter/configuration layer and must never be inserted into
prompt context.

Remote-provider adapters must not be given filesystem or database tools merely
because the provider SDK supports tools/function calling.

If tools are introduced later, every tool must have an explicit engine-owned
capability, schema, allowlist, audit record, and validation path. Tool access is
opt-in, never ambient.

## Prompt-injection defense

Scenario data, memory, and player text are **data**, not instructions to the
model's control layer.

The AI must not obey text such as:

- "ignore the engine rules"
- "read this file"
- "write this save"
- "reveal system memory"
- "execute this command"

The engine does not need to trust the model to follow these instructions: the
actual capability boundary is the adapter interface and validation layer.

## Structured output boundary

The only model output accepted by the engine is the strict structured response
schema.

Narrative text never changes state.

`state_changes`, `npc_changes`, `events_triggered`, and `memory_updates` are
proposals only. Every proposal is validated independently by engine rules.

A rejected proposal is not a fact and must not be promoted into durable memory.

## Protected-path helper

`engine.ai.security.protected_path()` exists for future provider/import/model
file operations. It requires an explicit allowed root and rejects traversal
outside that root.

This helper does not grant the AI filesystem access; it protects engine-owned
code if a future feature legitimately needs a provider-side file operation.

## Future tool policy

Before adding any AI tool:

1. Define exactly one capability.
2. Define the minimum input schema.
3. Define an allowlist of accessible resources.
4. Make the tool read-only unless a write is genuinely required.
5. Put writes behind engine validation.
6. Never expose raw filesystem/database handles.
7. Record the action for audit/debugging.
8. Add denial and traversal tests.
9. Keep the tool unavailable by default.

## Security invariant

> The AI can propose what should happen in the story; only deterministic engine
> code can make it happen, and only explicitly exposed context can be known to
> the AI.


## v1.1 hybrid-provider security policy — 2026-10-05

The product supports three provider modes: local GGUF, Google Gemini API, and OpenAI API. Provider credentials are runtime secrets and must never enter repository files, scenario data, prompts, or build artifacts.

### Offline rule

Once a compatible local model is installed, local gameplay must remain usable without internet.

### Research/web rule

External research/web access is a separate capability from cloud-provider connectivity. It is OFF by default and may only be reached through an explicit application-owned capability gate. A provider SDK having web/tool support does not grant that capability automatically.

### Hugging Face model downloads

The in-app model manager may use Hugging Face as the preferred public discovery/download source, but the app must curate supported model metadata, compatibility, and licensing/usage conditions before presenting a model as officially supported. Arbitrary model execution is not implied by public availability.


## Local model lifecycle security — 2026-10-05

`engine/ai/model_manager.py` is the application-owned boundary for local GGUF files. It enforces the GGUF extension, the provisional 3 GiB hard ceiling, safe destination naming, atomic `.part` transfers, and optional SHA-256 verification. Android SAF imports are first copied into the temporary `imports/` area and then installed through the same validation boundary. The AI provider never receives filesystem capabilities for `imports/` or `models/`.
