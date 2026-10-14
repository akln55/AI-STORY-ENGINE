# AI-STORY-ENGINE — Geliştirme Planı ve Çalışma Kuralları

**Durum:** Plan hazır; uygulama değişiklikleri kullanıcı onayı bekliyor  
**Plan tarihi:** 2026-10-14  
**Repository:** `akln55/AI-STORY-ENGINE`  
**Planın hazırlandığı kaynak commit:** `59e30799162f94fa59201f75b0b9972577718032`  
**Ürün sürümü:** `v1.1.4`  

> Bu belge, yapılacak işleri ve kabul kriterlerini tanımlar. Bu planın yazılması, kod değişikliklerinin veya APK build'inin otomatik olarak onaylandığı anlamına gelmez. Her uygulama aşaması başlamadan önce plan kullanıcıya sunulur ve onay alınır.

## 1. Öncelik puanlama yöntemi

Puan, **bu projede işi ne kadar erken yapmamız gerektiğini** 10 üzerinden gösterir; görevin ne kadar zor olduğunu göstermez. Puanlar canlı kullanım telemetrisi değil, şu anda doğrulanabilen hata etkisi, ürün hedefini engelleme derecesi, veri/doğruluk riski ve diğer işlerin bağımlılıkları üzerinden verilmiş mühendislik öncelikleridir. Herhangi bir puan test sonucu veya ölçülmüş kullanıcı sayısı gibi sunulmamalıdır.

- **P0 — Sürüm/temel kullanım engeli:** çözülmeden senaryo yükleme veya güvenilir oyun döngüsü kabul edilemez.
- **P1 — Yüksek:** veri doğruluğu, kullanıcı akışı veya önemli kalite sorunu.
- **P2 — Orta:** bakım kolaylığı, kullanılabilirlik ve güvence işleri.
- **P3 — Sonraki iyileştirme:** daha kapsamlı test, performans veya kalite çalışmaları.

İş sırası öncelik puanına göre yapılır; aynı işi zorlaştıran bilinmeyen bir girdi varsa kod yazmak yerine önce girdi istenir.

## 2. Önceliklendirilmiş yapılacaklar listesi

| Sıra | İş | Öncelik / 10 | Durum | Neden |
|---:|---|---:|---|---|
| 1 | Senaryo paketinin neden yüklenemediğini gerçek dosyayla teşhis et ve şemayı uzlaştır | **10.0** | Açık; arşiv gerekli | Kullanıcının ana hedefi olan kendi senaryo verisini uygulamaya yükleyip oynatmasını doğrudan engelliyor. |
| 2 | ChatGPT tarafından üretilebilen, doğrulanabilir senaryo paketi standardı oluştur | **9.8** | Planlandı | Dosya yalnızca okunabilir bir hikâye değil; uygulamanın doğrulayabildiği makine-okunur data paketi olmalı. |
| 3 | Oyun ekranında “Senaryolar” alanı ve senaryo yönetimi; kalıcı demo kısayolunu kaldır | **9.5** | Açık | Demo ana menüde/oyun listesinde kalıcı bir öğe gibi davranıyor; kullanıcı senaryo ve demoyu silmek/yönetmek istiyor. |
| 4 | Reddedilen AI olay önerisinin kalıcı hafızaya gerçekmiş gibi yazılmasını engelle | **9.4** | Kod incelemesinde yeniden üretildi | `GameSession._ingest_memory_updates()` olay önerilerini normal reddedilmiş durum değişiklikleriyle aynı şekilde korumuyor. |
| 5 | Yinelenen bellek kaydı güncellenince tüm ikincil arama indekslerini tutarlı güncelle | **9.2** | Kod incelemesinde yeniden üretildi | Yeni etiket/konum/varlık/olay verisi kayıtta bulunmasına rağmen indeksli arama 0 sonuç verebiliyor. |
| 6 | Hugging Face indirmesinde uygulama kapanması sonrası devam ettirme akışını görünür ve güvenilir yap | **8.9** | Kısmi altyapı var; uçtan uca doğrulama gerekli | Backend `.part` dosyası ve HTTP Range ile devam ettirmeyi destekliyor; Android süreç/ekran yaşam döngüsü ve kullanıcıya devam ettirme deneyimi doğrulanmalı. |
| 7 | Android sohbet giriş alanı, klavye, metin/imleç hizası ve gönder düğmesini gerçek cihazda düzelt | **8.7** | Açık | Kaynakta `PillInput` ve sohbet composer var; bu varlık görsel ve cihaz davranışının doğru olduğu anlamına gelmiyor. |
| 8 | API ayarlarını sağlayıcıya göre sadeleştir; gereksiz alanları gizle, ikon/font ve ayar ekranını düzelt | **8.5** | Açık | Gemini gibi sağlayıcılarda gereksiz endpoint alanı hâlâ görsel olarak yer alabiliyor; gerçek ekran doğrulaması eksik. |
| 9 | Tam sayı bekleyen efekt değerlerinde `bool` değerini reddet | **8.3** | Kod incelemesinde yeniden üretildi | JSON `true`, Python'da `int` alt sınıfı olduğundan kaynak değeri olarak kabul edilip HP'yi değiştirebildi. |
| 10 | Uçtan uca senaryo testleri: import → başlat → AI context/retrieval → kayıt/yükleme | **8.3** | Planlandı | Tekil testler, ChatGPT üretimli gerçek paketle tüm ürün yolunu kanıtlamaz. |
| 11 | `tools/run_tests.py` uyumluluğunu düzelt veya desteklenen kullanımını netleştir | **7.8** | Doğrulandı, yardımcı betik başarısız | Elle çalıştırıldığında 5 hata veriyor; güncel CI ise doğrudan pytest kullandığından yeşil kalabiliyor. |
| 12 | Onaylanan kod değişiklikleri sonrasında güncel kaynak için APK üret, artifact'ı doğrula ve cihaz kabul testlerini yap | **8.6** | Sonraki kapı | Önceki başarılı APK, mevcut commit'i veya açık sorunların çözüldüğünü kanıtlamıyor. |
| 13 | Kurulum/silme/indirme/geri alma ve uzun oturum senaryolarında regresyon ve güvenlik testlerini genişlet | **7.5** | Planlandı | Güçlü test altyapısının kullanıcı akışlarını kapsaması gerekiyor. |

