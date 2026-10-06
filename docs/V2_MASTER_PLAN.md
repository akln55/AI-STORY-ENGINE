
# CURRENT EXECUTION OVERRIDE — 2026-10-05

The v2.0 definition of done below remains the product authority. The implementation is currently **between engine-completion and Android-product verification**, not at the final v2.0 state.

Current evidence:
- 435 automated tests pass; compile, mutation, scenario, and Android-readiness checks pass.
- Real Android APK build/device verification is still open.
- Gate F local-AI product work is incomplete: model downloader/catalog, model lifecycle management, Android-native llama.cpp runtime, and device inference QA remain open.
- GitHub migration and reproducible CI are not complete.

Therefore do not advance the version to a release-complete state based only on module/unit-test presence. The next execution order is: **secure GitHub normalization -> test CI -> Android CI -> real-device QA -> local-AI Android runtime -> remaining v2 gameplay/social/scenario gates**.

# RPG Engine — v2.0 Master Development Plan

**Status:** Canonical execution plan updated at v1.24.0
**Target:** v2.0.0 = fully playable Android RPG campaign, not a prototype
**Rule:** Implement in the order below. Do not skip foundational gates for cosmetic or secondary features.

## 1. v2.0 definition of done

v2.0 is released only when a clean Android APK can:

1. install without Termux/Python;
2. create/select a campaign from an installed scenario;
3. load a real multi-chapter scenario;
4. create a player and enter the world;
5. move, inspect, collect/use items, fight, use techniques and progress;
6. meet and talk to NPCs through the configured AI provider;
7. make dialogue produce validated relationship/memory/quest consequences;
8. accept, progress, complete, fail and reward quests, including chains/branches;
9. persist NPC, relationship, quest, event, memory and progression state;
10. advance scenario chapters/events without losing canon or runtime state;
11. survive malformed AI output/provider failure without corrupting the campaign;
12. save, load, autosave, recover and manage multiple campaigns;
13. run a bounded living-world simulation where NPC/faction/world changes have persistent consequences;
14. complete a documented end-to-end campaign QA run on a real Android device.

A feature is not `complete` merely because a module or unit test exists. The real application path, persistence path, security boundary and product target must be verified.

## 2. Release/version policy

- `1.19.x`: small, compatible improvements, hardening, bug fixes and narrow feature slices.
- `1.20.x`, `1.21.x`, etc.: larger subsystem milestones when a coherent phase is completed.
- `2.0.0`: only after every v2.0 definition-of-done gate passes.
- Patch releases must update code version, README/checkpoint/roadmap/handoff and test baseline together.
- Never inflate the major version merely because a feature was added.
- Never leave implementation state only in chat; canonical docs travel with every handoff ZIP.

## 3. Execution gates

### Gate A — Campaign integrity

**Purpose:** make long-running campaigns safe before adding complexity.

Deliverables:
- atomic save writes;
- backup/recovery path;
- multiple save slots in the engine;
- save metadata and campaign identity;
- scenario version binding and compatibility errors;
- persistence round-trip coverage for all authoritative systems;
- long-session corruption/recovery tests.

Exit criteria: a deliberately corrupted primary save cannot silently destroy a campaign and a valid recovery copy can be restored.

### Gate B — Playable gameplay core

**Purpose:** complete the actual player loop.

Deliverables:
- deterministic inventory/use semantics;
- currency/economy foundation;
- complete progression transaction;
- advanced combat state: statuses, buffs/debuffs, battle actions and multi-target support where scenario rules require them;
- NPC combat behavior;
- deterministic death/defeat consequences;
- quest chains, branching prerequisites and reward transactions;
- hidden objectives and failure/deadline handling;
- dialogue → quest/relationship/memory/event consequences.

Exit criteria: a scenario can contain a meaningful quest/combat/progression loop with persistent consequences without relying on narrative text to fake state.

### Gate C — Social world

**Purpose:** make NPCs and factions actual simulation participants.

Deliverables:
- NPC goals and deterministic goal execution;
- reactions to player/world changes;
- NPC↔NPC relationship evolution;
- faction reputation/access/hostility/alliance rules;
- faction goals and events;
- information and rumor propagation with visibility boundaries;
- persistent consequences of player actions.

Exit criteria: an action in turn N can cause an observable, rule-backed social/world consequence in later turns.

### Gate D — Scenario/canon engine

**Purpose:** make large fictional worlds playable without canon drift.

Deliverables:
- chapter/arc progression fully bound to runtime;
- chapter and arc summaries injected into context;
- canonical timeline enforcement;
- character presence/appearance windows;
- encounter conditions and power/access constraints;
- structured story progression;
- research-source records and cross-reference validation;
- large scenario benchmarks and lazy/indexed retrieval.

Exit criteria: a multi-chapter scenario can progress through its canonical structure while alternate player actions affect runtime state without corrupting immutable canon.

### Gate E — AI/context reliability

**Purpose:** make AI useful at long-session scale without granting authority.

Deliverables:
- relevance-ranked scenario/memory retrieval;
- bounded token budgeting;
- chapter/arc summary strategy;
- contradiction detection/resolution policy;
- long-session memory compaction;
- malformed-output stress tests;
- provider timeout/retry/fallback behavior;
- local llama.cpp adapter hardening.

