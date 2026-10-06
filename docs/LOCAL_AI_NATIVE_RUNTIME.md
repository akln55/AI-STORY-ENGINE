# Local AI Native Runtime — v1.1 milestone

## Status

Date: 2026-10-06
Priority: **10/10**

The Android-native runtime source path is implemented and the reproducible CI build contract is now defined. Real APK creation and physical-device inference remain verification gates.

## Implemented in source

- `engine/ai/model_manager.py` owns GGUF validation, import, storage and Hugging Face file download.
- `engine/ai/llama_native_runtime.py` owns the lifecycle of a bundled ARM64 Android `llama-server` executable.
- Android local AI now uses the native runtime boundary and then connects through `LlamaCppProcessAdapter` on `127.0.0.1`.
- Desktop/development environments may continue using `LlamaCppAdapter`.
- The Android application reports a clear error rather than pretending local inference works when the native binary is missing.

## Native build source

The reproducible build script is:

`tools/build_llama_server_android.sh`

It pins llama.cpp to:

- tag: `v0.6.0`
- commit: `d81235049384534c167caea52b85a694f6103d14`

The script cross-compiles an ARM64 Android `llama-server` with the Android NDK. The portable baseline keeps OpenMP, OpenSSL, llamafile, CURL and the embedded web UI disabled, and builds the server as a static native executable.

The upstream llama.cpp Android documentation supports CMake cross-compilation for `arm64-v8a`, `ANDROID_PLATFORM=android-28`, and the same `GGML_NATIVE=OFF`, `GGML_OPENMP=OFF`, `GGML_LLAMAFILE=OFF`, and `LLAMA_OPENSSL=OFF` constraints used here.

## CI build contract

The intended CI workflow is:

`.github/workflows/android-build.yml`

Build host:

- Ubuntu `24.04`
- Java 17
- Android NDK `29.0.14206865`
- Android platform API 36
- Buildozer `1.6.0`
- python-for-android stable `v2026.05.09` / commit `58d21141f17c889bf8585f5665921d72028f8831`
- ABI `arm64-v8a`

The native step must create:

`android_native/arm64-v8a/llama-server.bin`

before the Buildozer packaging step. The native binary remains ignored by Git and exists only in the CI workspace/build artifact.

## Packaging contract

At application startup/activation:

1. the packaged binary is copied to app-private `native_runtime/`;
2. the file is checked as ELF64 AArch64;
3. executable permission is applied;
4. `llama-server` is started on `127.0.0.1` only;
5. `/health` must return HTTP 200;
6. only then is `LlamaCppProcessAdapter` connected.

## Verification boundary

The following are now separately tracked:

- source/runtime tests: **must pass in CI**;
- native `llama-server` cross-build: **must pass in CI**;
- APK packaging: **must pass in CI**;
- APK artifact hash/metadata: **must be recorded in CI**;
- real Android installation and local-model inference: **still requires a physical-device smoke test**.

The project must not be described as Android-verified until the last item passes.


## 2026-10-06 — CI pre-flight defect correction

Before the first cloud run, the native build contract was statically audited and corrected. The previous script used `--no-checkout`, compared a full Git SHA to a short SHA, and attempted to execute the ARM64 Android binary on the x86_64 CI host. These are now fixed. CI records the native ELF metadata and the pinned build-info line instead of executing the foreign-architecture binary.
