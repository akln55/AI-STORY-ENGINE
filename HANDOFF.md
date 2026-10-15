# RPG Engine — Current Handoff

> **Dikkat — güncellik doğrulaması gerekli:** Bu dosya, önceki bir geliştirme oturumu tamamlanmadan durdurulduğu için güncel olmayan veya kısmen yanlış bilgiler içerebilir. İçindeki durum ve mimari iddialarını güncel gerçek kabul etme. Bir işe başlamadan önce ilgili kaynak kodu, testleri, güncel `main` HEAD'ini ve en son CI sonuçlarını doğrula. Çelişki bulursan bunu sessizce varsayımla düzeltme; gerçek durumu belirt. Her çalışma sonunda bu dosyayı ve etkilenen tüm bilgi içeren `.md` dosyalarını güncelle. Kanıt yoksa bir işi tamamlandı işaretleme.


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


## Revised master implementation campaign — 2026-10-14 (approved; in progress)

The user has added these product requirements to the existing blocker list:

- A source-based scenario workspace with scenario personalization, ordered chapter/source uploads, visible arrows for processing order, progress/status/errors, restart/resume, and the ability to add later chapter packs without losing earlier data.
- Long works (potentially thousands of chapters) must be processed incrementally, with stable entity IDs, duplicate reconciliation, source preservation, and a clear separation between canonical source facts and player-altered runtime state.
- A ChatGPT-facing scenario creation MD that matches the engine's actual import schema, plus a separate in-game AI behaviour guide that is actually injected into the runtime prompt/context path.
- A professional rounded chat composer with correct input/cursor/keyboard layout; simplified provider-aware API settings; a rounded API key input.
- Every planned task must have a persistent checkbox. Mark [x] only after acceptance criteria and evidence pass; default to retaining completed tasks as checked rather than deleting task history. Update docs after each completed task.

**Canonical updated plan:** [docs/DEVELOPMENT_PLAN.md](docs/DEVELOPMENT_PLAN.md). It replaces the former priority list and defines weighted priority scoring, dependencies, one approved implementation campaign, acceptance tests and release gates.

### Highest priorities

1. Inspect the actual failed .rpgscenario.zip and identify the import root cause (9.9/10); the original archive is still missing, so this is blocked and the root cause remains unknown.
2. Engine-compatible scenario schema, validator/example pack, and ChatGPT scenario creation guide (9.9/10).
3. Incremental chapter/source pipeline, stable-ID merge and safe later updates (9.5/10).
4. Runtime AI behaviour guide connected to prompt/context builder (9.3/10).
5. End-to-end scenario import/play/retrieval/save-load tests (9.2/10).

The user approved the campaign. Source and documentation changes are underway. The original scenario archive was supplied and inspected; do not mark import fixed until official validator and app/device acceptance pass. Preserve saves by default; never silently delete campaign saves while removing a scenario.


## Scenario ZIP diagnosis — 2026-10-14

The user uploaded `Return_Survival_Kirilma_Noktasi.rpgscenario.zip`. Archive inspection verified two schema/runtime mismatches:

1. `data/characters.json:npc_kim_minjae.goals[0]` is a string, but `ScenarioRegistry` requires each goal to be an object with `id`, `description`, and `priority`.
2. `world.json.relationships` uses descriptive keys (`rel_minjae_yuna`, `rel_minjae_dohyun`), while runtime invariants require the key `"|".join(sorted([party_a, party_b]))`.

JSON parsing, canonical embedded IDs, explicit references, and chapter count/pack IDs were manually checked and passed. This is not yet a complete engine validation. A corrected local copy was generated and basic structural checks passed, but it has not been run through the actual project validator or Android import path.

Code/docs already changed on main:
- `engine/scenario/registry.py`: goal validation error now includes the offending index and expected fields.
- `tests/test_scenario_registry.py`: regression test for malformed string goal.
- `docs/SCENARIO_CREATION_GUIDE.md`: new ChatGPT-facing guide; documents structured goals and canonical runtime relationship keys.
- `docs/DEVELOPMENT_PLAN.md`: records verified findings and leaves task 1 unchecked until engine validation passes.

