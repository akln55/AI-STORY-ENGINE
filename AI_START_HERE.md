# AI-STORY-ENGINE — Start Here

This file is the concise entrypoint. **Read `AI_RULES.md` first.** Nothing in this file replaces inspection of current source, configuration, tests, branch/HEAD, and CI evidence.

## Mandatory onboarding order

1. **[`AI_RULES.md`](AI_RULES.md)** — binding roles, decision authority, build/merge gates, security, rank signatures, and archive policy.
2. **[`AI_START_HERE.md`](AI_START_HERE.md)** — this repository map and onboarding order.
3. **[`AI_SESSION_HANDOFF.md`](AI_SESSION_HANDOFF.md)** — only as a task handoff; verify that it matches the actual current branch and HEAD.
4. **[`docs/AI_STORY_ENGINE_PROJECT_PROFILE.md`](docs/AI_STORY_ENGINE_PROJECT_PROFILE.md)** — project and environment baseline; verify time-sensitive claims.
5. **[`docs/PROJECT_GOALS.md`](docs/PROJECT_GOALS.md)** — the single active goal list.
6. **[`docs/AI_WORKFLOW.md`](docs/AI_WORKFLOW.md)** — planning, tool discovery, implementation, testing, and reporting workflow.
7. **[`docs/PROJECT_TECHNICAL_REFERENCE.md`](docs/PROJECT_TECHNICAL_REFERENCE.md)** — consolidated architecture and data-contract overview.
8. Read only the specialist contracts required by the assigned goal.

## First task for a new Komutan session

**Perform a read-only repository audit before planning implementation.** Do not begin coding merely because an old handoff contains a task.

1. Confirm repository identity, default branch, current branch/HEAD, working diff if available, and the newest relevant CI result.
2. Read the navigation aids: [project atlas](docs/project_atlas_map.md), [runtime flow map](docs/runtime_flow_map.md), and [test map](docs/test_map.md). These are navigation aids, not guarantees that paths or behavior remain current.
3. Compare the maps to the actual repository tree. Inspect the entrypoints, relevant engine modules, current configuration, tests, and workflows.
4. Cross-check the maps and project profile against [active goals](docs/PROJECT_GOALS.md), [technical reference](docs/PROJECT_TECHNICAL_REFERENCE.md), and the relevant specialist specs.
5. Separate facts verified in current source, historical notes, user-reported symptoms, hypotheses, and unknowns.
6. Return a prioritized audit report: current project shape; what is implemented versus actually verified; stale/conflicting docs; active goals and dependencies; risks; the recommended next task and measurable acceptance criteria.
7. **Do not change files, create branches, delegate tasks, merge, or trigger a build during the initial audit.** Ask for a decision only when an important unresolved product/security/data-loss choice truly requires Mareşal authority. Routine, reversible analysis decisions belong to Komutan.

## Product and architecture invariant

AI-STORY-ENGINE is an Android-first, local-first AI-assisted text RPG/scenario engine. The deterministic engine owns authoritative game state. AI may narrate and propose structured effects; the engine must validate proposals before any state change. Scenario canon and mutable runtime state remain separate. A successful unit test or CI run does not prove a fresh APK installs, local inference starts, or the game works on a physical Android device.

## Repository map (verify on every task)

- `rpg_android_app.py` — Android/Kivy application entrypoint and UI.
- `engine/` — deterministic game logic, AI adapters/security/context, scenario loading, memory, rules, and persistence.
- `tests/` — automated tests.
- `tools/` — validation and engineering utilities.
- `scenarios/` — scenario packs and demo content; files here may be application data, not disposable documentation.
- `android/` and `android_native/` — Android/build/runtime support.
- `.github/workflows/` — CI and explicitly triggered build workflow.
- `docs/` — active specialist contracts, project navigation, profiles, goals, log, and archive.

## Document authority and archive policy

- `AI_RULES.md`, this entrypoint, `docs/AI_WORKFLOW.md`, active goals, and current specialist contracts govern current work.
- `docs/PROJECT_LOG.md` is a short record of verified changes. `docs/PROJECT_HISTORY.md` is historical context.
- `docs/_archive/` contains preserved legacy documents. They are **not** current instructions, plans, test evidence, or status. Only Komutan should decide whether a specific archived file needs to be consulted for historical context. Asker and Denetçi must use current canonical rules and must not follow archived directions unless Komutan explicitly assigns a historical investigation.
- The archive is a procedural boundary, not a technical access-control mechanism. The repository is public, so archived files remain publicly readable. Never place secrets in the archive.
- Do not delete scenario Markdown, technical contracts, or other files just because they end in `.md`; first identify whether they are application data or active specifications.

## Evidence and safety

- Verify code, config, tests, and CI against the exact commit being discussed.
- A reported Android issue is not a proven root cause. Source-level tests, CI, APK creation, APK installation, and physical-device acceptance are different gates.
- Preserve API keys, tokens, `.env`, signing material, saves, user data, private models, and build artifacts.
- **Never start, stop, or retrigger an Android build unless Mareşal explicitly requests it.** Build permission is not implied by a code change or passing tests.
- Do not merge until every required check and an independent Denetçi review are PASS. Asker and Denetçi never merge.
