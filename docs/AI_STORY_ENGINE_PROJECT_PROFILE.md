# AI-STORY-ENGINE — Proje Profili

> Bu dosya başlangıç profili ve son doğrulanmış snapshot'tır; canlı telemetry değildir. Her görevde güncel HEAD, kod, yapılandırma, testler, CI ve gerekiyorsa gerçek cihaz sonucu yeniden doğrulanmalıdır.

## Kimlik
- Depo: https://github.com/akln55/AI-STORY-ENGINE
- Varsayılan branch: `main`
- Dokümantasyon değişikliği öncesi incelenen main HEAD: `da9e97504a07d91f14bb1c41ca93c7892bbedd0e` (2026-10-16; bu snapshot'tan sonra değişmiş olabilir)
- Ürün hedefi: Android'e paketlenen, local-first, AI destekli metin RPG/senaryo oyuncusu.
- Geliştirici çalışma cihazı: Android telefon. Build araçlarının telefonda çalıştığı varsayılmaz.

## Dil, runtime ve build zinciri

| Katman | Kayıtlardaki teknik temel | Kesinleştirme yolu |
|---|---|---|
| Ana dil | Python 3.11 | Güncel CI, Python dosyaları ve bağımlılık yapılandırması |
| UI | Kivy; Android build belgesinde Kivy 2.3.1 | Build konfigürasyonu ve CI |
| Android paketleme | Buildozer 1.6.0 + python-for-android | `buildozer.spec`, CI |
| Tercih edilen build host'u | GitHub Actions / Ubuntu 24.04 Linux runner | `.github/workflows/android-build.yml` |
| Yedek/debug build ortamı | Google Colab | Yalnızca gerektiğinde; ana yol değil |
| Yerel AI | llama.cpp native ARM64 `llama-server`, GGUF modeller | Runtime adapter, native build script ve cihaz testi |
| Bulut AI | Gemini API ve OpenAI/OpenAI-uyumlu adaptörler; gerçek destek güncel kaynakta doğrulanır | Provider config/adapters |
| Kalıcılık | SQLite (`sqlite3`) | Persistence katmanı |
| Test | `pytest`, ayrıca Android readiness/compile/mutation kontrolleri | `.github/workflows/test.yml` |
| Kaynak kontrol | Git + GitHub | Repo |

Bu tablo eski teknik belgelerden çıkarılmış bir başlangıç noktasıdır. Her oturumda aktif sürüm ve yapılandırma doğrulanır. Önceki belgelerde farklı ürün sürümleri/test sayıları bulunması güncel durumu kanıtlamaz.

## Ürün ve mimari sözleşmeleri
- Engine senaryodan bağımsızdır; kurallar ve authoritative oyun durumu motora aittir.
- AI narration + structured proposals üretir. Validation geçidi olmadan state değişikliği uygulanmaz.
- Tam geçmişi her tur modele göndermek yerine sınırlı bağlam, bellek ve lore retrieval kullanılır.
- Player-known, NPC-known ve system-only/secret bilgi ayrı filtrelenir.
- Kanonik senaryo verisi oyun içi runtime state'ten ayrıdır.
- Senaryo paketi desteklenen JSON + Markdown yapısından oluşturulur ve `.rpgscenario.zip` olarak dağıtılır.
- Mevcut kaynakta `engine/scenario/loader.py` sabitleri `PACK_FORMAT_VERSION = 2`; tipik paket kökünde `manifest.json` ve `world.json` bulunur. Dosya biçimi değişikliklerinde kod/validator son sözü söyler.

## Build ve doğrulama zinciri
1. Kaynak testleri: `python -m pytest -q tests`.
2. Python syntax/compile: `python -m compileall -q .`.
3. Android readiness: `python tools/verify_android_readiness.py`.
4. Mutation smoke: `python tools/mutation_smoke.py`.
5. Gerekli/ayrı yetkili Android build'de native ARM64 llama.cpp cross-build, APK build, APK staging/metadata/hash/provenance.
6. Fiziksel cihaz: açılış, oyun eylemi, save/load, SAF senaryo importu ve gerekli durumlarda gerçek yerel AI üretimi.

Android build workflow yalnızca `workflow_dispatch` ile çalışır. Test workflow pull request ve main push olaylarında çalışır. **Mareşal açıkça istemedikçe Android build workflow çalıştırılmaz.** CI testi ile Android APK/cihaz kanıtı birbirinden ayrı tutulur.

## Son kaydedilmiş durum — güncelliği doğrulanmalı
- Kaynakta son raporlanan yeşil kapsam: 2026-10-15 tarihli `docs/TESTING.md` notu, commit `51f44c7f9cf2fa1aa0a16fdecb50c89123bf112d`, CI run 38690247384, 610 test + compileall + Android readiness + mutation smoke PASS. Bu HEAD'den sonra main'de dokümantasyon commitleri bulunduğundan, bu sonuç şu anki HEAD'in doğrudan kanıtı değildir.
- Son bildirilen Android sorunları (2026-10-15): yerel `llama-server` başlatmada `[Errno 13] Permission denied`; aktivasyon başarısızlığından sonra `(no AI adapter configured)`; GGUF seçimi/importu sırasında olası siyah ekran; sohbet/ayarlar giriş alanlarında metin görünürlüğü, keyboard/focus/dokunma sorunları. Belirtiler rapor edilmiştir; kök nedenler bu profil oluşturulurken yeniden cihazda doğrulanmadı.
- Fiziksel Android doğrulaması: Bu dokümantasyon oturumunda çalıştırılmadı; güncel cihaz durumu kanıtlanmış değil.
- APK/build: Bu dokümantasyon oturumunda build başlatılmadı.
- Bu dokümantasyon değişikliği öncesi main HEAD: `da9e97504a07d91f14bb1c41ca93c7892bbedd0e`.

## Aktif dokümantasyon görevi
- Hedef: Ana AI kurallarını, teknik proje profilini ve yeni sohbet handoff şablonlarını tek tutarlı sistemde toplamak.
- Kapsam: Markdown dokümantasyonu ve şablon eklentisi; uygulama kodu kapsam dışı.
- Bir sonraki adım: Branch diff'ini bağımsız inceletmek, gerekli test/CI kanıtını kontrol etmek, ardından merge kararını vermek.
