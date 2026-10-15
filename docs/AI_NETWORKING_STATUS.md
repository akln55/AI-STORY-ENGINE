# AI Networking and Stage 1 Status — 2026-10-13

> **Dikkat — güncellik doğrulaması gerekli:** Bu dosya, önceki bir geliştirme oturumu tamamlanmadan durdurulduğu için güncel olmayan veya kısmen yanlış bilgiler içerebilir. İçindeki durum ve mimari iddialarını güncel gerçek kabul etme. Bir işe başlamadan önce ilgili kaynak kodu, testleri, güncel `main` HEAD'ini ve en son CI sonuçlarını doğrula. Çelişki bulursan bunu sessizce varsayımla düzeltme; gerçek durumu belirt. Her çalışma sonunda bu dosyayı ve etkilenen tüm bilgi içeren `.md` dosyalarını güncelle. Kanıt yoksa bir işi tamamlandı işaretleme.


**Scope:** Source-level AI/network reliability and mobile UX/download recovery. APK build, physical-device validation, and scenario testing remain deferred.

## Implemented

- Android build configuration declares `INTERNET` and `ACCESS_NETWORK_STATE` permissions in `buildozer.spec`.
- `engine/ai/https_transport.py` centralizes outbound transport for the Gemini adapter, OpenAI-compatible adapter, and API model-list connectivity probe.
- HTTPS uses a verified SSL context, preferring `certifi` roots when available. Hostname and certificate verification remain enabled; there is no insecure TLS fallback.
- Localhost HTTP remains allowed for the local llama.cpp server.
- `engine/ai/connectivity.py` probes the provider's model-list endpoint. This is a low-cost connection/auth check, not proof that the selected model can generate a valid RPG response.
- The AI settings screen includes “Gerçek AI yanıtını test et”, which calls the configured adapter's actual `generate` method. This makes model-list connectivity and real generation separate checks. A generation test can consume API usage.
- The model-download dialog retains repository, filename, revision, and optional SHA-256 inputs, snapshots them on the UI thread, validates the resulting specification, and exposes progress/error/retry state.
- Hugging Face model downloads resume a preserved partial `.part` file when the server returns a valid HTTP Range response. If Range is ignored or invalid, the downloader restarts safely rather than appending incompatible bytes. Interrupted downloads preserve partial data for retry; checksum validation and atomic finalization remain in place.
- Chat message bubbles now size to their rendered text, with alignment and spacing adjusted for player/AI messages. UI labels covered by the existing readiness tests were updated accordingly.

## Latest source verification

- [GitHub Actions run 38450747404](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38450747404) completed successfully on commit `9ccf25b1e96abb4df40e9cf8684e641373aeee86`.
- The run passed the full pytest suite, Python `compileall`, Android readiness contract, and mutation smoke.
- Earlier failure [run 38450321810](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38450321810) exposed three stale assertions after the dialog and bubble changes. The UI snapshots and tests were corrected; the later run above is green.

## Not proven yet

- The current installed APK contains these changes.
- DNS, TLS, provider access, and generation work over the user's mobile-data connection.
- The configured API key has sufficient permissions/quota, or that every selected model accepts the structured-response request.
- Real AI generation or local GGUF inference works on the physical Android device.
- The chat layout has been visually inspected on the actual device.

Source CI validates code contracts, not carrier/provider behavior or physical-device rendering. A green source run is not an APK/device test.

## Stage 1 exit criteria

- [x] Source-level test suite and compile checks pass.
- [x] Android readiness contract passes.
- [x] Mutation smoke passes.
- [x] Download interruption/resume paths have automated tests.
- [x] Model download form values are captured before worker execution.
- [x] Current CI result is recorded here.
- [ ] Physical-device network and UI verification — deferred until an APK build is explicitly authorized.
- [ ] APK build and scenario testing — outside this stage's agreed scope.

**Conclusion:** Stage 1 source work is complete and CI-green. Device-specific behavior remains unverified; do not describe the APK as built or device-tested.

## Follow-up findings from user device feedback — 2026-10-14

The networking implementation has source-level tests, but the user reports the wider AI settings UX remains inadequate. Open work for the next implementation pass:

- Reduce API configuration to the minimum fields required by the selected provider. Do not ask for a custom endpoint for Gemini; expose custom endpoint configuration only for OpenAI-compatible providers.
- Preserve the distinction between a model-list connection probe and an actual generation request.
- Fix the remaining text-entry/composer layout, settings-screen usability, and malformed/inconsistent UI symbols; these are UI acceptance blockers, not networking test failures.
- A scenario import also fails with `characters.json:npc_kim_minjae.goals entries must be objects`; track this separately as a scenario data-contract issue, not as a network failure.

The Android build [run 38455404595](https://github.com/akln55/AI-STORY-ENGINE/actions/runs/38455404595) succeeded and uploaded an APK artifact, but it built commit `ad611254d90578e375b53f7445d1e7f1d4d243ae`, before the above follow-up fixes. It does not establish physical-device rendering, provider access over mobile data, or successful scenario import. Do not mark these gates complete until tested.
