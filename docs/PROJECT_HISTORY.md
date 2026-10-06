# RPG Engine — Unified Project History

**Purpose:** the single chronological record for project history, durable decisions, major failures, corrective actions, and lessons learned.

**Current state:** `AI_START_HERE.md` is authoritative for the present. This file is historical; it must not be used to infer current implementation status when it conflicts with code/tests.

---

## 1. Early foundation and architecture

### v1.7.2 foundation audit

The project performed an explicit foundation audit covering roadmap drift, checkpoint drift, scenario-manifest cross-validation, canonical scenario registry boundaries, chapter Markdown indexing, and the Android boundary. The audit deliberately kept several larger systems deferred rather than pretending they were complete.

### v1.16.0 independent forensic audit

An independent read-only audit found that the deterministic engine/security architecture was materially sound but exposed integration and documentation problems. Important findings included scenario runtime wiring gaps, parser/quest/bootstrap issues, test-runner convention problems, linear retrieval/persistence scaling risks, Android storage/lifecycle risks, and substantial checkpoint/version/test-count drift.

The most important documentation lesson from this audit was itself architectural: **multiple root-level handoff/checkpoint documents can become stale and contradictory even while the code improves.**

### v1.17.0 remediation

The high-value findings from the v1.16 audit were selectively remediated and regression-tested. The engine-authority/security model was preserved. Some scalability and product-level features remained deliberately deferred.

### v1.19–v1.24 gameplay consolidation

The engine expanded through campaign metadata, NPC schedules/movement, temporary status/effect handling, scenario composition and persistence identity, indexed memory retrieval work, NPC living-world foundations, quest/event integration, and related deterministic gameplay systems. The guiding rule remained that AI proposes and the deterministic engine validates/applies.

### v1.26.0 source hardening

The project entered a stronger source-verification phase. Test infrastructure, scenario/runtime wiring, persistence, memory, NPC, quest/event, and Android-shell foundations were progressively hardened. The project continued to distinguish implemented code from unverified Android/device behavior.

---

## 2. v1.27–v1.28 Android/product line

### v1.27.0 — Android readiness milestone

The Android shell moved toward the practical product target: API 36, Kivy 2.3.1, SAF scenario import, and Android readiness verification. Device/APK proof remained explicitly open.

### v1.28.0 — Android UI/provider foundation

The Android UI was rebuilt around a dark/gray ChatGPT-like visual language with rounded controls and lightweight transitions. Provider selection, GGUF SAF import, generic OpenAI-compatible API support, and the Scenario Data Pack Master Specification were added. Native Android llama.cpp remained a separate task at this point.

### v1.28.3 — Android/Colab stabilization baseline

The build path was hardened around persistent caches, non-interactive Android SDK licensing, aligned Android entrypoints/tests, and source packaging verification. This became the historical engineering baseline for the later v1.1 product line.

---

## 3. Historical Android startup failure and root cause

A physical-device launch failure from the older Android line closed the app shortly after startup. The decisive packaged/staged error was:

`ModuleNotFoundError: No module named 'android.main'`

The stale packaged tree contained the obsolete Android entrypoint even though the source architecture had moved to `rpg_android_app.py`. The root cause was therefore **source/staging provenance drift**, not merely a Kivy UI exception.

Corrective architecture:

- canonical entrypoint became `main.py -> rpg_android_app.py`
- obsolete `android.main` / `android.file_picker` references are forbidden
- staged critical files are hash-checked before trusting an APK
- Android startup failures are surfaced through visible diagnostics instead of silent disappearance
- Buildozer cache/staging paths were isolated to reduce stale-source reuse

**Lesson:** a successful Buildozer invocation or an APK file on disk is not proof of correct packaged source.

---

## 4. Colab build lessons

The project initially treated Google Colab as the primary APK delivery environment. Several failures showed that the environment itself was becoming a source of uncertainty:

1. required Python venv support was absent even though basic Python tooling appeared present;
2. a half-created virtual environment survived a failed run and was incorrectly treated as valid on the next run;
3. later builds encountered repeated Buildozer friction and user-reported Colab UI freezes.

