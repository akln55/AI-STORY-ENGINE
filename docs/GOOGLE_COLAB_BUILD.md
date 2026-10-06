
# Google Colab Android Build — v1.28.3 (historical / fallback)

> Colab is **not the preferred delivery path anymore**. GitHub Actions/Linux CI is the preferred reproducible build path. Keep this notebook for fallback/debugging and for environments where CI is temporarily unavailable.

## Build contract

- Host Python: 3.12 when available (fallback depends on the notebook preflight)
- Buildozer: current/pinned according to the notebook in use
- python-for-android: stable `v2026.05.09` via `p4a.branch = master` and pinned commit `58d21141f17c889bf8585f5665921d72028f8831`
- Android API: 36
- Android NDK: 29
- Architecture: arm64-v8a
- Kivy: 2.3.1
- Cython: 0.29.34 in the hardened Colab notebook
- Java: 17

## Important Colab lessons already learned

1. The environment must install the Python venv package before invoking `python -m venv`.
2. A usable venv is defined by **both** `bin/python` and `bin/pip` being present and executable; a half-created venv must be recreated.
3. Persistent Buildozer/p4a caches should survive normal retry cycles.
4. `FORCE_CLEAN` is for suspected corruption, not a default reaction to every error.
5. A Colab notebook can be technically correct yet still be a poor delivery path when the hosted session UI freezes near the end of a native build.

## Current intended cache paths

- source: `/content/rpg-engine`
- virtualenv: `/content/rpg-build-venv`
- Buildozer/build cache: `/content/rpg-build-cache`
- APK/bin output: `/content/rpg-build-bin`

## Verification boundary

Static source/tests and APK package integrity can be verified automatically. A real Android launch, import, save/load, autosave, and local-model inference remain device-level checks.


## v1.1 position

Colab is a **fallback/debug path**. GitHub Actions/Linux CI is the primary reproducible delivery route because previous Colab sessions exposed missing venv packages, half-created virtual environments, and later UI/build friction.

The application architecture must not be redesigned merely to work around a Colab/toolchain failure.
