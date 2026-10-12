# Repository Privacy and Secret Handling

Last reviewed: 2026-10-12

## Critical: repository visibility

The repository `akln55/AI-STORY-ENGINE` was verified as **public** during this review. Public means source code, history, issues, workflow files, and committed documentation are readable by anyone. A `.gitignore` does not make a public repository private, and deleting a file from the latest commit does not remove it from earlier Git history.

The GitHub connection used for this code change does not expose repository-visibility administration. To keep this project private, change visibility in GitHub:
1. Open [repository settings](https://github.com/akln55/AI-STORY-ENGINE/settings).
2. Open **General** and scroll to **Danger Zone**.
3. Choose **Change repository visibility**, select **Private**, and confirm GitHub's prompts.

If the project must be private, do this before continuing to treat repository contents as confidential. Verify the repository header shows **Private** afterward. Do not assume a successful commit or `.gitignore` setting hides existing code.

## Secret handling rules

- Never commit real API keys, access tokens, passwords, signing keys, certificates, keystores, service-account files, or production data.
- Keep local credentials in an ignored `.env` / `.env.local` file only for tools that explicitly read them. The current Android app does **not** load API credentials from a developer `.env`; its API screen accepts a key at runtime and passes it to the selected provider adapter.
- Never copy a developer `.env` into the Android package. Any secret embedded in an APK can be extracted by its recipient.
- Use GitHub Actions Secrets only when a workflow genuinely needs a credential. The current Android build workflow is read-only and should not need provider API keys or signing secrets.
- Keep local models, saves, imports, logs, signing material and build outputs out of Git.
- Review `git status --short` and `git diff --cached` before every commit. Check tracked files with `git ls-files`; ignore rules do not untrack files already committed.
- Do not paste credentials into source, issues, workflow logs, screenshots, or AI prompts.

## If a credential may have been exposed

1. Revoke or rotate it at the provider immediately.
2. Remove it from the current tree.
3. Review Git history and logs; a new cleanup commit is not sufficient to erase earlier copies.
4. Use GitHub's sensitive-data removal procedure if history rewriting is required, then coordinate any cloned copies.
5. Review Actions artifacts and cached outputs for copies of the credential.

## Current configuration findings

- `.gitignore` already ignores `.env`, `.env.*`, key/certificate/keystore patterns, credential JSON, APK/AAB outputs, saves, imports, models and GGUF files; `.env.example` is the only explicit env-file exception.
- Additional local secret/signing patterns are now ignored, including `.envrc`, `.direnv/`, `*.secret`, `*.token`, `*.p8` and mobile provisioning profiles.
- The Android workflow uses read-only `contents: read` permissions, pinned action SHAs, and disabled checkout credential persistence. It currently does not consume GitHub Secrets.
- The API key UI uses a password field and passes the entered key to the provider adapter. Do not persist or log that value.
- The repository being public is the main confidentiality gap. File ignore patterns cannot correct repository visibility or erase history.