The durable decision was to make **GitHub Actions/Linux CI the primary reproducible build route** and retain Colab only as fallback/debug tooling.

**Lesson:** diagnose the failing toolchain layer before changing application code.

---

## 5. v1.1 product reset and hybrid-AI direction

On 2026-10-05 the practical product baseline was consolidated under **v1.1**, while v1.28.3 was retained as the historical engineering baseline.

The product contract became:

- local GGUF + Gemini + OpenAI
- offline play after a compatible local model is installed
- Android standalone product; no Termux requirement for end users
- AI remains a bounded proposer/narrator, never the state authority
- external web/research capability remains separate and off by default

### Local model lifecycle

A product-owned model manager was introduced for validated GGUF import/download, app-private storage, size limits, SHA-256 verification where applicable, atomic partial-file handling, and lifecycle separation from the inference runtime.

### Native llama.cpp direction

The Android runtime contract was defined around a pinned native `llama-server` build for `arm64-v8a`, with Python connecting through the existing process adapter over localhost. The runtime is copied to app-private storage, checked as ELF64 AArch64, and launched only on loopback.

Pinned native source:

- llama.cpp v0.6.0
- commit `d81235049384534c167caea52b85a694f6103d14`

---

## 6. 2026-10-06 — CI/toolchain stabilization

The Android CI contract was hardened around:

- Ubuntu 24.04
- Java 17
- Android NDK `29.0.14206865`
- Buildozer 1.6.0
- python-for-android stable `v2026.05.09` / commit `58d21141f17c889bf8585f5665921d72028f8831`
- pinned llama.cpp source
- isolated build/output directories
- architecture-aware native-binary validation
- pinned GitHub Actions checkout/artifact dependencies

A defect in the first CI design attempted to execute an ARM64 Android binary on an x86_64 host. That was removed and replaced by ELF/header/build-information validation.

A separate application bug was corrected so a desktop user's original GGUF file is not deleted during model activation/import.

A separate **test-only CI gate** was added so source tests and readiness checks run before the expensive native Android build.

---

## 7. Stage 1 — Android startup and staging reliability

**Date:** 2026-10-06  
**Product version:** v1.1.1

Implemented:

- startup/bootstrap diagnostics
- visible Kivy initialization-failure screen
- critical staged-source SHA-256 verification
- rejection of obsolete Android entrypoint references
- local/CI staging verification before APK trust

Verification at the stage boundary was source-level. Real CI packaging and physical-device launch remained unproven.

---

## 8. Stage 2 — Persistence, lifecycle, and data integrity

**Date:** 2026-10-06  
**Product version:** v1.1.2

Implemented:

- autosave after completed mutating turns
- defensive Android lifecycle saves
- diagnostics for autosave failures
- scenario installation/removal ordering hardening
- canonical engine version in new persistence metadata

Verification: **465 passed, 0 failed** at the stage boundary.

---

## 9. Stage 3 — Local AI and provider hardening

**Date:** 2026-10-06  
**Product version:** v1.1.3

Implemented:

- cheap GGUF header/size checks for listings
- full integrity validation immediately before execution
- GGUF structure/version checks before promotion
- cleanup of partial `.part` files
- backgrounding of heavy model import/activation work
- safer native-runtime model replacement using a new loopback port before stopping the old runtime
- direct Gemini selection in Android UI
- HTTPS enforcement for remote OpenAI-compatible endpoints; localhost HTTP remains allowed

Verification: **474 passed, 0 failed**, compileall PASS, Android readiness PASS, scenario validation PASS, mutation smoke PASS.

Still unproven: final CI APK, physical-device install/launch, and real-device local inference.

---

## 10. Stage 4 — UI/UX, presentation, and release QA

**Date:** 2026-10-06  
**Product version:** v1.1.4

Implemented:

- role-aware player/NPC message bubbles
- player messages right-aligned; NPC messages left-aligned
- visible typing state
- presentation-only progressive NPC text reveal
- explicit cancellation of presentation animation events
- persistence completed before result animation begins
- UI focus behavior improved
- version consistency for engine/build metadata
- readiness tests for the new UI/persistence ordering

