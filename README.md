# Music Co-Pilot

An AI-powered music production assistant built as a multi-agent system. The core thesis: be the "Lovable for music production" — a tool that understands both music theory and DAW workflows, translates natural language into validated chord progressions and step-by-step Ableton instructions, and teaches you *why* things work as it helps you build them. This is not Suno. It doesn't generate music for you. It amplifies your ability to generate music yourself.

![Screenshot](docs/screenshot-placeholder.png)

---

## Architecture

Music Co-Pilot uses a 7-agent architecture where each agent has a defined role, grounding context, and clear handoff protocol. The Orchestrator routes every request to the minimum set of agents required.

| Agent | Role |
|-------|------|
| **Orchestrator** | Entry point. Parses intent (mood/vibe, theory request, production question), manages token budget, routes to downstream agents. |
| **Theory Agent** | Generates musically accurate chord progressions with structured output (key, scale, chords with exact note names and octaves). |
| **Theory Validator** | Deterministic Python validation using music21. Checks note spelling, chord tones, voice leading, scale membership. Not an LLM — a quality gate. |
| **Production Agent** | Translates validated theory into step-by-step Ableton Live 12 instructions. MCP-commented for future automation. |
| **Teaching Agent** | Explains the *why* behind every suggestion. Adapts depth to user's theory level. |
| **Sound Engineering Agent** | Handles mixing, EQ, compression, sidechain, and sound design questions. Grounded in production best practices. |
| **UX Designer Agent** | Reviews frontend decisions during development. Not called on user requests. |
| **Technical Architect Agent** | Reviews architectural decisions during development. Not called on user requests. |

**Cost efficiency**: Local lookups handle theory data (20+ genre progressions, 18 drum patterns) with zero API cost. Tiered model routing uses Haiku for simple tasks, Sonnet for creative work.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.9+, FastAPI, Uvicorn |
| Frontend | React 18, Vite, CSS Modules |
| Theory Validation | music21 |
| Audio Preview | Tone.js |
| LLM | Anthropic Claude API (optional — local mode works without it) |
| Persistence | JSON file per session |

---

## Run Locally

### Prerequisites
- Python 3.9+
- Node.js 18+
- (Optional) Anthropic API key for enhanced generation

### Backend
```bash
cd ~/Documents/"Ableton Copilot"
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000
```
API docs: http://localhost:8000/docs

### Frontend
```bash
cd frontend
npm install
npm run dev
```
App: http://localhost:5173

### Test the API (no frontend required)
```bash
python test_api.py
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/generate` | POST | Main generation (prompt → agents → output) |
| `/api/session` | POST | Create new session |
| `/api/session/{id}` | GET | Get session by ID |
| `/api/session/{id}/history` | GET | Get session history |
| `/api/feedback` | POST | Record thumbs_up / thumbs_down / regenerate |

**Local mode**: Set `use_api: false` in the generate request to run entirely locally with zero API cost. Uses keyword-based intent detection and pre-built theory lookups.

---

## What's Built

### Phase 0: Foundation
- Project structure with agent modules
- Orchestrator with intent detection and routing
- Theory module: scales, chords, 20+ genre progressions, 18 drum patterns
- Theory Validator using music21
- Token tracking and cost management
- End-to-end pipeline verified

### Phase 1: Core Loop
- Production Agent with Ableton Live 12 instructions (MCP-ready)
- Teaching Agent with adaptive explanations
- Session memory with JSON persistence
- FastAPI backend with 6 endpoints
- React frontend with Theory, Production, and Session panels
- Tone.js audio preview
- Drum grid visualization
- Feedback UI (thumbs up/down)

---

## What's Next

### Phase 2: Polish & Demo-Readiness
- UX Designer Agent reviews frontend
- Clarification loop for ambiguous input
- Sound Engineering Agent integration
- Cost logging dashboard
- 60-second demo video

### Phase 3: Ableton MCP Integration
- Connect to Ableton Live via MCP (Model Context Protocol)
- Production Agent's MCP comments become live automation
- Prompt in browser → chord progression appears in Ableton Piano Roll

---

## Design Philosophy

**Amplify, don't replace.** Every design decision flows from this principle:

1. **The human composes.** The system suggests, validates, and teaches — but the creative decisions stay with the user.

2. **Correctness is non-negotiable.** Music theory output passes through deterministic validation. The LLM doesn't get the final word on whether an A belongs in a C major chord.

3. **Teach as you go.** Every suggestion comes with an explanation. The user should understand more about music theory after each session, not less.

4. **Minimize friction to output.** Natural language in, validated progressions out, with exact Ableton steps to build it. No manual translation required.

5. **Cost-aware by design.** Not every request needs 7 agents. Local lookups handle the common cases. The LLM is called only when it adds value.

---

## Project Structure

```
/agents              Orchestrator, Production, Teaching agents
/api                 FastAPI backend
/docs                Grounding documents (Ableton guide, music theory, etc.)
/frontend            React app (Vite)
/memory              Session persistence
/theory              Local music theory lookups
/utils               Token tracking, model config
/validator           music21 validation scripts
CLAUDE.md            Architecture spec and build sequencing
```

---

## License

MIT

---

*Built by someone learning Ableton who got tired of Claude hallucinating chord progressions.*
