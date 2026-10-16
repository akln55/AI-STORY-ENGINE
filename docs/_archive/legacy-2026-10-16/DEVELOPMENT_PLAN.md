> **ARCHIVED — 2026-10-16.** This is preserved for historical recovery only. It is not a current source of instructions or status. Consult `docs/_archive/README.md` and follow `AI_RULES.md` first.

---

# AI-STORY-ENGINE — Geliştirme Planı ve Çalışma Kuralları

> **Dikkat — güncellik doğrulaması gerekli:** Bu dosya, önceki bir geliştirme oturumu tamamlanmadan durdurulduğu için güncel olmayan veya kısmen yanlış bilgiler içerebilir. İçindeki durum ve mimari iddialarını güncel gerçek kabul etme. Bir işe başlamadan önce ilgili kaynak kodu, testleri, güncel `main` HEAD'ini ve en son CI sonuçlarını doğrula. Çelişki bulursan bunu sessizce varsayımla düzeltme; gerçek durumu belirt. Her çalışma sonunda bu dosyayı ve etkilenen tüm bilgi içeren `.md` dosyalarını güncelle. Kanıt yoksa bir işi tamamlandı işaretleme.


**Durum:** Kullanıcı tarafından onaylanan uygulama kampanyası yürütülüyor; kabul testleri devam ediyor  
**Plan tarihi:** 2026-10-14  
**Repository:** `akln55/AI-STORY-ENGINE`  
**Planın hazırlandığı kaynak commit:** `59e30799162f94fa59201f75b0b9972577718032`  
**Ürün sürümü:** `v1.1.4`  

> Bu belge, onaylanan kampanyanın kapsamını ve kabul kriterlerini tanımlar. Kampanya onaylandı; uygulama değişiklikleri kabul testleri, CI ve release kapılarına göre ilerletilir. Kapsam dışı yıkıcı migration veya yeni büyük bağımlılık gerekirse yeniden onay alınır.

## 1. Puanlama yöntemi

Puanlar bu projedeki mühendislik önceliğini gösterir; zorluk veya tamamlanma yüzdesi değildir. Her iş şu dört alt puanla (0–10) karşılaştırılır:

- Kullanıcı etkisi: %35
- Temel ürün hedefini engelleme: %25
- Diğer işlerin bağımlılığı / teknik kaldıraç: %20
- Veri bütünlüğü, güvenilirlik ve güvenlik riski: %20

Toplam puan, bu ağırlıklarla hesaplanan mühendislik tahminidir. Bu değerler kullanım telemetrisi değildir; kaynakta doğrulanmış bulgular ve kullanıcının bildirdiği/gösterdiği sorunlara dayanır. Görüntü veya etkileşim sorunlarında gerçek cihaz doğrulaması yoksa durum açık kalır. Bilinmeyen kök neden kesinmiş gibi raporlanmaz.

## 2. Güncellenmiş, öncelik sıralı ana görev listesi

| Öncelik | Görev paketi | Etki | Engel | Bağımlılık | Bütünlük riski | Puan / 10 | Uygulama paketi | Durum |
|---:|---|---:|---:|---:|---:|---:|---|---|
| 1 | Gerçek başarısız senaryo ZIP'ini incele; import kök nedenini kanıtla ve loader/üretici sözleşmesini düzelt | 10.0 | 10.0 | 10.0 | 9.5 | **9.9** | 0 | [ ] Goal, ilişki anahtarı ve `interact` hedef türü uyuşmazlıkları bulundu; resmi doğrulama ve gerçek uygulama import'u bekliyor |
| 2 | Engine şemasına bağlı senaryo sözleşmesi, validator örnekleri ve ChatGPT Senaryo Oluşturma Rehberi (MD) | 10.0 | 9.8 | 10.0 | 9.5 | **9.9** | 1 | [ ] Rehber `interact` hedefi ve açık kayıt bağlantılarıyla güncellendi; CI/validator kabulü bekliyor |
| 3 | Uzun hikâyeler için kaynak paketi yaşam döngüsü: sıralı işleme, checkpoint/devam etme, kararlı ID ile birleştirme ve yeni chapter paketleri ekleme | 9.5 | 9.8 | 9.3 | 9.5 | **9.5** | 1 | [ ] Kaynak kuyruğu/checkpoint/aday indeksi/dışa aktarma kodu ve testleri mevcut; sahte/stale checkpoint doğrulaması ve tam kabul CI bekliyor |
| 4 | Oyun AI Davranış Rehberi ve gerçek prompt/context bağlantısı: anlatıcı/NPC rolü, kanon/runtime ayrımı, bilgi görünürlüğü ve doğrulamaya bağlı efekt önerileri | 9.0 | 9.3 | 9.4 | 9.5 | **9.3** | 2 | [x] Runtime sözleşmesi ve retrieval kodu/testleri mevcut; PR CI run 38690247384 tüm 610 testi ve ek kapıları geçti |
| 5 | Senaryo import → başlat → retrieval/context → oynama → save/load uçtan uca testleri ve geçerli/bozuk fixture'lar | 8.8 | 9.4 | 9.6 | 9.4 | **9.2** | 1, 5 | [ ] Genel entegrasyon testleri mevcut; gerçek kullanıcı arşivi ile import → play → save/load kabulü bekliyor |
| 6 | Tam regresyon, CI, güncel APK build, artifact/provenance ve gerçek cihaz kabul kapısı | 9.0 | 8.0 | 9.5 | 9.2 | **8.9** | 5 (son kapı) | [ ] Bağımlı işlerin ardından |
| 7 | Profesyonel Senaryo Oluştur çalışma alanı: kişiselleştirme, kaynak yükleme/sıralama okları, işlem durumu/ilerlemesi, hatalar ve yeni paket ekleme | 9.5 | 8.5 | 8.6 | 8.5 | **8.9** | 3 | [ ] Kaynak ekranı ve temel akış kodlandı; bölüm paketlerine devam etme, kullanılabilirlik ve cihaz kabulü açık |
| 8 | Motor bütünlüğü düzeltmeleri: reddedilmiş event'ten sahte memory yazılmasını engelle; dedup sonrası indeksleri yenile; resource integer doğrulamasında bool reddet | 8.3 | 8.3 | 7.8 | 9.7 | **8.5** | 4 | [x] Düzeltmeler ve regresyon testleri mevcut; PR CI run 38690247384 610 testi ve ek kapıları geçti |
| 9 | Oyun/Senaryolar listesi ve demo yönetimi: demo sabitlenmesini kaldırma, silme onayı ve save koruması | 8.2 | 8.0 | 7.0 | 8.0 | **7.9** | 3 | [x] Demo sabitleme ve silme onayı/save koruması kaynak testlerinde mevcut; gerçek cihaz kabulü ayrı kapı |
| 10 | Sohbet yazma alanı: yuvarlak composer, metin/imleç/hint hizası, uzun metin, klavye ve gönderme kontrolü | 8.8 | 7.0 | 7.0 | 7.0 | **7.6** | 3 | [ ] Composer boyutlandırma/çift gönderim korumaları kaynak testlerinden geçiyor; klavye görünürlüğü, imleç/hint hizası ve kaydırma gerçek cihazda doğrulanmadı |
| 11 | AI/API ayarlarını sadeleştir: sağlayıcı seçimi + anahtar; OpenAI-compatible için gerekli gelişmiş alanları koşullu göster; API anahtarı girişi tasarımı | 7.8 | 7.0 | 7.5 | 7.7 | **7.5** | 3 | [ ] Sağlayıcıya göre alan gizleme ve bağlantı/gerçek generation ayrımı kaynakta mevcut; fiziksel cihazdaki kullanım kabulü açık |
| 12 | Hugging Face indirmesinde partial dosyayı koruma ve uygulama yeniden açılınca devam etme akışını doğrula | 7.5 | 6.8 | 6.8 | 8.2 | **7.3** | 4 | [ ] Range/ETag/partial doğrulama kodu ve birim testleri mevcut; uygulama kapat-aç ve Android cihaz lifecycle kabulü açık |
| 13 | tools/run_tests.py davranışını düzelt veya desteklenen test komutunu açıkça belgele | 6.5 | 5.5 | 5.8 | 6.5 | **6.1** | 4 | [x] Tam proje komutu `python -m pytest -q tests` runner içinde belgeli; eski 31/5 sonucu tarihî. Güncel CI run 38690247384 610 test ve tüm ek kapılardan geçti |

