# RPG ENGINE --- SCENARIO / CHAPTER DATA CREATION MASTER SPECIFICATION

## Canonical Scenario Authoring & Data-Pack Production Standard --- v3.0

**Status:** Current authoring specification\
**Target engine baseline:** RPG Engine v1.27.x\
**Purpose:** This document is the master specification and reusable
prompt for another AI/research agent that converts source material into
scenario data for the RPG Engine.

------------------------------------------------------------------------

# 1. PURPOSE

A scenario is **not** a generic story summary.

It is a structured, persistent world/canon package that allows the
deterministic RPG Engine to know:

-   which entities exist;
-   where they can be;
-   how they are related;
-   what events happened;
-   what items/techniques/factions/locations exist;
-   what each character can know;
-   what information is available at a given point;
-   which NPCs can be encountered;
-   which NPC schedules/goals are defined;
-   which quests/events exist;
-   how canonical history changes over time.

The runtime AI is a **narration and proposal layer**.

The deterministic engine remains the authority over actual runtime
state.

> **Canon is data. Runtime state is state. AI is not the authority over
> either.**

------------------------------------------------------------------------

# 2. CRITICAL ARCHITECTURAL RULE

The project has two different layers:

``` text
CANONICAL SCENARIO DATA
        ↓
ScenarioRegistry / ScenarioRetrieval / ChapterManager
        ↓
ScenarioContext
        ↓
AI context + deterministic engine
        ↓
GameState
        ↓
PLAYER TIMELINE / RUNTIME CHANGES
```

Never merge canonical scenario data with player-mutated runtime state.

Correct:

``` text
scenario canon
    ↓
GameState
    ↓
player actions
    ↓
runtime divergence
```

Incorrect:

``` text
player action
    ↓
characters.json
```

Canonical scenario data must remain immutable during normal gameplay.

------------------------------------------------------------------------

# 3. IMPORTANT v3.0 DISTINCTION: AUTHORING DATA VS RUNTIME DATA

The research AI may produce a rich authoring package containing
per-chapter extraction records, evidence, provenance, ambiguities and
other material.

However, **the current engine does not automatically treat arbitrary
per-chapter JSON files as runtime registry categories.**

The current runtime loader directly supports:

``` text
manifest.json
world.json

data/
    characters.json
    locations.json
    factions.json
    items.json
    techniques.json
    realms.json
    creatures.json
    events.json
    relationships.json
    timeline.json
    knowledge.json

chapters/
    <pack>/
        chapter_manifest.json
        *.md

lore/
    *.md
```

Therefore the production pipeline is:

``` text
SOURCE MATERIAL
      ↓
RESEARCH / EXTRACTION AI
      ↓
AUTHORING DATA
      ↓
VALIDATION / COMPILATION
      ↓
CURRENT RUNTIME SCENARIO FORMAT
      ↓
ScenarioRegistry + ChapterManager + Retrieval
      ↓
RPG Engine
```

Per-chapter JSON is an **authoring/intermediate representation** unless
and until the engine receives a dedicated chapter-record loader.

Do not falsely claim that a file is runtime-consumable merely because it
exists inside the ZIP.

------------------------------------------------------------------------

# 4. FILE FORMAT POLICY

## 4.1 JSON --- authoritative structured data

JSON is authoritative for machine-readable scenario facts.

Current runtime-supported canonical categories:

-   characters
-   locations
-   factions
-   items
-   techniques
-   realms
-   creatures
-   events
-   relationships
-   timeline
-   knowledge

The current runtime bootstrap is:

``` text
world.json
```

`world.json` contains the initial GameState bootstrap, including the
structures currently supported by the engine such as:

-   player character bootstrap
-   locations
-   exits
-   items
-   NPCs
-   relationships
-   events
-   quests

The exact runtime schema must be checked against the current engine
before generating a pack.

## 4.2 Markdown --- evidence and human-readable research

Markdown may contain:

-   chapter overview
-   chronology
-   event explanations
-   character notes
-   location notes
-   research notes
-   ambiguity/conflict notes
-   provenance explanations
-   extraction rationale
-   lore

Markdown is explanatory. It must not silently override equivalent JSON.

## 4.3 ZIP --- distribution

The normal distribution unit is:

``` text
ScenarioName.rpgscenario.zip
```

The player should not need to manually edit internal files.

------------------------------------------------------------------------

# 5. STABLE ID POLICY

Every persistent entity receives a stable ID.

IDs must:

-   be deterministic;
-   be unique within their category;
-   remain stable across chapter packs;
-   not depend on display capitalization;
-   not be replaced because an alias/title changes.

Examples:

``` text
char_yang_kai
loc_black_book_city
faction_blood_demon
item_space_ring
technique_void_collapse
event_sect_war
quest_forest_supply
```

