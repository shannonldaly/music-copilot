"""
FastAPI Backend — Music Co-Pilot API

Endpoints:
- POST /api/generate - Main generation endpoint (orchestrator → agents)
- POST /api/session - Create new session
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

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.orchestrator import Orchestrator, IntentType
from agents.production_agent import (
    ProductionAgent,
    generate_chord_instructions_local,
    generate_drum_instructions_local,
)
from agents.teaching_agent import (
    TeachingAgent,
    generate_progression_explanation_local,
    generate_rhythm_explanation_local,
)
from validator import TheoryValidator, validate_progression
from memory import SessionManager, get_or_create_session, UserProfile, ProjectContext
from utils.tokens import TokenTracker


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

    # Agent outputs
    production_steps: Optional[str] = None
    teaching_note: Optional[str] = None

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
    feedback: str = Field(..., description="thumbs_up, thumbs_down, or regenerate")


class SessionResponse(BaseModel):
    """Session data response."""
    session_id: str
    created_at: str
    user_profile: Dict
    current_project: Dict
    history_count: int


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


def detect_intent_local(prompt: str) -> tuple:
    """
    Simple keyword-based intent detection (no API needed).

    Returns (intent_type, confidence, extracted_data)
    """
    prompt_lower = prompt.lower()

    # Keywords for each intent
    mood_keywords = ['melancholic', 'happy', 'sad', 'dark', 'chill', 'uplifting',
                     'epic', 'dreamy', 'nostalgic', 'aggressive', 'romantic']
    genre_keywords = ['lo-fi', 'lofi', 'trap', 'jazz', 'rock', 'pop', 'edm',
                      'house', 'hip-hop', 'hip hop', 'r&b', 'classical', 'ambient']
    drum_keywords = ['beat', 'drum', 'rhythm', 'pattern', 'groove']
    production_keywords = ['how do i', 'how to', 'sidechain', 'eq', 'compress',
                          'reverb', 'delay', 'mix', 'master']

    extracted = {'moods': [], 'genres': []}

    # Check for moods
    for mood in mood_keywords:
        if mood in prompt_lower:
            extracted['moods'].append(mood)

    # Check for genres
    for genre in genre_keywords:
        if genre in prompt_lower:
            extracted['genres'].append(genre.replace('-', '_'))

    # Determine intent type
    if any(kw in prompt_lower for kw in production_keywords):
        return ('production_question', 0.8, extracted)
    elif any(kw in prompt_lower for kw in drum_keywords):
        extracted['genres'] = extracted['genres'] or ['trap']  # Default to trap
        return ('drum_pattern', 0.85, extracted)
    elif extracted['moods'] or extracted['genres']:
        return ('mood_vibe', 0.9, extracted)
    else:
        # Default to mood_vibe with generic extraction
        return ('mood_vibe', 0.5, {'moods': [], 'genres': []})


@app.post("/api/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """
    Main generation endpoint.

    Takes a user prompt, routes through orchestrator, returns music data.
    """
    # Get or create session
    session = get_or_create_session(session_manager, request.session_id)

    # Use local intent detection if not using API
    if not request.use_api:
        intent_type, confidence, extracted = detect_intent_local(request.prompt)

        # Build a mock result for local processing
        class LocalResult:
            pass

        result = LocalResult()
        result.clarification_needed = False
        result.clarification_question = None

        class LocalIntent:
            pass

        result.intent = LocalIntent()
        result.intent.intent_type = IntentType(intent_type)
        result.intent.confidence = confidence
        result.intent.extracted = extracted
        result.token_summary = {"total_tokens": 0, "total_cost_usd": 0.0}

        # Do local lookup based on intent
        from theory import search_progressions, get_drum_patterns_by_genre

        result.local_data = {}

        if intent_type in ['mood_vibe', 'theory_request']:
            moods = extracted.get('moods', [])
            genres = extracted.get('genres', [])

            progressions = []
            for mood in moods:
                progs = search_progressions(mood=mood)
                progressions.extend(progs)
            for genre in genres:
                progs = search_progressions(genre=genre)
                progressions.extend(progs)

            if not progressions and not moods and not genres:
                # Default search
                progressions = search_progressions(mood='melancholic')

            # Dedupe and convert
            seen = set()
            unique = []
            for p in progressions:
                if p.name not in seen:
                    seen.add(p.name)
                    unique.append(p)

            # Convert to chord data
            from theory import get_progression_chords
            result.local_data['progressions'] = []
            for prog in unique[:3]:
                try:
                    chords = get_progression_chords(prog.numerals, 'A', prog.key_type, octave=3)
                    result.local_data['progressions'].append({
                        'name': prog.name,
                        'numerals': prog.numerals,
                        'key': f'A {prog.key_type}',
                        'chords': chords,
                        'tempo_range': prog.tempo_range,
                        'description': prog.description,
                        'moods': prog.moods,
                        'genres': prog.genres,
                    })
                except ValueError:
                    pass

        elif intent_type == 'drum_pattern':
            genres = extracted.get('genres', ['trap'])
            patterns = []
            for genre in genres:
                genre_patterns = get_drum_patterns_by_genre(genre)
                patterns.extend(genre_patterns)

            seen = set()
            unique = []
            for p in patterns:
                if p.name not in seen:
                    seen.add(p.name)
                    unique.append(p)

            result.local_data['drum_patterns'] = []
            for pattern in unique[:3]:
                result.local_data['drum_patterns'].append({
                    'name': pattern.name,
                    'description': pattern.description,
                    'tempo_range': pattern.tempo_range,
                    'swing': pattern.swing,
                    'grid': pattern.to_grid(),
                    'genres': pattern.genres,
                })
    else:
        # Use full orchestrator with API
        orchestrator = Orchestrator()
        result = orchestrator.process(request.prompt)

    # Check for clarification needed
    if result.clarification_needed:
        return GenerateResponse(
            success=True,
            session_id=session.session_id,
            intent=result.intent.intent_type.value,
            confidence=result.intent.confidence,
            clarification_needed=True,
            clarification_question=result.clarification_question,
        )

    # Build response
    response_data = {
        "success": True,
        "session_id": session.session_id,
        "intent": result.intent.intent_type.value,
        "confidence": result.intent.confidence,
    }

    # Process local data
    if result.local_data:
        # Progressions
        if "progressions" in result.local_data:
            response_data["progressions"] = result.local_data["progressions"]

            # Validate first progression
            if result.local_data["progressions"]:
                prog = result.local_data["progressions"][0]
                validation_data = {
                    "key": prog["key"],
                    "chords": [
                        {
                            "numeral": c["numeral"],
                            "name": c["name"],
                            "notes": c["note_names"],
                        }
                        for c in prog["chords"]
                    ]
                }
                validator = TheoryValidator()
                validation_result = validator.validate_progression(validation_data)
                response_data["validation"] = validation_result.to_dict()

                # Generate production steps (local)
                response_data["production_steps"] = generate_chord_instructions_local(prog)

                # Generate teaching note (local)
                response_data["teaching_note"] = generate_progression_explanation_local(prog)

        # Drum patterns
        if "drum_patterns" in result.local_data:
            response_data["drum_patterns"] = result.local_data["drum_patterns"]

            if result.local_data["drum_patterns"]:
                pattern = result.local_data["drum_patterns"][0]

                # Generate production steps for drums
                if not response_data.get("production_steps"):
                    response_data["production_steps"] = generate_drum_instructions_local(pattern)
                else:
                    response_data["production_steps"] += "\n\n---\n\n" + generate_drum_instructions_local(pattern)

                # Generate teaching note for rhythm
                if not response_data.get("teaching_note"):
                    response_data["teaching_note"] = generate_rhythm_explanation_local(pattern)
                else:
                    response_data["teaching_note"] += "\n\n---\n\n" + generate_rhythm_explanation_local(pattern)

    # Use API for enhanced output if requested
    if request.use_api and result.local_data:
        try:
            # Production Agent (API)
            production_agent = ProductionAgent(tracker=orchestrator.tracker)
            production_result = production_agent.generate_from_local_data(
                result.local_data,
                user_level=session.user_profile.production_level,
            )
            if "chord_instructions" in production_result:
                response_data["production_steps"] = production_result["chord_instructions"]["markdown"]

            # Teaching Agent (API)
            teaching_agent = TeachingAgent(tracker=orchestrator.tracker)
            teaching_result = teaching_agent.explain_from_local_data(
                result.local_data,
                user_level=session.user_profile.theory_level,
            )
            if "progression_explanation" in teaching_result:
                response_data["teaching_note"] = teaching_result["progression_explanation"]["explanation"]

        except Exception as e:
            # Fall back to local if API fails
            pass

    # Add token tracking from orchestrator
    if result.token_summary:
        response_data["tokens_used"] = result.token_summary.get("total_tokens", 0)
        response_data["cost_usd"] = result.token_summary.get("total_cost_usd", 0.0)

    # Save to session history
    session_manager.add_to_history(
        session,
        request=request.prompt,
        intent_type=result.intent.intent_type.value,
        output={
            "progressions": response_data.get("progressions"),
            "drum_patterns": response_data.get("drum_patterns"),
        },
    )

    return GenerateResponse(**response_data)


@app.post("/api/session", response_model=SessionResponse)
async def create_session(
    theory_level: str = Query("rusty_intermediate"),
    production_level: str = Query("beginner"),
):
    """Create a new session."""
    profile = UserProfile(
        theory_level=theory_level,
        production_level=production_level,
    )
    session = session_manager.create_session(user_profile=profile)

    return SessionResponse(
        session_id=session.session_id,
        created_at=session.created_at,
        user_profile=session.user_profile.__dict__,
        current_project=session.current_project.__dict__,
        history_count=0,
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


@app.post("/api/feedback")
async def record_feedback(request: FeedbackRequest):
    """Record feedback on a generation."""
    session = session_manager.load_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if request.feedback not in ["thumbs_up", "thumbs_down", "regenerate"]:
        raise HTTPException(status_code=400, detail="Invalid feedback type")

    success = session_manager.record_feedback(
        session,
        entry_index=request.entry_index,
        feedback=request.feedback,
    )

    if not success:
        raise HTTPException(status_code=400, detail="Could not record feedback")

    return {"success": True, "feedback": request.feedback}


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
