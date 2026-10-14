# RPG Engine — Durable Memory

## Project identity

- Android-first deterministic text RPG engine with hybrid AI.
- Product release: `v1.1.4`.
- Historical engineering baseline: `v1.28.3`.
- Repository: `akln55/AI-STORY-ENGINE`.
- Canonical current state: `AI_START_HERE.md`; chronology: `docs/PROJECT_HISTORY.md`.

## Architecture rules

- Deterministic engine owns truth.
- AI is an untrusted proposer/narrator behind adapter boundaries.
- AI proposals must pass schema/security/gameplay validation before mutation.
- AI never gets direct GameState/save/database/scenario-file authority.
- UI provider paths: Local GGUF, Gemini, OpenAI, OpenAI-compatible endpoint.
- Offline play after compatible local model installation is a product goal; physical-device inference still needs proof.
- External web/research capability is separate and off by default.

## Android contract

- Kivy 2.3.1; Buildozer 1.6.0.
- python-for-android v2026.05.09 / `58d21141f17c889bf8585f5665921d72028f8831`.
- API 36 / minimum API 26 / `arm64-v8a`.
- NDK 29.0.14206865.
- llama.cpp v0.6.0 / `d81235049384534c167caea52b85a694f6103d14`.
- Entrypoint: `main.py -> rpg_android_app.py`; SAF helper: `rpg_android_file_picker.py`.
- Physical target: Redmi Note 12 Pro 4G.
- Never restore `android.main` or `android.file_picker`.

## Current UI/AI notes

- Hugging Face search and connectivity diagnostics are separate actions.
- The API connection check calls the provider's model-list endpoint; it does not generate text.
- AI settings now has a separate “Gerçek AI yanıtını test et” control that invokes the configured adapter's generation endpoint.
- Gemini, OpenAI-compatible calls, and provider model-list probes use `engine/ai/https_transport.py`; HTTPS hostname and certificate verification stay enabled. Localhost HTTP is preserved for the local llama-server.
- API settings support provider-aware endpoint/model defaults and custom OpenAI-compatible endpoints.
- See `docs/AI_NETWORKING_STATUS.md` for the current investigation and verification boundaries.
- Chat has distinct player/narration/error role markers; operational failures must not masquerade as story text or expose raw exception strings.
- Progressive text reveal is presentation-only.

## Latest source verification

- Last green networking baseline: [CI run 38345698305](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38345698305), 538 tests passed; compileall, Android readiness, and mutation smoke 3/3 passed.
- A later run failed because a UI readiness test still expected the old AI panel height (`dp(512)`) after the real-generation control expanded it to `dp(562)`. The test was updated in commit `145d3b13dc6107b893909f32ff4743082697b11a`; see [run 38439396555](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38439396555) for the latest gate.
- No APK build was started for the current networking task.
- Physical-device mobile-data access and real provider generation remain unverified.

## Release gates

- Test-only CI before packaging.
- Native llama.cpp cross-build and APK packaging must both pass.
- Inspect final APK metadata, provenance, and SHA-256.
- Run ARM64 device startup/crash smoke.
- Run gameplay, save/load/autosave, SAF scenario import, and local-GGUF inference tests.
- Do not label Android release verified before device evidence exists.

## Workflow preferences

- Work one stage at a time; group related changes into atomic commits.
- Fix the first failing layer before changing architecture.
- Preserve solved Android/security fixes.
- Never commit API keys, tokens, passwords, signing material, model files, local saves, APKs, build caches, or secret `.env` files.
- Do not confuse product version v1.1.4 with historical engineering baseline v1.28.3.

## User-reported blockers for the next implementation pass (2026-10-14)

These are open requirements, not completed features:

- Chat bubbles are improved, but text-entry fields/composer remain broken.
- API settings still request unnecessary information; provider-specific minimal forms are required.
- Settings screen has not received the meaningful changes expected by the user; UI symbols/icons remain malformed or inconsistent.
- Scenario import fails for the user's generated scenario: `characters.json:npc_kim_minjae.goals entries must be objects`. Inspect the real archive and schema producer/consumer; preserve goal data and add regression tests.

User expects implementation, tests, GitHub changes, and a new APK build—not just an audit or plan. Never claim the current old APK includes these fixes.

Last baseline build: [run 38455404595](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38455404595), success on `ad611254d90578e375b53f7445d1e7f1d4d243ae`; artifact `rpg-engine-v1.1.4-android-debug`, ID `11845055403`, digest `sha256:513c11b5287e35a1122ee583ce62ad584afd5e661222c5f5653c70cae5e2657e`. This is only a successful baseline packaging run; device launch/rendering, gameplay, and SAF scenario import remain unproven.


## 2026-10-14 — Approval workflow and verified review notes