Do not claim the archive or app import is fully fixed yet. Next: verify CI for the error-message test, validate a corrected pack using the actual loader, then continue the approved campaign in dependency order.

## Campaign execution checkpoint — 2026-10-14

The user approved the full campaign. Work has started; the main task checkboxes remain unchecked until tests and acceptance evidence pass.

- Actual scenario ZIP inspected: invalid string goal in `data/characters.json:npc_kim_minjae.goals[0]`; runtime relationship keys in `world.json` are not canonical. A corrected local copy exists but has not passed the real project validator yet.
- Added `docs/SCENARIO_CREATION_GUIDE.md` and `docs/IN_GAME_AI_BEHAVIOR_GUIDE.md`.
- Improved scenario goal validation diagnostics and added a regression test.
- Added gameplay simulation instructions to runtime context and a test.
- Modified `rpg_android_app.py` to draw rounded inputs with a transparent native TextInput background, allow a multi-line growing gameplay composer, and hide routine provider endpoint/model fields behind advanced settings. Device testing is still required.
- Fixed known engine correctness cases in code: rejected event proposals now block associated memory updates; deduplicated memory updates refresh secondary indexes; boolean resource values are rejected as integers. Regression tests were added.
- Latest relevant CI run: [38621453513](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38621453513) is pending at this checkpoint. Do not claim tests passed until the run finishes.
- Remaining major work includes the actual scenario-builder/source queue and checkpointed chapter pipeline, scenario/demo deletion semantics, download resume lifecycle verification, full test/CI/APK gate, and real-device acceptance.


## Current implementation checkpoint — 2026-10-14

- The screenshot's follow-up blocker was identified in the supplied archive: quest `quest_confirm_date`, objective `obj_check_phone`, uses `type: interact` targeting `item_phone`; runtime objective validation previously accepted only `collect`, `reach`, `defeat`, and `talk`.
- The corrected archive has `quest_confirm_date.status = available`. The new deterministic interaction signal advances the target only when the quest is active; accept the quest first, or deliberately mark it active in scenario data if the story design makes it a starting objective.
- Implemented an explicit interaction rule for inspecting an accessible item, NPC, or current location. English and Turkish inspection command forms are routed to the deterministic rule; quest evaluation consumes the rule's explicit interaction signal, not AI prose.
- Added regression coverage for interaction parsing/objective completion plus deterministic knowledge-graph tests. Fresh CI run [38624639579](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38624639579) passed 560 tests, `compileall`, Android readiness, and mutation smoke 3/3.
- Added `engine/scenario/knowledge_graph.py` to construct a deterministic graph over existing canonical JSON records. It resolves stable IDs/names/aliases and follows explicitly declared reference fields. `ScenarioRetriever` surfaces linked records after rechecking viewer/chapter visibility, and the AI context expands a small bounded set of relevant hits with those links.
- This graph phase is deliberately not described as a general prose-understanding model. Automatic extraction from chapter Markdown, provenance-rich candidate validation, stable-ID merge, restart/resume, and source preservation are still required for the full source-processing pipeline.
- Updated the ChatGPT scenario guide with the supported `interact` objective and structured entity conventions; updated the in-game behaviour guide with graph retrieval and inference limits. Added `tests/test_scenario_knowledge_graph.py`.
- Earlier CI runs surfaced the stale API-panel assertion, a small-context budget regression, and generic `inspect` commands being intercepted from the AI memory path. These were addressed. Fresh run [38624639579](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38624639579) passed 560 tests, compileall, Android readiness, mutation smoke 3/3.
- Corrected scenario ZIP has only passed manual structural checks so far. Official `tools/validate_scenario.py`, app import, fresh full CI, fresh Android build, and physical-device smoke remain unverified.

### Current source links

