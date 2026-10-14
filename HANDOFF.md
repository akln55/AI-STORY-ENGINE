# RPG Engine — Current Handoff

**Updated:** 2026-10-13  
**Product version:** v1.1.4  
**Historical engineering baseline:** v1.28.3  
**Repository:** `akln55/AI-STORY-ENGINE`

## Read this first

- `AI_START_HERE.md` is the canonical current state and next-gate document.
- `MEMORY.md` stores durable project decisions.
- `docs/PROJECT_HISTORY.md` is chronological history, not current-state authority.

When documents disagree, prefer current source code/tests/configuration and observed CI results. Do not revive stale status claims from older dated documents.

## Product and architecture

RPG Engine is a deterministic Android text RPG with hybrid AI. The deterministic engine owns authoritative state. AI is a bounded proposer/narrator; all state-changing effects pass validation before atomic application.

Required provider paths in the app:
- Local GGUF
- Google Gemini
- OpenAI
- OpenAI-compatible custom endpoint/model

Once a compatible local model is installed and local runtime works, offline play is a product goal. External web/research access is a separate capability and is off by default.

## Android target

- Kivy 2.3.1; Buildozer 1.6.0.
- python-for-android stable v2026.05.09 / `58d21141f17c889bf8585f5665921d72028f8831`.
- Target API 36; minimum API 26; ABI arm64-v8a.
- NDK 29.0.14206865.
- llama.cpp v0.6.0 / `d81235049384534c167caea52b85a694f6103d14`.
- Entrypoint: `main.py -> rpg_android_app.py`.
- SAF helper: `rpg_android_file_picker.py`.
- Physical target: Redmi Note 12 Pro 4G.

Never restore `android.main` or `android.file_picker`.

## Current focus: AI/network connectivity

Read `docs/AI_NETWORKING_STATUS.md` for the evidence-backed state. Shared verified HTTPS transport now serves Gemini, OpenAI-compatible requests, and API model-list probes. The AI settings screen has a separate real-generation test so model-list reachability is not mistaken for working generation.

Latest green source baseline: [run 38345698305](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38345698305), 538 tests passed, compileall/readiness passed, mutation smoke 3/3. The later generation-test UI change had one stale height assertion; it was updated in commit `145d3b13dc6107b893909f32ff4743082697b11a`. [Its CI run](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38439396555) is the current gate.

Do not start an Android build for this task. Physical mobile-data access and provider generation remain unverified; CI cannot establish device/carrier behavior.

## Recent implementation changes

- Added Hugging Face connectivity diagnostics separate from model search/download.
- Expanded API provider selection with OpenAI-compatible endpoint/model fields and provider-aware defaults.
- Added compact visual markers in AI settings and gameplay chat.
- Distinguished gameplay errors from story narration and stopped showing raw exception strings in the chat.
- Added regression coverage for provider choices, chat markers, and safe gameplay error presentation.
- Added a shared verified HTTPS transport for remote AI endpoints; certificate verification remains enabled.
- Added a real AI generation check in settings, separate from the lower-cost model-list probe.

## Non-negotiables

- AI cannot directly mutate GameState, persistence, scenario canon, or arbitrary files.
- Never commit secrets, API keys, model binaries, APKs, build caches, signing material, private credentials, or local saves.
- An imported GGUF is not proof of local inference.
- A built APK is not proof of Android runtime success.
- Keep verified, implemented, and unproven status separate.

## Release sequence

Source tests -> native cross-build -> APK build -> static APK/provenance verification -> ARM64 device startup smoke -> gameplay/save-load/SAF smoke -> local-GGUF inference smoke.

## CI discipline

Do not treat pending/cancelled runs as evidence. On failure, inspect the first failed job/step/log and fix that root cause before changing architecture. Group related changes to avoid unnecessary concurrent workflow churn.

## Open blockers reported by the user — 2026-10-14

These remain unresolved until a later commit and verification demonstrate otherwise:

- Chat message bubble overflow is improved, but the **text-entry/composer areas are still broken**. Inspect Kivy sizing, canvas drawing, hint/text/cursor alignment, keyboard resize/scroll behavior, and send button placement.
- **API settings ask for unnecessary information.** Implement a minimal provider-aware form: only show relevant fields; Gemini must not require a custom endpoint; custom OpenAI-compatible providers need endpoint/model/key. Keep connection/model-list probing distinct from actual generation.
- **Settings and UI symbols remain visibly broken/inconsistent.** The user reports no meaningful settings improvement. Verify actual layout and icon/font availability; do not claim visual polish based on source inspection alone.
- **Scenario import fails** with `Import başarısız: scenario data characters.json:npc_kim_minjae.goals entries must be objects`. Inspect the exact imported scenario archive and its `characters.json`; reconcile the data producer and loader schema, preserve NPC goal information, and add regression tests. Do not weaken validation to hide the error.

### Last Android build (baseline only)

[Run 38455404595](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38455404595) succeeded on `ad611254d90578e375b53f7445d1e7f1d4d243ae`; it uploaded `rpg-engine-v1.1.4-android-debug` (artifact ID `11845055403`, SHA-256 digest `513c11b5287e35a1122ee583ce62ad584afd5e661222c5f5653c70cae5e2657e`). **This APK does not include fixes for the blockers listed above**, because those fixes have not yet been implemented. No physical-device acceptance test is established by this run.

### Next handoff acceptance gate

Implement the blockers in source, add scenario/UI regression tests, run full pytest + compileall + Android readiness + mutation smoke, push the verified changes, then trigger and verify a fresh Android build and artifact. Inspect the first failing CI step/log if anything fails. Report actual results only; keep device verification separate.


## Prioritized plan and approval gate — 2026-10-14

Use docs/DEVELOPMENT_PLAN.md for priorities and acceptance criteria. First priorities: inspect the actual failing scenario archive (10.0/10), define the ChatGPT-generated .rpgscenario.zip contract (9.8/10), refactor scenario listing/demo management (9.5/10), and repair verified memory/index/type issues (9.4/9.2/8.3).

Before changing code or product behavior: plan the scope, unknowns, acceptance criteria and tests; obtain user approval. Ask for the real scenario archive instead of guessing at its schema. After every implementation, run applicable tests and update the handoff docs with evidence.

Current HEAD 59e30799162f94fa59201f75b0b9972577718032: pytest 549 passed; compileall/readiness passed; mutation smoke 3/3; demo-bootstrap valid. tools/run_tests.py had 31 passed / 5 failed (pytest/monkeypatch helper incompatibility). CI run 38517225272 succeeded. The last successful APK is for an older commit; no APK/device test was done for this HEAD. The commit that adds this plan is documentation-only.