- Binding workflow: plan -> show impact/unknowns/acceptance/tests -> obtain user approval before any code or product behavior change. Do not guess at unprovided schemas or deletion semantics.
- Plan: docs/DEVELOPMENT_PLAN.md. After every implementation, update AI_START_HERE.md, HANDOFF.md, MEMORY.md and relevant technical docs with real observed results.
- HEAD 59e30799162f94fa59201f75b0b9972577718032: pytest 549 passed; compileall/readiness passed; mutation smoke 3/3; demo-bootstrap valid; current CI run 38517225272 succeeded.
- tools/run_tests.py: 31 passed / 5 failed from pytest import/monkeypatch fixture incompatibility.
- Reproduced findings: rejected event-trigger proposals can still yield persisted memory claims; deduplicated memory updates do not refresh secondary indexes; JSON boolean resource values can be treated as integers.
- Scenario-import root cause remains unknown until the original failing archive is inspected. Do not relax validation merely to silence the error.
- Model downloader already has .part and HTTP Range resume logic. Verify recovery after process/app closure instead of rewriting it from scratch.
- Last successful APK is on an older commit; no APK or physical-device evidence for current HEAD.


## 2026-10-14 — Revised master campaign and new user requirements

- Updated canonical priority plan: docs/DEVELOPMENT_PLAN.md. The new weighted scores and one-campaign execution sequence supersede the prior priority table.
- New scope: engine-compatible ChatGPT scenario creation guide + validator; separate runtime AI behaviour guide connected to prompt/context; incremental chapter/source queue with visible order arrows, checkpoints, stable-ID merge, source retention and later additions; scenario customization workspace; consistent scenario/demo management; rounded chat composer/keyboard fixes; simple provider/key setup; downloader resume checks; previously reproduced memory/index/bool issues; test-helper repair; full test/CI/current APK gates.
- The user explicitly requires task tracking: use persistent checkboxes, mark [x] only when acceptance criteria and evidence pass, keep partial/incomplete work [ ], prefer retaining checked task history, and update relevant Markdown/handoff documents after every completed task.
- Original failed scenario .rpgscenario.zip is still needed. The screenshot identifies the validation message but not the exact malformed source data. Never claim root cause without the archive.
- The existing Master Specification should be reconciled against actual loader/registry models; do not copy schema examples blindly. Runtime instructions must be programmatically included in prompts, not merely stored as an unused Markdown file.
- This was a documentation-only planning update. No application code, UI, validator or APK changes have been made; the implementation campaign awaits explicit user approval.


## 2026-10-14 — Actual scenario archive diagnosis

- Uploaded archive: `Return_Survival_Kirilma_Noktasi.rpgscenario.zip`.
- Confirmed first blocker: `data/characters.json:npc_kim_minjae.goals[0]` is a plain string, while `engine/scenario/registry.py` requires goal objects containing `id`, `description`, and `priority`.
- Confirmed second blocker after the goal is corrected: the two `world.json.relationships` keys use human-readable IDs rather than runtime canonical keys (`sorted party IDs joined by "|"`).
- Manifest chapter count, chapter pack IDs, embedded canonical IDs, and explicit `references` targets passed manual structural checks.
- Improved the goal validation error, added a regression test, and created `docs/SCENARIO_CREATION_GUIDE.md`. Corrected local ZIP has only passed manual structural checks, not actual engine validation.
- Keep the import task unchecked until the real validator and app import path pass.

## 2026-10-14 — Implementation started under approved campaign

- Full campaign was approved by the user; execution has started.
- Actual archive issues confirmed: `data/characters.json:npc_kim_minjae.goals[0]` is a string rather than an object; `world.json.relationships` keys do not follow canonical sorted-party-ID key format.
- Created `docs/SCENARIO_CREATION_GUIDE.md` and `docs/IN_GAME_AI_BEHAVIOR_GUIDE.md`; the in-game behaviour rules were added to runtime context.
- Modified scenario validation diagnostics, gameplay composer, provider settings, rejected-event memory gating, memory secondary indexes, and resource integer validation. Regression tests were added but latest CI is pending.
- A corrected archive is available locally; it passed manual structure checks only, not the official engine validator or Android import.
- Keep all relevant tasks unchecked until tests pass and update these documents after each completed task.


## 2026-10-14 — Explicit interaction objectives and scenario knowledge graph

- Inspected the uploaded `Return_Survival_Kirilma_Noktasi.rpgscenario.zip`; the visible error comes from `quest_confirm_date.obj_check_phone` using `type: interact` for `item_phone`. The prior engine objective enum did not include `interact`.
- Added a deterministic explicit-interaction rule and quest progress signal so narration alone cannot complete an interact objective. Added English/Turkish parser coverage and a quest regression test.
- Added `ScenarioKnowledgeGraph` on top of canonical scenario registry records; supported nodes include all scenario categories, while edges are created only from explicit structured references and IDs. Retrieval now resolves names/aliases and can include chapter-/viewer-filtered neighboring records in the bounded AI context.
- Updated scenario creation and in-game behaviour guides to tell ChatGPT to preserve IDs, use aliases and explicit references, respect `interact` objective semantics, and avoid presenting guessed links as canon.
- A fresh tests/CI result is still required. A prior workflow run failed 552 tests passed / 2 failed; changes for both known failures and graph tests were committed afterward, but the latest run has not yet been verified. Do not mark these tasks complete yet.
- The graph reads structured JSON facts; it does not automatically extract every entity from free chapter prose. Resumable source ingestion, provenance and stable-ID reconciliation remain next-stage requirements.
