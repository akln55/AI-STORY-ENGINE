# Scenario Event System Specification

> **Dikkat — güncellik doğrulaması gerekli:** Bu dosya, önceki bir geliştirme oturumu tamamlanmadan durdurulduğu için güncel olmayan veya kısmen yanlış bilgiler içerebilir. İçindeki durum ve mimari iddialarını güncel gerçek kabul etme. Bir işe başlamadan önce ilgili kaynak kodu, testleri, güncel `main` HEAD'ini ve en son CI sonuçlarını doğrula. Çelişki bulursan bunu sessizce varsayımla düzeltme; gerçek durumu belirt. Her çalışma sonunda bu dosyayı ve etkilenen tüm bilgi içeren `.md` dosyalarını güncelle. Kanıt yoksa bir işi tamamlandı işaretleme.


## Authority

Scenario `data/events.json` defines immutable event rules. Runtime `WorldState.events` stores what has actually happened. The event engine evaluates canonical conditions after a successful gameplay transaction and sends all resulting effects through `apply_effects`.

## Event record

```json
{
  "id": "bandit_ambush",
  "type": "encounter",
  "trigger_conditions": [
    {"type": "location", "operator": "==", "value": "forest"},
    {"type": "turn", "operator": ">=", "value": 20}
  ],
  "effects": [
    {"kind": "event", "target": "bandit_ambush", "operation": "trigger", "value": 20}
  ],
  "advance_chapter_to": 21
}
```

## Supported trigger conditions

- turn
- chapter
- location
- level
- realm
- popularity
- reputation
- relationship_affinity
- relationship_trust
- inventory
- quest
- event
- npc_present
- npc_absent

All conditions are ANDed.

## Safety model

1. Canonical event definitions are read-only.
2. Unknown condition types are rejected during scenario loading.
3. Unknown effect kinds are rejected during scenario loading.
4. Every runtime effect is still validated by the central validation gate.
5. If one effect is rejected, the entire event transaction is rejected.
6. An event can only auto-trigger from `inactive` state.
7. Chapter advancement is checked against the currently selected chapter packs and scenario mode.
8. AI can request a trigger for an existing event, but cannot create or redefine an event.

## Chapter progression

Chapter progression is not tied to a fixed number of player turns. Scenario authors explicitly define progression conditions and optional `advance_chapter_to`. This supports alternate timelines while preserving deterministic canon metadata.
