# RPG Engine

## Current state

- **Product release:** `v1.1.4`
- **Current handoff:** [`AI_START_HERE.md`](AI_START_HERE.md)
- **Project history:** [`docs/PROJECT_HISTORY.md`](docs/PROJECT_HISTORY.md)
- **Latest source CI:** **524 passed**; Python compile check PASS; Android readiness PASS; mutation smoke **3/3 detected**
- **Android debug APK:** GitHub Actions build #122 is running; APK metadata/provenance verification and artifact upload are not yet confirmed.
- **Physical Android verification:** not yet complete.

Read `AI_START_HERE.md` first. It describes current state only. Historical milestones and retired assumptions belong in `docs/PROJECT_HISTORY.md`.

## Product target

RPG Engine is a deterministic, local-first text RPG for Android—not a prose-only chatbot. The target is a standalone APK that can manage scenarios, start campaigns, play, save/load, and use local or cloud AI without requiring end users to install Termux or Python.

Local AI is designed around app-private GGUF storage and a bundled Android-native llama.cpp runtime. Gemini, OpenAI, and OpenAI-compatible API endpoints are available as cloud-provider paths. Actual local inference still requires physical-device verification. Google Colab is fallback/debug tooling, not the primary release path.

## Architecture contract

The deterministic engine owns authoritative state. AI receives bounded context and returns proposals; the engine validates and applies permitted effects atomically.

```text
Player action
  -> parser and deterministic rules
  -> authoritative GameState
  -> bounded memory/scenario/NPC context
  -> AI proposal
  -> validation/security gate
  -> atomic state update
  -> event/quest/memory updates
  -> persistence
```

AI never receives direct authority to mutate GameState, saves, databases, scenario canon, or arbitrary files.

## Current application work

- Dark mobile UI with separate player/narration bubbles and readable role labels.
- AI settings for Local GGUF, Gemini, OpenAI, and OpenAI-compatible endpoints.
- Hugging Face catalog search plus a connection diagnostic that does not download a model.
- API connectivity/model discovery controls and provider-aware endpoint/model defaults.
- Gameplay errors are presented separately from story narration; raw exception text is not shown in the chat.
- Text reveal is presentation-only and must not control persistence semantics.

## Verification boundaries

The latest test-only workflow passed 524 tests in 10.09 seconds. It also passed `compileall`, Android readiness (`version=1.1.4, target_api=36, SAF=enabled`), and mutation smoke (3/3 detected). These are source-level checks, not proof of a successful APK or physical-device behavior.

Release gates remain separate:

1. Source tests and static readiness checks.
2. Native llama.cpp Android cross-build.
3. APK packaging and package/hash/provenance verification.
4. ARM64 device startup/crash smoke.
5. Gameplay, save/load, SAF import, and local-GGUF inference smoke.

## Documentation index

| File | Purpose |
|---|---|
| `AI_START_HERE.md` | Canonical current handoff and next gates |
| `MEMORY.md` | Durable project constraints and workflow decisions |
| `HANDOFF.md` | Compact continuation handoff |
| `docs/PROJECT_HISTORY.md` | Chronological milestones, failures, and lessons |
| `docs/CONSTITUTION.md` | Binding architecture/security rules |
| `docs/ARCHITECTURE.md` | Engine architecture and gameplay loop |
| `docs/DATA_MODELS.md` | Data contracts |
| `docs/SCENARIO_DATA_FORMAT.md` | Scenario pack format |
| `docs/AI_SECURITY_SPEC.md` | AI security boundary |
| `docs/AI_EXECUTION_POLICY.md` | AI transaction policy |
| `docs/TESTING.md` | Test and release verification contract |
| `docs/ANDROID_BUILD.md` | Reproducible Android build contract |
| `docs/ANDROID_APK_SMOKE.md` | Static APK and real-device startup gates |

Technical specifications remain separate from current-state summaries. When documents disagree with implementation, current code, tests, configuration, and observed CI evidence take precedence.