Görev 13'ün puanı yüksek olsa da diğer işler tamamlanmadan APK üretmek doğru sıralama değildir. Puan önem/etkiyi, aşağıdaki kampanya akışı ise bağımlılıkları gösterir.

Puan sınırları: Gerçek ZIP artık incelendi; üç ayrı şema/runtime uyuşmazlığı tespit edildi. Görev 1'in tamamlanması için resmi validator ve uygulama import'u hâlâ gerekiyor. Görev 7'deki durumlar için doğru render/etkileşim ancak Android cihazında test edilince onaylanabilir.

## 3. Senaryo sistemi — hedeflenen davranış ve teşhis planı

### Kullanıcı hedefi

Kullanıcı ayrı bir ChatGPT sohbetinde “Martial Peak için senaryo oluştur” gibi bir istek verebilmeli ve gerekirse kaynak bilgi dosyalarını ekleyebilmelidir. ChatGPT; uygulamanın kabul ettiği, indirilebilir **`.rpgscenario.zip`** arşivi oluşturmalı. Kullanıcı bu paketi Android uygulamasından içe aktarmalı. Uygulama paketi doğrulamalı, başlangıç dünya durumunu kurmalı, kanonik verileri aramaya/context'e açmalı ve AI bu bilgileri kullanarak oynanabilir bir hikâye çalıştırmalıdır.

Paket; serbest biçimli sohbet transkripti veya yalnızca lore Markdown'ından ibaret olmamalıdır. Hikâye anlatımına yardımcı dosyalar olabilir; fakat dünyayı kuran ve oyun kurallarınca referans verilen veriler şemaya uygun JSON olmalıdır.

### Kaynakta doğrulanmış paket sözleşmesi

Güncel loader'a göre:

- `manifest.json` ve `world.json` gereklidir.
- Kanonik data dosyaları arşivde `data/` altında bulunur ve desteklenen dosya adları ile sınırlıdır: `characters.json`, `locations.json`, `factions.json`, `items.json`, `techniques.json`, `realms.json`, `creatures.json`, `events.json`, `relationships.json`, `timeline.json`, `knowledge.json`.
- `lore/*.md` ve chapter manifest/content dosyaları ek bağlam sağlayabilir.
- `manifest.json` kimliği, sürümü ve paket formatı; JSON referansları ve NPC goals gibi yapılandırılmış alanlar loader/registry kurallarına göre doğrulanır.
- NPC `goals` girdileri nesne olmalı; geçerli girişler en az `id`, `description`, `priority` taşımalıdır. Desteklenen `kind` değerleri ve `move_to`, `follow_npc`, `meet_npc`, `patrol` koşulları loader/registry ile tutarlı olmalıdır.
- Başlatılan dünya `world.json` üzerinden kurulmalıdır. AI'nın kullanabileceği kanonik bilgi, registry/retrieval context yolu üzerinden sağlanmalıdır; modelin dosyayı doğrudan açtığı varsayılmamalıdır.

### Senaryo hatasını çözme sırası

1. Kullanıcıdan **başarısız olan orijinal senaryo `.zip`/`.rpgscenario.zip` dosyasını** iste. Dosya olmadan alan biçimini tahmin etme.
2. Arşivi değiştirmeden listele; `manifest.json`, `world.json`, ilgili `data/characters.json` ve hata veren `npc_kim_minjae.goals` girdisini çıkar.
3. Arşivin gerçek yapısını, ChatGPT tarafından üretilen dosyayı oluşturan talimat/şema ile karşılaştır.
4. Hatanın sınıfını belirle: üretim biçimi uyuşmazlığı mı, eski şema uyumluluğu mu, loader doğrulama hatası mı, yoksa paket yolu/formatı hatası mı?
5. `goals` bilgisini silmeden veya doğrulamayı kapatmadan düzelt. Gerekirse açık bir schema sürüm/uyumluluk kuralı ekle; eski ve yeni paketleri ayrı test et.
6. Başarısız dosyayı temsil eden bir regresyon fixture'ı, geçerli/bozuk goal örnekleri ve tam import → launch testleri ekle.
7. Başarılı paketin `tools/validate_scenario.py`/`load_scenario()` kontrolünden ve gerçek uygulama import yolundan geçtiğini doğrula.

### ChatGPT senaryo üretim kuralı

Her yeni senaryo üretiminde:

1. Önce bu belge ve kodla aynı sürümdeki senaryo formatını oku; güncel örnek/şablon ve validator sonucunu temel al.
2. Dünya başlangıç durumu, lokasyonlar/bağlantılar, karakterler/NPC'ler, item/ilişki/event/quest verilerini tutarlı ID'lerle üret.
3. Data/lore ayrımını koru. Bir oyun etkisi, referans veya başlangıç durumu için gereken bilgi yalnızca serbest Markdown metnine saklanmasın.
4. Her `*_id` referansını doğrula; ID'leri farklı dosyalarda aynı tut. NPC goals ve chapter manifests için geçerli şemayı uygula.
5. Paketi arşivlemeden önce validator ile kontrol et. Doğrulayıcı çalıştırılamıyorsa paket “test edildi” diye sunulmasın; sınır açıkça belirtilsin.
6. Kullanıcıya tek ve anlaşılır `.rpgscenario.zip` dosyası ver; içine `manifest.json`, `world.json`, `data/` ve isteğe bağlı desteklenen lore/chapter belgeleri konulsun.
7. Uygulamaya import ve AI retrieval doğrulaması yapılmadan “oynanabilir ve tamamen uyumlu” denmesin.

## 4. Senaryo listesi ve demo davranışı

Hedeflenen ekran:

- **Oyun** sekmesinde `Senaryolar` başlığı ve senaryoların listesi görünür.
- Uygulamanın örnek `demo-bootstrap` dünyası da bu listede normal bir senaryo girdisi olur; ana ekranda veya oyun ekranında zorunlu/kalıcı bir demo sohbeti olarak sabitlenmez.
- Kullanıcı içe aktardığı senaryoyu başlatabilir, son oyununu uygun bir “Devam et” davranışıyla açabilir ve senaryoyu listeden kaldırabilir.
- Bir senaryoyu kaldırma işleminden önce açık onay alınır; yanlışlıkla silmeyi azaltmak için senaryo adı gösterilir.
- Silme işleminin senaryo dosyasını mı, son oynananlar kaydını mı, ilişkili kayıt slotlarını mı etkileyeceği açıkça tasarlanmalı. Aktif kampanya veya ona ait kayıtlar sessizce silinmemeli.
- Demo uygulama tarafından yeniden oluşturulacak bir örnek mi yoksa silinince geri getirilebilen normal paket mi olacak, uygulamaya geçmeden önce kullanıcıyla netleştirilir.

**Uygulamaya geçmeden önce kullanıcıdan sorulacak konu:** Demo kaldırıldığında yalnızca listeden kaldırılması mı, uygulamanın kurulu demo paketinin silinmesi mi, yoksa demo ile ilişkili kayıtların da silinmesi mi isteniyor? Varsayılan güvenli yaklaşım, ilişkili kayıtları otomatik silmemektir.

