"""
FastAPI Backend — Music Co-Pilot API

Endpoints:
- POST /api/generate - Main generation endpoint (orchestrator → agents)
- POST /api/send-to-ableton - Send progression to Ableton via MCP
- POST /api/session - Create new session
- PATCH /api/session/{id} - Update session (e.g. song_name)
- GET /api/session/{id} - Get session
- POST /api/feedback - Record feedback on output
- GET /api/health - Health check (music21, API key, Ableton connection)

Run with:
    uvicorn api.main:app --reload --port 8000
"""

import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.progression_utils import expand_chords_from_names

from agents.orchestrator import Orchestrator
from memory import SessionManager, get_or_create_session, UserProfile, ProjectContext
from services.mcp_client import AbletonMCPClient


# =============================================================================
# App Setup
# =============================================================================

app = FastAPI(
    title="Music Co-Pilot API",
    description="AI-powered music production assistant",
    version="0.1.0",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
session_manager = SessionManager()


# =============================================================================
# Request/Response Models
# =============================================================================

class GenerateRequest(BaseModel):
    """Request for music generation.

    use_api controls intent detection and creative generation mode:
    - False (default): keyword intent detection, curated local databases.
      Teaching Agent still calls Sonnet API when ANTHROPIC_API_KEY is set
      (quality decision), SE Agent falls back to API for unrecognized topics.
    - True: Haiku LLM for intent detection, Sonnet for all creative agents.
    """
    prompt: str = Field(..., description="User's request", min_length=1)
    session_id: Optional[str] = Field(None, description="Session ID for context")
    use_api: bool = Field(False, description="Use LLM for intent detection and all creative agents")


class GenerateResponse(BaseModel):
    """Full response from the generation pipeline. Fields populated depend on intent type."""
    success: bool = Field(..., description="Whether the request completed successfully")
    session_id: str = Field(..., description="Session ID for this request (auto-created if not provided)")
    intent: str = Field(..., description="Detected intent type: mood_vibe, drum_pattern, sound_engineering, artist_blend, artist_reference, production_question")
    confidence: float = Field(..., description="Intent detection confidence (0.0–1.0)")

    # Core outputs
    progressions: Optional[List[Dict]] = Field(None, description="Array of full note-level progressions. Each has: name, numerals, key, chords (with numeral, name, note_names), tempo_range, moods, genres")
    drum_patterns: Optional[List[Dict]] = Field(None, description="Array of drum patterns. Each has: name, description, tempo_range, swing, grid (sound→step arrays), genres")
    progression: Optional[Dict] = Field(None, description="The primary progression (first item of progressions array), for convenience")

    # Sidebar metadata
    key: Optional[str] = Field(None, description="Musical key of the primary progression, e.g. 'A minor', 'Bb major'")
    key_was_specified: bool = Field(False, description="True if the user explicitly requested a key in their prompt")
    bpm: Optional[int] = Field(None, description="Tempo in BPM (midpoint of tempo_range)")
    progression_name: Optional[str] = Field(None, description="Name of the primary progression or drum pattern")
    genre_context: Optional[str] = Field(None, description="Comma-separated genre tags for the result")

    # Agent outputs
    production_steps: Optional[str] = Field(None, description="Markdown string with step-by-step Ableton Live instructions and MCP v2 comments")
    teaching_note: Optional[str] = Field(None, description="Markdown string explaining why the progression works — music theory education")

    # Theory Agent extended output
    alternatives: Optional[List[Dict]] = Field(None, description="3 alternative progressions: darker, more movement, unexpected. Each has: label, progression_name, chords (as {name, numeral} objects), character")
    melody_direction: Optional[Dict] = Field(None, description="Melody guidance: start_note, start_note_context, contour, rhythm_feel, avoid_on_strong_beats, avoid_context, suggested_range, artist_reference")

    # Sound Engineering Agent output
    sound_engineering_response: Optional[Dict] = Field(None, description="Structured SE advice: summary, steps (list), ableton_path, principle, artist_reference")

    # Artist Blend output
    artist_blend: Optional[Dict] = Field(None, description="Blend of two artists: artist_1, artist_2, blend_description, from_artist_1, from_artist_2, production_direction")

    # Validation
    validation: Optional[Dict] = Field(None, description="Theory validation result: passed (bool), errors (list), warnings (list), corrected_output")

    # Metadata
    tokens_used: Optional[int] = Field(None, description="Total API tokens used for this request (0 in local mode)")
    cost_usd: Optional[float] = Field(None, description="Estimated API cost in USD for this request")
    clarification_needed: bool = Field(False, description="If true, the orchestrator needs more info — check clarification_question")
    clarification_question: Optional[str] = Field(None, description="The one clarifying question to ask the user before proceeding")


class FeedbackRequest(BaseModel):
    """Record user feedback on a generation output."""
    session_id: str = Field(..., description="Session ID containing the history entry")
    entry_index: int = Field(-1, description="History entry index to apply feedback to (-1 for most recent)")
    feedback: str = Field(
        ...,
        description="Feedback type: thumbs_up, thumbs_down, regenerate, or progression_swap",
    )
    swap_label: Optional[str] = Field(None, description="Required when feedback is progression_swap — the alternative label to swap in")


class SessionCreateBody(BaseModel):
    """Create a new session with user profile settings."""
    theory_level: str = Field("rusty_intermediate", description="User theory level: beginner, rusty_intermediate, intermediate, advanced")
    production_level: str = Field("beginner", description="User production level: beginner, intermediate, advanced")
    session_mode: Optional[str] = Field(None, description="Session workflow mode: chords, drums, mixing, or full")


class SessionPatchBody(BaseModel):
    """Partial session update. song_name is stored on current_project.name."""
    song_name: Optional[str] = Field(None, description="New display name for the session/project")


class SessionResponse(BaseModel):
    """Session data returned by session CRUD endpoints."""
    session_id: str = Field(..., description="Unique session identifier (UUID)")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    user_profile: Dict = Field(..., description="User profile: theory_level, production_level, preferred_genres, daw")
    current_project: Dict = Field(..., description="Current project context: key, bpm, genre, name")
    history_count: int = Field(..., description="Number of history entries in this session")
    session_mode: Optional[str] = Field(None, description="Session workflow mode: chords, drums, mixing, or full")


class ExpandProgressionRequest(BaseModel):
    """Expand lightweight alternative chord names to full note-level data + validation."""
    chords: List[str] = Field(..., min_length=1, description="Chord names to expand, e.g. ['Am', 'F', 'Dm', 'G']")
    key: str = Field(..., min_length=1, description="Musical key, e.g. 'A minor'")
    progression_name: str = Field(..., min_length=1, description="Progression name, e.g. 'i – VI – iv – VII'")
    session_id: Optional[str] = Field(None, description="Optional session ID for context")


class ExpandProgressionResponse(BaseModel):
    """Full note-level expansion of a lightweight alternative progression."""
    success: bool = Field(..., description="Whether expansion succeeded")
    key: str = Field(..., description="Musical key used for expansion")
    scale: str = Field(..., description="Scale type: natural minor, major, etc.")
    progression_name: str = Field(..., description="Progression name")
    chords: List[Dict] = Field(..., description="Full chord data with numeral, name, note_names for each chord")
    validation: Optional[Dict] = Field(None, description="Theory validation result for the expanded progression")


class ProjectUpdateRequest(BaseModel):
    """Update the current project context for a session."""
    session_id: str = Field(..., description="Session ID to update")
    key: Optional[str] = Field(None, description="Musical key, e.g. 'A minor'")
    bpm: Optional[int] = Field(None, description="Tempo in BPM")
    genre: Optional[str] = Field(None, description="Genre tag, e.g. 'lo-fi'")
    name: Optional[str] = Field(None, description="Project display name")


# =============================================================================
# Endpoints
# =============================================================================

@app.get("/api/health")
async def health_check():
    """Health check — verifies actual dependencies, not just 'I'm running'.

    Returns structured status: music21 loaded, API key configured.
    Status is 'ok' if all dependencies pass, 'degraded' if any fail.
    """
    checks = {}

    # Check music21
    try:
        from music21 import pitch
        pitch.Pitch("C4")
        checks["music21"] = True
    except Exception:
        checks["music21"] = False

    # Check API key (don't call the API, just verify env var exists)
    checks["api_key_configured"] = bool(os.environ.get("ANTHROPIC_API_KEY"))

    # Check Ableton MCP connection
    checks["ableton_connected"] = AbletonMCPClient().is_connected()

    all_ok = all(checks.values())

    return {
        "status": "ok" if all_ok else "degraded",
        "music21": checks["music21"],
        "api_key_configured": checks["api_key_configured"],
        "ableton_connected": checks["ableton_connected"],
        "timestamp": datetime.now().isoformat(),
        "version": "0.1.0",
    }


@app.post("/api/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """
    Main generation endpoint.

    Delegates to Orchestrator.execute() for the full pipeline:
    intent detection → local lookup → agent calls → response assembly.
    """
    session = get_or_create_session(session_manager, request.session_id)
    orchestrator = Orchestrator()

    result = orchestrator.execute(request.prompt, use_api=request.use_api)
    result["session_id"] = session.session_id

    # Clarification-only responses skip history
    if result.get("clarification_needed"):
        result.setdefault("key_was_specified", False)
        return GenerateResponse(**result)

    # Save to session history
    session_manager.add_to_history(
        session,
        request=request.prompt,
        intent_type=result.get("intent", "unknown"),
        output={
            "progressions": result.get("progressions"),
            "drum_patterns": result.get("drum_patterns"),
        },
    )

    result.setdefault("key_was_specified", False)
    return GenerateResponse(**result)


class SendToAbletonRequest(BaseModel):
    """Send the current progression to Ableton via MCP."""
    progression: Dict = Field(..., description="Progression dict with 'chords' list (each chord has name, numeral, note_names)")
    bpm: int = Field(120, description="Tempo in BPM")


@app.post("/api/send-to-ableton")
async def send_to_ableton(request: SendToAbletonRequest):
    """Send a chord progression to Ableton Live via the MCP socket server.

    Creates a MIDI track named 'Rubato Chords', sets the tempo, creates a clip,
    and adds all chord notes. Returns {success, message}.
    If Ableton is not running, returns graceful failure.
    """
    client = AbletonMCPClient()
    result = client.send_progression_to_ableton(request.progression, bpm=request.bpm)
    return {"success": result["success"], "message": result["message"]}


@app.post("/api/session", response_model=SessionResponse)
async def create_session(body: SessionCreateBody = Body()):
    """Create a new session (optional session_mode for Phase 2 workflow)."""
    profile = UserProfile(
        theory_level=body.theory_level,
        production_level=body.production_level,
    )
    session = session_manager.create_session(
        user_profile=profile,
        project_context=ProjectContext(name="Untitled Session"),
        session_mode=body.session_mode,
    )

    return SessionResponse(
        session_id=session.session_id,
        created_at=session.created_at,
        user_profile=session.user_profile.__dict__,
        current_project=session.current_project.__dict__,
        history_count=0,
        session_mode=session.session_mode,
    )


@app.patch("/api/session/{session_id}", response_model=SessionResponse)
async def patch_session(session_id: str, body: SessionPatchBody = Body(...)):
    """Update session fields. song_name maps to current project display name."""
    session = session_manager.load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if body.song_name is not None:
        cleaned = body.song_name.strip() or "Untitled Session"
        session_manager.update_project_context(session, name=cleaned)
        session = session_manager.load_session(session_id)

    return SessionResponse(
        session_id=session.session_id,
        created_at=session.created_at,
        user_profile=session.user_profile.__dict__,
        current_project=session.current_project.__dict__,
        history_count=len(session.history),
        session_mode=session.session_mode,
    )


@app.get("/api/session/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get session by ID."""
    session = session_manager.load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionResponse(
        session_id=session.session_id,
        created_at=session.created_at,
        user_profile=session.user_profile.__dict__,
        current_project=session.current_project.__dict__,
        history_count=len(session.history),
        session_mode=session.session_mode,
    )


@app.get("/api/session/{session_id}/history")
async def get_session_history(session_id: str, limit: int = Query(10)):
    """Get session history."""
    session = session_manager.load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    recent = session_manager.get_recent_history(session, count=limit)
    return {
        "session_id": session_id,
        "history": [
            {
                "timestamp": h.timestamp,
                "request": h.request,
                "intent_type": h.intent_type,
                "feedback": h.feedback,
            }
            for h in recent
        ],
    }


@app.post("/api/progression/expand", response_model=ExpandProgressionResponse)
async def expand_progression(req: ExpandProgressionRequest):
    """Expand chord names to full note-level data + music21 validation."""
    try:
        chords_out, val, scale = expand_chords_from_names(
            req.chords,
            req.key.strip(),
            req.progression_name.strip(),
        )
        return ExpandProgressionResponse(
            success=True,
            key=req.key.strip(),
            scale=scale,
            progression_name=req.progression_name.strip(),
            chords=chords_out,
            validation=val,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/feedback")
async def record_feedback(request: FeedbackRequest):
    """Record feedback on a generation."""
    session = session_manager.load_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if request.feedback not in [
        "thumbs_up",
        "thumbs_down",
        "regenerate",
        "progression_swap",
    ]:
        raise HTTPException(status_code=400, detail="Invalid feedback type")

    if request.feedback == "progression_swap" and not request.swap_label:
        raise HTTPException(status_code=400, detail="swap_label required for progression_swap")

    success = session_manager.record_feedback(
        session,
        entry_index=request.entry_index,
        feedback=request.feedback,
        feedback_label=request.swap_label,
    )

    if not success:
        raise HTTPException(status_code=400, detail="Could not record feedback")

    return {
        "success": True,
        "feedback": request.feedback,
        "swap_label": request.swap_label,
    }


@app.post("/api/project")
async def update_project(request: ProjectUpdateRequest):
    """Update project context."""
    session = session_manager.load_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session_manager.update_project_context(
        session,
        key=request.key,
        bpm=request.bpm,
        genre=request.genre,
        name=request.name,
    )

    return {
        "success": True,
        "current_project": session.current_project.__dict__,
    }


@app.get("/api/sessions")
async def list_sessions():
    """List all sessions."""
    sessions = session_manager.list_sessions()
    return {"sessions": sessions}


# =============================================================================
# Run server
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