Do not create duplicate IDs such as:

``` text
yang_kai
yangkai2
yang_kai_final
yang-kai-new
```

for the same canonical entity.

If a character changes:

-   name;
-   title;
-   alias;
-   disguise;
-   body;
-   public identity;

preserve the stable ID unless the source establishes that it is
genuinely a different entity.

------------------------------------------------------------------------

# 6. RESEARCH AI EXTRACTION CONTRACT

For every supplied chapter/chapter range, extract all relevant canon
facts.

Do not only follow the protagonist.

Extract:

1.  New entities.
2.  Returning entities.
3.  Entity state changes.
4.  Location changes.
5.  Faction changes.
6.  Relationship changes.
7.  Item creation/discovery/destruction/ownership.
8.  Technique introductions/use/revelations.
9.  Realm/power progression.
10. Events.
11. Timeline facts.
12. Knowledge changes.
13. Secrets.
14. Rumors.
15. NPC presence.
16. NPC encounter/access conditions.
17. NPC goals/schedules where canonically established.
18. Dialogue/speech-style characteristics.
19. Deaths/disappearances.
20. Injuries/status changes.
21. First/last known appearance.
22. References to earlier events.
23. References to future events.
24. Quest-related facts where supported.
25. Canon changes that become true because of the chapter.

If a fact is uncertain:

``` text
confirmed
probable
uncertain
disputed
```

must be used rather than silently inventing certainty.

------------------------------------------------------------------------

# 7. CANON CHAPTER NUMBER VS RUNTIME TURN

This distinction is mandatory.

A source chapter is not automatically an engine turn.

A chapter answers:

> Where in the source material did this fact become established?

A runtime turn answers:

> When did something happen in this player's simulation?

Therefore:

``` text
chapter 120
```

must NOT automatically become:

``` text
turn 120
```

Likewise, a canonical first appearance at chapter 120 must not
automatically become a runtime restriction preventing an
alternate-timeline encounter.

Canonical chapter metadata may be stored as:

``` json
{
  "first_appearance_chapter": 120
}
```

Runtime NPC presence currently uses turn-oriented fields such as:

``` json
{
  "location_id": "loc_capital",
  "from_turn": 100,
  "to_turn": 150
}
```

Do not fabricate a turn conversion from chapter numbers.

If the scenario has a documented chapter-to-runtime timeline mapping,
use that mapping. Otherwise retain chapter information as canon
metadata.

------------------------------------------------------------------------

# 8. CHARACTER RECORD

A character record should contain only fields compatible with the
current engine or clearly marked as authoring metadata.

Example:

``` json
{
  "id": "char_example",
  "name": "Example Character",
  "aliases": ["Example Lord"],
  "faction_id": "faction_example",

  "first_appearance_chapter": 120,
  "last_appearance_chapter": 180,

  "status": "alive",

  "personality": {
    "discipline": 70,
    "aggression": 40,
    "patience": 65,
    "honor": 80,
    "ambition": 55,
    "sociability": 35,
    "caution": 75,
    "curiosity": 60
  },

  "speech_style": {
    "formality": "formal",
    "verbosity": "medium",
    "tone": ["controlled", "respectful"],
    "patterns": ["rarely raises voice"]
  },

  "presence": [],
  "schedule": [],
  "goals": [],
  "encounter_conditions": [],
  "knowledge_boundary": [],
  "references": {
    "factions": ["faction_example"]
  }
}
```

Do not invent a personality numeric model if the current engine/schema
does not define how those values are consumed.

When a field is authoring-only, mark it clearly rather than pretending
it is an active runtime mechanic.

------------------------------------------------------------------------

# 9. NPC PRESENCE

Presence answers:

> Where can this NPC physically be?

Current runtime-compatible presence structure:

``` json
"presence": [
  {
    "location_id": "loc_town",
    "from_turn": 0,
    "to_turn": 50,
    "confidence": "confirmed"
  }
]
```

Important:

-   `from_turn` and `to_turn` are runtime concepts.
-   Canonical chapter ranges should remain chapter metadata unless
    explicitly mapped.
-   Never fabricate exact times or turns.
-   Do not use presence to represent encounter permissions.

Presence and encounterability are separate.

------------------------------------------------------------------------

# 10. NPC SCHEDULE

The current engine supports scenario-authored NPC schedules.

Example:

``` json
"schedule": [
  {
    "location_id": "loc_market",
    "from_turn": 0,
    "to_turn": 20
  },
  {
    "location_id": "loc_inn",
    "from_turn": 21,
    "to_turn": 40
  }
]
```

Cyclic schedules may use:

``` json
{
  "location_id": "loc_market",
  "from_turn": 0,
  "to_turn": 4,
  "cycle_turns": 10
}
```

