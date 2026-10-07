# RPG Engine — Durable Memory

## Project identity

- Android-first deterministic text RPG engine with hybrid AI.
- Product release: `v1.1.4`.
- Historical engineering baseline: `v1.28.3`.
- Public GitHub repo: `akln55/AI-STORY-ENGINE`.

## Architecture rules

- Deterministic engine owns truth.
- AI is an untrusted proposer/narrator behind adapter boundaries.
- AI proposals must pass schema/security/gameplay validation before mutation.
- AI never gets direct GameState/save/database/scenario-file authority.
- Local GGUF + Gemini + OpenAI are the required provider family.
- Offline play must remain possible once a compatible local model is installed.
- External web/research capability is separate and off by default.

## Android contract

- Kivy `2.3.1`
- Buildozer `1.6.0`
- p4a stable `v2026.05.09` / `58d21141f17c889bf8585f5665921d72028f8831`
- API 36 / min API 26 / `arm64-v8a`
- NDK `29.0.14206865`
- llama.cpp `v0.6.0` / `d81235049384534c167caea52b85a694f6103d14`
- target device: Redmi Note 12 Pro 4G
- entrypoint: `main.py -> rpg_android_app.py`
- SAF helper: `rpg_android_file_picker.py`
- never restore `android.main` or `android.file_picker`

## Verification memory

- Best clean-package baseline: `481 passed`.
- Compileall: PASS.
- Android readiness: PASS.
- Mutation smoke: `3/3`.
- Demo validation: `3 locations / 2 NPCs / 3 items / 2 quests / 1 lore`.
- These are package/source verification results, not physical Android proof.

## CI memory

- Test-only CI is independent of Android packaging.
- Android build is manual (`workflow_dispatch`).
- The current verifier checks the final APK directly.
- GitHub Test Suite #30 and #32 failed in the test stage; #31 was cancelled by concurrency.
- Known causes: stale CI assertions, a test-local `UnboundLocalError`, verifier self-match, and an older package-domain expectation.

## Workflow

- Work one stage at a time.
- Fix the first failing layer before changing architecture.
- Preserve solved Android/security fixes.
- Never call Android release verified before a real APK + device smoke test.
