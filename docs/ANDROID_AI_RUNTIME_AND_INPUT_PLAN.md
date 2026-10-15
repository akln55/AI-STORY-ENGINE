# Android AI Runtime, GGUF Import ve Yazı Alanları — Öncelikli Plan

**Tarih:** 2026-10-15  
**Durum:** Plan kaydedildi; uygulama kodu henüz değiştirilmedi.  
**Repo:** `akln55/AI-STORY-ENGINE`  
**Ana plan:** [`docs/DEVELOPMENT_PLAN.md`](DEVELOPMENT_PLAN.md)  
**Ürün sürümü:** `v1.1.4`

> Bu, mevcut ana geliştirme kampanyasını silen veya onun yerine geçen yeni bir master plan değildir. Kullanıcının telefonda test ettiği APK'nın engelleyici AI/runtime ve giriş alanı sorunlarını önce çözen, ardından daha önce kaldığımız master plan görevlerine dönmek için kullanılan öncelikli alt plandır. Aşağıdaki kutular yalnızca gerçek test kanıtı görüldüğünde işaretlenebilir.

## 1. Kullanıcıdan alınan kanıt ve açık sorunlar

### A. Yerel AI çalışmıyor — en yüksek öncelik

Android ekran görüntüsündeki hata:

```text
runtime could not start: could not start llama-server:
[Errno 13] Permission denied:
'/data/data/org.rpgengine/files/native_runtime/…'
```

Daha sonra oyun ekranında:

```text
You can't do that.
(no AI adapter configured)
```

Bu iki mesaj, model etkinleştirme / yerel runtime başlangıç zincirinin tamamlanmadığını gösteriyor. İlk hata doğrudan `llama-server` çalıştırılırken `Permission denied`; ikinci mesajda oturumun etkin bir AI adapter'ı yok. **Android'in bu dosyayı neden çalıştırmayı reddettiği henüz kanıtlanmış değil.**

Kaynakta `engine/ai/llama_native_runtime.py` içindeki `install_runtime_binary()`, dosyayı uygulamanın özel `native_runtime` dizinine kopyalıyor ve `os.chmod(..., 0o700)` çağırıyor. Bu nedenle yalnızca chmod satırını eklemek/tekrarlamak kök neden çözümü olarak kabul edilmemeli. Dosya modu, dizin erişimi, Android çalıştırma kısıtları ve paketlenmiş ikili dosyanın gerçek konumu cihazda/derleme çıktısında teşhis edilmeli.

### B. GGUF içe aktarma / etkinleştirme

- Kullanıcı, Ayarlar > Yerel modeller bölümünde **GGUF içe aktar** seçeneğine dokunup dosya seçtikten sonra ekranın siyah kaldığını ve iş akışının devam etmediğini bildiriyor.
- Kullanıcı ayrıca model kataloğundan bir model indirdikten sonra etkinleştirme sırasında hata aldığını bildirdi.
- Ekran görüntüsü bu hataların tam stack trace'ini sağlamıyor; iki akışın aynı kök nedene sahip olduğu varsayılmamalı.
- Dosya seçimi iptali, kopyalama, model doğrulaması, UI thread/worker geçişi ve adapter/runtime başlatma adımları ayrı ayrı izlenmeli.

### C. Yazı alanları / klavye / dokunma alanları

- Yazı girilebiliyor ve gönderilebiliyor; fakat kullanıcı yazdığını gönderim öncesi metin alanında göremiyor. Metin, balonun/başka bir widget'ın arkasında veya altında kalıyor.
- Oyun sohbet yazma alanı, API ayarlarının yazı alanları ve gelişmiş ayarlar çevresinde yerleşim/dokunma çakışması var.
- Kullanıcı gelişmiş ayarlar düğmesine dokunurken bazen klavyenin açıldığını söylüyor; bu, odak yönetimi ve widget hitbox/yerleşiminin gerçek cihazda sınanmasını gerektiriyor.
- Amaç genel tasarım yenilemesi değil; yazılan metnin daima görünmesi, gerçek düğmenin doğru tepki vermesi ve klavyenin yalnızca uygun giriş alanına dokunulduğunda açılması.

## 2. Öncelik sırası

### P0 — Yerel runtime başlatma hatasının kök nedenini bul ve düzelt