Only create a schedule when the source establishes a repeatable pattern
or the scenario explicitly defines one.

Do not convert ordinary narrative movement into an invented daily
schedule.

------------------------------------------------------------------------

# 11. NPC GOALS

The current engine supports deterministic NPC goals.

Supported goal kinds:

``` text
passive
move_to
follow_npc
meet_npc
patrol
survive
```

Example:

``` json
"goals": [
  {
    "id": "goal_return_home",
    "description": "Return to the eastern settlement.",
    "kind": "move_to",
    "priority": 50,
    "target_location": "loc_eastern_settlement"
  }
]
```

For a patrol:

``` json
{
  "id": "goal_guard_patrol",
  "description": "Patrol the outer road.",
  "kind": "patrol",
  "priority": 40,
  "required_progress": 10,
  "data": {
    "locations": [
      "loc_gate",
      "loc_road",
      "loc_watchtower"
    ]
  }
}
```

The research AI must not invent goals simply because an NPC is
important.

Goals must be supported by:

-   explicit canon behavior; or
-   explicit scenario design.

------------------------------------------------------------------------

# 12. NPC ENCOUNTER MODEL

Encounterability answers:

> If the player is here now, can the player actually interact with this
> NPC?

Current supported encounter condition types include:

``` text
location
popularity
reputation
level
realm
relationship_affinity
relationship_trust
relationship_flag
inventory
quest
event
npc_present
npc_absent
```

Example:

``` json
"encounter_conditions": [
  {
    "type": "location",
    "operator": "==",
    "value": "loc_royal_palace"
  },
  {
    "type": "relationship_trust",
    "target": "char_king",
    "operator": ">=",
    "value": 50
  }
]
```

Only create a condition if:

1.  the source explicitly establishes it; or
2.  it is a direct structural consequence of an established world fact.

Never invent:

``` text
power >= 100
```

merely because the NPC is powerful.

Never invent:

``` text
reputation >= 80
```

merely because the NPC is a king.

------------------------------------------------------------------------

# 13. FIRST APPEARANCE IS NOT AN ENCOUNTER GATE

This rule remains non-negotiable.

``` json
{
  "first_appearance_chapter": 500
}
```

means:

> The source first establishes this character at chapter 500.

It does NOT mean:

> The player is forbidden from encountering this character before
> chapter 500.

Alternate timelines are a core scenario capability.

If the player changes the world at chapter 100, the runtime may produce
a different history while the canonical source record remains unchanged.

------------------------------------------------------------------------

# 14. KNOWLEDGE MODEL

Knowledge is separate from existence.

A character can exist without the player knowing them.

Example:

``` json
{
  "id": "knowledge_001",
  "subject_type": "character",
  "subject_id": "char_secret_master",
  "fact": "The master possesses a hidden technique.",
  "available_from_chapter": 240,
  "known_by": ["char_yang_kai"],
  "visibility": "restricted"
}
```

Supported visibility concepts include:

``` text
public
player
npc
restricted
secret
system
```

`system` information must never be exposed to player-facing context
unless a gameplay rule explicitly reveals it.

------------------------------------------------------------------------

# 15. FUTURE KNOWLEDGE PROTECTION

A research AI may know the entire source.

The player may not.

Example:

``` json
{
  "fact": "Character X eventually betrays Faction Y.",
  "canon_chapter": 800,
  "available_from_chapter": 800,
  "known_by": [],
  "visibility": "restricted"
}
```

This fact can exist in the scenario database.

It must not be retrieved as player knowledge in an earlier state unless
gameplay has revealed it.

The research AI must distinguish:

``` text
FACT EXISTS IN CANON
```

from:

``` text
PLAYER/NPC KNOWS FACT
```

------------------------------------------------------------------------

# 16. EVENTS

Every persistent important event should receive a stable ID.

Example:

``` json
{
  "id": "event_sect_battle",
  "type": "battle",
  "start_chapter": 300,
  "end_chapter": 305,
  "locations": ["loc_sect"],
  "participants": [
    "char_a",
    "char_b"
  ],
  "outcomes": [],
  "facts": [],
  "references": {
    "characters": ["char_a", "char_b"],
    "locations": ["loc_sect"]
  }
}
```

Events may record:

-   participants;
-   locations;
-   cause;
-   consequences;
-   beginning/end;
-   factions;
-   characters;
-   items;
-   knowledge produced;
-   visibility;
-   canonical outcome.

Do not write player-generated outcomes into canonical event data.

------------------------------------------------------------------------

# 17. TIMELINE

Timeline is separate from chapter numbering.

A timeline record describes an in-world event/order.

Example:

``` json
{
  "id": "timeline_001",
  "event_id": "event_sect_battle",
  "relative_order": 20,
  "source_chapters": [300, 301, 302]
}
```