## 5. Hugging Face indirme — hedeflenen davranış

Kaynakta indirme işlemi zaten ayrı bir worker thread içinde çalışıyor; `.part` dosyası, dosya boyutu sınırları, bütünlük kontrolleri ve HTTP Range ile devam ettirme mantığı mevcut. Bu nedenle indirme altyapısını sıfırdan yazmak ilk tercih değildir.

Öncelikli iyileştirme ve doğrulama:

- İndirme ilerlemesi UI thread'ini bloklamamalı.
- İndirme sırasında modal pencere/uygulama kapatılırsa indirme işleminin durumu açıkça belirtilmeli; kullanıcı yanlışlıkla indirmeyi yok ettiğini sanmamalı.
- Süreç kapanması veya bağlantı kesilmesi sonrasında `.part` dosyası korunmalı, bozuk/kısmi içerik geçerli `.gguf` gibi listelenmemeli.
- Aynı repo + dosya adı + revision tekrar seçildiğinde mevcut partial bulunmalı ve güvenli şekilde devam ettirilmeli; Range desteklenmiyorsa dosya kontrollü olarak baştan başlatılmalı.
- İndirme ekranında yarım kalan işler ve `Tekrar dene / devam et` davranışı açık olmalı. Uygulama yeniden açıldığında kullanıcının dosya adı/revision değerlerini ezbere girmesi gerekmemesi hedeflenir.
- Son dosya yalnızca uzunluk/GGUF-header/SHA-256 kontrolleri tamamlandıktan sonra nihai `.gguf` adıyla görünür olmalı.
- Ağ kesintisi, uygulama sürecinin öldürülmesi, tekrar açılma, HTTP 206/200 yanıtları, yanlış boyut/digest ve çift indirme için testler eklenmeli.

**Kapsam ayrımı:** “Uygulamaya dönünce indirmeye devam et” ile “uygulama Android'de arka plandayken veya işlem sonlandırılmışken indirme sürsün” farklı garantilerdir. İlk hedef kalıcı partial + yeniden açınca devam ettirmedir. Gerçek Android foreground service/background transfer gerekirse ayrıca tasarlanmalı ve kullanıcı onayı alınmalıdır; sadece daemon thread çalışıyor diye OS düzeyinde kesintisiz arka plan garantisi verilmez.

## 6. Kod doğruluğu ve test yapılacakları

### Bellek indekslerinin güncellenmesi

- Yinelenen `MemorySystem.add()` çağrısı mevcut kaydı güncellediğinde `_entity_index`, `_location_index`, `_event_index`, `_tag_index` ve `_gram_index` eski/yeni değerleri yansıtmalı.
- Düzeltmeden önce ve sonra testler; yeni etiket, lokasyon, entity ve event filtreleriyle kaydı bulabilmeli.
- Yükleme ile indekslerin yeniden kurulması ve dedup davranışı da korunmalı.

### Reddedilmiş event önerisi ve hafıza

- `events_triggered` önerisi reddedildiğinde, aynı yanıtın event'in gerçekleştiğini iddia eden `memory_updates` alanı gerçeğe dönüştürülmemeli.
- `state_changes`, `npc_changes` ve event trigger önerileri için ortak kabul/ret politikası tanımlanmalı.
- Saf bellek güncellemesinin (hiç reddedilen efekt bulunmayan durumda) kabul edilmesi gibi geçerli senaryolar korunmalı.

### Tip güvenliği

- Tam sayı isteyen `resource` değerleri `bool` türünü reddetmeli (`isinstance(value, int) and not isinstance(value, bool)` veya eşdeğer katı doğrulama).
- Başka alanlarda int/bool tutarlılığı kontrol edilmeli; clamp davranışı geçerli integer'lar için sürdürülmeli.

### Test runner

- Tercih edilen komut CI ile aynı olmalı: `python -m pytest -q tests`.
- `tools/run_tests.py` destekleniyorsa `pytest`, `monkeypatch` ve mevcut fixture kullanımını gerçekten desteklemeli; değilse “stdlib runner” iddiası ve talimatları güncellenmeli.
- Test runner başarısızlığını kapatmak için CI'de testleri sessizce atlama veya assertion kaldırma yapılmamalı.

## 7. Android UI kabul kriterleri

- Oyun tabında `Senaryolar` bölümü açıkça görünür; boş/kurulu/son oynanan/aktif kampanya durumları birbirinden ayrılır.
- Demo diğer senaryolarla benzer yönetim akışında bulunur ve zorunlu şekilde sabitlenmez.
- Senaryo başlatma, silme onayı, iptal, liste yenileme ve aktif kayıt koruması test edilir.
- Sohbet composer'da metin/hint/cursor aynı hizadadır; yuvarlak arka plan input boyutuna senkron kalır.
- Android sanal klavyesi açılırken giriş alanı/gönder düğmesi görünür ve sohbet kaydırması kullanılabilir kalır.
- Gemini seçiliyken gereksiz endpoint alanı gizlenir; OpenAI-compatible için endpoint ve model alanları gerekir. Model-listesi bağlantı testi, gerçek generation testi yerine sayılmaz.
- Font/ikon karakterleri gerçek cihaz ekranında kontrol edilir; desteklenmeyen sembol veya bozuk glyph bırakılmaz.
- UI kaynak testi ve gerçek Android cihaz ekran görüntüsü/etkileşim testi ayrı raporlanır.

## 8. Geliştirme çalışma kuralları (bağlayıcı)

1. **İşe başlamadan önce bağlamı oku:** `AI_START_HERE.md`, `HANDOFF.md`, `MEMORY.md`, `docs/CONSTITUTION.md` ve görevle ilgili teknik belgeleri oku. Bu kullanıcı tarafından sağlanan `AI_Tooling_Guide_GitHub_Composio_Webcmd.md` rehberi de mevcutsa oku.
2. **Araçları keşfet:** Her oturumda gerçekten mevcut araç kataloğunu ve gerekli şemaları doğrula. Geçmişten kalan tool slug, branch, commit, run ID veya parametreleri doğrulamadan kullanma.
3. **Önce plan, sonra izin:** Her hata düzeltme veya geliştirmeden önce etki, varsayımlar, değişecek olası dosyalar, testler, kabul kriterleri ve geri alma yaklaşımını içeren kısa plan hazırla. **Kod/ürün davranışını değiştirmeye başlamadan önce kullanıcı onayı al.** Kullanıcının onayı olmayan farklı işleri aynı commit'e gizlice ekleme.
4. **Bilinmeyenleri tahmin etme:** Şema, davranış veya silme etkisi belirsizse gerçek kaynak/veri dosyasını iste veya kullanıcıya sor. Hata mesajına bakarak producer/consumer tarafını kesin suçlama. Bir varsayım zorunluysa açıkça belirt ve onay almadan geri dönüşü zor davranış seçme.
5. **En küçük ilişkili değişikliği yap:** Önce kök nedeni çöz; genel yeniden yazım veya alakasız refactor yapma. Güvenlik/validasyon kontrolünü sadece hatayı susturmak için kaldırma.
6. **Testleri değişiklikle beraber yaz:** Yeni özellik veya bug fix için hedefli regresyon testi ekle. Ardından ilgili testler, `python -m pytest -q tests`, `python -m compileall -q .`, Android readiness ve mutation smoke çalıştır; hangi komutların gerçekten koştuğunu açıkça bildir.
7. **Kanıt seviyelerini ayır:** “Kodda mevcut”, “kaynak testinden geçti”, “GitHub CI geçti”, “APK build edildi”, “APK metadata/provenance doğrulandı” ve “gerçek cihazda test edildi” ayrı durumlardır. Birini diğerinin kanıtı gibi sunma.
8. **Belgeleri her işten sonra güncelle:** `AI_START_HERE.md`, `HANDOFF.md`, `MEMORY.md` ve konuyla ilgili `docs/*.md` içindeki mevcut durum, blocker, test/build kanıtı ve açık kalan işler aynı gerçeği anlatmalı. Eski tarihli/historical belgeleri güncel durum gibi yeniden yazma; gerekiyorsa tarihli ek yap.
9. **GitHub güvenliği:** Doğru repo/branch/head SHA ve mevcut diff'i doğrula. Birbiriyle ilgili değişiklikleri atomik, açıklayıcı commit'le gönder. Commit sonrası dosyaları yeniden oku ve yeni commit SHA'yı doğrula.
10. **Sırları koru:** Token, API key, parola, `.env`, signing key, GGUF, APK, build cache veya yerel oyun kayıtlarını repoya ekleme. Hata loglarında sırları/kullanıcı verisini ifşa etme.
11. **Build'i gerekçesiz başlatma:** Kod değişiklikleri onaylandıktan ve source gates geçtikten sonra Android build için plan/izin akışını takip et. Build başarısızsa ilk başarısız job/step/log'u incele; rastgele tekrarlama yapma.
12. **Son rapor zorunludur:** Yapılan değişiklikler, dosyalar, commit SHA, test sonuçları, CI/build/run bağlantısı, artifact durumu, fiziksel cihaz testleri ve açık işler birbirinden ayrı belirtilmeli.
13. **Onay kapsamına sadık kal:** Bir aşama onaylandıysa sadece o aşamayı yürüt; yeni risk veya yeni belirsizlik ortaya çıkarsa dur, bulguyu açıkla ve yeniden onay iste.

