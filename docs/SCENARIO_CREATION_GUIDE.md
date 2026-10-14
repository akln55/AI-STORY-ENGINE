# AI-STORY-ENGINE — ChatGPT Senaryo Oluşturma Rehberi

**Amaç:** Bu belgeyi okuyan ChatGPT'nin uygulamaya aktarılabilir `.rpgscenario.zip` paketleri üretmesi. Bu rehber, depodaki `engine/scenario/loader.py` ve `engine/scenario/registry.py` dosyalarının mevcut davranışına göre hazırlanmıştır. Motor şeması değişirse bu belge ve örnek paket aynı görevde güncellenmelidir.

## 1. ChatGPT için bağlayıcı üretim talimatı

Bir senaryo üretirken:

1. Sonuç tek bir `.rpgscenario.zip` arşivi olmalı. JSON dosyalarını arşivin köküne koy: `manifest.json`, `world.json`, `data/`, isteğe bağlı `lore/` ve `chapters/`.
2. JSON'u yorum satırı veya Markdown kod çiti olmadan, geçerli UTF-8 JSON olarak yaz.
3. Her kanonik veri kaydı bir JSON nesnesi olmalı. Nesnenin `id` alanı, onu kapsayan nesnedeki anahtarla **harfiyen aynı** olmalı.
4. Her ID sabit, benzersiz ve ASCII harf/rakam/alt çizgi/tire kullanılarak oluşturulmalı. Bölüm paketleri eklendiğinde var olan ID'leri yeniden adlandırma.
5. `data/characters.json` içindeki NPC `goals` değerlerini asla düz metin dizeleri olarak yazma. Her hedef aşağıdaki yapıda bir nesne olmalı. Aynı kural `world.json` içindeki aktif NPC hedefleri için de geçerlidir.
6. Bir alanın şemasından emin değilsen yeni bir alan uydurma. Bilgiyi desteklenen kayıt alanlarında veya `lore/*.md` açıklama belgelerinde tut; ancak motorun çalışması için gerekli konum, başlangıç durumu, ID ve ilişki verilerini yalnızca Markdown'a saklama.
7. Paket hazır demeden önce bütün JSON dosyalarını parse et, ID ve referansları kontrol et ve mümkünse `python tools/validate_scenario.py <paket-yolu>` komutuyla doğrula. Validator çalıştırılmadıysa test edildiğini iddia etme.

## 2. Zorunlu paket yapısı

```text
MyScenario.rpgscenario.zip
├── manifest.json
├── world.json
├── data/
│   ├── characters.json
│   ├── locations.json
│   ├── factions.json
│   ├── items.json
│   ├── techniques.json
│   ├── realms.json
│   ├── creatures.json
│   ├── events.json
│   ├── relationships.json
│   ├── timeline.json
│   └── knowledge.json
├── lore/
│   └── world.md
└── chapters/
    └── scenario_0001_0100/
        ├── chapter_manifest.json
        └── overview.md
```

`manifest.json` ve `world.json` zorunludur. `data/*.json` dosyaları isteğe bağlıdır; ancak bir dosya kullanılıyorsa listelenen adlardan biri olmalıdır ve `data/` altında tam bir klasör derinliğinde bulunmalıdır. `data/custom.json`, `data/characters/custom.json` veya desteklenmeyen isimler geçerli değildir. Lore ve chapter Markdown dosyaları isteğe bağlıdır. Chapter Markdown, kendisine karşılık gelen bir `chapter_manifest.json` bulunan klasörde olmalıdır.

## 3. manifest.json

Önerilen v2 örneği:

```json
{
  "pack_format": 2,
  "scenario_id": "return-survival-alt",
  "name": "Return Survival: Kırılma Noktası",
  "version": "1.0.0",
  "engine_min_version": "1.27.0",
  "description": "Alternatif zaman çizgisinde geçen hayatta kalma senaryosu.",
  "schema": "rpg-engine-scenario-v1",
  "chapter_pack_size": 100,
  "chapter_count": 200,
  "chapter_packs": [
    "return_survival_0001_0100",
    "return_survival_0101_0200"
  ]
}
```

- `scenario_id`, `name` ve `version` boş olmayan metin olmalı.
- `pack_format` mevcut destekli değer olarak `2` olmalı; eski formatlar için açık uyumluluk gerekmedikçe yeni paket üretiminde v1 kullanma.
- `chapter_pack_size`, tek bir chapter paketindeki en yüksek bölüm sayısıdır; pozitif tam sayı olmalı.
- `chapter_count`, paket sayısı değil, manifestlerde kapsanan **toplam bölüm sayısıdır**.
- `chapter_packs`, chapter manifestlerindeki `pack_id` değerlerini sıra ile ve birebir aynı şekilde listelemeli.

## 4. Chapter paketleri ve sıra

Her paket için `chapters/<klasör>/chapter_manifest.json` ekle:

```json
{
  "pack_id": "return_survival_0001_0100",
  "chapter_start": 1,
  "chapter_end": 100,
  "sequence": 1
}
```

Kurallar:

- `pack_id` benzersiz ve boş olmayan metin olmalı.
- `chapter_start` ve `chapter_end` 1'den başlayan geçerli bölüm aralığını tanımlamalı.
- `sequence` 1'den başlamalı ve kesintisiz artmalı.
- Bölüm aralıkları çakışmamalı ve boşluk bırakmadan devam etmeli.
- `previous_pack` ve `next_pack` kullanılırsa komşu paketlerin doğru ID'lerini göstermeli.
- `chapter_count`, bütün paketlerin kapsadığı bölüm adedine eşit olmalı.
- `chapter_pack_size`, hiçbir paketin bölüm adedinden küçük olmamalı.
- Her pakette `overview.md` gibi kısa bir özet kullanılabilir. Binlerce bölümlük eseri tek bir Markdown dosyasına doldurma; bölümleri küçük, sıralı ve eklenebilir paketlere ayır.

## 5. Kanonik kayıtlar ve ID'ler

Kanonik dosyaların her biri, ID'leri anahtar olan bir JSON nesnesidir. Örnek:

```json
{
  "loc_guro_apartment": {
    "id": "loc_guro_apartment",
    "name": "Guro Apartmanı",
    "type": "building",
    "connected_locations": ["loc_apartment_lobby", "loc_rooftop"]
  }
}
```

Dosyalar: `characters.json`, `locations.json`, `factions.json`, `items.json`, `techniques.json`, `realms.json`, `creatures.json`, `events.json`, `relationships.json`, `timeline.json`, `knowledge.json`.

- Bir karakterin veya mekânın kimliği chapter'lar arasında değişmez.
- `references` alanı kullanılıyorsa anahtarları yalnızca desteklenen kategori adlarından biri olmalı ve değerleri ilgili kategori içinde var olan ID'lerin listesi olmalı.
- Referans verdiğin her ID'nin hedef kaydı pakette bulunmalı.
- Kaynakta bilinmeyen bir alanı kesin gerçek gibi uydurma. Bilinmeyenleri açıkça belirsiz olarak kaydet veya lore notlarında belirt.
- Kaynak bölümlerde geçen bütün karakterleri, yerleri, eşyaları ve ilişkileri tek bir serbest metin özetine sıkıştırma; motorun arayabileceği yapılandırılmış kayıtlar oluştur.

## 6. NPC goals — en kritik kural

**Yanlış — bu format import hatası üretir:**

```json
"goals": [
  "Salgından önce hazırlık yapmak"
]
```

**Doğru — her hedef nesne olmalı:**

```json
"goals": [
  {
    "id": "goal_prepare",
    "description": "Salgın başlamadan temel hazırlıkları yapmak",
    "priority": 9,
    "kind": "passive"
  }
]
```

Zorunlu alanlar:

- `id`: bu hedef için sabit, benzersiz kimlik.
- `description`: hedefin açık anlatımı.
- `priority`: tam sayı.
- `kind`: verilmezse varsayılan `passive`; izin verilen türler `passive`, `move_to`, `follow_npc`, `meet_npc`, `patrol`, `survive`.

Koşullu alanlar:

- `kind: "move_to"` için `target_location` metni gerekir.
- `kind: "follow_npc"` veya `kind: "meet_npc"` için `target_id` metni gerekir.
- `kind: "patrol"` için `data.locations` boş olmayan bir liste olmalı.
- `required_progress` kullanılıyorsa en az 1 olan tam sayı olmalı.

Aynı hedefi `data/characters.json` ve `world.json` içinde tanımlıyorsan iki yerde de nesne kullan. Kanonik kayıttaki hedef açıklaması ile başlangıç oyun durumundaki hedefi çeliştirme. Oyuncu eylemleriyle değişen aktif hedef ilerlemesi runtime/save durumuna aittir; kaynak kanonunu sessizce değiştirme.

### Runtime relationship key rule

`world.json` içindeki `relationships` nesnesinin anahtarı, ilişki kaydının açıklayıcı ID'si değildir. Motorun beklediği anahtar, `party_a` ve `party_b` değerlerini alfabetik sıralayıp `|` ile birleştirmektir.

Örnek: taraflar `npc_kim_minjae` ve `npc_seo_yuna` ise anahtar `npc_kim_minjae|npc_seo_yuna` olmalıdır. `rel_minjae_yuna` gibi keyfî bir ad, mevcut runtime invariant kontrolünden geçmez. Kanonik `data/relationships.json` kaydının kendi ID'si ayrı kalabilir; bu kural yalnızca `world.json` içindeki aktif runtime ilişkilerine uygulanır.

## 7. world.json — başlangıç oyun durumu

