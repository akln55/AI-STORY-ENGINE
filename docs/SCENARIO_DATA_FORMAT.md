# Scenario Data File Contract

The canonical scenario authoring/distribution format is:

- **JSON** = machine-readable authoritative scenario data.
- **Markdown (.md)** = human-readable research, lore, summaries and source notes.
- **ZIP (.rpgscenario.zip)** = installable distribution package containing both.
- **TXT is not an authoritative format**; it may be used as temporary research input only.

Recommended structure:
```text
ScenarioName/
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
    0001-0400/
      chapter_manifest.json
      overview.md
      timeline.md
      events.md
      characters.md
      locations.md
      knowledge.md
  lore/
    *.md
```

For the application the user imports the final `.rpgscenario.zip`; the app validates it, installs it into app-private scenario storage, and treats the scenario data as read-only during gameplay.


## Canonical JSON record contract

Each canonical `data/*.json` file is an object keyed by stable record ID:

```json
{
  "hero": {
    "id": "hero",
    "name": "Example Character"
  }
}
```

Rules:

1. The filename must be one of the eleven canonical data files listed above.
2. Every non-empty record must contain a non-empty `id`.
3. The object key and embedded `id` must be identical.
4. IDs are stable identifiers; display names are not identifiers.
5. Records are loaded into an immutable `ScenarioRegistry`; they do not become mutable
   `GameState` merely because they exist in the scenario package.
6. A record may optionally contain an explicit `references` object for cross-document
   validation:

```json
{
  "hero": {
    "id": "hero",
    "references": {
      "locations": ["village"],
      "factions": ["wanderers"]
    }
  }
}
```

Reference category names must be canonical categories and every referenced ID must
exist in that category. The engine intentionally does not guess arbitrary references
from field names; explicit references make generated scenario data deterministic and
validator-friendly.

## Deterministic retrieval contract (v1)

The scenario loader indexes Markdown source documents into immutable `ScenarioDocument`
records. Chapter Markdown is scoped to its declared chapter pack. Global `lore/*.md`
files are not returned by chapter-scoped retrieval unless the caller explicitly opts in;
this prevents a global lore file from becoming an accidental future-knowledge channel.

`ScenarioRetriever` provides deterministic lexical retrieval over canonical JSON records
and Markdown. It supports category, record ID, chapter, pack, kind and viewer filters.
Canonical records may use `first_appearance`, `first_chapter`, `available_from_chapter`,
`known_from_chapter`, `last_appearance`, or `last_chapter` to constrain chapter visibility.
Knowledge records may additionally use `visibility` (`public`, `system`, `secret`) and
`known_by` to constrain who may receive the record. These are retrieval guards, not a
replacement for runtime GameState authority.

The retrieval layer is intentionally non-semantic in this phase: no embeddings, network
service, AI call, randomness, or vector database is required. A later semantic retriever
may augment this deterministic layer without bypassing chapter/visibility checks.


## Context integration
ScenarioRegistry/ScenarioRetriever data is optional context material for the AI layer.
It never mutates GameState and never overrides deterministic encounter/rule validation.
Chapter-scoped Markdown is bounded and global lore is excluded by default.