## 9. Tek onayla yürütülecek uygulama kampanyası

Kullanıcı tüm bu kapsamı onaylarsa işler tek bir geliştirme kampanyası olarak, bağımlılık sırasıyla yürütülür. Bu, her şeyi tek dev commit'e koymak demek değildir: ilişkili değişiklikler küçük, atomik commit'ler ve doğrulama kapılarıyla yapılır. Onay verilen kapsam içinde her paket başında tekrar onay istenmez; yeni özellik, yıkıcı davranış veya plan dışı teknik karar gerekirse durulur ve yeniden onay alınır.

### Paket 0 — Girdi ve mevcut durum doğrulaması (koda dokunmadan)

1. Gerçek repo HEAD'ini, araçları, senaryo loader/registry/context akışını yeniden doğrula.
2. Kullanıcının başarısız .rpgscenario.zip arşivini iste; arşivi değiştirmeden içeriğini incele.
3. manifest.json, world.json, data/characters.json ve npc_kim_minjae.goals kaydını gerçek doğrulama kurallarıyla karşılaştır.
4. Kanıtlı kök neden ve dosya bazlı planı çıkar. ZIP yoksa bu teşhis alt görevi açık kalır; üreticiyi veya loader'ı sebepsiz suçlama.

### Paket 1 — Senaryo sözleşmesi ve uzun hikâye veri hattı

1. Engine'in kabul ettiği JSON alan/türlerini tek ve sürümlenebilir sözleşmeye bağla; desteklenmeyen özellikleri varmış gibi belgeleme.
2. Validator, çalışır örnek paket ve dosya/alan bazında anlaşılır hata raporu ekle.
3. ChatGPT'nin doğrudan üretebileceği Senaryo Oluşturma Rehberi MD'sini hazırla. Kullanıcının MASTER SPEC belgesini kavramsal gereksinim olarak kullan; engine ile çelişen örnekleri körlemesine kopyalama.
4. Kaynak chapter paketlerinde sıra, aralık, işlem durumu, checkpoint ve hata bilgisi sakla.
5. Paketleri kararlı ID'lerle birleştir; mükerrer varlıkları eşleştir, çelişkileri raporla. Sonraki chapter eklenince eski kaynakları ve save dosyalarını ezme.
6. Kanon kayıtları, gerçekleşmiş oyun durumu ve gelecekte gerçekleşebilecek olayları ayır.
7. Orijinal kaynakları silme; ekstraksiyon ara sonuçlarını ve kaldığı yerden devam etmeyi test et.

### Paket 2 — Oyun AI'sının çalışma sözleşmesi

1. Ayrı Oyun AI Davranış Rehberi/prompt şablonunu oluştur.
2. AI'nın anlatıcı ve NPC rolleri, bilgi sınırları, gizli/gelecek bilgi, olay/ilişki/konum güncelleme önerileri ve belirsizlik davranışını tanımla.
3. Rehberi gerçekten desteklenen backend'lere giden prompt/context oluşturma yoluna bağla. Dosyanın repoda durmasını “AI öğrendi” diye sunma.
4. Motorun son söz sahibi olmasını koru; AI doğrulamadan geçmeden GameState, canon veya save değiştiremesin.
5. Bilgi sızıntısı, geçersiz efekt, karakter tekrarları ve alternatif zaman çizgisi için test ekle.

### Paket 3 — Kullanıcı arayüzlerini tek geçişte düzenle

1. Profesyonel Senaryo Oluştur ekranı: isim, açıklama, tür, başlangıç rolü ve gerekli dünya kişiselleştirme seçenekleri.
2. Kaynak alanı: desteklenen chapter/dosya paketlerini yükleme; sıralama ve oklarla “önce bunu, sonra bunu” zinciri; sıralamayı değiştirme; kaldırma; işleniyor/tamamlandı/hata/tekrar dene durumları.
3. Kaynakları sırayla işleme, her adımda checkpoint, yeniden açılınca devam etme ve sonradan yeni kaynak ekleme.
4. Oyun/Senaryolar listesi ve demo: demo zorunlu/pinned olmasın; senaryo başlatma ve kaldırma tutarlı olsun. Save slotlarını varsayılan olarak otomatik silme; yıkıcı işlemde açık onay göster.
5. Composer: yuvarlak yazı alanı, metin/imleç hizası, uzun metin ve Android klavye/küçük ekran davranışı.
6. AI ayarları: basit görünümde sağlayıcı seçimi ve API anahtarı. Standart sağlayıcılarda gereksiz endpoint alanı gösterilmesin; özel OpenAI-compatible server için zorunlu alanlar koşullu/gelişmiş görünümde kalsın.
7. API key alanını yuvarlak tasarıma uydur; anahtarı loglara veya status ekranlarına yazma.
8. İkon/font sembollerini gerçek cihaz render'ında doğrula.

### Paket 4 — Motor ve araç kalitesi

1. Reddedilmiş event önerisine bağlı “gerçekleşti” memory claim'i kaydedilmesin.
2. Dedup sonrası metadata değişince eski ikincil indeks girdileri kaldırılsın, yenileri eklensin.
3. Resource alanlarında bool değeri integer olarak kabul edilmesin.
4. Model indirme partial dosyası ve HTTP Range yolunu uygulama kapanması/yeniden açılmasıyla doğrula; gerekiyorsa görünür “devam et/tekrar dene” kontrolü ekle.
5. tools/run_tests.py için fixture uyumluluğu sağla veya resmi komut ile yardımcı betik arasındaki farkı belgele.

### Paket 5 — Tam doğrulama ve teslim

