# Backlog — Music Co-Pilot

*Created: 2026-04-08 — Phase 0 Onboarding*

---

## 2026-04-08 — Onboarding audit

| # | Gap | Why deferred | Phase | Risk if ignored |
|---|-----|-------------|-------|----------------|
| 1 | **SE Agent return shape mismatch** — Local mode returns `{summary, steps, ableton_path, principle, artist_reference}`, API mode returns `{markdown, question}`. Frontend only consumes local shape. | API mode for SE not reachable in current flow, so no user-facing bug yet. | Pre-Phase 3 | **High** — enabling `use_api: true` will break SE rendering silently |
| 2 | **Grounding docs silently truncated** — All agents truncate grounding docs (4000-6000 chars) with no signal to the LLM about missing content. | Works for current doc sizes, but docs may grow. | Phase 3+ | **Medium** — LLM gives incomplete advice on topics covered in truncated portion. Flag for RAG evaluation. |
| 3 | **No error propagation from Theory Agent API mode** — If LLM returns unparseable JSON, `{"error": "..."}` passes through as if valid. | Local mode (default) doesn't hit this path. | Pre-Phase 3 | **Medium** — enabling API mode will surface silent failures |
| 4 | **Orchestrator routing plan never consumed** — `routing.agents` list is built but api/main.py does its own inline orchestration. `agent_outputs` dict is never populated. | Local mode doesn't use the Orchestrator at all. API mode uses Orchestrator only for intent detection. | Phase 3 | **High** — adding new agents requires updating both Orchestrator routing AND api/main.py inline logic. Single source of truth violated. |
| 5 | **`artist_reference` intent has no local-mode handler** — Single artist prompts (e.g., "something like Massive Attack") return empty results in local mode. | Only affects single-artist prompts. Blend (2 artists) works. | Phase 2 patch | **Medium** — user gets empty response for a valid query |
| 6 | **`production_question` intent has no local-mode handler** — "How do I..." prompts without a sound engineering keyword return empty results. | SE Agent catches most production questions via keyword matching. | Phase 2 patch | **Low** — most production questions hit SE keywords |
| 7 | **No automated test suite** — No test files exist. CLAUDE.md lists "writing and running tests" as owned by Claude Code. | Building features was prioritized over testing in Phases 0-2. | Phase 2 patch / Phase 3 | **High** — no regression safety net before MCP integration changes |
| 8 | **Session JSON files grow unbounded** — No max history size, no cleanup, no pagination. Each `add_to_history` appends and rewrites the full file. | Sessions are small during development. | Phase 3+ | **Medium** — performance degrades with long sessions. Flag for SQLite evaluation per CLAUDE.md spec. |
| 9 | **Feedback loop not connected to generation** — Feedback stored in session JSON but Orchestrator never reads it to influence output. | Explicitly scoped as v2 in CLAUDE.md. | v2 | **Low** — feature gap, not a bug |
| 10 | **Clarification loop not implemented** — Orchestrator can return `clarification_needed` but the conversational loop (ask → answer → re-route) isn't built. | Deferred to post-MCP per CLAUDE.md. | Post-Phase 3 | **Low** — user can rephrase manually |
| 11 | **Theory Validator correction loop not implemented** — CLAUDE.md specifies "Theory Agent → Validator → retry up to 2x". Currently, validation runs once and results are passed through regardless. | Local mode produces correct theory (deterministic), so validation rarely fails. | Pre-Phase 3 | **Medium** — API mode without correction loop risks passing invalid theory to user |
| 12 | **Teaching Agent adaptation not wired** — `UserProfile` has `skips_explanations` and `asks_followups` fields. `_update_profile_from_feedback()` updates them. Teaching Agent never reads these fields. | Needs real usage data to calibrate. | v2 | **Low** — explanations are always "normal" detail level |
| 13 | **Melody direction `scale_fifths` map only covers natural notes** — Sharps/flats (C#, Bb, F#, Eb) fall through to default "E4" start note. | Affects non-natural key roots only. Start note is a suggestion, not a hard constraint. | Phase 2 patch | **Low** — musically acceptable but imprecise |
| 14 | **`daw_target` parameter not wired to user input** — Production Agent has the parameter (default "ableton") but no UI or API field to change it. | CLAUDE.md notes DAW-agnostic as a long-term goal. | v2+ | **Low** — Ableton-only is fine for current scope |

---

## 2026-04-08 — Orchestrator consolidation (B+ refactor)

**Resolved in this decision:**
- ~~#1 SE Agent return shape mismatch~~ — Fixed. `answer_question_structured()` returns unified shape.
- ~~#4 Orchestrator routing plan never consumed~~ — Fixed. `execute()` is now the single entry point.
- ~~#5 artist_reference intent has no local-mode handler~~ — Fixed. Uses ARTIST_PROFILES.

**New gaps identified:**

| # | Gap | Why deferred | Phase | Risk if ignored |
|---|-----|-------------|-------|----------------|
| 15 | **`_get_artist_reference` doesn't prioritize the named artist** — "something like Massive Attack" returns a dark minor progression but melody_direction.artist_reference may cite Deftones or Portishead instead, because scoring matches by mood/genre overlap not by the user's named artist. | Existing behavior in theory_agent.py `_get_artist_reference()`. Musically correct output, cosmetically wrong attribution. | Phase 3 | **Low** — melody direction is guidance, not a hard constraint |
| 16 | **`production_question` intent still has no local handler** — "How do I..." without SE keywords returns empty. | Most production questions match SE keywords. Remaining cases are rare. | Phase 3 | **Low** — user can rephrase |
| 17 | **`use_api=true` API-mode pipeline still partial** — `execute()` calls `process()` for Haiku intent detection, then falls through to the same local lookup + build response. Full API-mode agent pipeline (Sonnet for Theory Agent creative generation) not yet wired. | API mode was never the primary path. Local mode + Teaching Agent API covers the quality gap. | Phase 3+ | **Medium** — `use_api=true` doesn't deliver the full LLM experience it promises |
| 18 | **Orchestrator file is 900+ lines** — Single file contains intent detection, lookup, response assembly, and all API agent wiring. | Functional and tested. Can be split into modules later if it becomes hard to navigate. | v2 | **Low** — works, just large |
