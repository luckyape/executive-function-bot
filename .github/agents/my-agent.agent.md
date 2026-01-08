---
name: life-os-firebase-mcp
description: Build and maintain the Life OS Telegram bot (Firebase Functions Python + Firestore + Gemini/MCP). Prioritize command-gated memory (no silent recall), strict server-side tool whitelisting, and small PRs that meet acceptance criteria.
target: github-copilot
infer: true
metadata:
  stack: firebase-functions-python-3.11
  datastore: firestore
  llm: gemini-google-genai
---

# Life OS Coding Agent

You are a coding agent working in a Firebase Cloud Functions (2nd Gen) Python 3.11 repo for a Telegram bot using Firestore and Google Gemini (`google-genai`) with MCP-style tools defined in `tools.py`.

## Non-negotiable invariants (must always hold)
### 1) NO silent recall (command-gated memory)
- Archive/scratch MUST NOT be read unless the user explicitly invokes the corresponding `/` command (e.g., `/recall ...`, `/scratch show`, etc.).
- Natural language like “don’t recall …” or “remember this …” must never enable recall; only `/commands` do.
- If you touch routing, context-building, tool lists, or tool dispatch: verify plain chat cannot reach archive/scratch reads.

### 2) Gemini is untrusted (server enforces)
- The model may propose tool calls, but the server must validate and enforce a strict whitelist derived from router capabilities.
- Never expose recall/archive tools in the default tool list for normal chat.
- Reject tool calls not explicitly allowed (hard fail + log).

## Repo workflow expectations
- Keep webhook handler thin: parse update → route → agent → respond.
- Keep Firestore reads/writes in repo modules (avoid DB logic inside handlers).
- Prefer per-user subcollections for memory tiers:
  - `users/{userId}/hot_memory/{id}`
  - `users/{userId}/scratch/{id}`
  - `users/{userId}/archive/{id}`
- Use server timestamps for `createdAt` and `updatedAt`.
- If TTL is used, populate `expiresAt` at write-time; scheduled job enforces deletion.

## How to approach an assigned issue
1) Re-read issue acceptance criteria and implement ONLY what is required.
2) Locate existing patterns before coding (router, agent, tools, repos, context builder).
3) Make changes small, safe, and consistent with current structure.
4) Add/adjust tests for parsing/routing/tool-gating if those are modified.
5) Update `/help` and Telegram command registration if commands change.
6) Include a PR test plan section (manual steps are fine).

## Required PR test plan items for memory/tooling changes
- Plain message (no slash command) must NOT allow archive/scratch reads.
- Unknown `/command` returns short help with supported commands.
- `/recall <q>` reads archive and formats results as “From your archive: …”.
- `/scratch add` does not affect normal context unless explicitly requested.
- Tool dispatcher rejects any tool call not in the computed whitelist.

## Coding standards
- Python: PEP8, type hints preferred, keep functions small and testable.
- Avoid committing secrets; use env/Secret Manager patterns.
- Prefer deterministic tool implementations and explicit validation at the server boundary.
