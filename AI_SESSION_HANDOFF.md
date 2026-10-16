# AI-STORY-ENGINE — Oturum Başlangıç/Handoff

**Snapshot:** 2026-10-16, Europe/Istanbul  
**Depo:** https://github.com/akln55/AI-STORY-ENGINE  
**Ana branch:** main  
**İncelenen başlangıç HEAD'i:** `da9e97504a07d91f14bb1c41ca93c7892bbedd0e`  
**Bu belge, aktif görev için hazırlanmış handoff'tur; yeni sohbette HEAD yeniden doğrulanmalıdır.**

## İlk okuma sırası
1. `AI_RULES.md` — bağlayıcı yetki ve çalışma kuralları.
2. `AI_START_HERE.md` — kısa yönlendirme.
3. `docs/AI_STORY_ENGINE_PROJECT_PROFILE.md` — teknoloji yığını ve kanıtlı durum.
4. `docs/PROJECT_GOALS.md` — aktif hedef.
5. `docs/AI_WORKFLOW.md` ve `docs/PROJECT_TECHNICAL_REFERENCE.md`.

## Proje
Android öncelikli local-first AI text RPG. Geliştirici Android telefondan çalışıyor. Kaydedilmiş stack: Python 3.11 + Kivy; Android paketleme Buildozer + python-for-android. Tercih edilen build host'u GitHub Actions/Linux CI; Google Colab fallback/debug. Yerel AI, Android ARM64 llama.cpp/llama-server ve GGUF model biçimine dayanıyor; bulut sağlayıcılar da adaptör üzerinden opsiyonel. Güncel config ve sağlayıcı desteği her oturumda kaynaktan doğrulanır.

Deterministik engine authoritative GameState'in tek sahibidir. AI yalnızca narration ve yapılandırılmış proposals üretir; validation/security/gameplay kuralları olmadan öneri uygulanmaz. Senaryo canon'u runtime state'ten ayrıdır.

## Etkin görev: belge sistemi ve başlangıç şablonları
- Hedef: AI_RULES, teknik profil, canonical teknik referans ve yeni sohbet handoff şablonlarını oluşturmak; çelişen eski AI yönergelerini çözmek; legacy doküman temizliğini kontrollü branch değişikliği olarak hazırlamak.
- Uygulama kapsamı: Markdown belgeleri ve Session Kit eklentisi.
- Uygulama kodu kapsam dışı.
- Build: bu görevde istenmedi ve başlatılmadı.
- Bağımsız denetim: merge öncesi ayrı AI/sohbet tarafından yapılmalı; bu sohbet kendi denetimini bağımsız onay sayamaz.

## Son kaydedilmiş test/Android durumu
- En son belgelenen yeşil source CI, 2026-10-15 audit notunda commit `51f44c7f9cf2fa1aa0a16fdecb50c89123bf112d`, run `38690247384`, 610 test ve compileall/Android readiness/mutation smoke PASS. Bu, 2026-10-16 başlangıç HEAD'inin güncel doğrudan kanıtı değildir.
- Kullanıcının son bildirdiği Android sorun kayıtları: llama-server Permission denied; model etkinleştirmesi sonrası adapter kurulmamış durumu; GGUF import/selection sırasında olası siyah ekran; chat/settings text-input görünürlük, klavye/odak/touch çakışmaları. Kök nedenler güncel cihaz kanıtıyla tekrar doğrulanmalıdır.
- Bu dokümantasyon görevi sırasında Android build ve gerçek cihaz testi yapılmadı.

## İlk açılışta yapılacaklar
1. Güncel main veya aktif task branch HEAD'ini doğrula.
2. AI_RULES.md ve bu handoff'u oku; uygun branch ve aktif goal'u doğrula.
3. İlgili diff, test konfigürasyonu ve CI sonuçlarını kontrol et.
4. Eski durum notları ile gerçek kaynak kod arasındaki farkları raporla.
5. Bu handoff eskiyse güncel kanıtla yenile; tahmini durumları gerçek diye sunma.
6. Merge'den önce bağımsız denetim ve gerekli test kapılarını tamamla.
