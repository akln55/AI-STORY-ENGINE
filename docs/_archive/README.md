# Legacy Documentation Archive

**Archived on:** 2026-10-16  
**Purpose:** Keep older overlapping plans, duplicate handoffs, dated audits, and retired policy documents available for historical recovery without allowing them to compete with the current project instructions.

## Authority rules

1. Read `AI_RULES.md` first and use the canonical documents listed in `AI_START_HERE.md`.
2. The documents in `legacy-2026-10-16/` are historical material, not current instructions, roadmaps, status, test proof, or technical authority.
3. **Komutan owns archive triage.** Komutan may consult an archived document when a historical question or missing decision requires it, then must validate any useful claim against current source/config/tests/CI. Komutan should not send Asker or Denetçi to the archive by default.
4. Asker and Denetçi must not treat archived content as current requirements. They may consult a specific archived record only if Komutan explicitly assigns a historical investigation and explains its bounded scope.
5. If an archived decision is still needed, transfer the verified decision—not the stale document—into the correct active canonical document and cite the historical source. Do not silently revive stale plans.
6. Never add secrets, user data, private model files, saves, or build artifacts to this archive.

## Why these files were archived

| Archived file | Reason |
|---|---|
| `HANDOFF.md` | Duplicate and dated session handoff; canonical start guidance now lives in `AI_START_HERE.md` and `AI_SESSION_HANDOFF.md`. |
| `MEMORY.md` | Mixed long-running notes and stale task status; current rules/goals/log/profile have separate roles. Preserved intact for historical retrieval. |
| `AI_EXECUTION_POLICY.md` | Overlaps the binding `AI_RULES.md` and `docs/AI_WORKFLOW.md`. |
| `CONSTITUTION.md` | Contains old architecture/scope decisions that may conflict with the current hybrid-provider direction; preserved pending any explicit reconciliation. |
| `DEVELOPMENT_PLAN.md` | Large historical master plan with stale completion states and duplicated tasks; preserved intact. |
| `ENGINE_COMPLETION.md` | Versioned completion/status snapshot; not a reliable current-state source. |
| `GITHUB_TRANSFER_PLAN.md` | One-time migration plan rather than ongoing operating guidance. |
| `PLAYABLE_MVP.md`, `PROTOTYPE_MVP.md` | Older, overlapping MVP plans whose current status is not authoritative. |
| `PROJECT_STATUS_AUDIT_v1.28.3.md` | Version-specific status snapshot; source and recent evidence take precedence. |
| `RISKS.md` | Dated/general risk register moved aside until its risks can be revalidated and reconciled with active goals. |
| `TECH_STACK.md` | Overlaps the consolidated `docs/PROJECT_TECHNICAL_REFERENCE.md`; retain only as historical detail. |
| `TEST_SYSTEM_AUDIT_2026-10-12.md` | Dated test audit; individual findings must be rechecked against current tests and CI. |
| `UI_AND_AI_RUNTIME_v1.28.0.md` | Versioned implementation notes superseded by current source and focused Android/runtime specifications. |
| `V2_MASTER_PLAN.md` | Competing roadmap; the single active priority list is `docs/PROJECT_GOALS.md`. |

## Access-control limitation

This is a public Git repository. GitHub does not provide private-folder permissions within a public repository, so no literal “Komutan-only” lock exists here. The restriction above is an AI workflow rule and a source-of-truth boundary, **not technical secrecy**. Do not place anything confidential in this directory.
