# Active Project Goals

This is the authoritative **active goal list**, not a feature wish list. Work on one goal at a time. Priorities may change only after reviewing evidence and getting a decision from the main project conversation/user.

## Rules

- Select the highest-priority actionable goal unless the user explicitly chooses another.
- Before implementation, inspect current code/tests and write a plan with measurable acceptance criteria.
- Do not assume a goal is still open or fixed: re-check current source and evidence.
- Do not add unrelated features while pursuing a goal.
- Once fully accepted, remove the goal from this active list and record it in `docs/PROJECT_LOG.md`. Do not erase history.
- Build/APK work is not implied by any goal; it requires an explicit user request.

## Active goals — priority order

### G0 — Consolidate project documentation and remove ambiguity
**Status:** Documentation branch prepared; independent review and merge pending  
**Purpose:** Keep one obvious instruction hierarchy, preserve genuinely useful specialist contracts, and move old overlapping plans/status notes out of the active documentation surface without destroying history.

Acceptance:
- [x] Inventory Markdown files and classify current instructions, specialist contracts, navigation aids, historical records, and scenario data.
- [x] Maintain a short `AI_START_HERE.md` and put binding role/emoji/archive rules in `AI_RULES.md`.
- [x] Maintain one active goal list (`docs/PROJECT_GOALS.md`) and one concise verified project log (`docs/PROJECT_LOG.md`).
- [x] Preserve historical files while moving 15 overlapping or stale documents to `docs/_archive/legacy-2026-10-16/`; no source history was rewritten.
- [x] Explain the archive's procedural Komutan-only decision rule and disclose that GitHub does not enforce private folders inside a public repository.
- [x] Keep active specialist specs, current project maps, scenario/lore Markdown, and application data out of the cleanup set.
- [x] No application code was changed and no build was triggered.
- [ ] Obtain independent Denetçi review of the documentation diff; merge only after the review and required checks are PASS.

### G1 — Resolve Android local-AI activation and input blockers
**Status:** Open; symptoms must be re-verified  
**Reported symptoms (2026-10-15):**
- Local `llama-server` launch in app-private `native_runtime` fails with `[Errno 13] Permission denied`; root cause not confirmed.
- Gameplay can report `(no AI adapter configured)` after activation fails.
- GGUF selection/import may lead to a black screen or activation error.
- Chat composer and API settings have text visibility, keyboard, focus, or hitbox problems.

Acceptance:
- [ ] Reproduce each applicable symptom on the current source/build and capture the actual error path.
- [ ] Identify root cause from evidence before changing code.
- [ ] Add regression tests for fixable code-level defects.
- [ ] Verify local model activation and player input on a real Android device, if device/build access is available and the user authorizes the required build.
- [ ] Report separately what CI, APK installation, and physical-device testing prove.

### G2 — Prove scenario import and playability end to end
**Status:** Open; previous archive diagnosis needs current-source revalidation  
Acceptance:
- [ ] Inspect the current scenario archive and validator contract without altering the source archive.
- [ ] Validate schema issues such as character-goal object shape and canonical relationship keys against current code.
- [ ] Pass the official scenario validator.
- [ ] Import the scenario through the app's real import path.
- [ ] Start a game, submit an action, receive a valid AI response, apply an allowed state change, save, reload, and continue.
- [ ] Add regression tests for every confirmed defect.
- [ ] Do not claim success from manual JSON parsing alone.

### G3 — Verify state and memory consistency
**Status:** Open; prior review findings require re-checking  
Investigate whether the current code still has these suspected defects:
- Rejected event proposals being persisted as triggered memory.
- Memory updates leaving secondary/search indexes stale.
- Boolean values being accepted where an integer resource is required.

Acceptance:
- [ ] Confirm each finding against current source and tests.
- [ ] Fix only defects that are still present.
- [ ] Add focused regression tests.
- [ ] Verify state, memory, and indexes remain consistent after rejected and accepted effects.

### G4 — Stabilize the minimum reliable gameplay loop
**Status:** Open; depends on G1–G3 findings  
Acceptance:
- [ ] Document one supported end-to-end user journey.
- [ ] Verify scenario import → game start → player action → AI response → validated state update → save → reload → continue.
- [ ] Prioritize correctness and recoverable errors over adding new features.
- [ ] Keep advanced authoring, broad NPC simulation, and extra providers out of scope unless required for this path.

### G5 — Release/build/device acceptance
**Status:** Deferred; explicit user authorization required  
Acceptance:
- [ ] Relevant tests and static checks pass.
- [ ] Current commit is identified and the intended build workflow is inspected.
- [ ] User explicitly asks to start the build.
- [ ] Build provenance, artifact, installation, and device results are reported separately.
- [ ] No claim of device acceptance is made without actual device evidence.

## Deferred / not approved automatically

New features, broad refactors, additional AI providers, expanded memory/NPC systems, and advanced scenario-authoring capabilities are not automatically approved. First prove the existing core path. Add a new goal only after discussing its value, dependencies, and cost.
