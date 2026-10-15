# RPG Engine — Durable Memory

> **Dikkat — güncellik doğrulaması gerekli:** Bu dosya, önceki bir geliştirme oturumu tamamlanmadan durdurulduğu için güncel olmayan veya kısmen yanlış bilgiler içerebilir. İçindeki durum ve mimari iddialarını güncel gerçek kabul etme. Bir işe başlamadan önce ilgili kaynak kodu, testleri, güncel `main` HEAD'ini ve en son CI sonuçlarını doğrula. Çelişki bulursan bunu sessizce varsayımla düzeltme; gerçek durumu belirt. Her çalışma sonunda bu dosyayı ve etkilenen tüm bilgi içeren `.md` dosyalarını güncelle. Kanıt yoksa bir işi tamamlandı işaretleme.


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
- Fresh CI run [38624639579](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38624639579) passed 560 tests, compileall, Android readiness, and mutation smoke 3/3. Earlier failures (stale panel assertion, context budget, and inspection commands intercepting the AI memory path) were resolved. Scenario validator/import and Android device acceptance remain unverified.
- The graph reads structured JSON facts; it does not automatically extract every entity from free chapter prose. Resumable source ingestion, provenance and stable-ID reconciliation remain next-stage requirements.

## 2026-10-14 — User requested one implementation batch before final validation

- User clarified that the scenario archive's official validation/import/APK/device tests are the last tasks, after remaining development changes are completed.
- Source of truth: `docs/DEVELOPMENT_PLAN.md` §14 covers the source/intermediate schema with provenance and stable IDs, resumable chapter processing, ordered source queue and status UI, safe scenario/demo management, composer/provider UX, model-download resume, and test runner.
- Existing graph/interaction/runtime-context and engine-correctness changes had a green baseline in Actions run 38625436847 (560 passed, compileall, Android readiness, mutation smoke 3/3). Extend/test these rather than recreating them.
- Targeted tests can run during implementation; comprehensive full CI, official validator, real import/play, APK build/provenance and device acceptance are deferred until the end as requested.
- The plan-writing task changes documentation only; source code has not been modified by this request.


## Zorunlu çalışma sonu kuralı — her oturumda uygulanır

- Her kod veya davranış değişikliği tamamlandığında bu dosyayı, `AI_START_HERE.md`, `HANDOFF.md`, `MEMORY.md`, `docs/DEVELOPMENT_PLAN.md`, ilgili checklist'i ve değişiklikten etkilenen **bütün bilgi içeren `.md` dosyalarını** güncelle.
- Her raporda kaynak branch/HEAD SHA'sını, değişen dosyaları, gerçek test komutlarını ve sonuçlarını, CI run bağlantısını, APK/artifact doğrulamasını ve fiziksel cihaz durumunu ayrı ayrı yaz.
- “Kaynakta mevcut”, “yerel test geçti”, “GitHub CI geçti”, “APK üretildi/metadata doğrulandı” ve “gerçek Android cihazında doğrulandı” farklı kanıt seviyeleridir. Birbirinin yerine kullanma.
- Eski tarihli kayıtları silme veya güncel gerçek gibi sunma; tarihî bağlamı koru ve yeni, yetkili durum bölümünü ekle.
- Önceki oturum kesilmişse veya dosyaların güncelliği belirsizse önce ilgili kodu, testleri, mevcut HEAD'i ve son CI kayıtlarını kontrol et. Eski Markdown durumunu kanıt kabul etme.
- Son kontrolde hiçbir bilgi belgesi eski veya çelişkili kalmamalı; kanıtı olmayan kabul kriterleri açık kalmalı.

## 2026-10-15 — Authoritative audit note (replaces stale live-status claims; preserves history)

- Review baseline: pre-audit `main` HEAD `5e4ae4668f310f425fbb398d2f180cbe801ad3a8`; latest reviewed implementation commit is `cdfb0a78eca2afe31c1b36d53d44f0e9a165b929` on `review/comprehensive-code-audit-2026-10-15` (PR #2).
- The last known Test Suite run for that baseline failed: run [38632774268](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38632774268). The failure is a stale source-level UI assertion in `tests/test_android_app_readiness.py`: it expected the removed `◇` prefix while `rpg_android_app.py` now uses `text="Yerel modeller · Local GGUF"`. Source shows 598 other tests passed in that run; this is not a current green CI result.
- The source-workspace queue/checkpoint/candidate-index/export implementation already exists in `engine/scenario/source_workspace.py`, is wired through `engine/app/controller.py`, is exposed by `SourceWorkspaceScreen`, and has targeted tests. Older checklist entries saying this feature is wholly unimplemented are stale; end-to-end acceptance and device behavior remain separate gates.
- Model download partial metadata, Range/If-Range resume and model-integrity checks exist in `engine/ai/model_manager.py` and have focused unit tests. App/process lifecycle and physical Android acceptance remain unproven.
- The audit patch validates source batches against the persisted checkpoint and re-derived source chunk; progress callbacks are best-effort. PR commit `cdfb0a78eca2afe31c1b36d53d44f0e9a165b929` passed [GitHub Actions run 38689828532](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38689828532): 601 tests passed, `compileall` passed, Android readiness passed (version 1.1.4, API 36, SAF enabled), and mutation smoke detected 3/3 mutations. This verifies source/CI gates only; no fresh APK or physical-device acceptance was performed.
- Still open: validate the actual user-provided scenario archive through the real engine validator/import path, confirm scenario quest authoring/export coverage, perform full pytest/compile/readiness/mutation gates, produce a fresh APK with provenance, and run real-device acceptance. Do not infer completion from source presence alone.
- Do not rewrite historical notes below as if they were current evidence. Use this dated audit and later dated evidence sections for current status.

## 2026-10-15 — Current implementation and acceptance status

- Latest code/documentation commit: `cdfb0a78eca2afe31c1b36d53d44f0e9a165b929`. CI: [run 38689828532](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38689828532) — 601 tests passed; Python compileall, Android readiness and mutation smoke (3/3) passed.
- Source workspace, ordered queue, durable checkpoints, candidate identity resolution and scenario ZIP export exist in code and have unit/integration tests. The PR also adds stale/forged chunk protection and callback-failure regression coverage.
- Provider-conditional API fields and separate connection/generation tests exist in source. Composer and keyboard behavior still need physical Android acceptance.
- Hugging Face range/resume/hash checks and tests exist; app/process lifecycle behavior still needs device acceptance.
- Still open: validate the actual user-provided scenario archive using the real validator/import/play/save/load flow; fresh APK build plus SHA/provenance; physical-device workflow. Do not mark those items complete based on source tests.
- The 2026-10-14 “not yet implemented” backlog is historical context. Source presence must be checked before repeating those claims; device/release gates remain open until evidence is recorded.