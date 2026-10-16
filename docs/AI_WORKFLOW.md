# AI Workflow and Tool Policy

This document governs AI coding sessions working on AI-STORY-ENGINE. Read it before making changes.

## 1. Role and scope

The main project conversation owns product direction and cross-task decisions. A task-specific AI is an implementer, not an independent product owner. It must work only on the assigned goal and report findings that require a broader decision instead of silently expanding scope.

At task start:

1. Confirm the repository and current branch/HEAD.
2. Read `AI_RULES.md` first, then `AI_START_HERE.md`, this workflow, the current `AI_SESSION_HANDOFF.md` if relevant, the project profile, and the selected goal in `docs/PROJECT_GOALS.md`.
3. Inspect relevant source, tests, current docs, Git status/diff if available, and the latest related CI run.
4. Separate **verified facts**, **user-reported symptoms**, **hypotheses**, and **unknowns**.
5. State the exact goal, success criteria, constraints, likely files, and verification plan before coding.
6. If scope is ambiguous, a destructive action is needed, or an important choice is unresolved, stop and ask the user. Do not fill gaps with guesses.

## 2. Planning and implementation discipline

- Prefer the smallest change that solves the assigned problem without weakening architecture or validation.
- Write a step-by-step plan in dependency order. Identify likely regressions and tests before editing.
- Stay within the plan. If evidence shows the plan is wrong or the task needs to expand, pause, explain the evidence, and request a decision.
- Preserve the deterministic engine as the authority over game state. AI output is untrusted input and must pass schema/rule validation.
- Do not perform broad refactors or add features unrelated to the selected goal.
- Do not replace a module wholesale merely because it is large; make incremental, testable changes.
- Never claim a fix from code inspection alone when runtime/device behavior is part of the acceptance criteria.

## 3. Tool selection and discovery

Use the least powerful tool that reliably completes the current step. Tool availability and permissions can differ between chats; never assume a tool or command exists.

### GitHub tools

Use GitHub tools for repository inspection and version-controlled changes. Common operations include:

- Read repository metadata and default branch before acting.
- Enumerate the current tree to find exact paths and inspect the actual structure.
- Read files before editing; use the current branch/ref and current file content.
- Use an atomic multi-file commit when several related documentation files must change together.
- Re-read changed files and inspect the resulting commit/HEAD after writing.
- Inspect Actions runs/logs/artifacts only when CI or build evidence is needed.

Composio may expose tools such as `GITHUB_GET_A_REPOSITORY`, `GITHUB_GET_A_TREE`, `GITHUB_GET_REPOSITORY_CONTENT`, `GITHUB_GET_RAW_REPOSITORY_CONTENT`, `GITHUB_COMMIT_MULTIPLE_FILES`, `GITHUB_CREATE_OR_UPDATE_FILE_CONTENTS`, and GitHub Actions tools. These are examples, not a guarantee that every chat has them.

### Composio

When using Composio, first search/discover tools for the exact task. Read the complete input schema for every tool that will be executed, and confirm the relevant account/connection is active. Use only returned tool slugs and documented argument fields; never invent tool names, parameters, IDs, or connection state. Respect prerequisites and execute dependent steps in order. If a tool reports a permission/connection restriction, stop and report it rather than attempting a speculative workaround.

### Webcmd, browser, and web search tools

Use web/browser/Webcmd tools when the task needs current external documentation, a remote page, official release information, or an external issue that cannot be resolved from the repository alone. First inspect what the installed tool actually supports. Prefer official documentation and primary evidence. Do not use web search as a substitute for reading the source code or tests. Do not expose repository secrets or private data in external queries.

### Local shell, Python, and test tools

Use repository-local commands when available and appropriate for tests, static analysis, parsing, or inspecting diffs. Check exit codes and actual output. Do not report success merely because a command was launched. Never assume that a remote shell is the user's local machine or that local test execution proves Android-device behavior.

### Build and release tools