Exit criteria: long sessions retain important facts and visibility boundaries while context size remains bounded and AI failure never mutates invalid state.

### Gate F — Android product

**Purpose:** turn the engine into the actual product.

Deliverables:
- real SAF-based scenario import;
- scenario manager UI;
- chapter/campaign setup UI;
- save-slot/campaign manager UI;
- settings and provider selection;
- local GGUF model manager;
- model validation/storage management;
- Android-native llama.cpp runtime integration;
- loading/error/offline UX;
- lifecycle/autosave verification on device.

Exit criteria: a user can install the APK and perform the complete v2 campaign flow without a terminal.

### Gate G — Release QA

Required evidence:
- clean source extraction test;
- compile test;
- full deterministic test suite;
- random-action/fuzz tests;
- 200+ turn campaign;
- 1000+ turn stress run;
- large-scenario benchmark;
- save corruption/recovery test;
- AI malformed-response/provider failure test;
- Android install/import/play/save/load/autosave test;
- final end-to-end campaign on a real device.

## 4. Planned release train

| Release | Primary objective |
|---|---|
| v1.19.1 | Campaign integrity: atomic saves + backup/recovery foundation |
| v1.19.2 | Multiple save slots + campaign metadata |
| v1.19.3 | Full persistence audit across quests/events/memory/NPC/social state |
| v1.21.1 | Gameplay Core: hostile NPC retaliation and combat-loop foundation |
| v1.21.1 | Playable Gameplay Core milestone |
| v1.20.x | Dialogue/quest/combat/progression completion and hardening |
| v1.21.1 | Social World milestone |
| v1.21.x | NPC goals, factions, rumors, reactions and consequence propagation |
| v1.24.0 | Scenario/Canon milestone |
| v1.22.x | Chapter/arc/timeline/presence/large-scenario hardening |
| v1.24.0 | AI/Context milestone |
| v1.23.x | Long-session retrieval, budgeting, local AI hardening |
| v1.24.0 | Android Product milestone |
| v1.24.x | SAF, model manager, native llama.cpp, settings and UX hardening |
| v1.25.0 | Release Candidate |
| v1.25.x | Full QA, device fixes and campaign stress remediation |
| v2.0.0 | Fully playable release |

The release train is a guide, not permission to ship incomplete gates. A phase can move forward only when its exit criteria are actually verified.

## 5. Current priority

The project is currently at **v1.24.0**. Gate A long-session persistence/recovery verification is complete for the deterministic test scope. Gate B Gameplay Core is active, starting with authoritative combat consequences.

The immediate order is:

1. Gate B combat consequences and defeat lifecycle;
2. status/effect system and combat action foundation;
3. progression transactions and level-up persistence;
4. quest lifecycle: chains, deadlines, branching prerequisites, reward/failure transactions;
5. dialogue -> quest/relationship/memory/event consequence integration;
6. item use/economy foundation;
7. Gate B end-to-end gameplay stress and vertical-slice verification.

## 6. Architectural constraints during execution

- No rewrite of the existing engine merely to introduce a new architecture.
- GameState remains authoritative.
- AI remains an untrusted proposer/narrator.
- All state mutation continues through validated engine paths.
- Scenario canon remains immutable during gameplay.
- New simulation systems must be deterministic where they own authoritative state.
- Android remains a first-class product target; Termux is never promoted to an end-user dependency.
- New subsystems require integration tests at the real application boundary.
- Every release updates the canonical handoff documents and produces a clean handoff-ready ZIP.

## 7. What is deliberately not the priority yet

- cosmetic UI redesign;
- advanced autonomous NPC behavior before campaign persistence is hardened;
- semantic retrieval before large-scenario benchmarks justify it;
- a wholesale relational-persistence rewrite before measured need;
- feature accumulation that does not move the project toward the v2.0 definition of done.


## v1.21.1 — Quest lifecycle milestone

- Added authoritative quest lifecycle timestamps and hidden-quest metadata.
- Added deterministic quest deadlines and failure transitions.
- Added completion/failure quest-chain unlocks with prerequisite checks.
- Quest rewards are now transactional: invalid reward batches roll back completion and claim state.
- Quest state round-trips through persistence.
- Demo Bootstrap now contains a two-step quest chain: Forest Supplies -> Drive Off the Wolf.
- Verified baseline: 380 tests passed; compile and scenario validation pass.


## Engine Completion — active gate

The priority is now to finish the reusable engine before expanding living-world or Android product features. The engine-completion sequence is:

1. authoritative state/effect contracts;
2. validation and atomic mutation boundaries;
3. turn lifecycle and temporary state;
4. persistence and recovery compatibility;
5. scenario runtime composition;
6. quest/event/progression transaction integrity;
7. combat primitives;
8. AI adapter/context contract;
9. deterministic long-session stress;
10. engine API/documentation freeze.

### v1.21.1 — Temporary State / Status Effects

Completed: player/NPC status-effect state, validation-gated stacking/removal/ticking, deterministic resource effects, action-blocking effects, persistence, AI context exposure, and regression coverage.


## v1.21.1 — Engine composition contract

Engine Completion work now includes a bundled scenario composition contract. The runtime pack, retriever, and chapter configuration are validated as one immutable context before a session starts.

