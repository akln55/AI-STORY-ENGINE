# App Readiness Checklist — current status

> **Dikkat — güncellik doğrulaması gerekli:** Bu dosya, önceki bir geliştirme oturumu tamamlanmadan durdurulduğu için güncel olmayan veya kısmen yanlış bilgiler içerebilir. İçindeki durum ve mimari iddialarını güncel gerçek kabul etme. Bir işe başlamadan önce ilgili kaynak kodu, testleri, güncel `main` HEAD'ini ve en son CI sonuçlarını doğrula. Çelişki bulursan bunu sessizce varsayımla düzeltme; gerçek durumu belirt. Her çalışma sonunda bu dosyayı ve etkilenen tüm bilgi içeren `.md` dosyalarını güncelle. Kanıt yoksa bir işi tamamlandı işaretleme.


## Source/package contract

- [x] Android entrypoint is root `main.py` -> `rpg_android_app.RPGEngineApp`
- [x] Engine/app version synchronized at `1.1.4`
- [x] Kivy pinned to 2.3.1
- [x] Target API 36; minimum API 26; arm64-v8a
- [x] Legacy external-storage permission removed
- [x] Android scenario import uses SAF
- [x] App-private save storage
- [x] Pause/stop autosave and deferred autosave during in-flight turns
- [x] Android readiness verifier
- [x] Source CI: 524 tests passed
- [x] `compileall`
- [x] Mutation smoke: 3/3 detected
- [x] Provider-aware AI settings and Hugging Face connectivity diagnostics
- [x] Gameplay errors separated from story narration

## Current Android build run

- [x] Source tests in Android build workflow
- [x] Pinned llama.cpp native cross-build
- [ ] APK debug build
- [ ] Final APK metadata/staging provenance verification
- [ ] APK SHA-256 and provenance artifact upload

