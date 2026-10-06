# App Readiness Checklist — v1.27.0

## Code/package readiness

- [x] Android entrypoint is root `main.py` → `rpg_android_app.RPGEngineApp`
- [x] Engine version and Buildozer version synchronized
- [x] Kivy pinned to 2.3.1
- [x] Target API 36
- [x] Legacy external-storage permission removed
- [x] Android scenario import uses SAF
- [x] App-private save storage
- [x] Pause/stop autosave handling
- [x] Deferred autosave after an in-flight turn
- [x] Android readiness verifier
- [x] 432 dependency-free tests
- [x] `compileall`
- [x] Scenario validation

## Environment/device verification

- [ ] Buildozer installed on Linux/macOS/WSL
- [ ] Android SDK installed
- [ ] Android NDK installed
- [ ] API 36 platform/build tools installed
- [ ] Debug APK successfully built
- [ ] APK installs on a real device/emulator
- [ ] First-launch smoke test
- [ ] Save/load smoke test
- [ ] Background/foreground autosave test
- [ ] SAF scenario import test
- [ ] Invalid scenario error-path test
- [ ] Gemini provider test with a real key
- [ ] Long-session mobile smoke test

The unchecked items require an Android build environment or real device and are intentionally not claimed as verified by the source-only sandbox.


### v1.28.2 startup fix
- Android app entry moved from `android.main` to `rpg_android_app`.
- SAF helper moved from `android.file_picker` to `rpg_android_file_picker`.
- Root `main.py` imports the application entry directly.
