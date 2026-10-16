# AI-STORY-ENGINE — Teknik Referans

> Bu belge, eski teknik notlardan çıkarılmış birleştirilmiş referanstır. Güncel kaynak kod ve doğrulayıcılar uygulama davranışı konusunda son sözü söyler. Buradaki sürüm/uygulama iddiaları görev başında yeniden doğrulanır.

## 1. Ürün sınırları
AI-STORY-ENGINE Android öncelikli, local-first metin RPG motorudur. Amaç, senaryo importu, campaign/gameplay, kalıcı durum, save/load, yerel GGUF modeli ve isteğe bağlı bulut AI sağlayıcılarını aynı uygulamada desteklemektir. Proje kararı hybrid-provider yaklaşımıdır: local GGUF, Gemini API ve OpenAI API/uyumlu endpoint'ler; dış web araştırması bundan ayrı bir capability'dir ve varsayılan kapalı kalmalıdır. Eski bir belgedeki networked services kapsam dışı ifadesi, hybrid-AI gereksinimini sessizce kaldırma izni değildir.

## 2. Yetkili gameplay pipeline
`player action → deterministic parser/rules → authoritative GameState → bounded context (state + relevant memory + lore) → AI adapter → structured proposal → schema/security/gameplay validation → accepted effects → memory/event/quest updates → persistence`

- Anlatı metni state değiştirmez ve anlatıdan oyun state'i parse edilmez.
- AI state/DB/save/scenario/filesystem/process üzerinde doğrudan write/tool yetkisine sahip değildir.
- Her AI önerisi bağımsız doğrulanır; reddedilen proposal gerçek kabul edilip kalıcı belleğe yazılamaz.
- Bir açık player action en fazla bir AI transaction'ı üretir. İşlem başına en çok iki provider çağrısı: ilk structured response ve yalnızca malformed yapılandırılmış çıktı için tek retry. Provider/network/model hataları sınırsız retry'ye dönüşmez.
- Otomatik AI→AI continuation, ek oyuncu girdisi olmadan ikinci tur ve re-entrant gameplay çağrıları yasaktır.
- Context, deterministik seçme ve bütçe sınırlarıyla oluşturulur. Bütün hikâye geçmişi her tur prompt'a dökülmez.

## 3. Durum ve veri modelleri
- Authoritative GameState içinde character/world/location/inventory/resources, NPC state, events, quests ve relationships gibi runtime varlıklar bulunur.
- Stable ID kullanılır; display name kimlik değildir.
- NPC modelinin belgelenmiş alanları HP/alive/disposition/traits, 0–100 personality değerleri, fears/preferences ve goals'dur. Kimlik/name ve NPC goals AI tarafından serbestçe değiştirilemez; goal mutation engine/scenario tarafından kontrol edilir.
- Memory typed records halinde kalıcı tutulur; görünürlük örnekleri `player`, `npc:<id>`, `faction:<id>`, `system`. Player context yalnızca player'ın bildiği kayıtları alır; NPC context kendi viewer identity'sine göre filtrelenir. Secret/system-only veri yanlış bağlama aktarılmaz.
- Event state lifecycle: `inactive → active → resolved|failed|cancelled`; AI yalnızca mevcut event'leri tetiklemeyi önerebilir. Event tanımları AI tarafından oluşturulamaz.
- Quest lifecycle ve objective ilerlemesi engine-owned'dur; narrative tek başına quest tamamlayamaz. Belgelenmiş objective türleri `collect`, `reach`, `defeat`, `talk`, `interact` olsa da her işte güncel validator kontrol edilir.
- Belgelenmiş status effect ID'leri: `poison`, `bleed`, `burn`, `regeneration`, `stamina_regen`, `stunned`, `rooted`; ekleme, stack, expiration ve turn ticks validation geçidinden geçer.