A build is a separate, potentially costly operation—not an automatic consequence of passing tests. **Do not start, stop, restart, or trigger a build unless the user explicitly asks for it.** The user may request a build only at the final stage. If build authorization is absent, finish the permitted checks and report that a build was not run. Never label an old APK as proof of the current source unless its commit provenance matches.

## 4. Test and acceptance order

Choose tests based on the changed behavior; do not run irrelevant checks merely to create activity.

1. Focused regression tests for the changed behavior.
2. Related test modules or component tests.
3. Full test suite and static/compile checks when practical.
4. Relevant repository validation/Android-readiness/mutation checks.
5. Integration or end-to-end tests for the actual user path.
6. Physical-device/APK acceptance only when explicitly authorized and available.

A test is **passed** only when its command/run completed successfully and its result is inspectable. Distinguish unit tests, CI, APK build, installation, and physical-device verification. Record the exact commit/run and any untested acceptance criteria. Do not start a build just because all earlier checks passed.

For core product flows, prefer end-to-end proof such as: import scenario → start game → submit player action → receive AI response → validate/apply state changes → save → reload → continue.

## 5. Security and data preservation

- Never print, commit, upload, or include API keys, tokens, passwords, private keys, or sensitive environment values in logs/prompts.
- Preserve `.env`, `.gitignore`, secret-scanning rules, user-provided scenario archives, models, saves, caches, runtime data, and build artifacts.
- Do not delete, rename, or bulk-move files without explicit user approval and a path-by-path proposal.
- Do not force-push, rewrite history, or bypass repository protections.
- Before committing, inspect the full diff and ensure it contains only the assigned task.
- If unrelated user changes or a running build may be affected, stop and ask before proceeding.

## 6. Documentation and goal lifecycle

Update documentation **after implementation and verification**, as the final work stage. Do not edit docs first to claim a fix that has not been verified. For a documentation-only task, documentation is the task itself and must be reviewed before commit.

At the end of a task:

1. Report changed paths and the reason for each change.
2. Report tests/checks with exact outcomes; state what was not tested.
3. Record the resulting commit/branch and link when available.
4. Update `AI_START_HERE.md` only if the entrypoint, important current status, or reading order changed.
5. Update `docs/PROJECT_LOG.md` with a concise entry for a completed, verified task.
6. Update `docs/PROJECT_GOALS.md`. Once a goal is fully accepted, remove it from the active list and record its completion in the project log so the history is retained.
7. Do not update every technical document by default. Update only documents whose facts/contracts were actually changed; keep specialist specifications focused.
8. Do not mark a goal complete while acceptance criteria remain open.

## 7. Definition of done

A task is done only when its agreed acceptance criteria pass, relevant tests are reported accurately, the diff is limited to scope, required documentation is updated, and remaining limitations are explicit. A commit, a green unit-test suite, or a successful build alone does not prove overall product readiness.


## 10. Canonical documentation and archive policy

- `AI_RULES.md` is the highest-priority project rule file after the Mareşal's latest explicit instruction. `AI_START_HERE.md` defines onboarding and navigation. `docs/PROJECT_GOALS.md` owns the active goals; `docs/PROJECT_LOG.md` records verified outcomes; the project profile and technical reference summarize baseline facts/contracts.
- Use `docs/project_atlas_map.md`, `docs/runtime_flow_map.md`, and `docs/test_map.md` as navigation aids only. Check all relevant paths and behavior against the current tree and source.
- `docs/_archive/legacy-2026-10-16/` holds preserved legacy plans, duplicate handoffs, older audits, and retired policy docs. They are not current sources of requirements or evidence. Komutan decides whether historical retrieval is necessary. Asker and Denetçi must not follow archived instructions unless Komutan explicitly assigns a bounded historical investigation.
- The repository is public: there is no actual folder-level "Komutan-only" permission. This rule controls workflow behavior, not visibility. Never put secrets in the archive.
- Do not archive specialist contracts, current security/runtime/scenario specifications, or Markdown under `scenarios/` just to lower the file count. Archive candidates must be obsolete or materially overlapping; preserve recoverable history, and record the reason in `docs/_archive/README.md`.