1. Hedefli regresyonlar; ardından python -m pytest -q tests, compileall, Android readiness, mutation smoke ve senaryo validator'ını çalıştır.
2. CI çalıştır; başarısız olursa ilk başarısız adımın logunu inceleyip kök nedeni düzelt.
3. Güncel HEAD için Android APK build yap; artifact, SHA-256 ve provenance doğrula. Eski APK'yı yeni çözüm gibi sunma.
4. Gerçek cihazda açılış, oyun, senaryo/kaynak içe aktarma, devam etme, composer, provider/API generation ve save/load testleri yap. Cihaz testi mümkün değilse o kriterleri açık bırak.
5. Her tamamlanan alt işten sonra planı, handoff belgelerini ve checkbox durumlarını güncelle.

### Geri alma / koruma

- Küçük atomik commit'ler yap; büyük yeniden yazım yapma.
- Import doğrulamasını hatayı susturmak için gevşetme.
- Kullanıcı kaynaklarını, save dosyalarını, API anahtarlarını veya indirilen modelleri silme.
- Şema değişirse sürüm/uyumluluk kuralı ve eski paket için test ekle.
- Bir paketin kabul testleri başarısızsa bağımlı işlere tamamlandı işareti koyma.

## 10. İnceleme sırasında elde edilen doğrulama kaydı

İncelenen commit: `59e30799162f94fa59201f75b0b9972577718032`.

| Kontrol | Sonuç | Açıklama |
|---|---|---|
| Git tree | 220 yol, `truncated=false` | Tüm ağaç envanterlendi. |
| Python kaynak derlemesi | PASS | `compileall` başarılı. |
| Pytest | 549 passed | Bu commit'in test paketi geçti. |
| Android readiness | PASS | v1.1.4, target API 36, SAF kontrolü geçti. |
| Mutation smoke | 3/3 | Üç mutation da tespit edildi. |
| Demo scenario validation | PASS | `demo-bootstrap` geçerli. |
| `tools/run_tests.py` | FAIL | 31 passed, 5 failed; `pytest` import/`monkeypatch` fixture uyumsuzluğu. |
| Güncel kaynak CI | PASS | [GitHub Actions run 38517225272](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38517225272). |
| Son başarılı APK build | Eski commit | [Run 38455404595](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38455404595), commit `ad611254d90578e375b53f7445d1e7f1d4d243ae`; mevcut commit için APK kanıtı değildir. |
| Fiziksel cihaz kabul testi | Doğrulanmadı | APK'nın gerçek cihazda açıldığı, UI'nin doğru çizildiği veya yerel AI inference çalıştığı bu incelemede doğrulanmadı. |

## 11. İlk uygulama adımından önce gereken kullanıcı girdisi

Önce Aşama A için hata veren senaryo `.zip`/`.rpgscenario.zip` dosyasını paylaş. Dosya gelince ilk iş, kod değiştirmeden paketi ve ilgili `characters.json`/`goals` verisini inceleyip kök neden raporu ve dosya bazlı düzeltme planı sunmak olacak. Bu rapor onaylanmadan senaryo loader'ı değiştirilmeyecek.

İkinci gerekli karar, demo silme davranışıdır: demo paketini mi kaldırmalı, yalnızca listeden mi çıkarmalı, yoksa ilişkili save slotları da kullanıcı açıkça seçerse mi silinmeli? Güvenli varsayılan, save slotlarını kendiliğinden silmemektir.


## 12. Yeni onay kapsamındaki ürün gereksinimleri

### 12.1 Uzun chapter serileri ve kaynak sırası

- 4.000 bölümlük bir eser tek dosya veya tek model bağlamına sığdırılacak varsayımıyla tasarlanmayacak.
- Kaynaklar sırayla işlenecek; arayüzde oklar sıralamayı gösterecek ve kullanıcı sıralamayı değiştirebilecek.
- Her kaynak tamamlandığında aynı dünyadaki varlıklar kararlı ID üzerinden birleştirilecek. Sonraki chapter paketi aynı karakteri yeniden yaratmayacak.
- Orijinal kaynaklar, çıkarılmış data ve checkpoint'ler ayrı tutulacak; kaynaklar korunacak ve sonradan yeni chapter eklenebilecek.
- Kaynak kanonu oyuncunun alternatif zaman çizgisiyle karıştırılmayacak. Gelecek olaylar koşullar sağlanmadan kesinleşmiş sonuç gibi uygulanmayacak.

### 12.2 Senaryo Oluştur çalışma alanı

- Yeni çalışma alanı mevcut paket içe aktarma desteğini kaybettirmeyecek.
- Kullanıcı senaryo bilgilerini kişiselleştirebilecek; kaynaklarını ekleyip sıralayabilecek; işleme ilerlemesini ve hataları anlayabilecek.
- Tasarım karanlık tema ve tutarlı yuvarlak kontroller kullanabilir. AI Dungeon etkileşim referansıdır, birebir kopya değildir.
- Yalnızca gerçekten parser desteği bulunan dosya uzantıları sunulacak.

### 12.3 İki ayrı AI kılavuzu

- Senaryo Oluşturma Rehberi: ChatGPT'nin motorla uyumlu JSON ve .rpgscenario paketi üretmesi için.
- Oyun AI Davranış Rehberi: uygulama içindeki modelin anlatım, NPC, bilgi görünürlüğü, olay tepkisi ve efekt önerilerini nasıl ele alacağı için.
- Rehberin dosyada bulunması runtime'a otomatik yüklendiği anlamına gelmez. Prompt/context entegrasyonu ve bunun testleri gereklidir.

### 12.4 Görev takip kuralı

- Her planlanan görev kalıcı bir checkbox ile izlenecek.
- Görev ancak kabul kriterleri ve gerekli test/kanıtlar geçince [x] yapılacak. Başlamadıysa veya kısmen yapıldıysa [ ] kalacak.
- Tamamlanan iş varsayılan olarak silinmek yerine [x] ve kanıtla korunacak; geçmiş görünür kalacak.
- Her görev sonrasında bu plan, ilgili teknik belgeler, AI_START_HERE.md, HANDOFF.md ve MEMORY.md güncellenecek. Eski işler yalnızca görünümü temizlemek için tamamlandı işaretlenmeyecek.

## 12.5. Bu planlama görevinin durumu

- [x] Yeni gereksinimler önceki teknik görevlerle birleştirildi.
- [x] Görevler ağırlıklı puanlama yöntemiyle yeniden sıralandı; uygulama sırası ve puan sırası ayrı gösterildi.
- [x] Tek onayla ilerleyecek kampanya, bağımlılıkları ve kabul kapıları yazıldı.
- [x] AI_START_HERE.md, HANDOFF.md, MEMORY.md ve APP_READINESS_CHECKLIST.md plana göre güncellendi.
- [x] Kullanıcı kampanya onayı verdi; gerçek senaryo arşivi incelendi ve kod geliştirmesi başladı.
- [x] Kullanıcının son talebi doğrultusunda açık geliştirmeler tek bir bütünleşik uygulama paketi olarak sıralandı; resmî senaryo doğrulama, gerçek import, son tam regresyon, APK ve cihaz kabulü en son aşamaya bırakıldı.

## 12.6. İlk senaryo arşivi incelemesi — 2026-10-14