- [Current main commit list](https://github.com/akln55/AI-STORY-ENGINE/commits/main/)
- [Scenario knowledge graph](https://github.com/akln55/AI-STORY-ENGINE/blob/main/engine/scenario/knowledge_graph.py)
- [Scenario creation guide](https://github.com/akln55/AI-STORY-ENGINE/blob/main/docs/SCENARIO_CREATION_GUIDE.md)
- [In-game AI behaviour guide](https://github.com/akln55/AI-STORY-ENGINE/blob/main/docs/IN_GAME_AI_BEHAVIOR_GUIDE.md)

## Single-batch implementation plan — 2026-10-14

The user clarified the sequence: complete the remaining implementation changes together as one campaign first; leave official scenario validation, the real app import/play test, the final full regression gate, fresh APK, artifact provenance and device acceptance until the end. This is a sequencing instruction, not permission to skip targeted regression tests during development.

The current code baseline is green: [CI run 38625436847](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38625436847) reports 560 passed, compileall passed, Android readiness passed, mutation smoke 3/3. `engine/scenario/knowledge_graph.py`, graph-backed retrieval, explicit `interact` objective handling, runtime AI rules and known engine-correctness fixes already exist; continue them rather than recreating them.

The integrated batch is documented in `docs/DEVELOPMENT_PLAN.md` §14: (1) source/intermediate schema and provenance/stable IDs, checkpoint/resume and safe chapter append; (2) ordered source queue and scenario workspace UI; (3) normal scenario/demo library management with save-safe removal confirmation; (4) finish composer and provider-specific API UX; (5) durable Hugging Face partial-download resume and test-runner behavior. Run targeted tests as each area changes. Only after those changes settle, run the full suite plus official archive validator/import/gameplay/save-load, build the current APK, check provenance, and perform device acceptance.

No product/code changes were made as part of the plan-writing request. Recheck current `main` HEAD before implementation begins. Do not check final acceptance boxes before evidence exists.


## Zorunlu çalışma sonu kuralı — her oturumda uygulanır

- Her kod veya davranış değişikliği tamamlandığında bu dosyayı, `AI_START_HERE.md`, `HANDOFF.md`, `MEMORY.md`, `docs/DEVELOPMENT_PLAN.md`, ilgili checklist'i ve değişiklikten etkilenen **bütün bilgi içeren `.md` dosyalarını** güncelle.
- Her raporda kaynak branch/HEAD SHA'sını, değişen dosyaları, gerçek test komutlarını ve sonuçlarını, CI run bağlantısını, APK/artifact doğrulamasını ve fiziksel cihaz durumunu ayrı ayrı yaz.
- “Kaynakta mevcut”, “yerel test geçti”, “GitHub CI geçti”, “APK üretildi/metadata doğrulandı” ve “gerçek Android cihazında doğrulandı” farklı kanıt seviyeleridir. Birbirinin yerine kullanma.
- Eski tarihli kayıtları silme veya güncel gerçek gibi sunma; tarihî bağlamı koru ve yeni, yetkili durum bölümünü ekle.
- Önceki oturum kesilmişse veya dosyaların güncelliği belirsizse önce ilgili kodu, testleri, mevcut HEAD'i ve son CI kayıtlarını kontrol et. Eski Markdown durumunu kanıt kabul etme.
- Son kontrolde hiçbir bilgi belgesi eski veya çelişkili kalmamalı; kanıtı olmayan kabul kriterleri açık kalmalı.

## 2026-10-15 — Authoritative audit note (replaces stale live-status claims; preserves history)

- Review baseline: pre-audit `main` HEAD `5e4ae4668f310f425fbb398d2f180cbe801ad3a8`; latest audited implementation commit is `51f44c7f9cf2fa1aa0a16fdecb50c89123bf112d` on `review/comprehensive-code-audit-2026-10-15` (PR #2).
- The last known Test Suite run for that baseline failed: run [38632774268](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38632774268). The failure is a stale source-level UI assertion in `tests/test_android_app_readiness.py`: it expected the removed `◇` prefix while `rpg_android_app.py` now uses `text="Yerel modeller · Local GGUF"`. Source shows 598 other tests passed in that run; this is not a current green CI result.
- The source-workspace queue/checkpoint/candidate-index/export implementation already exists in `engine/scenario/source_workspace.py`, is wired through `engine/app/controller.py`, is exposed by `SourceWorkspaceScreen`, and has targeted tests. Older checklist entries saying this feature is wholly unimplemented are stale; end-to-end acceptance and device behavior remain separate gates.
- Model download partial metadata, Range/If-Range resume and model-integrity checks exist in `engine/ai/model_manager.py` and have focused unit tests. App/process lifecycle and physical Android acceptance remain unproven.
- Audit fixes include checkpoint verification against the saved source chunk, best-effort progress callbacks, current UI assertion, PR CI trigger, and safe bounded release ZIP extraction. Commit `51f44c7f9cf2fa1aa0a16fdecb50c89123bf112d` passed [GitHub Actions run 38690247384](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38690247384): 610 tests passed, `compileall` passed, Android readiness passed, and mutation smoke detected 3/3 mutations. This verifies source/CI gates only; no fresh APK or physical-device acceptance was performed.
- Still open: validate the actual user-provided scenario archive through the real engine validator/import path, confirm scenario quest authoring/export coverage, perform full pytest/compile/readiness/mutation gates, produce a fresh APK with provenance, and run real-device acceptance. Do not infer completion from source presence alone.
- Do not rewrite historical notes below as if they were current evidence. Use this dated audit and later dated evidence sections for current status.

## 2026-10-15 — Current implementation and acceptance status

- Latest audited code commit: `51f44c7f9cf2fa1aa0a16fdecb50c89123bf112d`. CI: [run 38690247384](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38690247384) — 610 tests passed; Python compileall, Android readiness (version 1.1.4, target API 36, SAF enabled) and mutation smoke (3/3) passed.
- Source workspace, ordered queue, durable checkpoints, candidate identity resolution and scenario ZIP export exist in code and have unit/integration tests. Checkpoints now validate the current source metadata and re-derived source chunk; progress callbacks cannot mark an already completed chunk failed.
- Release verification ZIP extraction is hardened against POSIX/Windows path traversal, symlinks, duplicate/case-colliding paths, and excessive entry/expanded sizes. `tests/test_release_verify.py` covers these cases.
- Provider-conditional API fields and separate connection/generation tests exist in source. Composer and keyboard behavior still need physical Android acceptance.
- Hugging Face range/resume/hash checks and tests exist; app/process lifecycle behavior still needs device acceptance.
- Still open: validate the actual user-provided scenario archive using the real validator/import/play/save/load flow; fresh APK build plus SHA/provenance; physical-device workflow. Do not mark those items complete based on source tests.
- The 2026-10-14 “not yet implemented” backlog is historical context. Source presence must be checked before repeating those claims; device/release gates remain open until evidence is recorded.


## 2026-10-15 — User's latest Android test; next work plan

**Important:** the user installed and interacted with the built app on a physical phone. This reveals runtime failures not covered by the previous green source CI or APK packaging checks. Use [`docs/ANDROID_AI_RUNTIME_AND_INPUT_PLAN.md`](docs/ANDROID_AI_RUNTIME_AND_INPUT_PLAN.md) as the immediate ordered work plan; after it passes, resume the older open tasks in `docs/DEVELOPMENT_PLAN.md`.

1. **P0 local AI runtime:** device dialog says `runtime could not start: could not start llama-server: [Errno 13] Permission denied: /data/data/org.rpgengine/files/native_runtime/…`. The source implementation already copies the binary and calls `chmod(0o700)`; do not mark a further chmod as the answer without isolating Android's EACCES cause. Gameplay later reports `You can't do that. (no AI adapter configured)` because no usable adapter is active after the failure. Must validate real generation on-device.
2. **P1 GGUF workflow:** picking a GGUF for import leaves the screen black/stuck; a downloaded model's activation also fails. Diagnose import, background copy/validation, UI callback and runtime activation separately.
3. **P2 text fields:** chat composer and API/advanced settings text fields accept typing but characters are visually hidden/covered before submission. A tap near advanced settings sometimes opens the keyboard, suggesting a touch/focus/layout overlap. Fix actual drawing order, bounds, scroll/keyboard behavior and focus handling.
4. **P3 release proof:** full source tests, compile/readiness/mutation gates, native cross-build, fresh APK/provenance, and physical Android acceptance for P0/P1/P2.

Only this plan/documentation was added in the current planning pass. No code changes or fixes are claimed. Treat the exact runtime error and input visibility/touch behavior as acceptance targets. Once this plan is verified complete, return to the other still-open master-plan tasks; preserve their checkboxes and historical evidence.
