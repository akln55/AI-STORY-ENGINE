> HISTORICAL DOCUMENT — retained for traceability; do not treat as current v1.1 status.


# RPG Engine v1.28.3 — Current Status & Feature Audit

**Audit date:** 2026-10-05  
**Basis:** current clean source tree, project roadmap/specs, tests, source inspection, and the GitHub/Colab handoff history from the active engineering session.

> Scores are implementation-readiness scores, not quality-of-idea scores. A feature receives high credit only when the actual product path is implemented and there is evidence beyond a placeholder/module/unit test.

## Executive assessment

**Overall: 6.5 / 10**

The project is no longer a toy/prototype at the engine layer. Its deterministic state model, validation/atomic mutation boundary, AI security boundary, persistence, memory, scenario infrastructure, NPC foundations, quests/events, and test discipline are comparatively strong. The main reason the overall score is not higher is that the **shipping product path is still incomplete**: Android build/device verification is unproven, the local-AI experience is architectural/partial rather than operational, and several v2.0 social/dialogue/scenario/product-management gates remain open.

## Verification evidence

| Check | Result |
|---|---|
| `python tools/run_tests.py` | **435 passed, 0 failed** |
| `python -m compileall ...` | **PASS** |
| `python tools/mutation_smoke.py` | **3/3 detected** |
| `python tools/validate_scenario.py scenarios/demo-bootstrap` | **PASS** |
| `python tools/verify_android_readiness.py` | **PASS** |
| Real APK build | **unproven** |
| Physical-device launch | **unproven** |
| Real-device local GGUF inference | **unproven** |

## Feature scores

| Area | Score | Current reality | Main gap to 9–10 |
|---|---:|---|---|
| Deterministic engine core | **8.8/10** | Authoritative state, parser, effects, validation, atomic mutation, combat foundation, persistence, invariants, long-session tests are mature. | Final invariant/transaction matrix and broader end-to-end product QA. |
| AI architecture & security | **8.2/10** | Structured AI contract, retries, provider-error separation, authority boundary, security tests, Gemini/OpenAI-compatible/local adapters exist. | More provider hardening and full Android local runtime integration. |
| Memory / context | **8.0/10** | Typed memory, visibility, deterministic indexed retrieval, archive tier, persistence, bounded context tests. | Semantic retrieval, contradiction policy completion, advanced token budgeting. |
| Scenario / canon | **7.5/10** | Packs, manifests, chapters, registry, retrieval, configuration binding, immutable canon, validation exist. | Full authoring workflow, richer arc/timeline data, large-scenario benchmarks, product UX. |
| NPC / living world | **7.2/10** | Goals, schedules, movement, reactions, relationships, knowledge propagation, persistence are present in deterministic scope. | Full faction simulation, richer world events, deeper autonomous chains, product-scale verification. |
| Quest / event / progression | **7.0/10** | Quest lifecycle, prerequisites, chains, deadlines, rewards, events, atomic effects are substantially implemented. | More branching/dynamic quests, broader reward/economy systems, Android UX/end-to-end campaign proof. |
| Dialogue / social consequences | **6.0/10** | Talk flow, NPC targeting, personality/speech context, some quest/relationship integration exist. | Dialogue choices/topics/consequences, information acquisition, secrets/rumors, conversation memory. |
| Combat | **6.3/10** | Attack/defense/damage/HP/XP/level, techniques, stamina, hostile retaliation, defeat/recovery, status effects foundation. | Advanced battle actions, richer combat AI, multi-target/status/buff depth, real campaign QA. |
| Android product shell | **4.5/10** | Kivy UI exists, SAF import exists, provider UI exists, app-private saves/imports exist. | Real APK, device lifecycle QA, scenario/campaign manager UI, settings/provider UX completeness. |
| Local AI product | **3.6/10** | GGUF import/storage + development adapters and UI exist. | **Downloader/catalog, native Android llama.cpp, runtime/process lifecycle, real-device inference**. |
| Build/release pipeline | **4.0/10** | Buildozer spec and hardened Colab notebook exist; staging/path checks were improved. | Reproducible GitHub Actions, successful APK artifact, pinned supply chain, device release evidence. |
| Security / repo hygiene | **7.8/10** | Public-repo rules, `.gitignore`, `SECURITY.md`, secret scan, AI authority boundary, safe scenario ZIP validation. | Finish secure importer/CI permissions, action SHA pinning, release signing strategy, systematic secret scanning in CI. |

## Local AI: exact gap analysis

### Already implemented

- Android UI contains a **Local GGUF** section.
- Android SAF can select a `.gguf` file.
- The file is copied into app-private `models/` storage.
- `LlamaCppAdapter` exists for environments with `llama-cpp-python`.
- `LlamaCppProcessAdapter` exists for a running localhost `llama-server`.
- The controller can select a local adapter in development.
- Tests cover adapter contracts without requiring a real model/network.

### Not implemented / not proven

- There is **no in-app model catalog/downloader** in the current source.
- No code was found for a model URL/catalog, resumable download, checksum verification, storage quota, delete/replacement policy, or download progress UI.
- Android-native llama.cpp is not wired into the shipped APK.
- The process adapter assumes a server already exists; it does not manage the native process lifecycle.
- There is no physical-device proof of real GGUF inference.

### Product implication

Calling the current state "local AI support complete" would be inaccurate. The correct label is **"local model import architecture + development inference adapters implemented; Android local runtime incomplete."**

## Android/build assessment

The Android source contract is much healthier than the build/release state suggests. The historic `android.main` problem has been addressed in source and the current readiness verifier passes. The remaining uncertainty is operational: **can the exact source be reproducibly staged, compiled into an APK, installed, and run on hardware?**

The Colab history indicates that the last blockers were primarily environment/toolchain/host UX problems (missing venv package, broken partial venv, later build/UI friction), not evidence of a core RPG logic defect.

## GitHub migration assessment

The public repo has the right security direction, but the migration is intentionally not yet declared complete:

- source ZIP is present;
- `.gitignore` and `SECURITY.md` are present;
- temporary importer must be fixed before execution;
- importer should use a robust credential scan that cannot misparse a regex beginning with `-`;
- GitHub Actions third-party actions should be pinned by full commit SHA before relying on them;
- test-only CI should come before Android build CI.

## Highest-value next milestones

### Milestone 1 — Secure repository normalization

Extract the source ZIP safely into normal files, preserve security docs, delete the ZIP, run a public-repo secret scan, and commit the result as one auditable change.

### Milestone 2 — Test-only GitHub Actions

CI should reproduce the local evidence: 435-test baseline, compile, mutation smoke, scenario validation, Android readiness, and clean packaging checks.

### Milestone 3 — Android CI

Build with pinned/explicit toolchain inputs, inspect the staged source, produce the APK as an artifact, and record SHA-256 + package metadata.

### Milestone 4 — Device verification

Install/launch the APK, test deterministic gameplay, save/load/autosave, SAF scenario import, provider configuration, and capture logcat on failure.

### Milestone 5 — Local AI product completion

Implement model catalog/download, validation and storage lifecycle, native Android llama.cpp runtime, provider activation, progress/error/offline UI, and real-device inference QA.

## Release posture

**Current label:** `SOURCE / ENGINE VERIFIED — ANDROID RELEASE UNPROVEN`

Do not call v1.28.3 "release-ready" until there is a successful reproducible APK build and the required device QA evidence.