If exact dates are established:

``` json
{
  "calendar": "world_calendar",
  "date": "YEAR-03-MONTH-05-DAY-12"
}
```

If not established, use relative order.

Never fabricate dates.

------------------------------------------------------------------------

# 18. LOCATION RECORD

Locations need enough information for deterministic movement, retrieval
and encounter resolution.

Example:

``` json
{
  "id": "loc_example",
  "name": "Example City",
  "type": "city",
  "parent_location_id": "loc_region",
  "connected_locations": [
    "loc_road",
    "loc_capital"
  ],
  "factions_present": [],
  "important_characters": [],
  "access_conditions": [],
  "notable_events": []
}
```

A location existing in canon does not mean the player can instantly
access it.

Movement/access remains an engine responsibility.

------------------------------------------------------------------------

# 19. FACTIONS

Record, where supported:

-   stable ID;
-   name;
-   hierarchy;
-   members;
-   allies;
-   enemies;
-   territory;
-   public reputation;
-   public knowledge;
-   secrets;
-   important events;
-   historical changes.

Example:

``` json
{
  "id": "faction_example",
  "name": "Example Sect",
  "territories": ["loc_sect"],
  "members": ["char_a"],
  "relations": [
    {
      "faction_id": "faction_other",
      "relation": "hostile"
    }
  ]
}
```

Use references where possible so cross-entity validation can detect
broken IDs.

------------------------------------------------------------------------

# 20. ITEMS

Record:

-   stable ID;
-   name;
-   type;
-   known owner;
-   location;
-   first appearance;
-   properties;
-   rarity;
-   restrictions;
-   destruction/status;
-   related events;
-   historical ownership transitions.

Example:

``` json
{
  "id": "item_space_ring",
  "name": "Space Ring",
  "type": "equipment",
  "first_appearance_chapter": 12,
  "properties": [],
  "references": {
    "characters": ["char_example"]
  }
}
```

If ownership changes:

-   preserve the old historical fact;
-   add a new transition;
-   do not erase history.

------------------------------------------------------------------------

# 21. TECHNIQUES / ABILITIES

Record:

-   stable ID;
-   name;
-   type;
-   canonical realm requirement if known;
-   cost if canonically defined;
-   effect;
-   known users;
-   first appearance;
-   source chapter;
-   limitations;
-   relationships to other techniques.

Do not invent numeric power values.

Canonical power descriptions and engine balancing values must remain
separate.

------------------------------------------------------------------------

# 22. REALMS / POWER SYSTEM

Record the canonical progression hierarchy.

Example:

``` json
{
  "id": "realm_example",
  "tier": 3,
  "name": "Example Realm",
  "parent_realm_id": "realm_parent",
  "stages": [
    "early",
    "middle",
    "late",
    "peak"
  ]
}
```

Do not mix canon realm names with arbitrary engine numeric levels unless
the scenario explicitly defines the mapping.

------------------------------------------------------------------------

# 23. RELATIONSHIPS

Relationships are time-aware.

Example:

``` json
{
  "id": "rel_a_b",
  "source_id": "char_a",
  "target_id": "char_b",
  "type": "ally",
  "from_chapter": 100,
  "to_chapter": 150,
  "strength": 70,
  "visibility": "public"
}
```

When a relationship changes:

``` text
close old historical interval
        ↓
create new state
```

Do not overwrite history.

Runtime relationship values remain GameState data.

------------------------------------------------------------------------

# 24. QUESTS

Quest data must be compatible with the engine's current quest system.

At the current baseline, quest bootstrap data is part of `world.json`.

Example:

``` json
{
  "forest_supply": {
    "id": "forest_supply",
    "title": "Forest Supplies",
    "description": "Bring back the required item.",
    "status": "available",
    "giver": "elder",
    "objectives": [
      {
        "id": "mushroom",
        "description": "Collect the item.",
        "type": "collect",
        "target_id": "mushroom",
        "required_count": 1
      }
    ],
    "rewards": [
      {
        "type": "xp",
        "amount": 30
      }
    ]
  }
}
```

Do not create a fictional quest merely because an event could be
interpreted as a quest.

Quest prerequisites and rewards must use the actual engine-supported
schema.

------------------------------------------------------------------------

# 25. CHAPTER CHANGESET --- AUTHORING LAYER

Each chapter should have an explicit changeset in the **authoring
representation**.

Example:

``` json
{
  "chapter": 125,
  "changes": {
    "new_characters": ["char_new"],
    "new_locations": ["loc_new"],
    "new_items": ["item_new"],
    "new_events": ["event_new"],
    "new_techniques": ["tech_new"],
    "relationship_changes": ["rel_change_001"],
    "presence_changes": ["presence_change_001"],
    "knowledge_changes": ["knowledge_001"]
  }
}
```

