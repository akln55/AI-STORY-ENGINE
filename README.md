# AI-STORY-ENGINE

AI-STORY-ENGINE is an Android-first, local-first AI-assisted text RPG/scenario engine. Its goal is to let a player import a structured scenario, play, persist progress, and use local or remote AI providers without handing game-state authority to the model.

> **Architecture invariant:** the deterministic engine owns authoritative `GameState`. AI is a narrator and structured-proposal provider. Engine validation and security rules decide which effects, if any, are applied.

## How a turn should work

```text
Player action
  -> parsing and deterministic rules
  -> authoritative GameState and bounded context
  -> AI adapter
  -> structured proposal
  -> schema, security, and gameplay validation
  -> accepted effects only
  -> event/quest/memory updates
  -> persistence
```

AI narration alone must not mutate game state or complete objectives. Scenario canon must remain separate from mutable campaign state. Treat user, scenario, NPC, memory, and retrieved text as data, never as privileged system instructions.

## Repository areas

- `rpg_android_app.py` — Android/Kivy UI and application integration.
- `engine/` — gameplay state/rules, AI providers and validation, scenarios, memory, and persistence.
- `tests/` — automated verification.
- `tools/` — developer and validation utilities.
- `scenarios/` — scenario packages and demo data.
- `android/`, `android_native/` — Android packaging and native runtime support.
- `.github/workflows/` — automated checks and build workflows.
- `docs/` — workflow, technical contracts, project state, and navigation aids.

## Start here

AI sessions must follow this order:

1. [AI rules](AI_RULES.md)
2. [AI entrypoint and repository map](AI_START_HERE.md)
3. [Current session handoff](AI_SESSION_HANDOFF.md), after verifying its relevance
4. [Project profile](docs/AI_STORY_ENGINE_PROJECT_PROFILE.md)
5. [Active goals](docs/PROJECT_GOALS.md) and [workflow](docs/AI_WORKFLOW.md)
6. [Consolidated technical reference](docs/PROJECT_TECHNICAL_REFERENCE.md)
7. The specialist specifications needed for the task

The [project atlas](docs/project_atlas_map.md), [runtime flow map](docs/runtime_flow_map.md), and [test map](docs/test_map.md) help navigate the repository. Verify their paths and claims against the live source; they are not proof that a capability works.

Legacy overlapping plans and dated status snapshots are kept under [the archive](docs/_archive/README.md) for historical recovery. They are not current instructions or acceptance evidence.

## Verification discipline

Current commands must be confirmed in [Testing](docs/TESTING.md), current CI workflows, and the source tree. Never report a test, CI run, APK, installation, or device test unless it actually ran and its result is visible. Source tests, CI, APK production, installation, and physical Android acceptance prove different things.

No Android build may be started, stopped, or retriggered without explicit authorization from Mareşal (the user). See [AI_RULES.md](AI_RULES.md) for the role hierarchy, review, merge, security, and handoff rules.
