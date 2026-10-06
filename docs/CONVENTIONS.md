# RPG Engine — Conventions

Version 1.0 · Phase 0 · 2026-09-23

## 1. Code conventions

- Python 3.11+, stdlib-first (TECH_STACK.md dependency policy is binding).
- Type hints on all public functions; `dataclasses` or `TypedDict` for payloads.
- No global mutable state; `GameSession` owns the runtime.
- Engine modules never print — they return/raise; only CLI/UI prints.
- Errors: raise typed exceptions; validation rejections are logged with reasons.
- Docstrings: one line minimum, Google style.

## 2. Naming & layout

- Packages: `snake_case`. Files: `snake_case.py`. Classes: `PascalCase`.
- IDs: `snake_case` for named entities in packs; UUID/ULID for runtime instances.
- Scenario packs: `scenarios/<pack_id>/` where `pack_id` is kebab-case.
- Tests mirror source layout under `tests/`, named `test_<module>.py`.

## 3. Documentation conventions

- `docs/` is the source of truth; every architectural decision lands in
  `docs/PROJECT_HISTORY.md` as an ADR (`ADR-NNNN: title`, context, decision, consequences).
- Doc versions: `Version X.Y · Phase N · date`, bumped on any content change.
- Specs define contracts; code must match or trigger CONSTITUTION §3.3.
- README changes whenever structure or commands change.

## 4. Testing conventions

- Every phase adds tests before or with implementation (not after).
- Deterministic tests only: AI-touching tests use the scripted fake adapter.
- No network calls in the test suite.
- Long-session tests (1000-turn) run as a separate benchmark target, not in the
  fast suite.
- **Runner:** tests are written pytest-style but must stay runnable on bare
  Python engine development. Primary: `python -m pytest -v`. Android APK builds run in a cloud/desktop Linux environment. When pytest
  is unavailable: `python tools/run_tests.py` (stdlib runner; supports the
  fixtures in `tests/conftest.py` plus the `tmp_path` fixture). CI/handoff
  results must state which runner produced them. New tests must not hard-require
  pytest (use the local `raises` helper pattern from `tests/test_ai_schema.py`).

## 5. Git conventions

- Commit style: `<scope>: <imperative summary>` (e.g., `engine: add validation gate`).
- `saves/` is git-ignored; scenario content is committed.
- Never commit secrets, API keys, or local model paths. Adapters read config from
  a git-ignored local file.

## 6. Change process

Per CONSTITUTION §3: no silent architectural changes; ADR first, then implement.