This is valuable for:

-   research;
-   auditing;
-   merging chapter packs;
-   generating global canonical data;
-   resolving conflicts;
-   rebuilding a scenario.

But do not claim that the current runtime automatically loads arbitrary
`chapter.json` files.

A future `ChapterRecord` runtime subsystem may consume these directly.

------------------------------------------------------------------------

# 26. CHAPTER PACK MANIFEST

Current engine-compatible chapter manifest requires:

``` json
{
  "pack_id": "martial_peak_0001_0400",
  "chapter_start": 1,
  "chapter_end": 400,
  "sequence": 1,
  "previous_pack": null,
  "next_pack": "martial_peak_0401_0800"
}
```

The engine validates:

-   unique pack IDs;
-   contiguous sequences;
-   contiguous/non-overlapping chapter ranges;
-   valid previous/next links.

A research AI may include additional metadata, but it must not remove
these required fields.

------------------------------------------------------------------------

# 27. HUMAN-READABLE CHAPTER DOCUMENTS

The current engine can load Markdown documents inside declared chapter
packs.

Recommended files:

``` text
overview.md
timeline.md
events.md
characters.md
locations.md
knowledge.md
research_notes.md
```

These should explain the extracted facts without replacing authoritative
JSON.

Do not copy long copyrighted dialogue.

Extract speech characteristics instead.

------------------------------------------------------------------------

# 28. SPEECH STYLE

Record characteristics, not large dialogue passages.

Example:

``` json
{
  "speech_style": {
    "formality": "low",
    "verbosity": "short",
    "tone": ["dry", "confident"],
    "address_style": "uses titles for elders",
    "patterns": [
      "often answers indirectly"
    ]
  }
}
```

The goal is consistent NPC characterization without storing unnecessary
source text.

------------------------------------------------------------------------

# 29. PROVENANCE

Every important extracted fact should have provenance.

Example:

``` json
{
  "source": {
    "type": "chapter",
    "chapter": 125,
    "section": "event",
    "confidence": "confirmed"
  }
}
```

Multiple sources:

``` json
{
  "sources": [
    {
      "type": "chapter",
      "chapter": 125
    },
    {
      "type": "chapter",
      "chapter": 128
    }
  ]
}
```

Provenance is especially important for:

-   relationships;
-   NPC presence;
-   encounter restrictions;
-   knowledge;
-   chronology;
-   disputed facts.

------------------------------------------------------------------------

# 30. CONFLICT RESOLUTION

When sources conflict:

1.  Do not silently choose.
2.  Preserve the evidence.
3.  Mark the fact as disputed.
4.  Prefer a later explicit correction only when the source clearly
    establishes the correction.
5.  Record the resolution reason.
6.  Do not delete the earlier evidence.

Example:

``` json
{
  "status": "disputed",
  "values": [
    {
      "value": "Faction A",
      "source_chapter": 100
    },
    {
      "value": "Faction B",
      "source_chapter": 140
    }
  ],
  "resolution": {
    "value": "Faction B",
    "reason": "Later chapter explicitly corrects the earlier statement."
  }
}
```

------------------------------------------------------------------------

# 31. REFERENCES AND VALIDATION

Where the runtime schema supports references, use explicit references.

Example:

``` json
"references": {
  "characters": ["char_a", "char_b"],
  "locations": ["loc_sect"],
  "events": ["event_sect_war"]
}
```

The current registry validates references against known categories.

Therefore:

-   do not reference nonexistent IDs;
-   do not invent category names;
-   do not create duplicate IDs;
-   do not use display names where stable IDs are required.

------------------------------------------------------------------------

# 32. RETRIEVAL-AWARE DATA

The current scenario retrieval layer is deterministic and
metadata-driven.

It uses canonical records and Markdown documents.

Research data should therefore expose useful searchable fields such as:

-   `id`
-   `name`
-   `description`
-   `summary`
-   `aliases`
-   relevant metadata

Knowledge visibility must be explicit.

Do not rely on the runtime AI to infer whether a fact is safe to
retrieve.

------------------------------------------------------------------------

# 33. WHAT THE RESEARCH AI MUST NEVER DO

The research AI must NOT:

-   invent events;
-   invent characters;
-   invent locations;
-   invent relationships;
-   invent powers;
-   invent dates;
-   invent NPC requirements;
-   invent schedules;
-   invent goals;
-   invent quests;
-   infer arbitrary encounter gates;
-   treat chapter number as an automatic gameplay restriction;
-   turn narrative assumptions into hard engine rules;
-   merge characters because names are similar;
-   overwrite historical states;
-   leak future knowledge into earlier knowledge;
-   replace stable IDs;
-   remove canon facts without evidence;
-   write player-runtime outcomes into canon;
-   claim unsupported authoring files are runtime features;
-   silently convert chapter numbers into runtime turns;
-   copy long copyrighted dialogue.

