# NPC Simulation Specification — v1.24.0

## Scope

The deterministic NPC simulation owns physical movement, scenario-authored goal execution, and bounded NPC-to-NPC knowledge propagation. AI can consume the resulting behavior context but cannot execute goals or bypass validation.

## Goal kinds

- `passive`: legacy/context-only goal; no autonomous execution.
- `move_to`: move to `target_location`; completes on arrival.
- `follow_npc`: move toward the current location of `target_id`.
- `meet_npc`: move toward `target_id`; completes when co-located.
- `patrol`: cycle through `data.locations`, advancing deterministic progress.
- `survive`: deterministic progress-only goal for authored survival objectives.

Goals are selected by descending priority, then stable goal ID. One goal is selected per NPC per simulation turn.

## Authority

Goal execution produces ordinary `Effect` objects and calls the shared validation gate. Scenario data defines goals; runtime `NPCGoal` state owns progress/status. Invalid references are rejected by scenario validation and state invariants.

## Relationship reactions

`NPCReactionEngine` translates explicit interaction outcomes into bounded relationship effects. Current deterministic outcomes are `talk`, `help`, and `harm`. Dialogue uses `talk`; AI cannot directly invoke the reaction engine.

## Knowledge propagation

Co-located NPCs may exchange `knowledge` records when their relationship trust is at least 50. `secret`-tagged records are excluded. Transfers are deduplicated by the memory system and marked `propagated`.

## Determinism

NPC iteration is sorted by stable NPC ID. Goal selection is sorted by priority and stable goal ID. A 1,000-turn two-run deterministic regression is part of the engine test gate.
