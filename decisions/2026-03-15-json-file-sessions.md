# Decision: JSON file session storage

Date: ~2026-03-15 (Phase 0-1)
Status: Decided

## Problem
Sessions need persistence — user returns to a session and sees their history, feedback, and project context. Need a storage solution for v1.

## Options considered
| Option | Summary | Why not chosen |
|--------|---------|---------------|
| In-memory only | No persistence, sessions lost on restart | Breaks the "return to session" requirement |
| SQLite | Structured local database | More complexity than needed for v1 single-user |
| **JSON files** | One JSON file per session in `memory/sessions/` | Chosen for simplicity |

## Decision
Each session is a JSON file at `memory/sessions/{session_id}.json`. `SessionManager` handles CRUD, history append, feedback recording, and project context updates. `get_or_create_session()` provides a safe entry point that always returns a valid session. Schema includes `UserProfile`, `ProjectContext`, and `HistoryEntry` list.

## Tradeoffs accepted
- Entire file rewritten on every `add_to_history` call — O(n) with history length
- No indexing, no querying across sessions, no relationships
- No max history size — files grow unbounded
- No concurrent access protection (fine for single-user v1)
- `list_sessions()` reads every file in the directory

## Deferred
- Migration to SQLite (CLAUDE.md specifies "SQLite for v1 session persistence, Postgres later")
- History pagination / max size
- Cross-session analytics (taste model)