------------------------------------------------------------------------

# 34. WHAT THE RESEARCH AI SHOULD DO

For every source chapter:

``` text
READ SOURCE
    ↓
IDENTIFY ENTITIES
    ↓
RESOLVE STABLE IDS
    ↓
EXTRACT NEW FACTS
    ↓
EXTRACT STATE CHANGES
    ↓
EXTRACT PRESENCE
    ↓
EXTRACT SCHEDULES / GOALS IF SUPPORTED
    ↓
EXTRACT ENCOUNTER CONDITIONS
    ↓
EXTRACT KNOWLEDGE
    ↓
EXTRACT EVENTS
    ↓
EXTRACT RELATIONSHIPS
    ↓
EXTRACT TIMELINE
    ↓
EXTRACT QUEST/EVENT FACTS
    ↓
CROSS-REFERENCE
    ↓
VALIDATE
    ↓
WRITE AUTHORING JSON
    ↓
WRITE HUMAN-READABLE MARKDOWN
    ↓
COMPILE / MERGE INTO RUNTIME SCENARIO
```

------------------------------------------------------------------------

# 35. FULL SCENARIO PRODUCTION PIPELINE

For a large scenario:

``` text
SOURCE MATERIAL
      ↓
Research / extraction AI
      ↓
Global entity registry
      ↓
Per-chapter authoring records
      ↓
Chapter packs
      ↓
Cross-pack reconciliation
      ↓
Duplicate resolution
      ↓
Reference validation
      ↓
Timeline validation
      ↓
Knowledge visibility validation
      ↓
Presence / encounter validation
      ↓
NPC schedule / goal validation
      ↓
Runtime schema compilation
      ↓
Scenario ZIP
      ↓
RPG Engine validation
```

The final runtime pack must be loadable by the actual engine, not merely
structurally plausible.

------------------------------------------------------------------------

# 36. CHAPTER PACK MERGING

When importing:

``` text
pack 1
pack 2
pack 3
```

the authoring/compiler pipeline should:

1.  Validate each pack independently.
2.  Validate cross-pack IDs.
3.  Merge entities by stable ID.
4.  Append timeline entries.
5.  Apply state changes in chapter order.
6.  Preserve historical states.
7.  Detect contradictory changes.
8.  Detect references to nonexistent entities.
9.  Rebuild retrieval indexes.
10. Validate the final runtime scenario.
11. Produce a clean `.rpgscenario.zip`.

No runtime AI inference should be required for basic merging.

------------------------------------------------------------------------

# 37. PLAYER-ALTERED TIMELINE

Canonical data is immutable.

Example:

``` text
CANON:
NPC normally appears in City A at canonical chapter 300.

PLAYER TIMELINE:
The player changes the world before that event.
```

The canonical record remains:

``` text
chapter 300
```

The runtime state may diverge.

This is essential for alternate-story scenarios.

------------------------------------------------------------------------

# 38. CANONICAL FACT VS GAMEPLAY RULE

These are different.

Canonical fact:

``` text
The king is normally protected by palace guards.
```

Possible engine rule:

``` text
npc_present(char_palace_guard) blocks interaction.
```

Only encode the second if the source/scenario explicitly supports that
deterministic interpretation.

Never create arbitrary gameplay rules from narrative prestige, power or
common sense.

------------------------------------------------------------------------

# 39. QUALITY LEVELS

Every extracted fact should have:

``` text
confirmed
probable
uncertain
disputed
```

Recommended policy:

-   `confirmed`: eligible for deterministic canonical use;
-   `probable`: retained as evidence, but not automatically promoted to
    hard restriction;
-   `uncertain`: never silently converted into deterministic gameplay;
-   `disputed`: preserved with competing evidence and resolution status.

Scenario designers may explicitly promote a fact to deterministic
gameplay.

------------------------------------------------------------------------

# 40. RUNTIME COMPATIBILITY CHECKLIST

Before a scenario is considered runtime-ready:

## Structure

-   [ ] `manifest.json` exists.
-   [ ] `world.json` exists.
-   [ ] manifest contains required scenario identity/version fields.
-   [ ] chapter pack sequences are valid.
-   [ ] chapter ranges are contiguous and non-overlapping.
-   [ ] pack IDs are unique.

## Canonical data

-   [ ] Every canonical record has a stable ID.
-   [ ] JSON objects use matching key and embedded `id`.
-   [ ] Supported category names are used.
-   [ ] Cross-references resolve.
-   [ ] No duplicate entities exist.

## NPCs