Current run: [Android build #122](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38297334671). Refresh these boxes only after the workflow reports its final result.

## Device verification (not yet proven)

- [ ] APK installs on a compatible ARM64 device/emulator
- [ ] First-launch/startup smoke test
- [ ] Gameplay turn completes normally
- [ ] Save/load and background/foreground autosave
- [ ] SAF scenario import and invalid-scenario error path
- [ ] API provider configuration/connectivity
- [ ] Local GGUF activation and real inference
- [ ] Long-session stability and performance/thermal/memory checks

Source tests do not establish that an APK installs or works on a physical device. Do not mark the release Android-verified before device evidence exists.


## 2026-10-14 — Current source/release status

This dated note supersedes stale build-run references above without deleting the historical record.

- [x] Source CI run 38517225272 succeeded on HEAD 59e30799162f94fa59201f75b0b9972577718032.
- [x] Snapshot checks: pytest 549 passed; compileall and Android readiness passed; mutation smoke 3/3; demo-bootstrap scenario valid.
- [ ] Repair/document tools/run_tests.py: 31 passed / 5 failed (pytest/monkeypatch fixture incompatibility).
- [ ] Validate a real ChatGPT-generated scenario archive through import, launch, AI context/retrieval and save/load.
- [ ] Finish scenario list/demo deletion behavior and test Android composer/provider/settings UI on a device.
- [ ] Build APK from current HEAD and verify metadata, provenance and artifact.
- [ ] Physical-device launch, gameplay, save/load and local GGUF inference remain unverified.

Detailed plan: docs/DEVELOPMENT_PLAN.md. This commit updates documentation only; no code fix or APK build was performed.


## 2026-10-14 — Revised campaign acceptance backlog (not yet implemented)

- [x] Inspect the actual failed scenario archive and confirm root cause: string-valued NPC goal plus non-canonical runtime relationship keys. Actual engine validator/app import still pending.
- [ ] Create a schema-aligned ChatGPT scenario pack guide and validation examples.
- [ ] Add incremental ordered chapter/source processing, checkpoints, stable-ID merging, source retention and support for later chapter packages.
- [ ] Create and runtime-wire the in-game AI behaviour prompt/guide.
- [ ] Implement the professional Scenario Builder screen with personalization, ordered source queue, arrows, progress, errors and resume.
- [ ] Simplify provider/API settings and round the API-key input while retaining required OpenAI-compatible configuration.
- [ ] Fix chat composer, text/cursor/hint alignment, keyboard and small-screen behaviour on Android.
- [ ] Finish scenario list/demo removal semantics without silently deleting saves.
- [ ] Fix rejected-event memory, stale memory indexes, and bool-as-int resource validation; add regression tests.
- [ ] Verify downloader resume after app/process closure and fix/document the test helper.
- [ ] Run complete tests/CI, build and verify a fresh APK, and execute available device acceptance tests.

Task statuses must stay unchecked until the listed acceptance criteria are actually evidenced. This section records planned work only; no implementation is claimed.


Note: `docs/SCENARIO_CREATION_GUIDE.md` has been created and aligned to the current loader/registry contract. The broader schema/validator acceptance task remains unchecked until the corrected pack passes the real engine validator and import path.


## 2026-10-15 — Authoritative audit note (replaces stale live-status claims; preserves history)

- Review baseline: pre-audit `main` HEAD `5e4ae4668f310f425fbb398d2f180cbe801ad3a8`; latest audited implementation commit is `51f44c7f9cf2fa1aa0a16fdecb50c89123bf112d` on `review/comprehensive-code-audit-2026-10-15` (PR #2).
- The last known Test Suite run for that baseline failed: run [38632774268](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38632774268). The failure is a stale source-level UI assertion in `tests/test_android_app_readiness.py`: it expected the removed `◇` prefix while `rpg_android_app.py` now uses `text="Yerel modeller · Local GGUF"`. Source shows 598 other tests passed in that run; this is not a current green CI result.
- The source-workspace queue/checkpoint/candidate-index/export implementation already exists in `engine/scenario/source_workspace.py`, is wired through `engine/app/controller.py`, is exposed by `SourceWorkspaceScreen`, and has targeted tests. Older checklist entries saying this feature is wholly unimplemented are stale; end-to-end acceptance and device behavior remain separate gates.
- Model download partial metadata, Range/If-Range resume and model-integrity checks exist in `engine/ai/model_manager.py` and have focused unit tests. App/process lifecycle and physical Android acceptance remain unproven.
- Audit fixes include checkpoint verification against the saved source chunk, best-effort progress callbacks, current UI assertion, PR CI trigger, and safe bounded release ZIP extraction. Commit `51f44c7f9cf2fa1aa0a16fdecb50c89123bf112d` passed [GitHub Actions run 38690247384](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38690247384): 610 tests passed, `compileall` passed, Android readiness passed, and mutation smoke detected 3/3 mutations. This verifies source/CI gates only; no fresh APK or physical-device acceptance was performed.
- Still open: validate the actual user-provided scenario archive through the real engine validator/import path, confirm scenario quest authoring/export coverage, perform full pytest/compile/readiness/mutation gates, produce a fresh APK with provenance, and run real-device acceptance. Do not infer completion from source presence alone.
- Do not rewrite historical notes below as if they were current evidence. Use this dated audit and later dated evidence sections for current status.

## Zorunlu çalışma sonu kuralı — her oturumda uygulanır

- Her kod veya davranış değişikliği tamamlandığında bu dosyayı, `AI_START_HERE.md`, `HANDOFF.md`, `MEMORY.md`, `docs/DEVELOPMENT_PLAN.md`, ilgili checklist'i ve değişiklikten etkilenen **bütün bilgi içeren `.md` dosyalarını** güncelle.
- Her raporda kaynak branch/HEAD SHA'sını, değişen dosyaları, gerçek test komutlarını ve sonuçlarını, CI run bağlantısını, APK/artifact doğrulamasını ve fiziksel cihaz durumunu ayrı ayrı yaz.
- “Kaynakta mevcut”, “yerel test geçti”, “GitHub CI geçti”, “APK üretildi/metadata doğrulandı” ve “gerçek Android cihazında doğrulandı” farklı kanıt seviyeleridir. Birbirinin yerine kullanma.
- Eski tarihli kayıtları silme veya güncel gerçek gibi sunma; tarihî bağlamı koru ve yeni, yetkili durum bölümünü ekle.
- Önceki oturum kesilmişse veya dosyaların güncelliği belirsizse önce ilgili kodu, testleri, mevcut HEAD'i ve son CI kayıtlarını kontrol et. Eski Markdown durumunu kanıt kabul etme.
- Son kontrolde hiçbir bilgi belgesi eski veya çelişkili kalmamalı; kanıtı olmayan kabul kriterleri açık kalmalı.

## 2026-10-15 — Current implementation and acceptance status

- Latest audited code commit: `51f44c7f9cf2fa1aa0a16fdecb50c89123bf112d`. CI: [run 38690247384](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38690247384) — 610 tests passed; Python compileall, Android readiness (version 1.1.4, target API 36, SAF enabled) and mutation smoke (3/3) passed.
- Source workspace, ordered queue, durable checkpoints, candidate identity resolution and scenario ZIP export exist in code and have unit/integration tests. Checkpoints now validate the current source metadata and re-derived source chunk; progress callbacks cannot mark an already completed chunk failed.
- Release verification ZIP extraction is hardened against POSIX/Windows path traversal, symlinks, duplicate/case-colliding paths, and excessive entry/expanded sizes. `tests/test_release_verify.py` covers these cases.
- Provider-conditional API fields and separate connection/generation tests exist in source. Composer and keyboard behavior still need physical Android acceptance.
- Hugging Face range/resume/hash checks and tests exist; app/process lifecycle behavior still needs device acceptance.
- Still open: validate the actual user-provided scenario archive using the real validator/import/play/save/load flow; fresh APK build plus SHA/provenance; physical-device workflow. Do not mark those items complete based on source tests.
- The 2026-10-14 “not yet implemented” backlog is historical context. Source presence must be checked before repeating those claims; device/release gates remain open until evidence is recorded.

## 2026-10-15 — Current verified gates

- Source gates on commit `51f44c7f9cf2fa1aa0a16fdecb50c89123bf112d`: [CI run 38690247384](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38690247384) passed; 610 tests, compileall, Android readiness and mutation smoke 3/3.
- Source queue/checkpoint and bounded release ZIP extraction have regression coverage. The current review's code and docs are on PR #2.
- APK build/provenance, actual user-archive end-to-end validation, and physical Android device tests remain unchecked. Earlier “not implemented” bullets in dated historical backlog sections are not a current code inventory.


## 2026-10-15 — Android blocker sessions

- [x] Session 1 P0 native execution packaging fix and static APK/provenance checks passed in [run 38699968501](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38699968501); source CI passed in [run 38699968385](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38699968385), artifact id 11956422925.
- [ ] Confirm native runtime model activation and one real local AI response on physical ARM64 Android.
- [x] Session 2 implements worker-thread GGUF SAF copy, atomic temporary replacement, visible cancellation/error callbacks, and busy-state reset.
- [x] Session 2 disables/collapses hidden API TextInput hitboxes and scrolls focused settings fields into view with Android soft-input pan.
- [ ] Latest session-2 CI must pass. First run reported 627 passed / 1 stale source assertion failure; assertion fixed, retest [38703963704](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38703963704) was queued at note time.
- [ ] Device acceptance: GGUF import remains responsive on success/cancel/error; model activation produces one real response; composer/API characters are visible before submit; advanced settings do not open the keyboard through hidden input hitboxes.
