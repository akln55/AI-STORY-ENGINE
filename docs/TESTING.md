# RPG Engine Testing & Verification

## Purpose

The project uses layered verification. A green unit suite alone is not considered sufficient release evidence.

## Required layers

1. **Pytest suite** — primary test execution when pytest is available.
   ```bash
   python -m pytest -q
   ```
2. **Dependency-free runner** — validates that the same `test_*` functions can execute without pytest, which is important for Android/Termux-compatible environments.
   ```bash
   python tools/run_tests.py
   ```
3. **Mutation smoke test** — deliberately introduces three known-bad mutations into critical validation code and requires targeted regression tests to detect them.
   ```bash
   python tools/mutation_smoke.py
   ```
   This is a test-health signal, not a replacement for full mutation-testing software.
4. **Compilation check**
   ```bash
   python -m compileall -q engine tests tools
   ```
5. **Scenario validation**
   ```bash
   python tools/validate_scenario.py scenarios/demo-bootstrap
   ```
6. **Fresh-package verification** — extract the release ZIP into a clean directory and repeat the required checks there. This catches missing files, stale generated artifacts, and packaging-only failures.

## Dependency-free runner contract

`tools/run_tests.py` is intentionally small. It must fail when:

- a test module cannot import;
- a test raises an exception;
- a fixture name cannot be resolved;
- a test is asynchronous (unsupported by this runner);
- a test returns a value instead of using assertions;
- zero tests are collected.

The runner is not intended to emulate pytest. It provides a deterministic bare-Python execution path for this project's plain test functions and simple fixtures.

## Test-health principles

- Critical engine rules require both positive and negative tests.
- Atomicity requires a test that proves rejected batches do not partially mutate state.
- Security/authority boundaries require tests that prove forbidden mutation paths fail.
- Long-session tests periodically run invariants and persistence checks.
- Mutation smoke tests should be expanded whenever a new critical validation boundary is introduced.
- Release claims must report the exact command and result; do not copy an old test count into current documentation.

## Current v1.24.1 verification target

The test-system hardening milestone adds stricter dependency-free runner behavior, runner regression tests, and mutation smoke coverage. The release gate remains: pytest + stdlib runner + mutation smoke + compile + scenario validation + clean-package verification.

## Release verifier

A release archive can be independently verified from a fresh extraction:

```text
python tools/release_verify.py RPG_ENGINE_vX.Y.Z.zip
```

The verifier checks ZIP path safety, version synchronization, compileall, the
stdlib runner, mutation smoke, scenario validation, and pytest when available.
A release is not considered verified unless the required checks pass.

Mutation smoke is a separate final gate: `python tools/mutation_smoke.py`. It is intentionally not nested inside `release_verify.py` because it launches its own temporary pytest subprocesses.
