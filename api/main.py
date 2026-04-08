"""
FastAPI Backend — Music Co-Pilot API

Endpoints:
- POST /api/generate - Main generation endpoint (orchestrator → agents)
- POST /api/session - Create new session
- PATCH /api/session/{id} - Update session (e.g. song_name)
- GET /api/session/{id} - Get session
- POST /api/feedback - Record feedback on output
- GET /api/health - Health check

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
    """Request for music generation."""
    prompt: str = Field(..., description="User's request", min_length=1)
    session_id: Optional[str] = Field(None, description="Session ID for context")
    use_api: bool = Field(False, description="Use LLM API (costs money) vs local only")


class GenerateResponse(BaseModel):
    """Response from generation."""
    success: bool
    session_id: str
    intent: str
    confidence: float

    # Core outputs
    progressions: Optional[List[Dict]] = None
    drum_patterns: Optional[List[Dict]] = None
    progression: Optional[Dict] = None

    # Sidebar (Phase 2)
    key: Optional[str] = None
    key_was_specified: bool = False
    bpm: Optional[int] = None
    progression_name: Optional[str] = None
    genre_context: Optional[str] = None

    # Agent outputs
    production_steps: Optional[str] = None
    teaching_note: Optional[str] = None

    # Theory Agent extended output
    alternatives: Optional[List[Dict]] = None
    melody_direction: Optional[Dict] = None

    # Sound Engineering Agent output
    sound_engineering_response: Optional[Dict] = None

    # Artist Blend output
    artist_blend: Optional[Dict] = None

    # Validation
    validation: Optional[Dict] = None

    # Metadata
    tokens_used: Optional[int] = None
    cost_usd: Optional[float] = None
    clarification_needed: bool = False
    clarification_question: Optional[str] = None


class FeedbackRequest(BaseModel):
    """Feedback on a generation."""
    session_id: str
    entry_index: int = Field(-1, description="History entry index (-1 for last)")
    feedback: str = Field(
        ...,
        description="thumbs_up, thumbs_down, regenerate, progression_swap",
    )
    swap_label: Optional[str] = None


class SessionCreateBody(BaseModel):
    theory_level: str = "rusty_intermediate"
    production_level: str = "beginner"
    session_mode: Optional[str] = None


class SessionPatchBody(BaseModel):
    """Partial session update. song_name is stored on current_project.name."""
    song_name: Optional[str] = None


class SessionResponse(BaseModel):
    """Session data response."""
    session_id: str
    created_at: str
    user_profile: Dict
    current_project: Dict
    history_count: int
    session_mode: Optional[str] = None


class ExpandProgressionRequest(BaseModel):
    """Expand alternative chord names to full note-level progression."""
    chords: List[str] = Field(..., min_length=1)
    key: str = Field(..., min_length=1)
    progression_name: str = Field(..., min_length=1)
    session_id: Optional[str] = None


class ExpandProgressionResponse(BaseModel):
    success: bool
    key: str
    scale: str
    progression_name: str
    chords: List[Dict]
    validation: Optional[Dict] = None


class ProjectUpdateRequest(BaseModel):
    """Update project context."""
    session_id: str
    key: Optional[str] = None
    bpm: Optional[int] = None
    genre: Optional[str] = None
    name: Optional[str] = None


# =============================================================================
# Endpoints
# =============================================================================

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
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
