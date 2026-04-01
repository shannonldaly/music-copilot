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

from api.progression_utils import expand_chords_from_names, parse_bpm_from_tempo

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
from agents.theory_agent import generate_theory_output_local, generate_artist_blend_local
from agents.sound_engineering_agent import generate_sound_engineering_local
from validator import TheoryValidator
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
    progression: Optional[Dict] = None

    # Sidebar (Phase 2)
    key: Optional[str] = None
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


def _normalize_alternatives_for_api(alternatives: Optional[List[Dict]]) -> Optional[List[Dict]]:
    if not alternatives:
        return alternatives
    out: List[Dict] = []
    for a in alternatives:
        b = dict(a)
        lab = b.get("label") or ""
        b["label"] = lab.replace("_", " ") if isinstance(lab, str) else lab
        ch = b.get("chords") or []
        if ch and isinstance(ch[0], str):
            b["chords"] = [{"name": x, "numeral": ""} for x in ch]
        out.append(b)
    return out


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


def _extract_key_from_prompt(prompt: str) -> Optional[str]:
    """
    Extract an explicit key signature from a prompt.

    Matches patterns like: "in C major", "in C# minor", "in Db major", "in F# minor",
    "C major", "Bb minor", etc.

    Returns a string like "C# major" or None if no key found.
    """
    import re
    # Match note letter (A-G), optional sharp/flat (# or b), then major/minor
    pattern = r'\b([A-Ga-g][#b]?)\s+(major|minor|maj|min)\b'
    match = re.search(pattern, prompt, re.IGNORECASE)
    if match:
        note = match.group(1)
        # Normalize: uppercase first letter, preserve sharp/flat
        note = note[0].upper() + note[1:]
        mode = match.group(2).lower()
        # Normalize mode names
        if mode == 'maj':
            mode = 'major'
        elif mode == 'min':
            mode = 'minor'
        return f"{note} {mode}"
    return None


# Known artists from artist_dna.md (lowercase for matching)
KNOWN_ARTISTS = [
    'massive attack', 'portishead', 'skrillex', 'fred again',
    'ben böhmer', 'ben bohmer', 'hooverphonics', 'deftones',
    'nine inch nails', 'trent reznor', 'nin', 'clozee',
    'griz', 'deadmau5', 'sofi tukker',
]

# Canonical display names for matched artists
ARTIST_DISPLAY_NAMES = {
    'massive attack': 'Massive Attack', 'portishead': 'Portishead',
    'skrillex': 'Skrillex', 'fred again': 'Fred Again..',
    'ben böhmer': 'Ben Böhmer', 'ben bohmer': 'Ben Böhmer',
    'hooverphonics': 'Hooverphonics', 'deftones': 'Deftones',
    'nine inch nails': 'Nine Inch Nails', 'trent reznor': 'Nine Inch Nails',
    'nin': 'Nine Inch Nails', 'clozee': 'CloZee', 'griz': 'GRiZ',
    'deadmau5': 'Deadmau5', 'sofi tukker': 'Sofi Tukker',
}

# Blend trigger words — patterns like "X meets Y", "X and Y", "X x Y"
BLEND_PATTERNS = [' meets ', ' x ', ' and ', ' + ', ' with ', ' vs ']


def _extract_artists(prompt: str) -> List[str]:
    """Extract known artist names from a prompt. Returns canonical display names."""
    prompt_lower = prompt.lower()
    found = []
    for artist in KNOWN_ARTISTS:
        if artist in prompt_lower:
            display = ARTIST_DISPLAY_NAMES.get(artist, artist.title())
            if display not in found:
                found.append(display)
    return found


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
    sound_engineering_keywords = [
        'mix', 'eq', 'compress', 'reverb', 'automate', 'automation',
        'filter', 'frequency', 'sidechain', 'oscillator', 'synthesis',
        'sound design', 'plugin', 'bass eq', 'kick eq', 'high-pass',
        'low-pass', 'gain staging', 'lufs', 'mastering',
    ]
    production_keywords = ['how do i', 'how to']

    extracted = {'moods': [], 'genres': []}

    # Extract explicit key if specified
    key = _extract_key_from_prompt(prompt)
    if key:
        extracted['key'] = key

    # Extract artists
    artists = _extract_artists(prompt)
    if artists:
        extracted['artists'] = artists

    # Check for moods
    for mood in mood_keywords:
        if mood in prompt_lower:
            extracted['moods'].append(mood)

    # Check for genres
    for genre in genre_keywords:
        if genre in prompt_lower:
            extracted['genres'].append(genre.replace('-', '_'))

    # --- Determine intent type (order matters: most specific first) ---

    # Artist blend: two or more artists + a blend trigger word
    if len(artists) >= 2 and any(bp in prompt_lower for bp in BLEND_PATTERNS):
        return ('artist_blend', 0.95, extracted)

    # Sound engineering: specific mixing/production technique questions
    if any(kw in prompt_lower for kw in sound_engineering_keywords):
        extracted['question'] = prompt
        return ('sound_engineering', 0.9, extracted)

    # General production question (how-to without a specific SE keyword)
    if any(kw in prompt_lower for kw in production_keywords):
        return ('production_question', 0.8, extracted)

    # Drum patterns
    if any(kw in prompt_lower for kw in drum_keywords):
        extracted['genres'] = extracted['genres'] or ['trap']
        return ('drum_pattern', 0.85, extracted)

    # Single artist reference (not a blend)
    if len(artists) == 1:
        return ('artist_reference', 0.9, extracted)

    # Mood/genre/key
    if extracted['moods'] or extracted['genres'] or extracted.get('key'):
        return ('mood_vibe', 0.9, extracted)

    # Default
    return ('mood_vibe', 0.5, {'moods': [], 'genres': []})


