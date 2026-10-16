# Yeni Sohbet Başlangıç Dosyası — Şablon

## Zorunlu ilk okuma
1. `AI_RULES.md`
2. `AI_START_HERE.md`
3. `docs/AI_STORY_ENGINE_PROJECT_PROFILE.md`
4. `docs/PROJECT_GOALS.md` (yalnızca ilgili açık hedef)
5. `docs/AI_WORKFLOW.md` ve ilgili teknik referanslar

Önce depo/branch/HEAD ve güncel dosyaları doğrula. İnceleme yapmadan kod yazma, dosya silme veya build başlatma.

## Oturum
- Tarih/saat (Europe/Istanbul):
- Görev:
- Durum: PLAN / IN PROGRESS / PASS / FAIL / BLOCKED
- Repo: akln55/AI-STORY-ENGINE
- Branch / başlangıç HEAD:
- Hazırlayan:

## Projeyi anlamak için gerekenler
Android öncelikli, local-first, AI destekli text RPG. Geliştirici Android telefondan çalışır. Kaydedilmiş stack Python 3.11 + Kivy + Buildozer/python-for-android'dır; build tercih edilen yol GitHub Actions/Linux CI, Colab yedek/debug. Güncel sürümler/config her oturumda doğrulanır. Engine authoritative GameState'in tek sahibidir; AI anlatı/öneri üretir ve validation geçidini aşamaz.

## Görev sözleşmesi
- Tek hedef:
- Kabul kriterleri:
  - [ ] 
  - [ ] 
- İzin verilen dosya/alan kapsamı:
- Kapsam dışı alanlar:
- Bağımlılıklar/risk:
- Plan:
- Test planı:
- Gerekli onaylar:

## Anlık kanıt
- Güncel HEAD:
- İlgili diff/source/test dosyaları:
- Son test/CI sonucu ve commit:
- APK/device kanıtı (varsa; yoksa bilinmiyor):
- Kullanıcı tarafından bildirilen belirtiler:
- Doğrulanmış kök neden:
- Bilinmeyen/hipotez:

## Rütbe ve devir
- Mareşal: kullanıcı, nihai yetki.
- Komutan: plan, kapsam içi rutin kararlar, delegasyon ve merge koordinasyonu.
- Asker: yalnızca görev branch'i ve izinli dosyalar; main'e dokunmaz, merge etmez.
- Denetçi: uygulayıcıdan ayrı AI/sohbet; bağımsız PASS/FAIL/BLOCKED.
- Kapsam dışı değişiklikte Asker durur ve Komutan'a rapor verir.
- Zorunlu test ve bağımsız denetim PASS olmadan merge olmaz.
- Build yalnızca Mareşal açıkça istediğinde çalıştırılır.

## İlk işler
1. Aktif goal ve kapsamı doğrula.
2. İlgili kaynak, testler ve diff'i incele.
3. Kabul kriterleri ve test planı kesinleşince başla.
4. Hedefli testleri çalıştır ve sonuçları gerçek çıktıyla kaydet.
5. Teslimde branch/HEAD, dosyalar, test/CI, denetim, merge durumu ve engelleri belirt.
