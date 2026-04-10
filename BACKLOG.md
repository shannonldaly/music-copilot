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
| 18 | ~~Orchestrator file is 900+ lines~~ — Superseded by #19 below. | | | |
| 19 | **Pre-Phase 4: Orchestrator refactor sprint** — Split `orchestrator.py` (1021 lines), `theory_agent.py` (921 lines), `sound_engineering_agent.py` (498 lines) into modules per architect findings C1/C2/C3. Orchestrator → intent_detector + local_lookup + response_builder. Theory Agent → class + ARTIST_PROFILES data file + local generator. SE Agent → class + local responses data file. | Doesn't block MCP — MCP wires into /services/ and calls orchestrator as-is. Maintainability improvement. | Pre-Phase 4 dedicated session | **Medium** — navigating 1000-line files slows development |

---

## Future Architecture — Phase 5+

| Gap | Why deferred | Phase | Risk if ignored |
|-----|-------------|-------|----------------|
| Supabase migration for session storage | JSON flat files work at current scale, Supabase needed for multi-user and persistence across devices | Phase 5 | Medium — session data lost on server restart, no cross-device access |
| pgvector / RAG for agent memory | Flat file knowledge docs work under 4000 tokens, RAG needed when knowledge base grows | Phase 5 | Medium — artist_dna.md and music_theory.md currently truncated, agents miss content |
| Semantic memory for Teaching Agent | Teaching Agent currently stateless — same explanation every time regardless of user history | Phase 5 | Medium — limits personalization, teaching doesn't improve over time |
| Episodic logging to Supabase | Currently logging to console only, no persistent searchable log | Phase 5 | Low now, High at scale — no audit trail for client engagements |
| Playwright E2E test template (reusable) | Phase 3c covers Rubato-specific tests, reusable template is the next step | Phase 3c item 11 | High — manual testing is unsustainable across multiple client projects |
| CI/CD pipeline | No automated deploy on push to main | Phase 5 | Medium — manual deploys increase risk of shipping broken code |
| Deployment to real URL | Currently localhost only | Phase 5 | High for demo — can't share with Jerome/Outpost/LANDR without a real URL |
| Full onboarding flow | Currently placeholder welcome screen | Phase 5 | Low for now, High before public launch |
| Project create/open/resume | Currently placeholder Recent Sessions tab | Phase 5 | Medium — returning users can't resume sessions |
| Blueprint completion state | Currently placeholder | Phase 5 | Low — functional gap but not blocking demo |
| Stripe Checkout integration | No payment processing yet | Phase 5+ | N/A until productizing |
| Multi-user support | Currently single-user only | Phase 5+ | N/A until client deployments |
| Knowledge graph layer | For distilling agent memory into fewer tokens at scale | Phase 5+ | Low now — only needed at high API volume |
