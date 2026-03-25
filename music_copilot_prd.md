# Music Copilot
## Product Requirements Document
| **Version:** 0.3 | **March 2026**

---

## Overview

| | |
|---|---|
| **Status** | PRD Refinement — for further investigation |
| **Goal** | Build a functional Music Copilot app: frontend in Cursor, backend knowledge base, eventual Ableton MCP connection and agentic actions |
| **Current State** | Existing Claude GPT project not producing desired results — upgrading to a proper app architecture |
| **Priority** | MVP front end + knowledge base first. Ableton MCP and agentic actions as Phase 2 |

---

## 1. Primary User

The primary user is a musician with a music theory background and approximately four weeks of Ableton experience. She has a strong foundation in how music should feel and sound but is early in translating that knowledge into production execution. The goal is to learn production competency — not to outsource creative decisions — while reducing the frustration of navigating Ableton's complexity without a structured guide. A key requirement is that the app makes sense out of the overwhelming number of options in Ableton and provides a more structured path through the production process.

Creative goals are intentionally non-mainstream. The user wants to develop a genre-spanning sound with an emphasis on originality and creative risk-taking. Suggestions should challenge and push rather than default to conventional approaches.

As a builder, the user also wants to develop hands-on experience running an agentic team to build a working product end to end. The build process itself is a learning objective alongside the product outcome.

---

## 2. Problem Statement

Music production is an expert domain. The tools are powerful but assume a level of knowledge that most musicians — even experienced ones with theory backgrounds — don't have when they start. The gap between musical intent and production execution is wide, and there is no good guide that bridges that gap in real time.

The current Claude GPT project provides some of this but lacks structure, persistence, a proper UI, and the ability to take action inside Ableton. The goal is to build a real application that closes this gap.

---

## 3. Objectives

The Music Copilot should accomplish four core things:

- Provide structure around the music production process — help a producer move from intent to execution with a clear framework
- Provide suggestions and ideas based on a curated knowledge base — music theory, sound engineering, genre-specific practices
- Assist with Ableton as a tool — troubleshoot, explain, guide, and eventually act inside the DAW
- Build the bones of a song from natural language prompting — markers, baseline chord progressions, drum foundations — reducing the blank canvas problem

---

## 4. Success Metrics — Phase 1

Phase 1 is working when:

- Music theory guidance is verifiably accurate — correct scales, accurate chord relationships, correct relative major and minor identification, accurate transposition. The user must be able to trust the knowledge base as a source of truth, not a starting point requiring further verification
- A production session can start with a natural language prompt and produce a usable starting structure within five minutes
- Knowledge base responses are specific enough to be actionable in Ableton without additional research
- The app reduces the blank canvas problem — a session starts with direction rather than paralysis
- The user can troubleshoot a specific Ableton problem through the app without leaving to search YouTube or forums

---

## 5. Non-Goals

Music Copilot is explicitly not:

- A sample library or loop browser
- A DAW replacement or alternative to Ableton
- A general music education platform or structured curriculum
- An AI music generator — the output is always human-made, AI-assisted
- A tool for users with no musical background — assumes basic music literacy

---

## 6. Build Team (Agentic Roles)

For this phase, the agentic component is a team of AI specialists rather than autonomous agents. Each role brings a focused capability to the build and consultation process:

| Role | Responsibility |
|---|---|
| **UX Designer** | Frontend design, user flow, interface layout, interaction patterns |
| **Architect** | System design, component structure, data flow, API contracts |
| **Backend Developer** | Knowledge base construction, API integrations, data layer, Ableton MCP connection (Phase 2) |
| **Strategist** | Product thinking, prioritization, scope decisions, roadmap sequencing |

---

## 7. Knowledge Base

The backend knowledge base is the core intelligence layer of the app. Accuracy is non-negotiable — the theory layer in particular must be deterministic and verifiable, not generative. It should be structured, queryable, and expandable.

### 7a. Music Theory
- Chords, scales, transposing, chord progressions, common sequences
- Correct relative major and minor identification, accurate transposition
- Genre-specific theory (start with 3 genres — TBD)
- Rules engine approach: if genre = X, suggest chord progressions Y, Z

