# AI Execution Policy

## Purpose

The in-app AI is a synchronous narrator/proposal component. It is not an autonomous agent and it does not own the gameplay loop.

## Per-player-action contract

One explicit player action creates at most one AI transaction.

A transaction may make at most **2 provider calls**:

1. First structured-response generation.
2. One retry only when the first response is malformed structured output (`ValueError`).

Provider/network/model failures are not converted into retry feedback.

After a valid response is received:

- effects are validated once;
- state is applied once;
- memory proposals are processed once;
- one player-facing result is returned;
- the engine does not automatically call the AI again.

There is no AI -> AI -> AI autonomous loop.

## Re-entrancy guard

`GameSession` rejects an attempt to start another AI transaction while one is already active. This is a code-level invariant and does not depend on prompt compliance.

A future tool-enabled adapter must preserve this invariant.

## Repeated player input

The engine does **not** suppress a player deliberately submitting the same action twice. Two explicit player submissions are two turns. Only implicit/re-entrant repetition is blocked.

## Output budget

The current local llama.cpp adapters use a default maximum completion of 512 tokens per provider call. Context assembly uses a deterministic character budget and trims lower-priority context before failing on an irreducible core.

The engine never asks a provider for an unbounded completion.

## No autonomous continuation

The following are forbidden as an engine behavior:

- AI response causing another automatic AI response;
- AI response causing a second turn without player input;
- AI response recursively invoking `GameSession.handle_input`;
- AI response selecting or discovering another AI/tool and chaining it automatically;
- malformed output causing unbounded retries.

## Authority

The AI may propose narrative and structured effects. The deterministic engine validates and applies them. The AI cannot directly mutate `GameState`, memory storage, SQLite, saves, scenario files, or application files.
