# Android APK crash and startup verification

> **Dikkat — güncellik doğrulaması gerekli:** Bu dosya, önceki bir geliştirme oturumu tamamlanmadan durdurulduğu için güncel olmayan veya kısmen yanlış bilgiler içerebilir. İçindeki durum ve mimari iddialarını güncel gerçek kabul etme. Bir işe başlamadan önce ilgili kaynak kodu, testleri, güncel `main` HEAD'ini ve en son CI sonuçlarını doğrula. Çelişki bulursan bunu sessizce varsayımla düzeltme; gerçek durumu belirt. Her çalışma sonunda bu dosyayı ve etkilenen tüm bilgi içeren `.md` dosyalarını güncelle. Kanıt yoksa bir işi tamamlandı işaretleme.


An APK build is not proof that the application launches. This project uses two separate gates.

## Gate A — static APK verification

Run after producing the APK:

```bash
python tools/verify_android_apk.py .ci/bin/rpgengine-*-arm64-v8a-debug.apk \
  --source-dir . \
  --aapt "$ANDROID_SDK_ROOT/build-tools/36.0.0/aapt"
```

This checks ZIP safety, the Python entrypoint and critical-source hashes, obsolete Android imports, packaged ARM64 `llama-server`, and APK metadata.

## Gate B — real Android startup smoke

Use an ARM64 Android device because the product APK is currently arm64-v8a-only:

```bash
python tools/android_apk_smoke.py path/to/app.apk --adb adb
```

The smoke tool clears logcat, installs the APK, force-stops any existing app process, launches `org.rpgengine/org.kivy.android.PythonActivity` with a bounded wait, verifies that the process remains alive, captures logcat, and fails on startup process death or Android fatal-exception markers.

The output log should be retained as release evidence. A successful build plus Gate A without Gate B is still **not** Android release proof.

## CI strategy

GitHub-hosted Android emulator actions are useful for emulator-based Android testing, but this project currently ships an `arm64-v8a`-only APK and therefore the final startup proof should use a compatible ARM64 device/emulator. A self-hosted ARM64 device runner or local ADB session is the authoritative smoke target.
