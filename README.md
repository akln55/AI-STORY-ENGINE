# RPG Engine

## Current state

- **Product release:** `v1.1.4`
- **Current handoff:** [`AI_START_HERE.md`](AI_START_HERE.md)
- **Project history:** [`docs/PROJECT_HISTORY.md`](docs/PROJECT_HISTORY.md)
- **Latest green networking baseline:** [CI run 38345698305](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38345698305), **538 passed**; compileall, Android readiness, and mutation smoke **3/3 detected**
- **Current source CI:** [run 38439396555](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38439396555) checks the follow-up to a stale UI height assertion; confirm its result before claiming the latest code is green.
- **AI connectivity investigation:** see [AI networking status](docs/AI_NETWORKING_STATUS.md). Physical mobile-data and provider-generation behavior are not yet verified.
- **Android APK status:** no APK build was started for the current networking task. For release packaging status, use the [Android build workflow](https://github.com/akln55/AI-STORY-ENGINE/actions/workflows/android-build.yml).
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
- Verified HTTPS transport shared by remote AI calls, plus a separate actual-generation test in AI settings.
- Gameplay errors are presented separately from story narration; raw exception text is not shown in the chat.
- Text reveal is presentation-only and must not control persistence semantics.

## Verification boundaries

The latest fully green networking baseline is [run 38345698305](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38345698305) with **538 tests** plus compileall, Android readiness, and mutation smoke passing. A subsequent UI assertion was updated; the latest run is linked above. Source CI is not proof of mobile-data connectivity on a physical phone.

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
| `docs/AI_NETWORKING_STATUS.md` | AI connectivity implementation, evidence, and remaining device checks |

Technical specifications remain separate from current-state summaries. When documents disagree with implementation, current code, tests, configuration, and observed CI evidence take precedence.