`world.json`, motorun başlangıç durumunu kurduğu dosyadır. `character` ve `locations` nesne olmalıdır. Başlangıç karakterinin `location_id` değeri `locations` içinde bulunmalıdır. Çıkışlar var olan lokasyon ID'lerini göstermelidir. Eşya, NPC, ilişki, olay ve görevler motorun beklediği alanlarla tanımlanmalıdır.

Başlangıç NPC'si örneği:

```json
{
  "npc_kim_minjae": {
    "id": "npc_kim_minjae",
    "name": "Kim Min-jae",
    "location_id": "loc_guro_apartment",
    "hp": 75,
    "max_hp": 75,
    "attack_power": 9,
    "defense": 1,
    "alive": true,
    "personality": {
      "courage": 65,
      "aggression": 35,
      "sociability": 40,
      "honesty": 65,
      "greed": 45,
      "curiosity": 70,
      "loyalty": 55,
      "patience": 60
    },
    "goals": [
      {
        "id": "goal_prepare",
        "description": "Salgın başlamadan temel hazırlıkları yapmak",
        "priority": 9,
        "kind": "passive"
      }
    ]
  }
}
```

Bu nesne, `world.json` içindeki `npcs` nesnesinin içindeki bir kayıttır. `world.json` ayrıca en azından başlangıç `character`, `locations`, `exits`, `items`, `npcs`, `relationships`, `events`, `techniques` ve `quests` nesnelerini tutarlı şekilde içermelidir. Kullanılmayan kategoriler boş nesne olabilir.

## 8. Kaynak kanonu, alternatif zaman çizgisi ve NPC yaşamı

- Kaynak eserde gerçekten gerçekleşen olayları kanonik bilgi olarak kaydet.
- Oyuncunun oyun sırasında yaptığı değişiklikleri ayrı runtime durumunda tut.
- Gelecekte kaynak hikâyede gerçekleşen bir olay, alternatif zaman çizgisinde koşulları değiştiyse otomatik olarak zorla gerçekleşmemeli.
- NPC'nin hedefi, mevcut konumu, ilişkileri, bildikleri ve envanteri farklı kavramlardır; birini diğerinin yerine yazma.
- Bir NPC'nin gizli bilgisi herkese açık bilgi değildir. `knowledge.json` içindeki görünürlük ve kimin bildiği bilgilerini tutarlı kullan.
- Oyuncu bir karakterle veya eşyayla karşılaşmak istedi diye onu anında bulunduğu yere taşıma. Dünya konumu ve erişim koşulları başlangıç verileri ve motor kurallarıyla tutarlı olmalı.

## 9. Hatalı paketler ve doğrulama

Paket oluşturmadan önce şu kontrol listesini uygula:

- [ ] Bütün JSON dosyaları geçerli JSON olarak parse ediliyor.
- [ ] `manifest.json` ve `world.json` arşiv kökünde.
- [ ] Kanonik data dosyaları yalnızca desteklenen dosya adlarında ve `data/` altında.
- [ ] Her kaydın `id` değeri, kayıt anahtarıyla eşleşiyor.
- [ ] Her `references` hedefi mevcut.
- [ ] Her NPC goal bir nesne ve `id`, `description`, `priority` alanlarını taşıyor.
- [ ] `move_to`, `follow_npc`, `meet_npc` ve `patrol` hedeflerinin özel alanları tamam.
- [ ] Başlangıç karakteri ve tüm başlangıç NPC/eşya konumları mevcut lokasyonları gösteriyor.
- [ ] Chapter sıra numaraları ve aralıkları kesintisiz; manifest ile aynı.
- [ ] Aynı karakter, mekân veya eşya farklı chapter'larda yanlışlıkla yeni ID ile kopyalanmadı.
- [ ] Kaynak dosyalar korunuyor; oyun durumu kaynak metninin üzerine yazılmıyor.
- [ ] Validator çalıştırıldıysa sonucu kaydedildi; çalıştırılmadıysa bu açıkça bildirildi.

Resmî yerel doğrulama komutu:

```bash
python tools/validate_scenario.py path/to/MyScenario.rpgscenario.zip
```

Validator `INVALID` döndürürse hata mesajında adı geçen dosya ve alanı düzelt; hatayı gizlemek için alanı silme veya motor doğrulamasını kapatma. Bu komut yalnızca paket yükleme/başlangıç durumu doğrulamasıdır; AI'nin runtime davranışını tek başına kanıtlamaz.

## 10. ChatGPT teslim biçimi

Kullanıcıya şunları bildir:

1. Senaryo adı ve kısa açıklaması.
2. Arşivin adı.
3. Hangi bölüm aralıklarının kapsandığı.
4. Validator gerçekten çalıştırıldıysa sonucu; çalıştırılmadıysa doğrulamanın yapılmadığı.
5. Kaynakta eksik kalan veya belirsiz olan noktalar.

Paketin uygulamaya import edildiği, oynandığı ve AI retrieval yolunun doğru çalıştığı test edilmediyse “tamamen test edildi” veya “kesin uyumlu” iddiasında bulunma.
