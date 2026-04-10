# CLAUDE.md — Music Co-Pilot

## What This Project Is

An AI-powered music production co-pilot built as a multi-agent system. The user is a music producer learning Ableton Live — rusty on theory, beginner on production — who wants a tool that amplifies creative intent without replacing it. Think "Lovable for music production."

This is simultaneously:
1. A real tool the user actually uses while making music
2. A portfolio artifact to show companies like LANDR, Output, and Splice
3. A learning project to understand multi-agent orchestration

**North Star**: Keep the human creative and in control. Remove every technical barrier between intent and output. Never replace the composer — amplify them.

---

## Ownership Map — What Claude Code Can Decide Alone vs. What Needs Shannon

**Note**: Don't run the frontend — Cursor handles that on port 5173.

**Claude Code owns (decide and execute without asking):**
- Writing new Python agent files following existing patterns
- Writing new React components following existing CSS module patterns
- Adding new API endpoints following the existing FastAPI pattern
- Writing and running tests
- Installing pre-approved packages (anthropic, music21, fastapi,
  uvicorn, tone.js, axios, react)
- Git commits with descriptive messages
- Fixing bugs in code it just wrote in the same session

**Claude Code must ask Shannon first:**
- Any new dependency not in the approved list above
- Changes to the agent JSON contract structure (breaks frontend)
- Changes to session memory schema (breaks existing sessions)
- Any change to CLAUDE.md
- Deleting any files
- Changes to the folder structure defined in CLAUDE.md
- Anything that affects the Ableton MCP integration path

**Always stop and escalate (never proceed):**
- Anything involving API keys or credentials
- Anything involving user data or privacy
- Any decision that can't easily be undone
- Any change to git history or branch structure

---

## The Agent Team

There are 7 agents. Every agent has a defined role, grounding context, and clear handoff protocol. The Orchestrator runs first on every request and decides which agents to invoke.

### 1. Orchestrator Agent
**Role**: Entry point for every user request. Parses intent, detects request type, routes to the correct agents in the correct sequence, manages token budget.

**Intent types it detects**:
- `mood_vibe` — user describes a feeling, genre, or atmosphere ("something melancholic, rainy Sunday")
- `artist_reference` — user names an artist or track ("something like Bon Iver")
- `theory_request` — user asks for something specific ("give me a ii-V-I in a minor key")
- `production_question` — Ableton or sound engineering question ("how do I sidechain my bass to the kick")
- `feedback_loop` — user is reacting to previous output ("I like that but make it darker")
- `clarification_needed` — input is ambiguous or contradictory; trigger clarification loop before proceeding

**Token budget rule**: Not every request needs all 7 agents. Route only what is needed:
- Simple theory request → Theory Agent + Validator + Teaching Agent
- Production question → Production Agent + Teaching Agent
- Mood/vibe/artist → Orchestrator interprets → Theory Agent + Validator + Production Agent + Teaching Agent
- Ambiguous input → Ask one clarifying question before routing

**Handoff format**: Orchestrator passes a structured JSON context object to each downstream agent containing: `intent_type`, `user_input`, `interpreted_request`, `user_profile`, `session_history_summary`.

---

### 2. Theory Agent
**Role**: Generates musically accurate chord progressions, explains the harmony behind them, and outputs structured note data for validation.

**Implemented**: `agents/theory_agent.py` — supports both API mode (LLM-powered) and local mode (deterministic lookup, zero cost).

**Grounded in**:
- `/docs/music_theory.md` (Music Composition, Music Theory Best Practices & Chord Progressions Across All Genres)
- `/docs/artist_dna.md` (for `melody_direction.artist_reference` field)
- `/docs/advanced_harmony.md` (extended harmonic concepts)
- `/docs/famous_progressions.md` (curated progression reference)

