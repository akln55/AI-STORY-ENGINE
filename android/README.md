# Android shell

> **Dikkat — güncellik doğrulaması gerekli:** Bu dosya, önceki bir geliştirme oturumu tamamlanmadan durdurulduğu için güncel olmayan veya kısmen yanlış bilgiler içerebilir. İçindeki durum ve mimari iddialarını güncel gerçek kabul etme. Bir işe başlamadan önce ilgili kaynak kodu, testleri, güncel `main` HEAD'ini ve en son CI sonuçlarını doğrula. Çelişki bulursan bunu sessizce varsayımla düzeltme; gerçek durumu belirt. Her çalışma sonunda bu dosyayı ve etkilenen tüm bilgi içeren `.md` dosyalarını güncelle. Kanıt yoksa bir işi tamamlandı işaretleme.


This directory is retained for Android-oriented documentation. The active Kivy application shell is at repository root.

## Runtime

- App entrypoint: repository-root `main.py`
- UI: repository-root `rpg_android_app.py`
- Native document picker: repository-root `rpg_android_file_picker.py`
- Saves: app-private storage
- Scenario import: Android Storage Access Framework (`ACTION_OPEN_DOCUMENT`)
- GGUF model import: Android Storage Access Framework -> app-private `models/`
- Android target: API 36 / min API 26
- ABI: arm64-v8a
- Local inference runtime: app-managed native `llama-server`, no Termux dependency

## Local AI status

The project now contains the model lifecycle boundary and the Android-native llama.cpp runtime lifecycle. The CI build pipeline is responsible for producing the pinned `arm64-v8a` `llama-server` binary before Buildozer packaging.

A physical-device local-model inference test is still required before Android local AI can be marked verified.