-   [ ] NPC runtime bootstrap is valid.
-   [ ] Presence uses runtime-compatible fields.
-   [ ] Schedules use supported schema.
-   [ ] Goals use supported goal kinds.
-   [ ] Encounter conditions use supported condition types.
-   [ ] No arbitrary gates were invented.

## Knowledge

-   [ ] `known_by` is explicit where necessary.
-   [ ] visibility is explicit.
-   [ ] future information is protected.
-   [ ] system-only facts are not player-facing.

## Timeline

-   [ ] chapter metadata is not confused with runtime turns.
-   [ ] exact dates are not fabricated.
-   [ ] historical changes are preserved.

## Documentation

-   [ ] chapter Markdown is inside a declared chapter pack.
-   [ ] lore Markdown is separated from runtime JSON.
-   [ ] provenance and unresolved ambiguity are documented.

## Final validation

-   [ ] engine scenario validator passes.
-   [ ] scenario can be loaded.
-   [ ] ScenarioRegistry can be constructed.
-   [ ] ScenarioRetriever can index it.
-   [ ] ChapterManager accepts chapter selection.
-   [ ] NPC presence/encounter data passes validation.
-   [ ] no player-runtime state is written into canon.

------------------------------------------------------------------------

# 41. RESEARCH AI OUTPUT CONTRACT

When asked:

> Create Martial Peak chapters 1--400.

the research AI must NOT return a generic summary.

It must produce an authoring package containing, as applicable:

``` text
manifest / project metadata
global entity registry
characters
locations
factions
items
techniques
realms
creatures
events
relationships
timeline
knowledge
chapter extraction records
chapter changesets
presence changes
encounter conditions
NPC schedules/goals
quest/event facts
provenance
confidence
ambiguity/conflict records
human-readable Markdown
```

Then the package must be transformed into the current runtime scenario
format.

If the source does not establish a field, use:

``` text
null
[]
unknown
not_established
```

as appropriate.

Never fabricate.

------------------------------------------------------------------------

# 42. MASTER RESEARCH PROMPT

Use the following prompt when giving this specification and source
material to another AI:

> You are the scenario-data extraction and research agent for a
> deterministic RPG Engine.
>
> Your task is NOT to write a generic story summary.
>
> Your task is to convert the supplied source material into structured
> scenario authoring data that can later be compiled into the RPG
> Engine's runtime scenario format.
>
> Follow the RPG ENGINE --- SCENARIO / CHAPTER DATA CREATION MASTER
> SPECIFICATION v3.0 exactly.
>
> The deterministic engine is authoritative over runtime state.
>
> Your responsibilities are to extract and structure canon facts, not to
> invent gameplay outcomes.
>
> You must:
>
> 1.  Create stable IDs for persistent entities.
> 2.  Maintain the same IDs across chapter packs.
> 3.  Extract characters.
> 4.  Extract first/last canonical appearance.
> 5.  Extract physical NPC presence.
> 6.  Extract NPC schedules only when supported.
> 7.  Extract NPC goals only when supported.
> 8.  Extract encounter/access conditions only when explicitly
>     supported.
> 9.  Extract locations.
> 10. Extract factions.
> 11. Extract items.
> 12. Extract techniques.
> 13. Extract realms.
> 14. Extract creatures.
> 15. Extract events.
> 16. Extract relationships.
> 17. Extract timeline information.
> 18. Extract knowledge and knowledge visibility.
> 19. Protect future information.
> 20. Extract secrets and rumors when supported.
> 21. Extract quest/event facts when supported.
> 22. Produce per-chapter changesets in the authoring layer.
> 23. Preserve provenance and confidence.
> 24. Record unresolved conflicts instead of silently choosing.
> 25. Produce human-readable research Markdown.
>
> CRITICAL RULES:
>
> -   Chapter number is canon-source chronology, NOT automatically a
>     runtime turn.
> -   First appearance is NOT automatically an encounter restriction.
> -   Alternate timelines are allowed.
> -   Do not invent encounter requirements.
> -   Do not invent dates.
> -   Do not invent powers.
> -   Do not invent relationships.
> -   Do not invent schedules or goals.
> -   Do not invent quests.
> -   Do not leak future information into earlier knowledge.
> -   Do not duplicate entities across chapter packs.
> -   Preserve stable IDs.
> -   Preserve historical state transitions.
> -   Never write player-runtime changes into canonical data.
> -   Do not create a parallel gameplay engine.
> -   Do not claim authoring JSON is runtime-supported unless the
>     current engine actually loads it.
> -   Do not copy long copyrighted dialogue; describe speech style
>     instead.
> -   If information is unknown, explicitly say so.
>
> Before final output:
>
> 1.  Validate IDs.
> 2.  Validate references.
> 3.  Validate chapter ranges.
> 4.  Validate timeline ordering.
> 5.  Validate knowledge visibility.
> 6.  Validate NPC presence.
> 7.  Validate encounter conditions.
> 8.  Validate schedules/goals.
> 9.  Detect duplicates.
> 10. Report unresolved ambiguities.
>
> Produce the complete authoring data required to compile the supplied
> material into a valid RPG Engine scenario pack.

