# AI-STORY-ENGINE — Start Here

> **Authority rule:** This file is the short entrypoint, not a substitute for source-code verification. Before acting, inspect the current `main` HEAD, relevant code, tests, and latest CI evidence. Historical notes are not proof of current behavior. Do not silently resolve contradictions by guessing.

## Project in one paragraph

AI-STORY-ENGINE is an Android-first, local-first, AI-assisted text RPG/scenario player. The deterministic engine owns game state and validates every proposed state change. AI is a narrator/proposal provider behind adapters; it must never become the authority over canonical state. The project is not considered product-ready merely because tests pass: scenario import, actual gameplay, persistence, and Android-device behavior must also be verified.

## Read only what the task requires

1. **[AI workflow and tool rules](docs/AI_WORKFLOW.md)** — mandatory before editing code or using external tools.
2. **[Active project goals](docs/PROJECT_GOALS.md)** — choose one approved, unfinished goal; do not invent a parallel roadmap.
3. **[Project log](docs/PROJECT_LOG.md)** — concise record of completed work and verified outcomes.
4. **[Architecture](docs/ARCHITECTURE.md)** — engine boundaries and component relationships.
5. **[Testing](docs/TESTING.md)** — test layers and verification expectations.
6. **[Scenario data format](docs/SCENARIO_DATA_FORMAT.md)** and **[scenario creation guide](docs/SCENARIO_CREATION_GUIDE.md)** — when working on scenario packs or imports.
7. **[Android AI runtime and input plan](docs/ANDROID_AI_RUNTIME_AND_INPUT_PLAN.md)** — reported Android blockers; re-check them against current code/device evidence.
8. **[Security policy](SECURITY.md)** and **[repository privacy/secrets rules](docs/REPOSITORY_PRIVACY_AND_SECRETS.md)** — mandatory for all tasks.

Other technical specifications remain available under `docs/`. Read a specialist document only when it directly applies. Do not read or repeat every document by default.

## Repository map

- `rpg_android_app.py` — Android/Kivy application and UI entrypoint; currently large and should be changed incrementally.
- `engine/` — deterministic game engine, AI integration, scenario handling, memory, rules, and persistence.
- `tests/` — automated tests.
- `tools/` — validation, test, and development utilities.
- `scenarios/` — scenario packages and demo content.
- `android/` — Android-specific project/build support.
- `docs/` — technical specifications, workflow rules, and historical material.
- `.github/workflows/` — GitHub Actions workflows.

This map is intentionally high-level. Verify exact paths in the current repository tree before editing.

## Recorded baseline — verify before relying on it

- Repository: [`akln55/AI-STORY-ENGINE`](https://github.com/akln55/AI-STORY-ENGINE), default branch: `main`.
- Last inspected HEAD for this documentation pass: `82018ae48320c51e95c2405e5b60368d8b4ca951`.
- The last reviewed CI run reported 610 passing tests plus compile, Android-readiness, and mutation-smoke checks. Re-open the run and confirm it corresponds to the current HEAD before citing it as current evidence.
- The latest recorded Android-device blockers (2026-10-15) include local `llama-server` launch failing with `[Errno 13] Permission denied`, gameplay reporting no configured adapter after activation failure, possible black screen during GGUF selection/import, and text-entry/keyboard/focus problems in chat and settings. Root causes and fixes must be re-verified; do not claim these are solved without evidence.
- A passing CI run does not prove the APK installs, the native runtime launches, or the app works on a physical device.

## Non-negotiable principles

- One task, one explicit goal, one bounded plan.
- Inspect before modifying; do not guess when source evidence is available.
- Preserve secrets, `.env`, user data, models, saves, runtime data, build outputs, and unrelated work.
- No file deletion, destructive cleanup, build start/stop, release, or other high-impact action without explicit user authorization.
- Do not add features to compensate for an unverified core flow.
- Follow [AI_WORKFLOW.md](docs/AI_WORKFLOW.md) for planning, tool discovery, testing, approvals, and end-of-task documentation.
