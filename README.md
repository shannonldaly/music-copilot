# Music Co-Pilot (Rubato)

An AI-powered music production assistant built as a multi-agent system. Type a mood, genre, or artist reference — get a validated chord progression with Ableton instructions, a theory explanation, and audio preview. Not Suno. This doesn't generate music for you. It amplifies your ability to generate music yourself.

## Quick Start (5 minutes)

### Prerequisites
- Python 3.9+
- Node.js 18+
- (Optional) [Anthropic API key](https://console.anthropic.com/) for enhanced teaching explanations

### 1. Clone and set up backend
```bash
git clone https://github.com/shannonldaly/music-copilot.git
cd music-copilot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY (optional — app works without it)
```

### 3. Start the backend
```bash
uvicorn api.main:app --reload --port 8000
```

### 4. Verify it's working
```bash
curl http://localhost:8000/api/health
# Should return: {"status": "ok" or "degraded", "music21": true, "api_key_configured": true/false, ...}
```

### 5. Start the frontend (separate terminal)
```bash
cd frontend
npm install
npm run dev
# App runs at http://localhost:5173
```

### 6. Run tests
```bash
pytest tests/
# 92 tests across contract, integration, unit, and regression suites
```

---

## Architecture

The Orchestrator receives every request, detects intent via keyword matching (or Haiku LLM), routes to the minimum set of agents needed, assembles a structured response, and returns it. Theory output is validated by music21 before reaching the user. The Teaching Agent calls the Sonnet API for quality explanations when an API key is available, falling back to local templates when it's not. All agent calls are logged with structured fields (agent_name, method, duration_ms, success) ready for Postgres in Phase 5.

For the full system diagram and agent inventory, see [ARCHITECTURE.md](ARCHITECTURE.md).

| Agent | Role |
|-------|------|
| **Orchestrator** | Intent detection, routing, response assembly. Single entry point via `execute()`. |
| **Theory Agent** | Chord progressions with alternatives and melody direction. Local + API modes. |
| **Theory Validator** | Deterministic music21 validation. Not an LLM — a quality gate. |
| **Production Agent** | Step-by-step Ableton Live 12 instructions with MCP v2 comments. |
| **Teaching Agent** | Explains the *why*. Sonnet API when key available, local templates as fallback. |
| **Sound Engineering Agent** | Mixing, EQ, compression, sidechain. 9 local topics + API fallback. |
| **Session Manager** | JSON-based session persistence with history and feedback tracking. |

---

## API

Interactive docs at [http://localhost:8000/docs](http://localhost:8000/docs) when the server is running.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Dependency health check (music21, API key status) |
| `/api/generate` | POST | Main generation — prompt in, structured music data out |
| `/api/progression/expand` | POST | Expand a lightweight alternative to full note-level data |
| `/api/session` | POST | Create new session |
| `/api/session/{id}` | GET | Get session |
| `/api/session/{id}` | PATCH | Update session (e.g. song name) |
| `/api/session/{id}/history` | GET | Session history with feedback |
| `/api/sessions` | GET | List all sessions |
| `/api/feedback` | POST | Record thumbs_up / thumbs_down / regenerate / progression_swap |
| `/api/project` | POST | Update project context (key, BPM, genre) |

---

## Project Structure

```
/agents              Orchestrator + all agent modules
/api                 FastAPI backend + progression utilities
/docs                Grounding documents (music theory, Ableton guide, artist DNA, etc.)
/frontend            React app (Vite, CSS Modules, Tone.js)
/memory              Session persistence (JSON files)
/services            External integrations (empty — MCP client goes here in Phase 4)
/tests               pytest suite: contract/, integration/, unit/, regression/
/theory              Local music theory lookups (scales, chords, progressions, drums)
/utils               Token tracking, model config, structured logging
/validator           music21 validation scripts
/decisions           Architectural decision logs
ARCHITECTURE.md      System diagram + agent inventory
BACKLOG.md           Known gaps and deferred items
CLAUDE.md            Project spec, agent contracts, build sequencing
```

---

## Build Status

| Phase | Status |
|-------|--------|
| 0 — Foundation | Complete |
| 1 — Core Loop | Complete |
| 2 — Polish & Demo-Readiness | Complete |
| 3a — Architecture & Agent Quality | Complete |
| 3b — UX Design Sprint | In Progress |
| 3c — Operational Readiness | In Progress |
| 4 — Ableton MCP Integration | Planned |
| 5 — Operational Readiness Sprint 2 | Planned |
| 6 — Demo | Planned |

---

*Built by someone learning Ableton who got tired of Claude hallucinating chord progressions.*
