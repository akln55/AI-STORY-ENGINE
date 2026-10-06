## v1.1 delivery target (2026-10-06)

The active product release target is **v1.1**. The previous v1.28.3 line remains the historical engineering baseline.

Primary delivery route: **GitHub Actions/Linux CI**. Colab is fallback/debug tooling after repeated environment and UI friction.

Before trusting any APK, inspect staged source provenance and verify the active entrypoint `main.py -> rpg_android_app.py`; never reintroduce `android.main` or `android.file_picker`.

# CURRENT ANDROID RELEASE STATUS — 2026-10-06

- Source/readiness contract: **PASS**
- Full test suite before packaging: **MUST PASS**
- Native llama.cpp cross-build: **CI GATE**
- Real APK build: **CI GATE**
- Real-device launch: **NOT PROVEN**
- Preferred build host: **GitHub Actions/Linux CI**
- Colab: **fallback/debugging path**
- Local GGUF import: implemented
- Android-native local inference source path: implemented
- Android-native local inference on physical hardware: **NOT PROVEN**

Do not label the application Android-release-ready until a reproducible APK build and device smoke test are complete.

# Android Build & Device Verification

## Release contract

- Engine/App version: `1.1`
- Historical engineering baseline: `1.28.3`
- Kivy: `2.3.1`
- Buildozer: `1.6.0` in the CI environment
- python-for-android: stable `v2026.05.09` / commit `58d21141f17c889bf8585f5665921d72028f8831`
- Target API: `36`
- Minimum API: `26`
- ABI: `arm64-v8a`
- Native llama.cpp source: `v0.6.0` / `d81235049384534c167caea52b85a694f6103d14`
- Native NDK: `29.0.14206865` for the CI cross-build
- SDK license automation: `android.accept_sdk_license = True`
- UI bootstrap: Kivy / SDL2 through Buildozer/python-for-android
- Scenario import: Android Storage Access Framework (`ACTION_OPEN_DOCUMENT`)
- Save data: app-private storage

## CI order

1. Checkout source at the exact Git commit.
2. Run the Python test suite.
3. Install the exact Android NDK required by the native runtime step.
4. Cross-compile `llama-server` with `tools/build_llama_server_android.sh`.
5. Verify ELF64/AArch64 metadata and record the native binary SHA-256.
6. Build the APK with Buildozer using isolated build/bin directories.
7. Discover the APK only from the configured CI output directory.
8. Verify APK package metadata and SHA-256.
9. Publish the APK and provenance manifest as CI artifacts.

The upstream llama.cpp project currently documents `ubuntu-24.04` Android CI with NDK `29.0.14206865` and the same general CMake cross-build strategy used here.

## Host requirements

Buildozer's Android toolchain runs on Linux/macOS; Windows development should use a Linux environment such as WSL. The project intentionally pins CI to Ubuntu 24.04 rather than `ubuntu-latest`, avoiding future runner changes that could silently move the build onto an unsupported Python/Kivy combination. Current Buildozer 1.6.0 is the latest release, while Kivy 2.3.1 is not compatible with Python 3.14; this is another reason not to float the Ubuntu/Python environment.

Local environment checks remain:

```bash
python3 tools/check_android_env.py
python3 tools/verify_android_readiness.py
./tools/build_android_debug.sh
```

## Device install / smoke test

With Android platform tools installed on a development device:

```bash
adb devices
adb install -r <CI-artifact>.apk
adb logcat
```

The first smoke test should verify:

1. App launches to the gameplay screen.
2. `look` produces the initial world response.
3. A deterministic command advances the game normally.
4. Save succeeds.
5. Load restores the state.
6. Backgrounding the app during a turn does not lose the completed turn; deferred autosave completes when the turn returns to idle.
7. Scenario → Import opens the Android system document picker.
8. A `.rpgscenario.zip` can be selected and copied into app-private import storage.
9. The scenario can be installed and started.
10. Gemini configuration remains optional; the deterministic engine works without a provider.
11. A malformed/invalid scenario produces a user-visible error rather than crashing the app.
12. A compatible local GGUF can be imported into app-private model storage.
13. Native `llama-server` starts on loopback, becomes healthy, and answers one structured inference request.
14. The same local-model turn completes with networking unavailable.

## Important verification boundary

Static source checks are not device evidence. A release must not be marked **Android Verified** until a real APK has been built and the gameplay/local-inference smoke test above has been executed on Android hardware or a controlled emulator.