### 7b. Sound Engineering
- Best practices by genre: EQ, reverb, compression, oscillator settings
- Rules-based guidance: if genre = X and instrument = Y, recommend settings Z

### 7c. Sound and Instrument Matching
- Instrument pairing recommendations by genre
- Idea generation: given a sonic intent, suggest instrument combinations

### 7d. Ableton as a Tool
- Ableton-specific knowledge: interface, workflow, features, shortcuts
- Source: scrape documentation, forums, support articles

### 7e. Production Tutorials and Artist Analysis
- YouTube tutorial ingestion — production techniques, genre walkthroughs
- Artist analysis videos — how specific artists achieve their sound
- Open question: model ingestion vs. structured summarization approach

### 7f. Facilitation and Project Structure
- Best practices for managing a music production project from idea to finished track
- Session structure, goal setting, creative block management

### 7g. Genre Knowledge
- Artist references, sonic signatures, production conventions by genre
- Start with 3 genres — determine in consultation with Seth

---

## 8. Connectivity and Integrations

| Integration | Purpose | Phase |
|---|---|---|
| **Cursor** | Primary development environment for frontend and backend | Phase 1 |
| **Ableton MCP** | Direct connection to Ableton Live for agentic actions inside the DAW | Phase 2 |
| **Hooktheory** | Chord progression data and song theory database. Public API available with limited endpoints. Third-party MCP server exists — evaluate for Phase 2. Note: user-generated data, verify accuracy approach. | Phase 2 — TBD |

---

## 9. Frontend — Screen Architecture

### Projects Repository
- List of active and archived projects
- Project creation, naming, genre tagging
- Session history per project

### Account and Settings
- User profile and preferences
- Knowledge base configuration — which genres, which knowledge domains to prioritize
- Integration settings — Ableton connection status, API keys

### Prompting Interface
- Primary interaction surface — natural language input
- Context-aware: knows which project you're in, what you've built so far
- Supports structured prompts (build me a chord progression) and freeform (I want this to feel lonely but not slow)

### Workspace
- Active session view — current project, current suggestions, current state
- Eventually: live view of Ableton state when MCP is connected
- Session notes and outputs — exportable

### Knowledge Categories
- Browsable knowledge base interface
- Music theory reference, sound engineering guides, genre profiles
- Allows direct querying outside of the prompting interface

---

## 10. Data Persistence and Privacy

Session history and project data must persist across conversations and sessions. The projects repository requires a reliable storage layer that maintains context between uses.

Key questions for Seth: where does this data live, how is it stored, and what are the implications of a cloud versus local architecture? Privacy is relevant given that creative work and personal project notes will be stored. Preference is for a solution that keeps user data secure and exportable.

---

## 11. Phased Roadmap

### Phase 1 — Core App (Current Focus)
- Frontend built in Cursor with the five screen areas above
- Backend knowledge base — music theory, sound engineering, genre knowledge (3 genres)
- Ableton documentation ingested as tool knowledge
- Claude API integration for prompting and response
- Projects repository with session persistence

### Phase 2 — Ableton Connection
- Ableton MCP integration — read and write to Live session
- Agentic actions: create tracks, set parameters, build song structure from prompt
- Real-time workspace view reflecting Ableton state
- Evaluate Hooktheory MCP alongside Ableton MCP

### Phase 3 — Expanded Intelligence
- Additional genres beyond initial 3
- YouTube tutorial and artist analysis ingestion
- Voice input for in-session prompting (hands on keyboard)

---

## 12. Open Questions to investigate

- Tech stack recommendation — what backend framework, vector DB for knowledge base, hosting?
- Knowledge base architecture — how do we ensure the music theory layer is deterministic and verifiable rather than generative? What architecture prevents hallucination in the theory domain specifically? RAG vs. fine-tuning vs. structured rules engine?
- Ableton MCP — what exists today, what needs to be built, what are the constraints?
- Hooktheory API — is this viable as a data source given the user-generated accuracy question, or should we build the theory layer from scratch?
- Genre selection — which 3 genres to start with given my production goals?
- Frontend framework recommendation — React, Next.js, other?
- Data persistence architecture — cloud vs. local, storage approach for session history
- Biggest risk in the current plan — what am I missing?

---

*Music Copilot PRD v0.3 | Shannon | March 2026*
