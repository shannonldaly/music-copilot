# Decision: Local-first architecture

Date: ~2026-03-15 (Phase 0)
Status: Decided

## Problem
Building a multi-agent system that calls LLM APIs on every request would be expensive during development, slow for iteration, and create a hard dependency on API keys for anyone reviewing the portfolio project.

## Options considered
| Option | Summary | Why not chosen |
|--------|---------|---------------|
| API-only | All agents call LLMs for every request | Too expensive for development, blocks demo without API key |
| Local-only | All agents are deterministic, no LLM | Limits creative output, can't handle open-ended prompts |
| **Local-first with API upgrade path** | Build local/deterministic for every agent first, add LLM mode as opt-in | Chosen |

## Decision
Every agent has a local mode (deterministic, zero cost) as the default, with an API mode (LLM-powered) available via `use_api: true`. Local mode uses curated databases (20+ genre progressions, 18 drum patterns, 12 artist profiles, 9 sound engineering topics) and keyword-based intent detection. This means the full demo works without an API key.

## Tradeoffs accepted
- Local mode is limited to hardcoded knowledge — can't handle truly novel or open-ended requests
- Two code paths per agent (local and API) must be maintained in sync
- API mode is less tested because local mode is the default development path

## Deferred
- Testing API mode end-to-end (currently untested for most agents)
- Ensuring return shape consistency between local and API modes (known gap in SE Agent)