### Öncelik puanlarının kanıt sınırları

- 4, 5 ve 9 numaralı bulgular incelenen kaynak üzerinde küçük doğrulamalarla yeniden üretildi.
- 11 numaralı bulgu yardımcı betiğin mevcut test setiyle çalıştırılmasıyla gözlendi; CI'deki pytest çalışmasının başarısız olduğu anlamına gelmez.
- 1 numaralı senaryo hatasının tam kök nedeni henüz **kesinleştirilmedi**. Hata metni kaydedilmiş durumda; gerçek başarısız `.zip` paketi henüz incelenmedi. Bu yüzden “loader kesin hatalı” veya “üretici kesin hatalı” denmeyecek.
- 3, 7 ve 8 numaralı UI işleri, mevcut kaynak akışı ve kullanıcı raporlarına göre planlandı; gerçek cihazda render/etkileşim testi yapılmadan “düzeldi” kabul edilemez.
- 6 numarada indirme kodu `.part` dosyasını koruyup uygun HTTP Range yanıtında devam edebiliyor. Sorun, bu özelliğin uygulama kapatıldığında/geri açıldığında kullanıcıya güvenilir biçimde sunulduğunun henüz uçtan uca kanıtlanmamasıdır. Aynı işi sıfırdan yazmak yerine önce mevcut kod doğrulanacak.

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

## 9. Aşamalı uygulama planı

1. **Aşama A — Senaryo formatı ve gerçek arşiv:** Kullanıcı başarısız arşivi sağlar; kök neden raporu ve format değişikliği planı sunulur. Onay sonrası minimal düzeltme ve regresyon testleri.
2. **Aşama B — Senaryolar ekranı/demo yaşam döngüsü:** Silme kapsamı ve aktif save davranışı kullanıcıyla netleştirilir; sonra UI/controller/ScenarioManager değişiklikleri yapılır.
3. **Aşama C — Veri doğruluğu düzeltmeleri:** Event-memory, memory index ve bool tipi için ayrı regresyon testleri ve küçük düzeltmeler.
4. **Aşama D — İndirme güvenilirliği:** Mevcut resumable download akışı test edilir; partial keşfi/devam ettirme UI'si ve yeniden açılış testleri eklenir. Foreground service ayrı karar olarak kalır.
5. **Aşama E — UI düzeltmeleri:** Composer, sağlayıcı ayarları, ikonlar ve küçük ekran davranışı; kaynak kontrolleri ile cihaz testleri ayrı yürütülür.
6. **Aşama F — Release doğrulaması:** Full testler ve readiness gates; güncel kaynak için APK, metadata/provenance, artifact ve fiziksel cihaz kabul testleri.

Her aşama için uygulama başlamadan önce kapsam/kabul kriterleri kullanıcıya gösterilecek ve onay istenecek. Aşamalar bağımsız olarak onaylanabilir.

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
