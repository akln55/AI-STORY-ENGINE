# Security Policy

This repository is public and is used as a source repository for the Android build pipeline.

## Never commit secrets

Do not commit:

- API keys
- access tokens
- passwords
- private keys or certificates
- Android signing keys or keystores
- service-account credentials
- `.env` files containing secrets
- personal data
- local save data
- downloaded GGUF/model files

Use GitHub Actions Secrets or another managed secret store for CI credentials. Runtime provider credentials must be supplied through the application's runtime configuration and must never be hard-coded into source files.

## If a secret is exposed

Deleting the file or commit is not sufficient. Immediately revoke or rotate the exposed credential, then remove the secret from repository history before considering the repository clean again.

## Public repository rule

Assume every committed file is publicly visible. Only build-required source, tests, configuration, workflows, and non-sensitive documentation should be committed.

## Android build rule

Build caches, APKs, AABs, signing material, local Gradle state, virtual environments, and user/runtime data must remain outside Git tracking.

## Model files

GGUF and other downloaded model files are intentionally excluded from Git. They are runtime assets, not source code.

## CI credentials

GitHub Actions workflows must use the minimum permissions necessary. Credentials must come from GitHub Secrets or other managed secret stores, never from repository files.
