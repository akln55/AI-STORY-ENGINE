# RPG Engine — AI START HERE

> **Dikkat — güncellik doğrulaması gerekli:** Bu dosya, önceki bir geliştirme oturumu tamamlanmadan durdurulduğu için güncel olmayan veya kısmen yanlış bilgiler içerebilir. İçindeki durum ve mimari iddialarını güncel gerçek kabul etme. Bir işe başlamadan önce ilgili kaynak kodu, testleri, güncel `main` HEAD'ini ve en son CI sonuçlarını doğrula. Çelişki bulursan bunu sessizce varsayımla düzeltme; gerçek durumu belirt. Her çalışma sonunda bu dosyayı ve etkilenen tüm bilgi içeren `.md` dosyalarını güncelle. Kanıt yoksa bir işi tamamlandı işaretleme.


**Canonical current handoff:** this file  
**Canonical historical record:** `docs/PROJECT_HISTORY.md`  
**Product release:** `v1.1.4`  
**Current AI/network work:** see [AI networking status](docs/AI_NETWORKING_STATUS.md). Verified shared HTTPS transport was added for Gemini, OpenAI-compatible API calls, and provider connection probes. The latest UI generation-test change exposed one stale panel-height assertion; that assertion has been updated and the latest source CI is running.  
**Current Android build:** check the [Android build workflow](https://github.com/akln55/AI-STORY-ENGINE/actions/workflows/android-build.yml) for the newest run. Older build #122 is historical and does not validate the recent model-download/UI fixes; APK metadata/provenance verification and artifact upload must complete before claiming packaging success.

> This file describes current state only. Older checkpoint/version documents are historical evidence, not current-state authority.

## 1. Product identity

RPG Engine is a deterministic, local-first text RPG for Android, not a prose chatbot. The engine owns truth; AI proposes narration and structured effects only.

```text
Player action
  -> parser / deterministic rules
  -> authoritative GameState
  -> bounded memory, scenario, and NPC context
  -> AI proposal
  -> validation/security gate
  -> atomic state mutation
  -> event/quest/memory updates
  -> persistence
```

AI cannot directly write authoritative GameState, saves, databases, scenario canon, or arbitrary files.

## 2. Android target and entrypoint

- Standalone Android APK; no end-user Termux/Python requirement.
- Minimum API: **26**; target API: **36**.
- ABI: **arm64-v8a**.
- Kivy: **2.3.1**; Buildozer: **1.6.0**.
- python-for-android: **v2026.05.09**, commit `58d21141f17c889bf8585f5665921d72028f8831`.
- Android NDK: **29.0.14206865**.
- Native llama.cpp: **v0.6.0**, commit `d81235049384534c167caea52b85a694f6103d14`.
- Entrypoint: `main.py -> rpg_android_app.py`.
- SAF helper: `rpg_android_file_picker.py`.
- Physical validation target: Redmi Note 12 Pro 4G.

Never restore `android.main` or `android.file_picker`.

## 3. AI providers and local runtime

The UI exposes these provider paths:
- **Local GGUF** — import/select a model into app-private storage.
- **Gemini** — Google API provider.
- **OpenAI** — OpenAI API provider.
- **OpenAI-compatible** — custom compatible endpoint and model ID.

The Hugging Face catalog search is separate from connectivity diagnostics. The provider connection test probes the model-list endpoint and does not generate text. A separate “Gerçek AI yanıtını test et” control now calls the configured adapter's real generation endpoint. Source changes do not prove mobile-data access on the target phone; that remains unverified until an updated app is run on-device.

### Implemented in source

- GGUF import through Android SAF and app-private model storage.
- GGUF integrity/structure validation and model-manager lifecycle.
- `AIAdapter` boundary and development adapters.
- Android-native `llama-server` lifecycle code and pinned CI cross-build script.
- Provider selection and endpoint/model configuration.
- API connectivity/model discovery controls.
- Hugging Face catalog search and connection diagnostics.
- Bounded/sanitized provider diagnostics.
- Chat role bubbles, progressive text presentation, busy-state handling, and separate user-facing gameplay error bubbles.

### Still unproven or incomplete

- A successful, fully verified APK artifact from the current Android build run.
- Installation/launch on physical ARM64 Android hardware.
- Real local GGUF inference and performance/thermal/memory measurements on the target phone.
- A complete in-app model-management experience beyond current catalog/search/import capabilities.

Initial local-model policy remains conservative: roughly **1.5B–3B instruct**, efficient 4-bit variants, around 2 GB preferred and around 3 GB provisional maximum until device benchmarks exist.

## 4. Current source verification

The last fully green networking baseline is [CI run 38345698305](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38345698305): 538 tests passed, compileall passed, Android readiness passed, and mutation smoke detected 3/3. After adding the actual-generation UI control, run [38351205793](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38351205793) failed at one stale UI source assertion (`dp(512)` versus the intentionally expanded `dp(562)` panel). The assertion was updated in commit `145d3b13dc6107b893909f32ff4743082697b11a`; its CI run is the current verification gate.

No Android APK build was started for this networking task. Real mobile-data connectivity, provider authentication, and successful generation on the physical Redmi device remain unverified.

## 5. Release gates

1. Source tests and static checks.
2. Native llama.cpp cross-build.
3. Build APK.
4. Verify final APK metadata, source/staging provenance, and SHA-256.
5. Upload APK and provenance artifacts.
6. Install/launch on ARM64 Android and retain startup logs.
7. Verify gameplay, save/load/autosave, SAF scenario import, provider configuration, and local-GGUF inference.

Only call the app Android-verified after the relevant device gates pass.

## 6. Current UI contract

- Dark neutral hierarchy, rounded surfaces/controls, muted secondary text.
- Primary actions have explicit contrast and visible pressed/disabled states.
- Player messages are right-aligned; narration/NPC messages are left-aligned.
- Chat role markers distinguish `SEN`, `ANLATI`, and `HATA`.
- Busy state prevents duplicate submissions.
- Progressive text reveal is presentation-only and must not control save/state semantics.
- Operational/provider failures must not be rendered as story narration or expose raw exception details to the player.

## 7. Non-negotiable rules

- AI is an untrusted proposer, never the authority over game state.
- No secrets, API keys, model binaries, APKs, build caches, signing material, local saves, or secret `.env` files in Git.
- Do not treat GGUF import as proof of on-device inference.
- Do not treat an APK existing as proof the app launches.
- Keep implemented, source-verified, artifact-verified, device-verified, and planned states separate.
- If CI fails, inspect the first failing layer/log before changing architecture.

## 8. Reading order

1. This file — current state and next gate.
2. `docs/PROJECT_HISTORY.md` — chronological history and lessons.
3. `docs/ARCHITECTURE.md` — architecture and gameplay loop.
4. `docs/CONSTITUTION.md` — binding rules.
5. `docs/TESTING.md` and `docs/ANDROID_BUILD.md` — verification/release gates.
6. The relevant subsystem specification before changing that subsystem.

## 9. Handoff update — 2026-10-14 (current user-reported blockers)

The following issues are **open** and must not be described as fixed merely because older source checks or an APK build passed:

1. **Chat composer / text-entry UI:** user reports the message bubbles no longer overflow as often, but text-entry areas remain visually/layout broken. Fix input sizing, rounded shape, text/hint/cursor alignment, keyboard interaction, and send control placement on the actual Kivy screen.
2. **API settings UX:** the user explicitly requested that the app not ask for unnecessary information. Current provider form still needs a provider-specific minimal-fields pass; hide irrelevant fields (for example, a Gemini endpoint field) instead of merely disabling them. Keep model-list connectivity separate from real generation testing.
3. **Settings and icons:** user reports no meaningful settings-screen improvement and malformed/inconsistent UI symbols. Audit the actual screen, typography/icon support, control alignment, and small-screen behavior; do not claim visual success without rendered evidence.
4. **Scenario import blocker:** the user's imported scenario fails with: `Import başarısız: scenario data characters.json:npc_kim_minjae.goals entries must be objects`. Inspect the actual imported archive and its `characters.json`, then reconcile the producer's schema with `engine/scenario/loader.py` validation. Preserve valid NPC goals; do not remove validation simply to silence the error. Add a fixture and regression tests.
5. **Acceptance is implementation + verification:** fix code, add tests, run the full test and readiness gates, commit/push changes, then dispatch the Android build workflow and inspect its result/artifact. A successful older build is not proof these open issues are fixed.

### Last verified build evidence (not the fixes above)

- Android build workflow run [38455404595](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38455404595) completed successfully on commit `ad611254d90578e375b53f7445d1e7f1d4d243ae`.
- APK and provenance artifact: `rpg-engine-v1.1.4-android-debug`; artifact ID `11845055403`; size 58,551,775 bytes; archive digest `sha256:513c11b5287e35a1122ee583ce62ad584afd5e661222c5f5653c70cae5e2657e`; expires 2027-01-11.
- This artifact predates the outstanding UI/settings/scenario-import fixes and must not be represented as containing them.
- No physical-device visual/launch/gameplay test is evidenced by this build. Keep device verification explicitly open.
- Current source head at the time of this handoff: `ad611254d90578e375b53f7445d1e7f1d4d243ae`.

### Next AI: required working method

Read this file, `HANDOFF.md`, `MEMORY.md`, and the relevant UI/scenario code before editing. Treat the user's screenshot and exact import error as reproducible acceptance targets. Inspect current code rather than relying on older summaries. Make the smallest coherent implementation, test it, and update these status docs after observing real results. Do not start with a generic redesign plan or stop after producing recommendations.


## Development plan and approval gate — 2026-10-14

Prioritized work list and acceptance criteria: docs/DEVELOPMENT_PLAN.md. Before a code/product behavior change, prepare the plan (impact, unknowns, likely files, tests, acceptance criteria) and get user approval. Do not guess about scenario schema or deletion semantics; request the real file/clarification.

### Current source verification

- Inspected source HEAD: 59e30799162f94fa59201f75b0b9972577718032.
- Same source snapshot: pytest 549 passed; compileall, Android readiness, mutation smoke 3/3, and demo-bootstrap validation passed.
- tools/run_tests.py: 31 passed, 5 failed due to pytest import/monkeypatch fixture incompatibility. CI uses pytest directly; helper needs separate repair or documentation update.
- Current source CI: https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38517225272 succeeded.
- Latest successful APK build is for older commit ad611254d90578e375b53f7445d1e7f1d4d243ae: https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38455404595. No APK/device verification for current HEAD.
- Reproduced review findings: rejected event proposals can still add related memory; duplicate memory updates leave secondary indexes stale; boolean resource effects can pass as integers. Details and tests-to-add are in the development plan.
- Scenario import root cause is not known until the actual failing archive is inspected.

This is a documentation-only commit. No code fix or Android build is included.


## 10. Revised implementation campaign — 2026-10-14

The user has requested a unified implementation campaign covering scenario import and generation, long chapter-series source processing, runtime AI behaviour, scenario-building UX, chat composer, provider settings, known engine correctness bugs, download resume reliability, testing, and a fresh Android release gate.

- Master task list and weighted scores: [docs/DEVELOPMENT_PLAN.md](docs/DEVELOPMENT_PLAN.md).
- Priority scores are engineering estimates based on user impact, blocking severity, dependencies and data-integrity risk—not telemetry. Only mark tasks complete after tests/evidence meet their acceptance criteria.
- Use checkbox status in the plan. Keep completed work marked [x] with evidence; do not delete it merely to shorten the list. After each completed task, update the plan and relevant handoff docs.
- The failed scenario archive has not been provided. The exact import root cause is unknown until its JSON data is inspected; do not guess and do not weaken validation to hide the error.
- The user's uploaded Scenario Data Creation Master Specification is a requirements source, not automatic proof that every illustrated field is compatible with the current engine schema. Align the new ChatGPT guide with real loader/registry validation.
- A separate in-game AI behaviour guide is only useful when actually included in every applicable backend's runtime prompt/context path and covered by tests.
- Source-based chapter processing must be resumable, preserve the original source files, merge by stable IDs, and keep canon separate from player runtime state.
- No source code/UI/product behaviour or APK was modified by the plan revision. The campaign awaits explicit user approval.


## Scenario archive finding — 2026-10-14

The user supplied `Return_Survival_Kirilma_Noktasi.rpgscenario.zip`. Confirmed:
- `data/characters.json:npc_kim_minjae.goals[0]` is a string, but canonical scenario goal entries must be objects with `id`, `description`, and `priority`.
- Runtime `world.json.relationships` keys are not canonical; keys must be the alphabetically sorted pair of `party_a` and `party_b`, joined with `|`.

The chapter metadata and explicit canonical references passed manual structural checks. A corrected local archive passed manual structural checks, not yet the real engine validator. Keep the main task unchecked until `tools/validate_scenario.py` and real import tests pass.

See `docs/SCENARIO_CREATION_GUIDE.md` for the newly added generator guide. It is aligned to current loader/registry rules and must be updated together with schema changes.

## Active execution status — 2026-10-14

The full development campaign is approved and implementation has started. Current state is in progress, not complete.

- The actual uploaded scenario archive revealed two mismatches: string-valued canonical NPC goal and non-canonical runtime relationship keys. A corrected local archive has passed only manual structural checks.
- Read `docs/SCENARIO_CREATION_GUIDE.md` and `docs/IN_GAME_AI_BEHAVIOR_GUIDE.md`; the latter's core contract has also been injected into `engine/ai/context.py`.
- Code changes also cover actionable scenario-goal errors, a multiline rounded composer, simpler provider settings, rejected-event memory protection, secondary memory index refresh, and strict boolean rejection for integer resource values.
- Regression tests were added for the changed behaviours. The latest CI run is pending, so keep all implementation task checkboxes unchecked until tests pass.
- Continue with the approved campaign; preserve scenario sources and saves. Do not claim the corrected archive is engine-validated until the official validator and app import flow pass.


## 11. Current handoff — scenario reader and import work (2026-10-14)

The campaign is approved and in progress. Prefer the latest commit/workflow evidence over older status notes above.

### Screenshot error: `type: interact`

The uploaded archive's quest `quest_confirm_date` contains objective `obj_check_phone` with `type: interact` and `target_id: item_phone`. The existing engine enum previously accepted only `collect`, `reach`, `defeat`, and `talk`. The new code adds explicit interaction/inspection on accessible items, NPCs and the current location, and passes the resulting target ID to deterministic quest evaluation. AI narration alone must not grant progress.

### Scenario knowledge graph

- `engine/scenario/knowledge_graph.py` builds a deterministic graph over the canonical records already declared in scenario JSON.
- Nodes contain category, stable ID, name, aliases and summary; edges are built from explicit record IDs/reference fields rather than name-only guesses.
- `ScenarioRetriever.resolve_entities()` resolves IDs/names/aliases. `related_records()` returns linked records only after chapter/viewer filters are applied.
- The AI context includes a bounded number of linked records for better continuity.
- This is **not yet** automatic entity extraction from arbitrary chapter prose. The long-series source queue must still perform candidate extraction, source provenance, duplicate/stable-ID reconciliation, validation, checkpoint/resume, and source preservation.

### Test status

The first follow-up run found a self-referential `contract_lines` bug; the next exposed ordinary inspection commands being intercepted from the AI memory path. Both were corrected. Fresh Actions run [38624639579](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38624639579) passed 560 tests, Python compileall, Android readiness, and mutation smoke 3/3.

### Acceptance still open

- Full pytest (560 passed), compileall, Android readiness contract, and mutation smoke 3/3 passed on commit `1445c55297ab73ab98d5845d0daf34f01de2f93f`.
- Still run `python tools/validate_scenario.py <corrected-archive>` using the real project runtime; do not substitute manual JSON checks.
- Confirm APK scenario import and play the objective on Android.
- Build a fresh APK only after source gates pass; device UI/inference remains a separate gate.

## 12. Current sequencing instruction — one implementation batch, final gate last

The user requested that all still-open development changes be planned as one integrated campaign and that the official scenario ZIP validator, actual application import/play test, final full regression, fresh Android APK and physical-device acceptance be postponed until the end.

Source of truth: `docs/DEVELOPMENT_PLAN.md` §14. The plan covers source/intermediate schema with provenance and stable IDs, resumable chapter processing, ordered source queue and status UI, safe scenario/demo management, composer/provider UX, model-download resume, and the test helper. It explicitly preserves original source files and save slots. Existing graph, interaction objective, runtime AI context and engine-correctness work should be extended, not rewritten.

The last verified source gate before this plan was written: [run 38625436847](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38625436847) — 560 tests passed, compileall passed, Android readiness passed, mutation smoke 3/3. These checks predate future implementation changes and are only a baseline. During implementation, use targeted tests; perform the full final gate only after the integrated changes settle. The plan-writing request did not change application code.


## Zorunlu çalışma sonu kuralı — her oturumda uygulanır

- Her kod veya davranış değişikliği tamamlandığında bu dosyayı, `AI_START_HERE.md`, `HANDOFF.md`, `MEMORY.md`, `docs/DEVELOPMENT_PLAN.md`, ilgili checklist'i ve değişiklikten etkilenen **bütün bilgi içeren `.md` dosyalarını** güncelle.
- Her raporda kaynak branch/HEAD SHA'sını, değişen dosyaları, gerçek test komutlarını ve sonuçlarını, CI run bağlantısını, APK/artifact doğrulamasını ve fiziksel cihaz durumunu ayrı ayrı yaz.
- “Kaynakta mevcut”, “yerel test geçti”, “GitHub CI geçti”, “APK üretildi/metadata doğrulandı” ve “gerçek Android cihazında doğrulandı” farklı kanıt seviyeleridir. Birbirinin yerine kullanma.
- Eski tarihli kayıtları silme veya güncel gerçek gibi sunma; tarihî bağlamı koru ve yeni, yetkili durum bölümünü ekle.
- Önceki oturum kesilmişse veya dosyaların güncelliği belirsizse önce ilgili kodu, testleri, mevcut HEAD'i ve son CI kayıtlarını kontrol et. Eski Markdown durumunu kanıt kabul etme.
- Son kontrolde hiçbir bilgi belgesi eski veya çelişkili kalmamalı; kanıtı olmayan kabul kriterleri açık kalmalı.

## 2026-10-15 — Authoritative audit note (replaces stale live-status claims; preserves history)

- Review baseline: `main` HEAD `5e4ae4668f310f425fbb398d2f180cbe801ad3a8`. This is the snapshot reviewed before the audit patch. Re-check branch HEAD and current Actions after proposed changes.
- The last known Test Suite run for that baseline failed: run [38632774268](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38632774268). The failure is a stale source-level UI assertion in `tests/test_android_app_readiness.py`: it expected the removed `◇` prefix while `rpg_android_app.py` now uses `text="Yerel modeller · Local GGUF"`. Source shows 598 other tests passed in that run; this is not a current green CI result.
- The source-workspace queue/checkpoint/candidate-index/export implementation already exists in `engine/scenario/source_workspace.py`, is wired through `engine/app/controller.py`, is exposed by `SourceWorkspaceScreen`, and has targeted tests. Older checklist entries saying this feature is wholly unimplemented are stale; end-to-end acceptance and device behavior remain separate gates.
- Model download partial metadata, Range/If-Range resume and model-integrity checks exist in `engine/ai/model_manager.py` and have focused unit tests. App/process lifecycle and physical Android acceptance remain unproven.
- The audit patch adds validation that a returned source batch matches the currently persisted checkpoint and makes progress callbacks non-authoritative, plus regression tests. These changes are **not accepted until the new branch commit's CI runs successfully**.
- Still open: validate the actual user-provided scenario archive through the real engine validator/import path, confirm scenario quest authoring/export coverage, perform full pytest/compile/readiness/mutation gates, produce a fresh APK with provenance, and run real-device acceptance. Do not infer completion from source presence alone.
- Do not rewrite historical notes below as if they were current evidence. Use this dated audit and later dated evidence sections for current status.