@app.post("/api/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """
    Main generation endpoint.

    Takes a user prompt, routes through orchestrator, returns music data.
    """
    # Get or create session
    session = get_or_create_session(session_manager, request.session_id)

    extracted: Dict[str, Any] = {}

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

            # Parse user-specified key, or default to A minor
            user_key = extracted.get('key')  # e.g. "C# major" or None
            if user_key:
                key_parts = user_key.split()
                key_root = key_parts[0]  # e.g. "C#"
                key_mode = key_parts[1] if len(key_parts) > 1 else 'minor'  # e.g. "major"
            else:
                key_root = 'A'
                key_mode = 'minor'

            progressions = []
            for mood in moods:
                progs = search_progressions(mood=mood, key_type=key_mode)
                progressions.extend(progs)
            for genre in genres:
                progs = search_progressions(genre=genre, key_type=key_mode)
                progressions.extend(progs)

            if not progressions:
                # Broaden: search by key_type alone, or fall back to defaults
                progs = search_progressions(key_type=key_mode)
                if progs:
                    progressions.extend(progs)
                elif not moods and not genres:
                    progressions = search_progressions(mood='melancholic')

            # Dedupe and convert
            seen = set()
            unique = []
            for p in progressions:
                if p.name not in seen:
                    seen.add(p.name)
                    unique.append(p)

            # Convert to chord data using the user's key
            from theory import get_progression_chords
            result.local_data['progressions'] = []
            for prog in unique[:3]:
                try:
                    chords = get_progression_chords(prog.numerals, key_root, prog.key_type, octave=3)
                    result.local_data['progressions'].append({
                        'name': prog.name,
                        'numerals': prog.numerals,
                        'key': f'{key_root} {prog.key_type}',
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

        elif intent_type == 'sound_engineering':
            # Sound Engineering Agent — local response
            se_response = generate_sound_engineering_local(request.prompt)
            if se_response:
                result.local_data['sound_engineering_response'] = se_response

        elif intent_type == 'artist_blend':
            # Artist blend — pull two profiles and blend
            artists = extracted.get('artists', [])
            if len(artists) >= 2:
                blend_result = generate_artist_blend_local(artists[0], artists[1])
                if blend_result:
                    result.local_data['artist_blend'] = blend_result['artist_blend']
                    # Also generate progression + alternatives + melody_direction
                    if blend_result.get('progression'):
                        result.local_data['progressions'] = [blend_result['progression']]
    else:
        # Use full orchestrator with API
        orchestrator = Orchestrator()
        result = orchestrator.process(request.prompt)
        extracted = getattr(result.intent, "extracted", None) or {}

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

                response_data["progression"] = prog
                response_data["key"] = prog.get("key")
                response_data["bpm"] = parse_bpm_from_tempo(
                    prog.get("tempo_range"),
                    prog.get("tempo_suggestion"),
                )
                g = prog.get("genres")
                response_data["genre_context"] = (
                    ", ".join(g) if isinstance(g, list) else (g if isinstance(g, str) else None)
                )
                response_data["progression_name"] = prog.get("name") or "–".join(
                    prog.get("numerals") or []
                )

            # Generate alternatives and melody direction
            theory_output = generate_theory_output_local(
                result.local_data["progressions"],
                intent_data=extracted,
            )
            if theory_output.get("alternatives"):
                response_data["alternatives"] = _normalize_alternatives_for_api(
                    theory_output["alternatives"]
                )
            if theory_output.get("melody_direction"):
                response_data["melody_direction"] = theory_output["melody_direction"]

        # Drum patterns
        if "drum_patterns" in result.local_data:
            response_data["drum_patterns"] = result.local_data["drum_patterns"]

            if result.local_data["drum_patterns"]:
                pattern = result.local_data["drum_patterns"][0]

                response_data["bpm"] = parse_bpm_from_tempo(
                    pattern.get("tempo_range"),
                    pattern.get("tempo_suggestion"),
                )
                g = pattern.get("genres")
                response_data["genre_context"] = (
                    ", ".join(g) if isinstance(g, list) else (g if isinstance(g, str) else None)
                )
                response_data["progression_name"] = pattern.get("name")

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

        # Sound engineering response
        if "sound_engineering_response" in result.local_data:
            response_data["sound_engineering_response"] = result.local_data["sound_engineering_response"]

        # Artist blend response
        if "artist_blend" in result.local_data:
            response_data["artist_blend"] = result.local_data["artist_blend"]

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