## 4. Scenario package contract (current code baseline)
Tipik import: tek `.rpgscenario.zip` veya dizin. Runtime loader'da `PACK_FORMAT_VERSION = 2`. Tipik kök:
```
Scenario.rpgscenario.zip
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
├── chapters/<chapter-pack>/
│   ├── chapter_manifest.json
│   └── *.md
└── lore/*.md
```
- Manifestte en az `scenario_id`, `name`, `version` gerekir; format/version alanları güncel loader ile eşleştirilir.
- `world.json` oyunun başlangıç GameState'ini kurar. Location/exits, character location, item/NPC locations, events, quests ve relationships tutarlı olmalıdır.
- Canonical `data/*.json` dosyaları desteklenen on bir dosya adından biri olmalı ve her dosyada record ID, outer object key ile aynı olmalıdır.
- Stable IDs chapter paketleri arasında değişmez. Reference alanları explicit ve doğrulanabilir olmalı; AI/validator alan adlarından keyfi ilişki tahmin etmez.
- Her NPC goal düz yazı değil, en az `id`, `description`, `priority` alanları bulunan nesnedir. Koşullu goal türleri `move_to`, `follow_npc`, `meet_npc`, `patrol` ek alanlar gerektirir; güncel schema/validator kontrol edilir.
- `world.json` içindeki active relationship key'i taraf ID'leri alfabetik sıralanıp `party_a|party_b` birleştirilerek oluşturulur; kanonik relationship record ID ile karıştırılmaz.
- Chapter numarası runtime turn değildir. Canon source facts ile oyuncunun alternatif zaman çizgisi/runtime divergence durumu ayrı tutulur.
- Markdown, insan-okur lore/research/chapter dokümanıdır; JSON authoritative machine-readable veri olarak kalır. Canonical scenario verisi gameplay sırasında immutable olmalıdır.
- Import/validation: `python tools/validate_scenario.py <scenario-dir-or-zip>`. Çalıştırılmadıysa paketin doğrulandığı söylenmez. Hataları susturmak için alan silinmez/validator kapatılmaz.

## 5. Android, native runtime ve build
- Kaydedilmiş teknoloji zinciri: Python 3.11, Kivy, Buildozer + python-for-android; Buildozer 1.6.0, Kivy 2.3.1 ve pinned p4a/NDK değerleri build dokümanında listelenmiştir; güncel CI config'i doğrula.
- Tercih edilen build ortamı Linux/Ubuntu 24.04 GitHub Actions; Google Colab fallback/debug ortamıdır. Build Android telefonda çalıştırılıyor varsayımı yapılmaz.
- Android build workflow `workflow_dispatch` ve Android/native kaynaklarla ilgili dosya yollarına filtrelenmiş `pull_request` tetikleyicilerini kullanır. Test suite ayrı bir workflow'dur; her görevde gerçek tetikleyiciler `.github/workflows/` altındaki güncel dosyalardan doğrulanır, `main` push davranışı varsayılmaz.
- Android build zinciri: source pytest → native ARM64 llama.cpp server cross-build → ELF64/AArch64 ve binary provenance → Buildozer APK → package metadata + SHA-256 → CI artifact/provenance.
- Android'de local model dosyaları GGUF'tur; model manager belgelerinde güvenli destination, atomik `.part` aktarım ve SHA-256 doğrulama/limitlerden söz edilir. Gerçek kısıtları current code'dan doğrula.
- Android Storage Access Framework (SAF) ile scenario/GGUF importları uygulama-private storage'a alınmalıdır.
- APK build sonucu fiziksel cihazda çalışmayı kanıtlamaz. Cihaz smoke testinde app launch, deterministic action, save/load, SAF scenario importu, model import/activation ve gerekiyorsa gerçek local inference ayrı test edilir.
- Build asla yalnızca testlerin yeşil olması nedeniyle başlatılmaz; Mareşal'in açık isteği gerekir.

## 6. Test ve doğrulama
Kaydedilmiş CI test basamakları:
```bash
python -m pytest -q tests
python -m compileall -q .
python tools/verify_android_readiness.py
python tools/mutation_smoke.py
```
Task-specific additional checks:
```bash
python tools/validate_scenario.py <scenario-dir-or-zip>
python tools/release_verify.py <release-archive.zip>
```
Komutlar güncel repoda doğrulanmalıdır. Her rapor gerçek komutu, commit/HEAD ve sonucu verir. Yerel test, CI, APK ve cihaz kanıtları ayrı gösterilir.

## 7. Security and data
- Repository public kabul edilir; provider keys, tokens, `.env`, signing keys, saves, local GGUF, APK/build cache/output, personal data ve user imports commit edilmez.
- AI context'e key/credential, file handles, DB handles, tool registry veya arbitrary app objects konmaz.
- AI adapter yeteneği dar tutulur; dış araştırma/Web erişimi provider connectivity'den ayrıdır, varsayılan kapalıdır.
- Prompt injection metni, senaryo/lore/oyuncu/NPC/bellek verisi içindeki sıradan metindir; privilege kazanmaz.
- Save/package formatları versioned'dır; breaking change açık plan/uyumluluk ve test ister.