- [ ] Mevcut `llama_native_runtime.py`, controller'daki model etkinleştirme akışı, APK paketleme/staging doğrulayıcısı ve native build adımlarını birlikte incele.
- [ ] APK'nın gerçek içine `android_native/arm64-v8a/llama-server.bin` eklendiğini, ARM64 ELF olarak doğrulandığını ve kurulumda aynı dosyanın app-private dizine eksiksiz kopyalandığını kanıtla.
- [ ] Cihazdaki runtime ikilisi için dosya boyutu, ELF başlığı/mimari, izin bitleri, parent-directory erişimi, `os.access(..., X_OK)`, kopyalama/rename sonucu ve subprocess errno'sunu kontrollü tanılama kayıtlarına ekle. Kullanıcı verisi, model içeriği veya API anahtarları loglanmamalı.
- [ ] Android'in bu yolda executable çalıştırmayı reddedip reddetmediğini ayır; izin biti doğru olsa bile `EACCES` olasılığını araştır. Paketleme/yürütme yaklaşımı değiştirilirse Android'in desteklediği ve CI/cihaz testinde kanıtlanmış bir yol seç; yalnızca hatayı gizleme veya güvenlik denetimlerini kapatma.
- [ ] Başlatma hatalarını kullanıcıya anlaşılır ve eyleme dönük mesajla sun; dosya bulunamadı, izin/çalıştırma reddi, model geçersiz, süreç erken kapandı ve health-check timeout'u ayırt edilebilmeli.
- [ ] Model etkinleştirme hatasında sessizce adapter kuruldu izlenimi verme. Başarılı başlatmada doğru `LlamaCppProcessAdapter` etkin oturuma atanmalı; başarısız durumda mevcut sağlayıcıyı bozma veya açık hata göster.
- [ ] Regresyon testleri yaz: eksik/yanlış ELF, kurulum modu, subprocess EACCES hata raporu, process erken çıkışı, health-check timeout'u, tekrar başlatma/temiz kapatma.
- [ ] Fiziksel ARM64 Android'de model etkinleştir; server health endpoint'inin yanıt verdiğini ve gerçek generation çağrısının yanıt ürettiğini kanıtla.

**P0 tamamlanma ölçütü:** Sadece APK'nın derlenmesi değil; telefonda GGUF modeli etkinleşiyor, native server gerçekten çalışıyor, adapter ayarlanıyor ve en az bir gerçek AI üretimi tamamlanıyor. Hata yolu testleri de geçmeli.

### P1 — GGUF içe aktarma ve indirilmiş model etkinleştirme akışını sağlamlaştır

- [ ] `rpg_android_file_picker.py` → callback → model kopyalama/kurulum/doğrulama → UI sonuç durumunu adım adım izle.
- [ ] Dosya seçildikten sonra siyah ekran yaratan istisna/ekran geçişi/UI-thread problemini yakala; kullanıcıya ilerleme, başarı veya hata göster. Hata yutulup boş/siyah ekran bırakılmamalı.
- [ ] Büyük dosya kopyalama ve SHA/başlık doğrulamasının UI thread'ini bloke edip etmediğini kontrol et; ağır işler gerekiyorsa worker'da çalıştır ve UI güncellemelerini Kivy ana thread'ine planla.
- [ ] İçe aktarma, katalog indirme, yarım indirmeyi devam ettirme ve model etkinleştirme hatalarını ayrı akışlar olarak test et.
- [ ] İptal, geçersiz uzantı/başlık, boş/kesilmiş dosya, yetersiz alan ve kopyalama istisnası için kullanıcıya açık durum/hata ekle.
- [ ] Model import/activate için küçük test fixture'ları ve UI/controller regresyon testleri ekle; gerçek GGUF dosyasının içeriğini loglama veya Git'e koyma.

**P1 tamamlanma ölçütü:** Dosya seçimi siyah ekranda kalmıyor; geçerli model app-private alana kopyalanıp listeleniyor; geçersiz model anlaşılır hata veriyor; etkinleştirme P0 runtime kontrolüne bağlanıyor.

### P2 — Sohbet composer ve tüm giriş alanları

- [ ] `rpg_android_app.py` içindeki oyun composer'ını, `PillInput`/TextInput uygulamasını, API formunu ve gelişmiş ayarlar kontrollerini gerçek widget sınırlarıyla incele.
- [ ] Metin, hint ve cursor çiziminin arka planda kalma nedenini bul: canvas sırası, widget parent/overlay, boyut/konum veya kapsayıcı yerleşimini kanıtla; sadece renk değiştirerek çözülmüş sayma.
- [ ] Giriş alanları ile butonların `pos/size` çakışmalarını, ScrollView içerik yüksekliği ve küçük ekran/keyboard resize davranışını denetle.
- [ ] Klavye açılınca odaklı TextInput görünür kalmalı; ekran scroll/resize olsa bile yazılan metin görünür ve gönderme kontrolü erişilebilir olmalı.
- [ ] Gelişmiş ayarlar gibi butonlar TextInput odağını yanlışlıkla almamalı; butona dokunmak klavyeyi kendiliğinden açmamalı. Dokunma olayının başka widget'a sızmadığını doğrula.
- [ ] Test alanları: oyun mesajı, API endpoint/model/API key, model katalog araması ve gelişmiş ayarlar içindeki her metin alanı.
- [ ] Hata tekrarını engelleyen kaynak testleri ekle; ancak katmanlama/odak/klavye kabulü fiziksel Android'de ayrıca yapılmalı.

**P2 tamamlanma ölçütü:** Her giriş alanında karakterler gönderimden önce görünür; cursor ve hint doğru hizalı; düğmeler doğru çalışıyor; klavye yalnızca giriş alanında açılıyor ve odaklı alan ekran içinde kalıyor.

### P3 — Tam doğrulama ve fresh Android build