Verification:

- **477 passed, 0 failed**
- compileall PASS
- Android readiness PASS
- mutation smoke 3/3 detected
- demo scenario validation PASS
- clean release ZIP verification PASS

Release artifact SHA-256:

`b0c47286e3bfae623922b26f875d43a38e7f33d81c5f521e9eb47e456235e456`

### Important boundary

Stage 4 did **not** prove physical Android behavior. The remaining external proof is still a real CI APK plus physical-device QA.

---

## 11. Stage 5 — clean handoff and history consolidation

**Date:** 2026-10-06

The project previously accumulated overlapping current-state documents: root checkpoints, handoffs, memory handoffs, changelogs, decisions, release notes, roadmaps, and historical audits. Their overlapping status claims caused exactly the kind of version/test-count drift identified by the earlier forensic audit.

The cleanup establishes two continuity layers:

1. **`AI_START_HERE.md`** — one current-state handoff only.
2. **`docs/PROJECT_HISTORY.md`** — one chronological historical record containing durable decisions, failures, corrective actions, stage results, and lessons learned.

Technical contract documents such as architecture, constitution, testing, data models, scenario specifications, and AI/runtime specifications remain separate because they describe system behavior rather than project history.

The old duplicate checkpoint/handoff/history/roadmap documents are removed from the release tree so a new AI cannot mistake an old snapshot for the current state.

**Lesson:** current state, technical contract, and historical record are different document types. They should not be duplicated into multiple competing "current" files.

---

## 12. Durable architectural decisions

These decisions remain binding unless deliberately superseded:

1. **Engine authority:** deterministic GameState/rules own truth; AI proposes structured effects only.
2. **Validation gate:** AI-originated mutations must pass the common validation/security boundary.
3. **Scenario-as-data:** scenario canon is data, not executable engine code, and is read-only during gameplay.
4. **Android product boundary:** end users receive a standalone APK; Termux/Python is never a runtime dependency.
5. **Local model lifecycle boundary:** model storage/validation is separated from inference runtime execution.
6. **Native Android runtime:** pinned llama.cpp `llama-server`, loopback-only process communication, arm64 validation.
7. **Build strategy:** GitHub Actions/Linux CI is primary; Colab is fallback/debug.
8. **Test gate:** test-only CI precedes expensive native Android builds.
9. **Source provenance:** staged Android source must be verified before APK artifacts are trusted.
10. **Persistence/animation separation:** UI text animation is presentation-only and must not determine save semantics.
11. **Public repository security:** no credentials, signing material, model files, local saves, APKs, or build caches in Git.

---

## 13. Lessons learned

- **Stale staging can invalidate an otherwise correct source tree.** Verify packaged provenance.
- **APK existence is not runtime proof.** Installation, launch, gameplay, persistence, and inference need independent evidence.
- **Build environment failures should not be misdiagnosed as application defects.** Isolate the first failing layer.
- **A green unit suite can coexist with missing end-to-end Android proof.** Keep external gates explicit.
- **Documentation drift is a real engineering failure mode.** Multiple "current" files create contradictory state.
- **AI features must remain bounded by deterministic engine authority.** UI/provider additions must not weaken that boundary.
- **Heavy model operations must stay off the UI thread.** Presentation animation must remain independent from persistence.
- **Public source repositories require a strict secret/model/build-artifact boundary.**

---

## 14. Current open gates after history consolidation

Only these should be treated as active external product gates unless code/tests establish a new issue:

1. execute the real GitHub Actions test/build workflows;
2. inspect APK and provenance artifacts;
3. install and launch on the Redmi Note 12 Pro 4G;
4. verify scenario import, play, save/load, autosave, lifecycle behavior;
5. verify local GGUF inference on-device;
6. benchmark memory, latency, thermal behavior, and model-size policy;
7. complete any remaining product UX polish discovered by real-device QA.

No historical checkpoint below this line is an alternative current state.