**Output format** (always structured, never freeform):
```json
{
  "key": "A minor",
  "scale": "natural minor",
  "progression_name": "i–VI–III–VII",
  "chords": [
    { "numeral": "i", "name": "Am", "notes": ["A3", "C4", "E4"] },
    { "numeral": "VI", "name": "F", "notes": ["F3", "A3", "C4"] },
    { "numeral": "III", "name": "C", "notes": ["C3", "E3", "G3"] },
    { "numeral": "VII", "name": "G", "notes": ["G3", "B3", "D4"] }
  ],
  "tempo_suggestion": "85 BPM",
  "genre_context": "melancholic lo-fi / trap",
  "theory_explanation": "...",
  "voice_leading_notes": "...",
  "alternatives": [
    { "label": "darker", "progression_name": "i – VI – iv – VII", "chords": ["Am", "F", "Dm", "G"], "character": "Minor lo-fi with melancholic loop." },
    { "label": "more_movement", "progression_name": "i – VI – III – VII", "chords": ["Am", "F", "C", "G"], "character": "Endless loop that never resolves." },
    { "label": "unexpected", "progression_name": "i – VII – VI – V", "chords": ["Am", "G", "F", "E"], "character": "Descending bass line, Spanish/Flamenco flavor." }
  ],
  "melody_direction": {
    "start_note": "E4",
    "start_note_context": "The 5th of A minor — stable, neutral launching point",
    "contour": "descending with brief upward reaches",
    "rhythm_feel": "behind the beat, syncopated, lazy triplet feel",
    "avoid_on_strong_beats": ["D4"],
    "avoid_context": "the 4th degree creates unresolved tension on strong beats",
    "suggested_range": "A3 to E5",
    "artist_reference": "Massive Attack — sparse, Phrygian-influenced melodies..."
  }
}
```

**Alternatives contract**:
- Lighter-weight: chord names only, no note-level data
- Always 3 alternatives labeled: `darker`, `more_movement`, `unexpected`
- All alternatives stay in the same key and mode as the primary
- Alternatives bypass the Theory Validator
- When a user swaps an alternative to primary, the frontend calls `POST /api/progression/expand` to get full note-level data + validation

**Melody direction contract**:
- `artist_reference` pulls from `/docs/artist_dna.md` grounding context
- `suggested_range` defaults to a singable mid range (e.g., A3–E5)

**Critical rules**:
- Always output exact note names with octave numbers (e.g., C4, not just C)
- Never suggest notes outside the stated scale without explicitly flagging it as a borrowed chord
- Always pass primary output to Theory Validator before it reaches the user
- If the user requests something that has no musically coherent answer (e.g., contradictory constraints), return an error with an explanation, not a hallucinated answer

---

### 3. Theory Validator (Python / music21)
**Role**: Programmatic correctness check on all Theory Agent output. This runs as a Python script using the `music21` library. It is not an LLM — it is deterministic validation code.