- [ ] Önce ilk başarısız CI adımını düzelt; tüm `pytest` suite'ini çalıştır.
- [ ] `compileall`, Android readiness, mutation smoke ve native llama-server cross-build kapılarını çalıştır.
- [ ] Güncel HEAD'den yeni APK üret; APK metadata, native staging/provenance ve SHA-256 doğrulamasını kontrol et.
- [ ] Artifact yüklemesini ve build provenance çıktısını kontrol et.
- [ ] Tam olarak bu build'den çıkan APK'yı telefona kurup P0/P1/P2 kabul testlerini uygula; build başarısını cihaz kabulü olarak raporlama.
- [ ] Gerçek cihaz kanıtı, test sonucu ve bilinen sınırlamaları bu dosya ile canonical handoff belgelerine yaz.

## 3. Bağımlılık ve uygulama ilkeleri

1. **P0 → P1 → P2 → P3** sırasını koru. AI çalışma zamanı çalışmıyorken görsel düzeltmeleri tek başına çözüm olarak sunma.
2. Kök neden kod/cihaz kanıtıyla bulunmadan mimariyi büyük ölçüde değiştirme. Özellikle zaten bulunan `chmod(0o700)` kodunu incelemeden bir kez daha eklemeyi çözüm sayma.
3. Kullanıcının ekran görüntülerindeki iki metni regresyon kabul ölçütü olarak kullan: `Permission denied` runtime hatası ve `(no AI adapter configured)` mesajı. Başarılı yerel model etkinleştirmesi ardından ikinci mesaj normal oyun işlemlerinde görünmemeli.
4. API tarafında “Bağlantı başarılı” model listesi/endpoint erişimini gösterebilir; tek başına gerçek AI generation kanıtı değildir. API akışı P0 yerel AI sorununu örtmek için kullanılmamalı.
5. Kaynakta var, unit test'ten geçti, CI'dan geçti, APK'da mevcut ve fiziksel Android'de çalıştı durumlarını ayrı raporla.
6. API anahtarları, model dosyaları, kullanıcı kayıtları, APK'lar veya yerel build çıktıları Git'e eklenmemeli.
7. Bu plan bittikten sonra bu dosya silinmeyecek. [Ana geliştirme planında](DEVELOPMENT_PLAN.md) daha önce açık kalan ve bu alt planın kapsamına girmeyen görevler sıradaki öncelikli işe geri alınacak; tarihî/önceden tamamlanan kutular silinmeyecek veya yeniden açılmayacak.

## 4. Çalışma sonu kalıcı kayıt gereksinimi

Her uygulama paketinde:
- Tamamlanan alt kutulara commit/test/CI/cihaz kanıtı ekle.
- `AI_START_HERE.md`, `HANDOFF.md`, `MEMORY.md`, bu plan ve ana `docs/DEVELOPMENT_PLAN.md` dosyalarında durumu senkronize et.
- Bir oturum ortada kesilirse bir sonraki oturum önce bu dosyayı ve ilgili kaynak/testleri okusun.
- Açık kabul kriterlerini otomatik olarak tamamlandı işaretleme.

## 5. Mevcut durum özeti

- [x] Kullanıcıdan alınan runtime hatası ve yazı alanı sorunları bu planda kayıt altına alındı.
- [x] Kaynakta runtime binary kopyalama sonrası `chmod(0o700)` zaten uygulandığı doğrulandı.
- [ ] Android'deki `EACCES` kök nedeni tespit edildi.
- [ ] Yerel model etkinleştirme ve gerçek generation fiziksel cihazda doğrulandı.
- [ ] GGUF import siyah ekran hatası düzeltildi ve cihazda doğrulandı.
- [ ] Composer/API/advanced settings input çizimi, hitbox ve klavye davranışı düzeltildi ve cihazda doğrulandı.
- [ ] Full source CI, native build, APK provenance ve yeni artifact kapıları geçildi.
- [ ] Bu alt plan bittikten sonra ana geliştirme planındaki sıradaki iş yeniden seçildi.


## 2026-10-15 — Implementation progress (supersedes the initial plan-only status above)

**Session 1 / P0 runtime:** PR #4 contains the native-library execution fix. Source CI run [38699968385](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38699968385) and Android build/static APK provenance run [38699968501](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38699968501) passed. Artifact id: 11956422925. This does not close the physical-device gate: model activation and one real AI generation still need testing on an ARM64 Android device.

**Session 2 / P1 GGUF import + P2 text inputs:** implementation is in [PR #5](https://github.com/akln55/AI-STORY-ENGINE/pull/5), stacked on the session-1 branch. SAF copying now runs on a worker, writes a unique temporary file before atomic replacement, and reports cancellation/errors so the busy state can reset. The hidden API endpoint/model TextInputs are now themselves collapsed and disabled; Android soft input uses pan, and focused settings inputs are scrolled into view. Mocked SAF and input-readiness regressions were added.

The first session-2 CI run reported 627 passed / 1 failed; the failing test was a stale assertion for the prior desktop-import method name. The assertion was updated in commit d9a667b800b41d1c9a781b29f642a4c90aeed507. Retest [38703963704](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38703963704) was queued when this note was written. Do not mark P1/P2 or physical-device acceptance complete until latest CI and device checks pass.
