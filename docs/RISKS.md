# RPG Engine — Technical Risks

Version 1.0 · Phase 0 · 2026-09-23

| ID | Risk | Impact | Mitigation |
|----|------|--------|------------|
| R1 | **Buildozer packaging friction** — Python-for-Android builds are notoriously environment-sensitive | Phase 10 blocked or painful | Keep engine stdlib-first (few recipes); test APK early (Phase 7 exit, not Phase 10 discovery); fallback: cloud/desktop build environment; no Termux requirement for users |
| R2 | **Local LLM limits on phone** — RAM/CPU constrain model size; quality may disappoint | Narration quality low or unusable on-device | Adapter pattern (TECH_STACK.md) lets a remote OpenAI-compatible backend substitute; model size budget documented before Phase 3 ends |
| R3 | **Cloud build dependency** — Android APK builds require a Linux build environment and Android SDK/NDK tooling | Slower iteration if the build environment is unavailable | Keep a reproducible Colab build notebook; keep engine tests independent of Android tooling |
| R4 | **Context assembly quality** — poor retrieval causes AI inconsistency despite good architecture | Long-session quality failure | Benchmark harness in Phase 4/9 (Turn-1000 test); budgets fail loudly in dev; multiple retrieval modes evaluated |
| R5 | **Validation complexity creep** — the AI proposes diverse state changes; the validator grows into a mess | Engine fragility | Schema-first proposals (DATA_MODELS.md §3), typed operations, per-operation validators, rejection logging; MVP keeps change types minimal |
| R6 | **Save format churn** — evolving schema breaks old saves | Lost user progress | Versioned saves (Phase 8 contract); migrations are explicit, tested, ADR'd |
| R7 | **Semantic embeddings without paid APIs** — local embedding quality/speed on phone uncertain | Phase 4 retrieval weaker | FTS5 keyword/trigger + state-based retrieval first; embeddings are an additive layer, not a dependency |
| R8 | **Scenario pack format under-specified** — packs become engine-specific accidents | Engine no longer reusable | Pack format v1 frozen only at Phase 5 exit; validator tool enforces schema; second demo pack proves reusability |
| R9 | **AI schema reliability** — models return malformed JSON / hallucinated fields | Crashes or bad state | Strict parsing, retry-with-feedback loop (bounded), fake adapter for deterministic tests, never trust free text |
| R10 | **Scope creep** — RPG feature enthusiasm outpaces the plan | Never-shipping engine | Constitution §4 scope boundaries; ROADMAP exit criteria gate every phase |

Watch list (re-evaluated at each phase exit): R1, R2, R4.