**What it checks**:
- Each note name is a valid pitch (correct spelling, octave in range)
- Each chord's notes are consistent with the stated chord name and quality
- Each chord belongs to (or is explicitly a modal interchange from) the stated key and scale
- Voice leading between consecutive chords — flags parallel fifths, parallel octaves, and large leaps
- The progression makes harmonic sense in sequence (e.g., flags if a claimed ii–V–I doesn't actually resolve)

**Validation result format**:
```json
{
  "passed": true,
  "errors": [],
  "warnings": ["Large leap of a 7th in bass voice between chord 2 and chord 3 — consider smoother voice leading"],
  "corrected_output": null
}
```

If `passed: false`, the Validator returns the errors to the Theory Agent for correction. The loop runs maximum 2 times. If it still fails, the Orchestrator flags the output to the user with a warning rather than silently passing bad theory.

**Never skip this step.** The user has explicitly noted that Claude has produced incorrect music theory before. The Validator is the quality gate.

---

### 4. Production Agent
**Role**: Translates validated theory output into concrete, step-by-step Ableton Live instructions. Speaks Ableton fluently.

**Grounded in**: `/docs/ableton_guide.md` (Ableton Live: Complete Tutorial & Troubleshooting Guide)

**Output format**:
```markdown
## Building This in Ableton

**Track setup**
- Create a new MIDI track (Cmd+Shift+T)
- Load a piano or pad instrument (suggested: Ableton's Mellow Keys from the Core Library)

**Entering the notes**
1. Double-click the MIDI track to create a clip
2. Set the clip length to 4 bars
3. Enable Draw Mode (B)
4. Chord 1 — Am: Place A3, C4, E4 all starting at bar 1, beat 1. Duration: 1 bar each.
5. Chord 2 — F: Place F3, A3, C4 starting at bar 2, beat 1. Duration: 1 bar each.
[... continues for each chord ...]

**Suggested next steps**
- Add a sub bass track doubling the root note of each chord (A, F, C, G) one octave lower
- Sidechain the bass to a kick on beats 1 and 3 for that lo-fi pump
- Apply a high-pass filter at 80Hz on the chord track to leave room for the bass
```

**Ableton version awareness**: Default to Live 12 instructions. Note when a feature is version-specific (e.g., Scale Mode in the Piano Roll is Live 12+).

**MCP readiness**: Structure Ableton instructions so they map directly to AbletonMCP commands. For each step, include a comment like `# MCP v2: create_midi_clip(track=1, length=4)` — this makes the v2 upgrade path mechanical, not a rewrite.

---

### 5. Sound Engineering Agent
**Role**: Handles all mixing, mastering, EQ, compression, sidechain, spatial, and sound design questions for electronic music.

**Implemented**: `agents/sound_engineering_agent.py` — selectively loads relevant grounding context based on question keywords.

**Grounded in**:
- `/docs/electronic_music_production.md` (Electronic Music Production: History, How-To, Best Practices & Sound Engineering)
- `/docs/mixing_cheat_sheet.md` (Instrument-specific EQ, compression, and reverb reference)
- `/docs/automation_playbook.md` (When and what to automate by song section — loaded for automation/arrangement questions)
- `/docs/artist_dna.md` (Artist-specific production techniques and signatures — loaded for style/reference questions)

**Scope**:
- Frequency spectrum decisions (what lives where, what to cut)
- Compression settings for specific use cases (kick, bass, mix bus)
- Sidechain setup and pump effect
- Reverb and delay routing (always returns, never inserts on this genre)
- Gain staging and headroom for export
- LUFS targets by platform and genre
- Synthesis and sound design guidance (subtractive, FM, wavetable)

**Always grounds advice in the user's level**: Beginner on production. Explain *why* first, then the *how*. Never assume prior knowledge of a concept without a one-sentence explanation.

---

### 6. UX Designer Agent
**Role**: Reviews all frontend decisions, proposes UI layouts, flags UX anti-patterns, and ensures the app looks demo-worthy and employer-impressive. Acts as a creative director for the interface.

**Design direction for this product**:
- Aesthetic: Dark, focused, studio-like. Not a consumer music app. Not a developer tool. Somewhere between a high-end DAW plugin and a premium creative tool.
- Typography: Distinctive. Not Inter, not Roboto. Something with character.
- Color: Dark background, one strong accent color (not purple gradient — avoid generic AI aesthetics). Consider deep navy, charcoal, or matte black with an amber or electric blue accent.
- Layout: The chat input is not the hero. The *output* is the hero — chord display, Ableton steps, and teaching note should each have their own visual panel.
- Motion: Subtle. Agents "thinking" should be visually represented. Output panels should animate in sequentially, not all at once — this makes the multi-agent architecture *visible* to a demo audience.

**What this agent reviews**:
- Every new UI component before it's built
- Layout decisions that affect user flow
- Color, typography, and spacing choices
- The demo flow — what does an employer see in the first 30 seconds?

**Anti-patterns to flag immediately**:
- Generic chat bubble UI that looks like every other AI app
- Output as a wall of text with no visual hierarchy
- No loading/thinking states (makes the agents invisible)
- Mobile-first layout for a tool that lives next to a DAW (this is a desktop experience)

---

### 7. Technical Architect Agent
**Role**: Reviews all technical decisions for long-term coherence. Thinks 3 versions ahead. Prevents short-term choices from creating long-term debt.

**Current architecture principles**:
- **Backend**: Python (FastAPI or Flask). Agents are Python functions called in sequence by the Orchestrator. Each agent is its own module.
- **Frontend**: React. Communicates with backend via REST API (websockets later for streaming).
- **Validation**: music21 runs as a subprocess called from the Theory Validator module — not as an API call, not as an LLM prompt.
- **State**: SQLite for v1 session persistence. Postgres later.
- **MCP bridge**: In v1, Production Agent outputs Ableton steps as text + MCP-commented pseudocode. In v2, those comments become live calls via `ableton-mcp` (ahujasid/ableton-mcp or jpoindexter/ableton-mcp — evaluate both).
- **Audio preview**: v1 uses Tone.js in the browser to play chord progressions from MIDI note data. No audio files generated server-side in v1.
- **Cost management**: Orchestrator enforces a max token budget per request. Log every API call with token count. Set alerts before costs become a surprise.

**Long-term decisions to protect**:
- Agent modularity — every agent must be swappable without rewriting the Orchestrator
- The structured JSON contract between agents must be versioned
- The user profile / taste model must be designed now even if it's just a JSON file in v1 — the schema matters
- DAW-agnostic long term: don't hardcode Ableton. The Production Agent should have a `daw_target` parameter from day one.

**This agent reviews**: Any new dependency, any architectural shortcut, any "we'll fix it later" decision.

---

## The 5 Things Not to Forget

These were explicitly identified as missing from the initial spec. Every one of them must be addressed before v1 ships.

### 1. Session Memory & Persistence
Users return to sessions. The system must remember:
- What progressions were generated and whether the user liked them (thumbs up/down)
- What the user is currently working on (genre, key, vibe)
- User skill calibration (updates over time as they ask more advanced questions)

**v1 implementation**: JSON file per user session stored locally. Schema:
```json
{
  "session_id": "uuid",
  "created_at": "timestamp",
  "user_profile": {
    "theory_level": "rusty_intermediate",
    "production_level": "beginner",
    "preferred_genres": ["lo-fi", "trap"],
    "current_project": { "key": "A minor", "bpm": 85, "genre": "lo-fi" }
  },
  "history": [
    { "request": "...", "output": {...}, "feedback": "thumbs_up", "timestamp": "..." }
  ]
}
```

### 2. Audio Preview (Hear Before You Commit)
The output must be audible. Text-only chord suggestions break the core product promise.

**v1 implementation**: Tone.js in the browser. When the Theory Agent returns validated chord data (with note names and octave numbers), the frontend plays the progression automatically using a piano or pad sound. User can toggle playback on/off. Tempo is pulled from the Theory Agent's `tempo_suggestion`.

**This is a demo moment.** The employer hears the chord progression play in the browser. That's the wow.

### 3. Clarification Loop for Ambiguous Input
When input is contradictory or too vague to route confidently, the Orchestrator asks one clarifying question — not a list of questions, exactly one.

**Example**: "Give me something happy" → Orchestrator responds: "Happy like a summer pop track, or happy like an uplifting trance drop?" User answers, then routing proceeds.

**Rule**: Never produce output from ambiguous input. One question, then proceed.

### 4. Feedback Loop / Taste Profile
Every output has a simple reaction UI: 👍 / 👎 / 🔁 (regenerate). This data is written to the session JSON.

Over time this becomes the taste model. In v1 it's just stored data. In v2 the Orchestrator reads recent feedback before generating to bias toward what the user has liked.

**The Teaching Agent also adapts**: if the user consistently skips the theory explanation (no engagement, moves straight to Ableton steps), Teaching Agent shortens explanations. If they ask follow-up theory questions, it goes deeper.

### 5. API Cost Awareness
Seven agents on every request is expensive. The Orchestrator enforces routing discipline.

**Rules**:
- Log every API call: agent name, token count (input + output), timestamp
- Set a per-request budget cap (start at 4,000 tokens total across all agents)
- The Theory Validator is free (deterministic Python, no API call)
- The UX Designer Agent and Technical Architect Agent are NOT called on user music requests — they are called during development sessions only
- Display running cost in the dev UI (not in the demo UI) so you can see what each request costs in real time

---

## Build Sequencing

### Phase 0 — Foundation (Do This First, Before Any App Code) ✅ COMPLETE
*Goal: The skeleton exists and every agent can communicate.*

1. ✅ Set up project repo with clear folder structure:
   ```
   /agents          — one Python file per agent
   /api             — FastAPI backend + helpers
   /docs            — grounding documents (8 files — see below)
   /validator       — music21 validation scripts
   /frontend        — React app
   /memory          — session JSON storage
   /theory          — local music theory lookups (cost-efficient)
   /utils           — token tracking, model config
   CLAUDE.md        — this file
   ```
   **Grounding documents in `/docs`**:
   - `music_theory.md` — composition, theory best practices, chord progressions
   - `ableton_guide.md` — Ableton Live tutorial & troubleshooting
   - `electronic_music_production.md` — history, how-to, best practices
   - `mixing_cheat_sheet.md` — instrument-specific EQ, compression, reverb
   - `artist_dna.md` — 12 artist production profiles, signature techniques
   - `advanced_harmony.md` — extended harmonic concepts
   - `drum_patterns_extended.md` — expanded drum pattern reference
   - `famous_progressions.md` — curated famous progression reference
   - `automation_playbook.md` — when/what to automate by song section
2. ✅ Install dependencies: `anthropic`, `music21`, `fastapi`, `uvicorn`
3. ✅ Write the Orchestrator as a simple router (`agents/orchestrator.py`)
4. ✅ Write the Theory module with structured output (`theory/` — scales, chords, progressions, drum patterns)
5. ✅ Write the Theory Validator Python script (`validator/theory_validator.py`)
6. ✅ Confirm the Orchestrator → Theory → Validator pipeline works end to end

**Cost-efficient architecture**: Local lookups for theory data (20+ genre progressions, 18 drum patterns) with tiered model routing (Haiku for simple tasks, Sonnet for creative).

### Phase 1 — Core Loop (First Working Version) ✅ COMPLETE
*Goal: Type a prompt, get a validated chord progression with explanation and Ableton steps.*

1. ✅ Add Production Agent (`agents/production_agent.py`)
2. ✅ Add Teaching Agent (`agents/teaching_agent.py`)
3. ✅ Add Theory Agent (`agents/theory_agent.py`) — with alternatives array and melody_direction
4. ✅ Add Sound Engineering Agent (`agents/sound_engineering_agent.py`) — grounded in automation_playbook.md + artist_dna.md
5. ✅ Add session memory (JSON read/write) (`memory/session.py`)
6. ✅ Build minimal frontend: input box, three output panels (chords, Ableton steps, teaching note), thinking states for each agent
7. ✅ Add Tone.js audio preview
8. ✅ Add thumbs up/down feedback UI

**Definition of done**: You can type "give me something melancholic, lo-fi, minor key" and receive a validated chord progression that plays in the browser, with Ableton steps and a teaching note — and it's saved to session history. The response also includes three alternative progressions (darker, more movement, unexpected) and a melody direction object.

**API Endpoints (FastAPI)** — `api/main.py`:
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check, returns status and version |
| `/api/generate` | POST | Main generation endpoint — returns progressions, alternatives, melody_direction, production steps, teaching note |
| `/api/progression/expand` | POST | Expand a lightweight alternative to full note-level data + validation |
| `/api/session` | POST | Create new session with user profile |
| `/api/session/{id}` | GET | Get session by ID |
| `/api/session/{id}/history` | GET | Get session history with feedback |
| `/api/feedback` | POST | Record thumbs_up/thumbs_down/regenerate/progression_swap |
| `/api/project` | POST | Update project context (key, BPM, genre) |
| `/api/session/{id}` | PATCH | Update session (e.g. song_name) |
| `/api/sessions` | GET | List all sessions |

**`/api/generate` response contract** (key fields):
- `progressions` — array of full note-level progression data
- `alternatives` — 3 lighter-weight objects: `{label, progression_name, chords (names only), character}`
- `melody_direction` — `{start_note, start_note_context, contour, rhythm_feel, avoid_on_strong_beats, avoid_context, suggested_range, artist_reference}`
- `production_steps` — markdown Ableton instructions
- `teaching_note` — theory explanation
- `validation` — Theory Validator result for primary progression

**`/api/progression/expand` contract**:
- Request: `{chords: ["Am", "F", "Dm", "G"], key: "A minor", progression_name: "i – VI – iv – VII"}`
- Response: full note-level chord data + Theory Validator result

**Local Mode (No API Key Required)**:
The `/api/generate` endpoint supports `use_api: false` which runs entirely locally:
- Keyword-based intent detection (no LLM call)
- Local theory lookups from `theory/genre_progressions.py` and `theory/drum_patterns.py`
- Local production instructions from `generate_chord_instructions_local()` and `generate_drum_instructions_local()`
- Local teaching notes from `generate_progression_explanation_local()` and `generate_rhythm_explanation_local()`
- Local alternatives + melody direction from `generate_theory_output_local()`
- Zero API cost for development and testing

**To run the API**:
```bash
uvicorn api.main:app --reload --port 8000
```
API docs available at: `http://localhost:8000/docs`

### Phase 2 — Polish & Demo-Readiness ✅ COMPLETE
*Goal: Something you'd show an employer without apologizing for anything.*

1. ✅ Frontend overhaul — session modal, progress sidebar, Also Try interactive progressions, melody direction panel
2. ✅ Add Sound Engineering Agent to the routing (`agents/sound_engineering_agent.py`)
3. ✅ Enharmonic spelling fix — flat keys use flats, sharp keys use sharps, Theory Validator uses pitch-space comparison
4. ✅ Key extraction from prompts — user-specified keys (C# major, Bb minor, etc.) respected throughout the pipeline
5. ✅ PATCH `/api/session/{id}` endpoint — update song_name on sessions
6. ✅ Backend validated across A minor, F# minor, Bb minor, C# major, D major, Eb major, G minor, and drum patterns

**Not shipped in Phase 2** (deferred or not needed for demo):
- Clarification loop for ambiguous input (deferred to post-MCP)
- Teaching Agent calibration refinement (needs real usage data)
- Cost logging dashboard (dev-only, low priority)
- 60-second demo video (record after Phase 3 MCP integration)

### Phase 3a — Architecture & Agent Quality ✅ COMPLETE
*Goal: Orchestrator is the single source of truth. Agent quality gaps closed.*

1. ✅ Architect skill onboarding run — ARCHITECTURE.md, BACKLOG.md, decisions/ populated
2. ✅ Orchestrator consolidation (Option B+) — api/main.py generate() from 315 lines to 32 lines
3. ✅ Teaching Agent wired to always-API (Sonnet) with Approach C graceful degrade
4. ✅ SE Agent contract mismatch resolved — unified `{summary, steps, ableton_path, principle, artist_reference}` shape
5. ✅ SE Agent API fallback via `answer_question_structured()` for unrecognized topics
6. ✅ `artist_reference` intent handler — single-artist prompts now produce results
7. ✅ `use_api` flag semantics documented
8. ✅ All bare `except: pass` replaced with `logger.warning()`

**Decision log**: `decisions/2026-04-08-orchestrator-consolidation-b-plus.md`

### Phase 3b — UX Design Sprint (IN PROGRESS)
*Goal: The frontend is demo-worthy. Every feature is visually surfaced.*

1. Rubato branding — name, typography, color palette, logo
2. Sound Engineering Agent surfaced in UI with structured panel
3. Artist blend intent surfaced in UI with attribution columns
4. Piano roll legibility improvements
5. Project create / open / resume flow
6. Session history view
7. Onboarding flow for first-time users
8. Keep confirmation loop in session stages

### Phase 3c — Operational Readiness Sprint 1
*Goal: The system is testable, observable, and safe to modify. All BEFORE MCP.*

1. Contract tests for all 7 agents — verify input/output shapes match what both sides expect
2. Integration tests for `/api/generate` across all intent types (mood_vibe, drum_pattern, sound_engineering, artist_blend, artist_reference)
3. Unit tests for: TheoryValidator, detect_intent_local, key inference priority logic, enharmonic spelling
4. Convert 7 manual curl verifications to automated pytest suite
5. Structured logging: every agent logs what it received, returned, and how long it took
6. Health check endpoint (`/api/health`) actually verifies dependencies — music21 loaded, API key status
7. Error handling: every agent has a defined fallback — no silent nulls reaching the frontend
8. Secrets audit: no API keys in code or committed to git, `.env.example` exists
9. README updated: a new person can clone and run the project from these instructions alone
10. API documentation accurate at `/docs`
11. Playwright E2E test template — automated browser tests for the core user journey (welcome → modal → generate → Keep → stage advance). Written as a reusable template that travels to future client projects, not just Rubato-specific tests.
12. `/services/` folder created — empty folder at project root with a README.md explaining: all external integrations live here. MCP client will live here in Phase 4. Stripe, Supabase, webhooks go here in future projects.
13. Architect code review pass — run the architect skill against all files over 150 lines. Flag violations of the new code review standards (200-line limit, hardcoded values, no dead code, naming conventions). Produce a findings report. Fix critical violations before Phase 4.

### Phase 4 — Ableton MCP Integration
*Goal: Chord progressions appear directly in Ableton, no copy-paste.*

1. Install and configure `ableton-mcp` (evaluate ahujasid vs jpoindexter versions)
2. Convert Production Agent's MCP-commented pseudocode into live MCP calls
3. Test end-to-end: prompt in browser → chord progression in Ableton Piano Roll
4. This is the employer demo that closes the room

### Phase 5 — Operational Readiness Sprint 2
*Goal: Post-MCP hardening. The system is stable under real use.*

1. MCP-specific error handling — Ableton not running, connection lost, clip creation failed
2. End-to-end integration tests covering the MCP path
3. Performance baseline: measure and log request latency per agent
4. Session recovery — handle interrupted MCP operations gracefully
5. BACKLOG.md and decisions/ up to date with all Phase 4 decisions

### Phase 6 — Demo
*Goal: A 60-second video that makes employers reach out.*

1. Record the demo flow: prompt → chord progression plays in browser → appears in Ableton Piano Roll
2. Polish the first-30-seconds experience (what does an employer see?)
3. README with demo GIF/video, architecture diagram, and "why this exists" positioning
4. Ship to portfolio — LANDR, Output, Splice targeting

---

## What This Is Not

- Not Suno. This does not generate music for you. You generate the music. This amplifies your ability to do so.
- Not a replacement for learning. The Teaching Agent explains the *why* so you get smarter every session.
- Not a generic chatbot with a music skin. The agent architecture, the validation layer, and the Ableton integration make this a real production tool.

---

## Key External Resources

- **Ableton MCP (primary)**: https://github.com/ahujasid/ableton-mcp
- **Ableton MCP (extended, 200+ tools)**: https://github.com/jpoindexter/ableton-mcp
- **music21 (theory validation)**: https://github.com/cuthbertLab/music21
- **Tone.js (browser audio preview)**: https://tonejs.github.io
- **AbletonMCP + ElevenLabs integration reference**: https://github.com/uisato/ableton-mcp-extended

---

## User Profile (Hardcoded for v1, Dynamic in v2)

```json
{
  "theory_level": "rusty_intermediate",
  "production_level": "beginner",
  "daw": "Ableton Live 12",
  "preferred_input_styles": ["mood_vibe", "artist_reference", "theory_request"],
  "teaching_preference": "explain_why_first_then_how",
  "preferred_genres": ["lo-fi", "trap", "electronic"]
}
```

---

*Last updated: 2026-04-09 — Phase 3a complete (B+ Orchestrator consolidation). Phase 3b UX Sprint in progress. Build sequence updated: 3a → 3b → 3c → Phase 4 MCP → Phase 5 Ops Sprint 2 → Phase 6 Demo.*
*Next update trigger: Any agent spec change, any architectural decision, any new dependency added*

---

## Phases 3a–3c Definition of Done — Before Moving to Phase 4 MCP

Phases 3a through 3c are not complete until ALL of the following pass:

### Architecture (Phase 3a ✅)
- [x] Orchestrator refactor complete (Option B+ — per architect decision log)
- [x] Teaching Agent wired to API (always, not local fallback)
- [x] Sound Engineering Agent API fallback for unknown topics
- [x] SE Agent contract mismatch resolved (local and API return same shape)
- [x] Architect skill onboarding run complete
- [x] ARCHITECTURE.md, BACKLOG.md, and decisions/ populated

### Features (Phase 3b — in progress)
- [ ] Sound Engineering Agent surfaced in UI with structured panel
- [ ] Artist blend intent surfaced in UI with attribution columns
- [ ] UX design sprint complete — Rubato branding, piano roll legibility, project create/open/resume, session history, onboarding flow, Keep confirmation loop

### Testing & Operational Readiness (Phase 3c)
- [ ] Contract tests passing for all 7 agents — verify input/output shapes match what both sides expect
- [ ] Integration tests passing for /api/generate across all intent types (mood_vibe, drum_pattern, sound_engineering, artist_blend, artist_reference)
- [ ] Unit tests passing for: TheoryValidator, detect_intent_local, key inference priority logic, enharmonic spelling
- [ ] All existing manual curl verification tests converted to automated pytest suite
- [ ] Regression check: all tests pass after every change
- [ ] Structured logging: every agent logs what it received, returned, and how long it took
- [ ] Health check endpoint (/api/health) actually verifies dependencies — music21 loaded, API key status
- [ ] Error handling: every agent has a defined fallback — no silent nulls reaching the frontend
- [ ] Secrets audit: no API keys in code or committed to git, .env.example exists
- [ ] README updated: a new person can clone and run the project from these instructions alone
- [ ] API documentation accurate at /docs
- [ ] BACKLOG.md and decisions/ up to date with all Phase 3 decisions

Only after all boxes are checked: begin Phase 4 MCP Integration.
