# AI-STORY-ENGINE — Session Handoff

**Purpose:** starting context for a new project session. Always verify the current repository state; do not trust a stored branch/HEAD claim without checking it.
**Repository:** https://github.com/akln55/AI-STORY-ENGINE
**Working branch for this documentation cleanup:** `docs/session-kit-and-canonical-rules`
**Base branch:** `main`
**Scope:** Markdown governance/onboarding cleanup only. No application source or scenario data is in scope.

## Mandatory first reads

1. `AI_RULES.md`
2. `AI_START_HERE.md`
3. This handoff, if it still matches the task
4. `docs/AI_STORY_ENGINE_PROJECT_PROFILE.md`
5. `docs/PROJECT_GOALS.md`
6. `docs/AI_WORKFLOW.md`
7. `docs/PROJECT_TECHNICAL_REFERENCE.md`
8. Relevant specialist docs only

## Task status

- The working branch began from `main` at `da9e97504a07d91f14bb1c41ca93c7892bbedd0e`, then gained seven project-rules/session-kit documents in separate commits.
- A documentation cleanup has now been prepared on that branch: 15 overlapping, dated, or competing plan/status documents are being relocated to `docs/_archive/legacy-2026-10-16/` with an archive banner, while canonical instruction pages and the active goals/log are updated.
- Current state must be verified by querying the live branch and comparing it with `main`. Do not rely on the baseline SHA above as the current HEAD.
- The archive is a procedural Komutan-only triage boundary, not a technical lock. The repository is public. Never put confidential material there.
- Specialist specs, project maps, scenario format/creation docs, and Markdown under `scenarios/` are intentionally preserved in their active paths.

## Verification boundaries

- No app code change belongs to this task.
- Do not start, stop, or retrigger the Android build unless Mareşal explicitly asks.
- No test suite, CI run, APK build, installation, or physical-device check should be claimed unless it is actually performed and confirmed.
- The documentation diff requires an independent Denetçi review. The active task must not mark its merge complete before that review and all required checks are PASS.
- On completion, update `docs/PROJECT_LOG.md` based on observed results and keep `docs/PROJECT_GOALS.md` status accurate.

## Required next action

Inspect the current branch HEAD and diff; verify the moved files, archive manifest, key document links, and any workflow checks exposed by the pull request. Ask an independent Denetçi to review the actual diff. Do not merge on the author's self-review alone.