- [x] Kullanıcının `Return_Survival_Kirilma_Noktasi.rpgscenario.zip` arşivi açılmadan değiştirilmeden incelendi; içindeki 17 dosya ve 14 JSON dosyası listelendi.
- [x] JSON dosyaları parse edildi; kanonik kayıt ID'leri, `references` hedefleri ve chapter manifest sayıları temel kontrollerden geçirildi.
- [x] Birinci hata doğrulandı: `data/characters.json:npc_kim_minjae.goals[0]` düz metin; registry her hedefin `id`, `description`, `priority` alanlı bir nesne olmasını bekliyor.
- [x] İkinci uyumsuzluk doğrulandı: `world.json.relationships` anahtarları açıklayıcı ID olarak verilmiş; runtime invariant `party_a`/ `party_b` değerlerinin sıralanıp `|` ile birleştirildiği canonical key'i bekliyor.
- [x] Rehbere goal nesnesi ve runtime relationship key kuralları eklendi. Registry'nin goal hata mesajı dosya, kayıt, indeks ve beklenen alanları gösterecek şekilde iyileştirildi; regresyon testi eklendi.
- [ ] Düzeltilmiş arşiv gerçek `tools/validate_scenario.py` ile çalıştırılmalı ve uygulamanın gerçek import yolunda test edilmeli. Yerel manuel kontroller tek başına engine doğrulaması sayılmaz.
- [ ] İlk görev ancak bu doğrulamalar geçince tamamlanacak.

## 13. Şu anki blokaj ve onay kapısı

- Gerçek `.rpgscenario.zip` arşivi bulundu ve incelendi; `goals` girişi, runtime ilişki anahtarları ve `interact` görev hedefi şeması ayrı ayrı ele alınıyor.
- Uygulama kodu ve dokümantasyon değişiklikleri başladı. CI ve kabul testleri geçmeden import görevi tamamlanmış sayılmayacak.
- Düzeltilmiş arşivin yalnızca manuel yapısal kontrolü yapılmıştır; resmi validator ve Android import sonucu hâlâ bekleniyor.
- Demo silme için güvenli varsayılan: senaryo listesi/paketi ile save slotları ayrı tutulur; save slotları sessizce silinmez.
- Plan dışı yıkıcı migration, Android foreground service veya yeni dosya parser'ı gerekirse durup yeniden onay alınır.


## 12.7. Implementation progress log — 2026-10-14

**Campaign state:** started under the user's approval. No implementation task is marked complete until its tests and acceptance evidence pass.

- [x] Actual scenario ZIP inspected and two schema/runtime mismatches identified.
- [ ] Scenario import fix accepted by the real engine validator and app import path. A corrected local ZIP exists, but only manual structural checks have passed; `interact` code tests now pass in CI.
- [ ] Actionable goal validation message and regression test pass CI.
- [ ] ChatGPT scenario creation guide is committed at `docs/SCENARIO_CREATION_GUIDE.md`; the corrected pack still needs actual engine validation before the guide/schema task can be marked complete.
- [x] In-game AI behaviour guide is committed at `docs/IN_GAME_AI_BEHAVIOR_GUIDE.md`; core rules and linked entity retrieval are in `engine/ai/context.py`. Runtime-context tests passed in CI run `38624639579`.
- [ ] Composer and provider/API settings UI changes were committed in `rpg_android_app.py`; static/CI checks and real Android device acceptance are pending.
- [ ] Memory event-rejection, secondary-index, and boolean-resource fixes plus regression tests were committed; CI is pending.
- [ ] Full scenario-builder/source-queue workflow, chapter processing checkpoints, save-safe scenario management, download lifecycle and release build remain unimplemented.

Earlier verification had regressions, all then identified from logs. Fresh CI run `38624639579` on commit `1445c55297ab73ab98d5845d0daf34f01de2f93f` passed 560 tests, Python compileall, Android readiness and mutation smoke 3/3. Scenario validator/import on the corrected ZIP and APK/device acceptance remain open.

## 12.8 Knowledge graph and interaction objective checkpoint — 2026-10-14

- The actual imported quest `quest_confirm_date` contains `obj_check_phone` with `type: interact` and `target_id: item_phone`. This is a schema/runtime mismatch, not malformed story prose: the engine previously allowed only `collect`, `reach`, `defeat`, and `talk`.
- Added a deterministic engine-side `interact` command for explicitly inspecting an accessible item, NPC, or current location. The rule emits an explicit interaction signal; quest progression consumes that signal instead of trusting AI narration.
- Added Turkish/English inspection command aliases, objective reference validation, and a regression test. This addresses code-level behavior only; CI and real archive import remain the acceptance gate.
- Added `engine/scenario/knowledge_graph.py`: deterministic nodes for canonical records, name/alias resolution, and links created only from explicit structured IDs/references. `ScenarioRetriever` exposes entity resolution and visibility/chapter-filtered neighboring records; runtime context can include a small, bounded set of linked records.
- This first graph phase does **not** claim automatic extraction of new entities/facts from free chapter prose. A later, resumable source-ingestion phase must extract candidate records with provenance, reconcile stable IDs, validate output, and preserve original source files.
- Updated `docs/SCENARIO_CREATION_GUIDE.md` with `interact` semantics and structured entity links; updated `docs/IN_GAME_AI_BEHAVIOR_GUIDE.md` with graph and source-grounding limits.
- Added deterministic knowledge-graph tests and fixed the stale panel assertion, small-context budgeting, and ordinary `inspect` commands being intercepted from the AI memory path. Fresh CI run `38624639579` passed 560 tests, `compileall`, Android readiness and mutation smoke 3/3.
- Keep implementation tasks unchecked until a fresh CI result, actual official archive validation, and the relevant app/device acceptance gate are recorded.

## 14. Tek seferde uygulanacak geliştirme paketi — doğrulama en son

**Kullanıcının güncel talimatı:** Açık kalan ürün/kod değişikliklerini tek bir bütünleşik kampanya halinde tamamla; düzeltilmiş senaryonun resmî doğrulaması, gerçek uygulama import'u, son tam doğrulama, APK ve cihaz kabulünü geliştirmelerin en son kapısına bırak. Bu, ara adımlarda tekrar tekrar onay beklemek veya bütün değişiklikleri tek dev commit'e sıkıştırmak anlamına gelmez. İlişkili işler mantıksal gruplara ayrılarak bir kampanyada yürütülür; yeni ve kapsam dışı yıkıcı karar gerekmedikçe mevcut onay geçerlidir.

### A. Başlangıç referansı ve korunacak mevcut işler

- [x] İlk bilgi grafiği, açık ID/alias çözümü, ilişkili kayıt retrieval'ı, `interact` quest sinyali ve oyun AI davranış sözleşmesi repoda bulunuyor.
- [x] Reddedilmiş event ile memory arasındaki bağ, dedup sonrası ikincil indeksler ve bool-resource doğrulaması için değişiklikler/regresyonlar eklendi.
- [x] Başlangıç CI kanıtı: [run 38625436847](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38625436847), 560 test geçti; compileall, Android readiness ve mutation smoke 3/3 başarılı.
- [ ] Uygulamaya geçmeden önce güncel `main` HEAD, son diff ve mevcut ekran/manager/model-indirme akışları yeniden okunacak. Önceden uygulanmış özellikler yeniden yazılmayacak; eksikleri tamamlanacak.

### B. Senaryo verisi ve kaynak işleme hattı

