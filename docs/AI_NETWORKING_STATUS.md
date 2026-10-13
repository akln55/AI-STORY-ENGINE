# AI Networking Status — 2026-10-13

**Scope:** AI/network connectivity only. Android APK builds and scenario testing are deferred by the current task scope.

## Current implementation

- Android build configuration declares `INTERNET` and `ACCESS_NETWORK_STATE` permissions in `buildozer.spec`.
- `engine/ai/https_transport.py` centralizes outbound transport for the Gemini adapter, OpenAI-compatible adapter, and API model-list connectivity probe.
- HTTPS uses a verified SSL context, preferring `certifi` roots when available. Hostname and certificate verification remain enabled; there is no insecure TLS fallback.
- Localhost HTTP remains allowed for the local llama.cpp server.
- `engine/ai/connectivity.py` probes the provider's model-list endpoint. This is intentionally a low-cost connection/auth check, not proof that the selected model can generate a valid RPG response.
- The AI settings screen adds “Gerçek AI yanıtını test et”, which calls the currently configured adapter's actual `generate` method and reports a sanitized success/failure status.
- The generation test is an actual provider request and may consume a small amount of API usage.

## Evidence

- Last fully green source baseline for the shared HTTPS change: [GitHub Actions run 38345698305](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38345698305). It passed 538 tests, Python compileall, Android readiness, and mutation smoke 3/3.
- The generation-test UI change then exposed one stale test assertion expecting the former AI settings panel height `dp(512)` after the panel was expanded to `dp(562)`. Run [38351205793](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38351205793) failed with 1 failed and 537 passed. The assertion was updated in commit `145d3b13dc6107b893909f32ff4743082697b11a`.
- Latest source verification after that change and the documentation updates: [run 38439396555](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38439396555). Check its final conclusion before claiming the current tree is green.

## What is not proven

- The current installed APK contains these source changes.
- The app can resolve DNS, complete TLS, and reach the selected provider over the user's Istanbul mobile-data connection.
- The API key has valid permissions/quota or that the selected model accepts the engine's structured-response request.
- Real AI generation succeeds on the physical Redmi Note 12 Pro 4G.
- Local GGUF inference works on-device.

Source-level CI can test logic and contracts but cannot prove device/carrier/provider behavior. Presence of Android INTERNET permission is necessary but not sufficient.

## Next steps

1. Confirm the latest source CI result and fix any first failing test before further changes.
2. Continue the investigation in the AI/network boundary: distinguish DNS/connectivity/TLS/HTTP authentication/model/request failures, keeping timeouts bounded and credentials/provider response bodies out of logs.
3. Do not start an Android APK build or switch to scenario work unless the user changes the scope. Device-side proof requires a later run of an updated app, but no build is requested at this stage.
