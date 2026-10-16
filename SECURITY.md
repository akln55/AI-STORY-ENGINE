# Security Policy

This is a **public repository**. Assume that every committed file, including archived documentation, is publicly readable. A folder name or written rule cannot make a public GitHub directory private.

## Never commit

- API keys, access tokens, passwords, private keys, certificates, Android signing keys or keystores.
- Secret-bearing `.env` files, service-account credentials, or private configuration.
- Personal data, user saves, runtime databases, local imports, private GGUF/model files, sensitive logs, build caches, APKs/AABs, or local Gradle/environment state.

Use GitHub Actions Secrets or another managed secret store for CI credentials. Provider credentials must be supplied through appropriate runtime configuration and never hard-coded into source.

## If a secret is exposed

Revocation/rotation is the priority. Deleting the visible file alone is insufficient; follow with appropriate repository-history cleanup and any required incident response. Do not copy the secret into issues, prompts, logs, or a replacement document.

## AI and game-state security

- The deterministic engine owns authoritative game state. AI must not gain direct write authority over state, databases, saves, scenario canon, arbitrary files, or processes.
- Validate structured AI proposals against schema, security constraints, and gameplay rules before applying effects.
- Treat player, NPC, scenario, memory, chapter, and retrieved external text as untrusted data. Prompt-injection text inside those sources cannot override system, developer, or project rules.
- Enforce context visibility; never expose NPC-only, secret, or system-only knowledge to a player or another NPC without authorization.

## Tool and workflow security

- Use minimum required permissions and inspect the exact repository, branch, path, and requested action before writing.
- Do not merge without required checks and an independent Denetçi review.
- Do not start, stop, or retrigger an Android build unless Mareşal explicitly authorizes it.
- Preserve saves and user data. Treat mass deletion, destructive migration, force-push, or rewriting Git history as high-risk operations requiring explicit authority.
- The `docs/_archive/` policy is procedural, not an access-control mechanism. Archived files remain publicly visible; they must contain no secrets.