1. Engine'in gerçek kanonik JSON şemasını tek sözleşmede topla: kayıt kategorileri, zorunlu alanlar, ID biçimi, `references`, NPC goals, ilişkiler ve görev hedefleri. `interact` dahil desteklenen türler loader, registry, runtime invariant ve Markdown rehberinde aynı anlama gelmeli.
2. Kaynak işleme için kanonik `data/*.json` ile karıştırılmayan bir ara veri modeli tanımla. Her kaynak batch'i sıra, dosya adı, içerik hash'i, bölüm aralığı, işlem durumu, checkpoint ve hata/yeniden deneme bilgisiyle saklanmalı.
3. İlk sürüm yalnızca gerçek parser yolu bulunan `.txt`, `.md` ve bunları içeren açıkça tanımlanmış arşiv/ara-format girdilerini sunmalı. Desteklenmeyen dosya türü sessizce kabul edilmemeli; PDF/OCR gibi yeni parser kapsam dışında kalmalı.
4. Metni tek büyük isteme sığdırmaya çalışma. Kaynakları bölüm/alt parça halinde sırayla işle; her sonuç için aday karakter, mekân, nesne, grup, olay, ilişki, bilgi/sır ve zaman çizelgesi kayıtları üret.
5. Her bilgiyle kaynak dosyası/bölümüne dayanan provenance sakla. `explicit`, `inference`, `rumor`, `disputed` gibi kanıt durumları ayrılmalı; söylenti veya karakter inancı evrenin kesin gerçeğine çevrilmemeli.
6. Yeni aday kayıtları mevcut bilgi grafiğiyle ID, isim ve alias üzerinden eşleştir. Doğrulanmış aynı varlık mevcut ID'yi kullanmalı; belirsiz eşleşme birleştirilmemeli ve `unresolved` olarak işaretlenmeli.
7. İlişkileri yalnızca açık referanslarla veya kaynakta dayanak gösterilen, doğrulamadan geçmiş çıkarımlarla kur. AI çıktısı doğrudan GameState'i, mevcut kurulu senaryoyu ya da save dosyalarını değiştirememeli.
8. Her bölüm/batch sonrasında onaylı checkpoint ve ara çıktı yaz; uygulama kapanıp açıldığında biten parçalar tekrarlanmadan devam edebilmeli. Orijinal kaynaklar salt okunur korunmalı ve sonradan yeni bölüm paketleri eklenebilmeli.
9. ChatGPT'ye verilecek `SCENARIO_CREATION_GUIDE.md` dosyasını bu ara format, kategori/ilişki sözleşmesi, devam etme ve hatalı/eksik bilgi davranışına göre güncelle. Ara format ile doğrudan import edilebilen `.rpgscenario` formatı açıkça ayrılmalı.

### C. Senaryo oluşturma ve senaryo kütüphanesi arayüzü

1. Mevcut `ScenariosScreen` yalnızca içe aktarma ve başlatma sunuyor. Senaryo çalışma alanı ekle: ad/açıklama ve başlangıç ayarları, kaynak dosyalarını ekleme/kaldırma, sıra oklarıyla yukarı/aşağı taşıma ve kaynak zincirini görünür kılma.
2. Kaynak başına `Bekliyor / İşleniyor / Tamamlandı / Hata / Devam ettir` durumları, genel ilerleme, hata açıklaması ve güvenli tekrar deneme sağla. Durum/checkpoint uygulama yeniden açılınca korunmalı.
3. Daha sonra eklenen bölüm paketleri önceki kanonik kayıtları ve kaynakları kaybetmeden aynı senaryoya eklenmeli; paket kimliği ve sıra/bölüm aralığı çatışmaları kullanıcıya açıkça bildirilmeli.
4. Demo dünyasını ana/aktif oyun alanında zorunlu sabit kart olmaktan çıkarıp normal senaryo kütüphanesi davranışına taşı. Kurulu senaryolar ile son oynanan kayıtları birbirine karıştırma.
5. Senaryo kaldırma için senaryo adının yer aldığı açık onay kullan. Senaryo paketini kaldırmak save slotlarını sessizce silmemeli; aktif oyun/kayıt ilişkileri korunmalı ve dosya temizliği başarısız olursa indeks tutarlı kalmalı.

### D. Oyun ekranı ve AI/API ayarları

1. Mevcut yuvarlak/multiline composer değişikliklerini tamamla: metin, hint, imleç ve panel hizası; dört satıra kadar büyüme; çok uzun metin; Android klavyesi açıldığında input/gönder düğmesinin görünür kalması ve kaydırma davranışı.
2. API ayarlarını sağlayıcıya göre sade tut. Normal sağlayıcılarda yalnızca gereken alanlar; OpenAI-compatible için endpoint/model alanlarını koşullu göster. API anahtarı girişini tasarıma uydur, sırları log/status metinlerine yazma.
3. Bağlantı testi ile gerçek generation testini ayır; model listesi almak başarılı diye sohbet üretimi doğrulanmış sayılmamalı.
4. Demo/senaryo ekranları, ayarlar ve ikon/font glyph'leri için ekran kaynak kodu testlerini genişlet; cihazda görsel başarı ancak final cihaz kabulinde bildirilebilir.

### E. Model indirme ve geliştirici araçları

1. Mevcut `engine/ai/model_manager.py` içindeki partial dosya ve Range davranışını yeniden yazmadan önce incele. Repository/file/revision ve doğrulanan boyut/hash bilgileri kalıcı metadata'da tutulmalı.
2. Bağlantı kesilmesi veya uygulama kapanması `.part` dosyasını korumalı; yeniden açılınca doğru dosya sürümü için devam etmeyi/yeniden başlatmayı seçmeli. HTTP 206 devamı, HTTP 200 baştan indirme fallback'i, yanlış boyut/hash, çift indirme ve bozuk GGUF test edilmeli.
3. Son `.gguf` ismi yalnızca tamamlanmış dosya doğrulamadan geçince kullanılmalı; kısmi dosya kurulu model listesinde geçerli model gibi görünmemeli. Android OS sonlandırmasına karşı garanti verilmeyen durumda devam etme davranışını doğru adlandır; foreground service ayrıca izin/onay gerektirir.
4. `tools/run_tests.py` için pytest fixture/monkeypatch uyumsuzluğunu çöz veya tek desteklenen test komutuna açık, fail-fast yönlendirme yap. Başarısız testleri atlamak veya assertion kaldırmak çözüm sayılmaz.

### F. Geliştirme sırasındaki kontrol disiplini

- Her alt alanda hedefli testler ve küçük statik kontroller çalıştır; bunlar final kabul kapısının yerine geçmez.
- Kategoriler/ID/ilişki sözleşmesi, kaynak kuyruğu, UI, indirme ve test runner işi bitmeden final kabul kapısına geçme.
- İşlerin tamamlandığına ilişkin belgeleri ve checklist'i güncelle, ancak final validator/import/cihaz kriterlerini henüz `[x]` yapma.
- Mevcut güvenlik, save/source koruması ve engine-authoritative durum yönetimini koru; yeni büyük bağımlılık, veri kaybı riski veya yıkıcı migration gerekirse dur ve yeniden onay al.

### G. En son yapılacak kabul ve teslim kapısı

Bu kapı, B–F kapsamındaki kod ve dokümantasyon değişiklikleri tamamlandıktan sonra çalıştırılacak:

1. Tam `python -m pytest -q tests`, `python -m compileall -q .`, Android readiness, mutation smoke ve tüm GitHub Actions job'ları.
2. Düzeltilmiş `Return_Survival_Kirilma_Noktasi.rpgscenario.zip` üzerinde gerçek `python tools/validate_scenario.py` ve `load_scenario()` doğrulaması; manuel JSON kontrolü yerine geçmez.
3. Güncel uygulama import yolundan (Android SAF gerçek yolunu da kapsayacak biçimde) senaryoyu içe aktar, başlat, `quest_confirm_date` görevini etkinleştir, `item_phone` hedefini açıkça incele, görev ilerlemesini ve save/load turunu doğrula.
4. Son kod HEAD'i için Android APK oluştur; workflow, commit SHA, artifact adı/ID ve SHA-256/provenance kaydını doğrula. Eski APK'yı yeni kodun kanıtı olarak kullanma.
5. Gerçek cihazda açılış, senaryo kütüphanesi/oluşturma kuyruğu, yeniden açılıp devam etme, composer/klavye, sağlayıcı üzerinden generation, model indirme devamı ve save/load denemelerini yap. Fiziksel cihaz testi yapılamazsa ilgili kriterleri açık bırak; tahminle tamamlandı deme.
6. Kabul sonucu ve açık kalanlar `docs/DEVELOPMENT_PLAN.md`, `HANDOFF.md`, `MEMORY.md` ve `AI_START_HERE.md` içine commit SHA ve run/artifact bağlantılarıyla kaydedilsin.

