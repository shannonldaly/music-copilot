# CLAUDE.md — Music Co-Pilot

## What This Project Is

An AI-powered music production co-pilot built as a multi-agent system. The user is a music producer learning Ableton Live — rusty on theory, beginner on production — who wants a tool that amplifies creative intent without replacing it. Think "Lovable for music production."

This is simultaneously:
1. A real tool the user actually uses while making music
2. A portfolio artifact to show companies like LANDR, Output, and Splice
3. A learning project to understand multi-agent orchestration

**North Star**: Keep the human creative and in control. Remove every technical barrier between intent and output. Never replace the composer — amplify them.

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

**Grounded in**: `/docs/music_theory.md` (Music Composition, Music Theory Best Practices & Chord Progressions Across All Genres)

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
  "theory_explanation": "This progression stays in natural minor and avoids resolution — the VII chord never quite settles, which creates the looping, unresolved feeling common in lo-fi and trap production.",
  "voice_leading_notes": "Smooth voice leading between Am and F — C is a common tone, A moves down a semitone to A, E moves down a step to F. Minimal movement."
}
```

**Critical rules**:
- Always output exact note names with octave numbers (e.g., C4, not just C)
- Never suggest notes outside the stated scale without explicitly flagging it as a borrowed chord
- Always pass output to Theory Validator before it reaches the user
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

**Grounded in**:
- `/docs/electronic_music_production.md` (Electronic Music Production: History, How-To, Best Practices & Sound Engineering)
- `/docs/mixing_cheat_sheet.md` (Instrument-specific EQ, compression, and reverb reference)

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

## The 6 Things Not to Forget

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

### 5. CLAUDE.md is the Bridge
This file is what connects planning (Claude.ai Projects) to building (Claude Code). Every time a new Claude Code session starts, it reads this file first. Every architectural decision, every agent spec, every "don't forget" item lives here.

**Maintenance rule**: When a decision changes during the build, update this file immediately. Don't let it go stale. It's the source of truth.

### 6. API Cost Awareness
Seven agents on every request is expensive. The Orchestrator enforces routing discipline.

**Rules**:
- Log every API call: agent name, token count (input + output), timestamp
- Set a per-request budget cap (start at 4,000 tokens total across all agents)
- The Theory Validator is free (deterministic Python, no API call)
- The UX Designer Agent and Technical Architect Agent are NOT called on user music requests — they are called during development sessions only
- Display running cost in the dev UI (not in the demo UI) so you can see what each request costs in real time

---

## Build Sequencing

### Phase 0 — Foundation (Do This First, Before Any App Code)
*Goal: The skeleton exists and every agent can communicate.*

1. Set up project repo with clear folder structure:
   ```
   /agents          — one Python file per agent
   /docs            — the three grounding documents
   /validator       — music21 validation scripts
   /frontend        — React app
   /memory          — session JSON storage
   CLAUDE.md        — this file
   ```
2. Install dependencies: `anthropic`, `music21`, `fastapi`, `uvicorn`
3. Write the Orchestrator as a simple router — hardcode one intent type to start
4. Write the Theory Agent with structured JSON output
5. Write the Theory Validator Python script and confirm music21 catches a known error
6. Confirm the Orchestrator → Theory Agent → Validator pipeline works end to end with a test prompt

**Do not build the frontend yet. Do not build all agents at once. Confirm the core loop works first.**

### Phase 1 — Core Loop (First Working Version)
*Goal: Type a prompt, get a validated chord progression with explanation and Ableton steps.*

1. Add Production Agent
2. Add Teaching Agent
3. Add session memory (JSON read/write)
4. Build minimal frontend: input box, three output panels (chords, Ableton steps, teaching note), thinking states for each agent
5. Add Tone.js audio preview
6. Add thumbs up/down feedback UI

**Definition of done**: You can type "give me something melancholic, lo-fi, minor key" and receive a validated chord progression that plays in the browser, with Ableton steps and a teaching note — and it's saved to session history.

### Phase 2 — Polish & Demo-Readiness
*Goal: Something you'd show an employer without apologizing for anything.*

1. UX Designer Agent reviews and overhauls the frontend
2. Add clarification loop for ambiguous input
3. Add Sound Engineering Agent to the routing
4. Refine Teaching Agent calibration based on actual use
5. Add cost logging dashboard (dev-only)
6. Record a 60-second demo video

### Phase 3 — Ableton MCP Integration
*Goal: Chord progressions appear directly in Ableton, no copy-paste.*

1. Install and configure `ableton-mcp` (evaluate ahujasid vs jpoindexter versions)
2. Convert Production Agent's MCP-commented pseudocode into live MCP calls
3. Test end-to-end: prompt in browser → chord progression in Ableton Piano Roll
4. This is the employer demo that closes the room

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

*Last updated: Session 1 — Architecture & Planning*
*Next update trigger: Any agent spec change, any architectural decision, any new dependency added*
