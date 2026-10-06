# NPC Presence & Encounter Specification

## Purpose

An NPC can exist in canon without being physically present, accessible, or encounterable by the player.
The engine must never let AI narration bypass these distinctions.

## Authority

- `GameState.world.npcs[npc_id].location_id` and `alive` are authoritative runtime facts.
- Scenario `data/characters.json` is read-only canonical configuration.
- `EncounterResolver` evaluates whether an NPC is currently encounterable.
- AI cannot directly set `encounterable`, bypass a gate, or move an NPC through narration.

## Encounter pipeline

```text
NPC exists
  -> alive?
  -> same physical location as player?
  -> scenario presence rule?
  -> all encounter conditions pass?
  -> ENCOUNTERABLE
```

Location is the primary physical gate. Chapter number is not itself an encounter gate.
Canonical first-appearance/chapter metadata remains useful for canon and retrieval, but an
alternate-timeline game may encounter a known character earlier when physical and scenario
conditions permit it.

## Supported declarative conditions

All conditions in `encounter_conditions` are ANDed:

- `location`
- `popularity`
- `reputation`
- `level`
- `realm`
- `relationship_affinity`
- `relationship_trust`
- `inventory`
- `quest`
- `event`
- `npc_present`
- `npc_absent`

Unknown condition types are rejected while loading the scenario.

## Presence

A character may optionally define:

```json
"presence": [
  {"location_id": "royal_palace"}
]
```

A future extension may add deterministic turn windows. Presence never overrides the
runtime NPC location; it is an additional canonical constraint.

## Access gates

A king may be physically in the palace but inaccessible because a guard is present:

```json
"encounter_conditions": [
  {"type": "npc_absent", "npc_id": "royal_guard"}
]
```

After the guard is defeated or otherwise removed from the location, the same king can become
encounterable. Reputation, popularity, authority, quests, invitations, or power requirements
can be represented by additional conditions without hard-coding them into NPC logic.

## Player-character scenarios

If the scenario begins with the player inhabiting a canon character's body, the engine should
model that as the runtime player identity/bootstrap configuration. The canon character can be
known immediately because the player identity is already bound to that character; chapter-based
retrieval must not incorrectly hide the player's own identity.

## Anti-bypass rule

`look`, `talk`, `attack`, and technique targeting use the same encounter gate. AI-generated
narrative may describe an attempted interaction, but it cannot make an inaccessible NPC
available or cause a successful interaction without an engine-approved state transition.