**Kapsam dışında:** Bu plan sırasında kaynak metnin üzerinde otomatik yıkıcı değişiklik, save slotlarını otomatik silme, OCR/PDF desteği ya da Android foreground service eklenmeyecek. Bunlar gerekirse ayrı tasarlanıp onaylanmalı.


## 2026-10-15 — Authoritative audit note (replaces stale live-status claims; preserves history)

- Review baseline: pre-audit `main` HEAD `5e4ae4668f310f425fbb398d2f180cbe801ad3a8`; latest audited implementation commit is `51f44c7f9cf2fa1aa0a16fdecb50c89123bf112d` on `review/comprehensive-code-audit-2026-10-15` (PR #2).
- The last known Test Suite run for that baseline failed: run [38632774268](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38632774268). The failure is a stale source-level UI assertion in `tests/test_android_app_readiness.py`: it expected the removed `◇` prefix while `rpg_android_app.py` now uses `text="Yerel modeller · Local GGUF"`. Source shows 598 other tests passed in that run; this is not a current green CI result.
- The source-workspace queue/checkpoint/candidate-index/export implementation already exists in `engine/scenario/source_workspace.py`, is wired through `engine/app/controller.py`, is exposed by `SourceWorkspaceScreen`, and has targeted tests. Older checklist entries saying this feature is wholly unimplemented are stale; end-to-end acceptance and device behavior remain separate gates.
- Model download partial metadata, Range/If-Range resume and model-integrity checks exist in `engine/ai/model_manager.py` and have focused unit tests. App/process lifecycle and physical Android acceptance remain unproven.
- Audit fixes include checkpoint verification against the saved source chunk, best-effort progress callbacks, current UI assertion, PR CI trigger, and safe bounded release ZIP extraction. Commit `51f44c7f9cf2fa1aa0a16fdecb50c89123bf112d` passed [GitHub Actions run 38690247384](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38690247384): 610 tests passed, `compileall` passed, Android readiness passed, and mutation smoke detected 3/3 mutations. This verifies source/CI gates only; no fresh APK or physical-device acceptance was performed.
- Still open: validate the actual user-provided scenario archive through the real engine validator/import path, confirm scenario quest authoring/export coverage, perform full pytest/compile/readiness/mutation gates, produce a fresh APK with provenance, and run real-device acceptance. Do not infer completion from source presence alone.
- Do not rewrite historical notes below as if they were current evidence. Use this dated audit and later dated evidence sections for current status.

## Zorunlu çalışma sonu kuralı — her oturumda uygulanır

- Her kod veya davranış değişikliği tamamlandığında bu dosyayı, `AI_START_HERE.md`, `HANDOFF.md`, `MEMORY.md`, `docs/DEVELOPMENT_PLAN.md`, ilgili checklist'i ve değişiklikten etkilenen **bütün bilgi içeren `.md` dosyalarını** güncelle.
- Her raporda kaynak branch/HEAD SHA'sını, değişen dosyaları, gerçek test komutlarını ve sonuçlarını, CI run bağlantısını, APK/artifact doğrulamasını ve fiziksel cihaz durumunu ayrı ayrı yaz.
- “Kaynakta mevcut”, “yerel test geçti”, “GitHub CI geçti”, “APK üretildi/metadata doğrulandı” ve “gerçek Android cihazında doğrulandı” farklı kanıt seviyeleridir. Birbirinin yerine kullanma.
- Eski tarihli kayıtları silme veya güncel gerçek gibi sunma; tarihî bağlamı koru ve yeni, yetkili durum bölümünü ekle.
- Önceki oturum kesilmişse veya dosyaların güncelliği belirsizse önce ilgili kodu, testleri, mevcut HEAD'i ve son CI kayıtlarını kontrol et. Eski Markdown durumunu kanıt kabul etme.
- Son kontrolde hiçbir bilgi belgesi eski veya çelişkili kalmamalı; kanıtı olmayan kabul kriterleri açık kalmalı.

## 2026-10-15 — Current implementation and acceptance status

- Latest audited code commit: `51f44c7f9cf2fa1aa0a16fdecb50c89123bf112d`. CI: [run 38690247384](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38690247384) — 610 tests passed; Python compileall, Android readiness (version 1.1.4, target API 36, SAF enabled) and mutation smoke (3/3) passed.
- Source workspace, ordered queue, durable checkpoints, candidate identity resolution and scenario ZIP export exist in code and have unit/integration tests. Checkpoints now validate the current source metadata and re-derived source chunk; progress callbacks cannot mark an already completed chunk failed.
- Release verification ZIP extraction is hardened against POSIX/Windows path traversal, symlinks, duplicate/case-colliding paths, and excessive entry/expanded sizes. `tests/test_release_verify.py` covers these cases.
- Provider-conditional API fields and separate connection/generation tests exist in source. Composer and keyboard behavior still need physical Android acceptance.
- Hugging Face range/resume/hash checks and tests exist; app/process lifecycle behavior still needs device acceptance.
- Still open: validate the actual user-provided scenario archive using the real validator/import/play/save/load flow; fresh APK build plus SHA/provenance; physical-device workflow. Do not mark those items complete based on source tests.
- The 2026-10-14 “not yet implemented” backlog is historical context. Source presence must be checked before repeating those claims; device/release gates remain open until evidence is recorded.

## 2026-10-15 — Release-verifier security finding

- `tools/release_verify.py` now uses bounded, platform-independent ZIP extraction instead of `extractall` after a POSIX-only check. Regression tests cover path traversal, symlinks, duplicate paths and expanded-size limits.
- Source/CI evidence: commit `51f44c7f9cf2fa1aa0a16fdecb50c89123bf112d`, run [38690247384](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38690247384), 610 tests passed and all configured source gates passed.


## 2026-10-15 — User-tested Android AI/runtime blocker subplan

The user installed the latest Android debug APK and tested it on-device. A new focused, **not-yet-implemented** subplan has priority before resuming the pre-existing campaign: [`docs/ANDROID_AI_RUNTIME_AND_INPUT_PLAN.md`](ANDROID_AI_RUNTIME_AND_INPUT_PLAN.md).

Current observed acceptance blockers:

- [ ] Local GGUF activation fails while launching `llama-server` with Android `[Errno 13] Permission denied` under `/data/data/org.rpgengine/files/native_runtime/…`.
- [ ] Gameplay reports `(no AI adapter configured)` after that failed activation.
- [ ] Choosing a GGUF through import leaves the UI black/stuck; cause still unconfirmed.
- [ ] Chat composer, API text fields and advanced settings have invisible/occluded text and touch/focus overlap; touching a button can unexpectedly open the keyboard.
- [ ] Fixing local runtime must include actual model generation on an ARM64 Android device, not only source tests or successful APK packaging.

The runtime source already copies the packaged binary and calls `chmod(0o700)`. Therefore do not treat another chmod call as a proven fix. Diagnose the real Android `EACCES` cause first. Work in this order: P0 native runtime + real inference; P1 GGUF import/model activation UX; P2 composer/API/advanced-field rendering, touch regions and keyboard behavior; P3 full tests, fresh APK/provenance and device acceptance.

This subplan is an ordered detour for the currently blocking, user-verified Android issues. Once its acceptance criteria pass, return here and continue previously open master-campaign tasks without deleting or reopening historical completed tasks. No application code or runtime behavior is changed by this planning update.