------------------------------------------------------------------------

# 43. SCENARIO PACK INSTALLATION CONTRACT

A final scenario distributed to the player must be a single installable
package:

``` text
ScenarioName.rpgscenario.zip
```

The player-facing application should be able to:

``` text
Import Scenario
      ↓
Validate
      ↓
Register Scenario
      ↓
Select Chapter Pack(s)
      ↓
Create GameSession
      ↓
Play
```

The player should not need:

-   Termux;
-   Python;
-   a separate server;
-   a separate scenario-processing application;
-   manual JSON editing.

The scenario pack is content, not a second game engine.

------------------------------------------------------------------------

# 44. RELATIONSHIP TO THE RPG ENGINE

The scenario generator is designed around the current architecture:

``` text
ScenarioRegistry
      ↓
ChapterManager
      ↓
ScenarioConfiguration
      ↓
ScenarioRetriever
      ↓
NPC Presence / Encounter / Goals / Schedule
      ↓
ScenarioContext
      ↓
AI Context
      ↓
AI proposes
      ↓
Validation
      ↓
GameState
```

The scenario generator must remain compatible with:

-   Scenario Registry
-   Chapter Manager
-   Scenario Configuration
-   Scenario Retrieval
-   NPC Presence
-   NPC Encounter
-   NPC Goals
-   NPC Schedule
-   Memory / knowledge visibility
-   deterministic validation
-   quest/event state
-   persistence

It must NOT create a parallel runtime architecture.

------------------------------------------------------------------------

# 45. FUTURE EXTENSIONS

The format should remain extensible for:

-   richer chapter runtime records;
-   dialogue trees;
-   advanced schedules;
-   autonomous NPC behavior;
-   dynamic factions;
-   economy;
-   weather;
-   travel time;
-   world simulation;
-   semantic retrieval;
-   embeddings;
-   multilingual source packs;
-   alternate scenario branches;
-   dedicated scenario compiler;
-   scenario editor;
-   visual scenario authoring tools.

These must be additive and backward-compatible where possible.

------------------------------------------------------------------------

# 46. PRACTICAL EXAMPLE

Suppose the source says:

> The protagonist arrives at City X. A merchant is staying at the
> eastern inn. The merchant only meets trusted customers. The
> protagonist previously gained the merchant's trust.

The authoring extraction should preserve:

``` json
{
  "id": "char_merchant_x",
  "presence": [
    {
      "location_id": "loc_eastern_inn",
      "confidence": "confirmed",
      "source": {
        "type": "chapter",
        "chapter": 120
      }
    }
  ],
  "encounter_conditions": [
    {
      "type": "relationship_trust",
      "target": "char_merchant_x",
      "operator": ">=",
      "value": 50
    }
  ]
}
```

The exact runtime `from_turn`/`to_turn` mapping must only be generated
if the scenario defines a valid mapping.

The player can then:

``` text
travel → City X
travel → Eastern Inn
talk → Merchant
```

and the engine evaluates the encounter conditions.

The AI does not need to rediscover the merchant's location or invent the
requirement.

------------------------------------------------------------------------

# 47. FINAL ACCEPTANCE CRITERIA

A chapter pack is complete only if:

-   another AI does not need to reread the chapter during normal
    gameplay to rediscover basic structured facts;
-   NPC canonical appearance information is encoded;
-   NPC physical presence is encoded where supported;
-   NPC movement/schedule/goal information is encoded where supported;
-   encounter/access conditions are encoded where supported;
-   characters, locations, factions, items, techniques, creatures and
    events are linked by stable IDs;
-   timeline information exists;
-   knowledge boundaries exist;
-   future information is protected;
-   relationships are time-aware where required;
-   chapter changes are explicit in the authoring layer;
-   provenance/confidence exists;
-   JSON is authoritative for machine data;
-   Markdown is explanatory;
-   the final runtime ZIP matches the actual engine schema;
-   validation passes;
-   no player-runtime state is written into canon;
-   no unsupported gameplay rule has been invented.

------------------------------------------------------------------------

# 48. FINAL PRINCIPLE

The scenario data generator's job is:

> **Extract canon once, structure it correctly, preserve
> who/where/when/who-knows-what information, and compile it into data
> the engine can actually consume.**

The runtime AI's job is:

> **Use the already-structured information to narrate and propose
> actions.**

The deterministic engine's job is:

> **Decide what is actually true.**

The scenario system must preserve this separation.
