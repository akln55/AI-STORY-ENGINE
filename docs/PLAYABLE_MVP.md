# Playable MVP — v1.12

## Goal

The first real end-to-end playable slice is now defined as:

```text
Android APK
  -> start demo scenario
  -> look / status / inventory / movement / combat commands
  -> free-form player action
  -> bounded Gemini structured response (optional)
  -> engine validation
  -> narrative result
  -> save/load
```

## AI boundary

The Gemini adapter receives only the bounded context assembled by the engine.
It has no tools, filesystem API, database handle, scenario write access, code
execution, or process control. One player action owns one AI transaction; a
malformed JSON response may receive one format retry, while provider/network
errors are not retried by the engine.

## Provider

Gemini is an optional remote provider. The API key is entered at runtime and is
not bundled into the APK or repository. The adapter uses the Gemini REST
`generateContent` endpoint with structured JSON output. No Gemini SDK is
required, preserving the stdlib-first Android dependency policy.

## UI

The Android shell now contains:

- scrollable narrative log
- action input
- send button
- save/load controls
- Gemini provider setup
- non-blocking provider calls

The UI is intentionally thin: it delegates all gameplay to `GameSession`.

## Current limitation

This is the first playable vertical slice, not the final product UI. Scenario
import/selection, model manager, richer Android settings, chapter selection,
local llama.cpp Android runtime, and polished dialogue UI remain later phases.
