# NPC Behavior Context Specification

## Authority
The engine owns NPC state and decides whether an NPC can interact. AI may propose dialogue or actions but cannot execute them or bypass encounter gates.

## Inputs
- alive/dead state
- physical location
- scenario encounter conditions
- disposition
- personality
- active goals
- fears
- preferences
- player relationship
- NPC-scoped scenario knowledge
- NPC-scoped persistent memory

## Output
`NPCBehaviorContext` contains deterministic, read-only behavior boundaries including `can_interact` and `allowed_action_types`.

## Action categories
The current foundation exposes only broad categories: `observe`, `talk`, `trade`, `assist`, `flee`, and `attack`. These are not direct commands and do not mutate state. Future action-specific validators must independently validate every proposed effect.

## Encounter separation
Canonical first appearance is not an automatic encounter restriction. Physical presence and explicit access/encounter conditions determine whether the NPC can be interacted with.

## Knowledge isolation
NPC context uses `viewer=npc:<id>` for scenario knowledge and memory retrieval. System-only and other-NPC-private information must not cross that boundary.


## v1.24.0 execution boundary

Behavior context is now backed by an executable deterministic NPC layer. Active goals are no longer merely prompt signals when they use a supported goal kind; `NPCSimulationEngine` executes them before player action resolution. AI remains a proposal/narration layer and cannot create or execute goals.
