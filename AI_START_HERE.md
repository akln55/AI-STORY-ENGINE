# RPG Engine — AI START HERE

**Canonical current handoff:** this file  
**Canonical historical record:** `docs/PROJECT_HISTORY.md`  
**Current product release:** **v1.1.4**  
**Stage 5 status:** documentation/history consolidation complete; no functional version bump.

> **Rule:** This file describes only the current state. Do not use old checkpoint, handoff, roadmap, or release-note files as current-state evidence. Historical implementation decisions and milestones are consolidated in `docs/PROJECT_HISTORY.md`.

## 1. Product identity

RPG Engine is a deterministic, local-first text RPG for Android. It is a game/simulation engine, not a prose chatbot.

The authority chain is:

```text
Player action
  -> parser / deterministic rules
  -> authoritative GameState
  -> bounded memory/scenario/NPC context
  -> AI proposal
  -> validation/security gate
  -> atomic state mutation
  -> event/quest/memory updates
  -> persistence
```

**AI is never authoritative.** It cannot directly write GameState, saves, databases, scenario canon, or files.

## 2. Current Android target

- Android: standalone APK; no Termux/Python requirement for end users
- min API: **26**
- target API: **36**
- ABI: **arm64-v8a**
- Kivy: **2.3.1**
- Buildozer: **1.6.0**
- python-for-android: **v2026.05.09** / `58d21141f17c889bf8585f5665921d72028f8831`
- Android NDK: **29.0.14206865**
- Primary device for real-device validation: **Redmi Note 12 Pro 4G**
- Android entrypoint boundary: `main.py -> rpg_android_app.py`
- SAF helper: `rpg_android_file_picker.py`

Never restore `android.main` or `android.file_picker`.

## 3. Current AI product contract

Hybrid AI is mandatory at the product level:

- Local GGUF
- Google Gemini API
- OpenAI API

Once a compatible local model is installed, gameplay must remain possible offline. External web/research access is a separate capability and is off by default.

### Local AI status

**Implemented:**
- GGUF import through Android SAF
- app-private model storage lifecycle
- model integrity/structure validation
- AIAdapter boundary
- development llama.cpp adapters
- Android-native `llama-server` lifecycle code
- provider selection including Gemini
- provider/network hardening

**Still not proven:**
- CI-produced native `llama-server` successfully packaged into a final APK
- real-device GGUF inference
- device performance/thermal/memory benchmark
- fully in-app model catalog/downloader

Initial model policy remains conservative: roughly **1.5B–3B instruct**, efficient 4-bit variants, ~2 GB preferred and ~3 GB provisional maximum until real-device benchmarking.

## 4. Current UI contract

- dark/gray ChatGPT-like hierarchy
- rounded surfaces/controls
- player messages right-aligned
- NPC/other speakers left-aligned
- separate speaker bubbles
- NPC responses use progressive text reveal as **presentation only**
- text animation must not control save/persistence semantics

## 5. Current verified source state

The v1.1.4 release package was independently re-verified after packaging:

- **481 passed, 0 failed**
- `compileall`: **PASS**
- Android readiness verifier: **PASS**
- mutation smoke: **3/3 detected**
- demo scenario validation: **PASS** — 3 locations / 2 NPCs / 3 items / 2 quests / 1 lore
- release verification on the clean ZIP: **PASS**

Release ZIP used for this handoff:

`RPG_ENGINE_v1.1.4_UI_UX_RELEASE_HARDENED.zip`

SHA-256:

`b0c47286e3bfae623922b26f875d43a38e7f33d81c5f521e9eb47e456235e456`

## 6. What is proven vs. unproven

### Proven at source/package level

- deterministic engine and validation boundary
- persistence/autosave/lifecycle hardening
- GGUF lifecycle and provider hardening
- Android startup diagnostics and staged-source verification
- current UI/message presentation implementation
- automated regression suite and clean-package verification

### Not proven yet

- a successful real GitHub Actions Android APK build execution
- installation and launch on the Redmi Note 12 Pro 4G
- scenario import/play/save-load/autosave on physical Android hardware
- real local GGUF inference on physical Android hardware
- final performance, thermal, and memory behavior on the target phone

Therefore: **source/package verified, Android release not yet physically verified.**

## 7. Current delivery strategy

1. GitHub Actions/Linux CI is the primary build route.
2. Colab is fallback/debug tooling, not the release path.
3. Test-only CI is the low-cost gate before Android/NDK builds.
4. Android staging provenance must be verified before trusting APK metadata.
5. After the first successful CI APK, run the physical-device verification matrix.
6. Only after device proof should Android/local-AI support be called release-complete.

## 8. Immediate next engineering gate

Stage 5 documentation cleanup is complete. The next engineering task is **external proof**, not another architecture rewrite:

**GitHub Actions test/build execution -> APK provenance inspection -> physical-device QA -> local-GGUF device inference/benchmark.**

If CI fails, diagnose the first failing layer before changing application architecture.

## 9. Non-negotiable regression rules

- Do not reintroduce `android.main` / `android.file_picker`.
- Do not give AI direct state/file/DB/save authority.
- Do not treat a file existing as proof that an APK works.
- Do not treat GGUF import as proof of on-device inference.
- Do not delete persistent build cache on every retry without evidence of corruption.
- Do not commit API keys, tokens, passwords, signing material, model files, local saves, APKs, build caches, or secret `.env` files.
- Do not silently change settled architecture/security decisions.
- Report verified and unverified status separately.

## 10. Reading order for a new AI/developer

1. **This file** — current state and next action.
2. `docs/PROJECT_HISTORY.md` — one chronological record of prior milestones, decisions, failures, and lessons.
3. `docs/ARCHITECTURE.md` — current system architecture.
4. `docs/CONSTITUTION.md` — project rules.
5. `docs/TESTING.md` — verification expectations.
6. Relevant subsystem specification under `docs/` before modifying that subsystem.

Technical specifications remain separate because they define contracts; historical/current-state duplication does not.

## 11. Latest CI audit

The latest CI failures were traced to three issues: a stale CI assertion, a self-match bug in the APK verifier, and an APK package-ID assertion from an older commit. The current build contract uses `package.domain = org` and `package.name = rpgengine`, so the expected generated identifier is `org.rpgengine`.

The corrected verifier checks the final APK rather than trusting Buildozer's internal staging tree. Physical Android installation and local-GGUF inference are still separate release gates.
