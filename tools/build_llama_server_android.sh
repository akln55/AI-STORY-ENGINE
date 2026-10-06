#!/usr/bin/env bash
set -euo pipefail

LLAMA_TAG="v0.6.0"
LLAMA_COMMIT="d81235049384534c167caea52b85a694f6103d14"
OUT="android_native/arm64-v8a/llama-server.bin"
WORK="build/native/llama.cpp"

: "${ANDROID_NDK:?ANDROID_NDK must point to the Android NDK root}"

rm -rf "$WORK"
mkdir -p "$(dirname "$WORK")"
git clone --filter=blob:none --depth 1 --branch "$LLAMA_TAG" https://github.com/ggml-org/llama.cpp "$WORK"
ACTUAL_COMMIT="$(git -C "$WORK" rev-parse HEAD)"
test "$ACTUAL_COMMIT" = "$LLAMA_COMMIT"

cmake -S "$WORK" -B "$WORK/build-android" \
  -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_TOOLCHAIN_FILE="$ANDROID_NDK/build/cmake/android.toolchain.cmake" \
  -DANDROID_ABI=arm64-v8a \
  -DANDROID_PLATFORM=android-28 \
  -DBUILD_SHARED_LIBS=OFF \
  -DGGML_NATIVE=OFF \
  -DGGML_OPENMP=OFF \
  -DGGML_LLAMAFILE=OFF \
  -DLLAMA_BUILD_COMMON=ON \
  -DLLAMA_BUILD_SERVER=ON \
  -DLLAMA_BUILD_TESTS=OFF \
  -DLLAMA_BUILD_EXAMPLES=OFF \
  -DLLAMA_BUILD_TOOLS=ON \
  -DLLAMA_BUILD_UI=OFF \
  -DLLAMA_USE_PREBUILT_UI=OFF \
  -DLLAMA_SUBPROCESS=OFF \
  -DLLAMA_OPENSSL=OFF \
  -DLLAMA_CURL=OFF

cmake --build "$WORK/build-android" --config Release --target llama-server -j "$(nproc)"

mkdir -p "$(dirname "$OUT")"
cp "$WORK/build-android/bin/llama-server" "$OUT"
chmod 0755 "$OUT"

printf 'llama.cpp tag=%s commit=%s\n' "$LLAMA_TAG" "$LLAMA_COMMIT" > "$OUT.build-info"
