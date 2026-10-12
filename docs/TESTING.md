# RPG Engine Testing & Verification

## Purpose

Verification is layered. A green unit suite alone is not sufficient release evidence. Report the exact run/result rather than copying old counts into current documentation.

## Source CI contract

The current test workflow runs:

1. **Full pytest suite**
   ```bash
   python -m pytest -q tests
   ```
2. **Python compilation**
   ```bash
   python -m compileall -q .
   ```
3. **Android readiness contract**
   ```bash
   python tools/verify_android_readiness.py
   ```
4. **Mutation smoke**
   ```bash
   python tools/mutation_smoke.py
   ```

Latest completed source-only run for the current application code: **524 passed in 10.09s**, compileall PASS, Android readiness PASS (`version=1.1.4, target_api=36, SAF=enabled`), mutation smoke **3/3 detected**.

The Android build workflow also reruns source tests before building the pinned native llama.cpp server and APK.

## Additional local/release checks

These checks are useful when the task or release contract requires them; they are not all part of every source-only CI run:

- Dependency-free runner:
  ```bash
  python tools/run_tests.py
  ```
- Demo scenario validation:
  ```bash
  python tools/validate_scenario.py scenarios/demo-bootstrap
  ```
- Clean release archive verification:
  ```bash
  python tools/release_verify.py RPG_ENGINE_vX.Y.Z.zip
  ```

The dependency-free runner must fail on import errors, exceptions, unresolved fixtures, unsupported async tests, accidental return values, and zero collected tests. Mutation smoke is a targeted test-health signal, not a replacement for full mutation testing.

## Test-health principles

- Critical engine rules need positive and negative tests.
- Atomicity needs proof that rejected batches do not partially mutate state.
- Security/authority boundaries need tests proving forbidden mutation paths fail.
- Long-session tests should periodically check invariants and persistence.
- New critical validation boundaries should add regression coverage and, where appropriate, mutation checks.

## Android release gates

1. Source tests and static readiness checks.
2. Native llama.cpp cross-build.
3. APK packaging.
4. Final APK metadata, staging provenance, and SHA-256 verification.
5. Artifact upload with provenance.
6. ARM64 device startup/crash smoke.
7. Gameplay, save/load/autosave, SAF import, and local-GGUF inference smoke.

An APK build is not physical-device verification. Keep source, artifact, and device evidence distinct.
