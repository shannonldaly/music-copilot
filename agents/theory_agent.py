"""
Theory Agent — Generates musically accurate chord progressions via LLM.

For local (zero-cost) generation, see theory_local.py.
For artist profiles and blend logic, see artist_data.py.

Output contract:
- Primary progression: full note-level data (key, scale, chords with octave numbers)
- Alternatives: 3 lighter-weight objects (label, progression_name, chords as names, character)
- Melody direction: structured guidance for melodic composition
"""

import json
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from pathlib import Path

from anthropic import Anthropic

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.tokens import TokenTracker, log_api_call
from utils.models import ModelConfig, TaskType, get_model_for_task
from utils.logging import log_agent_call

# Re-export for facade compatibility
from agents.theory_local import generate_theory_output_local  # noqa: F401
from agents.artist_data import generate_artist_blend_local, ARTIST_PROFILES  # noqa: F401

logger = logging.getLogger(__name__)


# =============================================================================
# Data classes
# =============================================================================

@dataclass
class Alternative:
    """A lighter-weight progression alternative."""
    label: str
    progression_name: str
    chords: List[str]
    character: str


@dataclass
class MelodyDirection:
    """Structured guidance for melodic composition."""
    start_note: str
    start_note_context: str
    contour: str
    rhythm_feel: str
    avoid_on_strong_beats: List[str]
    avoid_context: str
    suggested_range: str
    artist_reference: str


@dataclass
class TheoryOutput:
    """Complete Theory Agent output."""
    key: str
    scale: str
    progression_name: str
    chords: List[Dict]
    tempo_suggestion: str
    genre_context: str
    theory_explanation: str
    voice_leading_notes: str
    alternatives: List[Alternative]
    melody_direction: MelodyDirection


# =============================================================================
# Theory Agent (LLM-powered)
# =============================================================================

class TheoryAgent:
    """
    Generates chord progressions with full note data, alternatives, and melody direction.

    API mode: LLM-powered creative output via generate().
    Local mode: use generate_theory_output_local() from theory_local.py.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_config: Optional[ModelConfig] = None,
        tracker: Optional[TokenTracker] = None,
    ):
        self.client = Anthropic(api_key=api_key) if api_key else Anthropic()
        self.model_config = model_config or ModelConfig()
        self.tracker = tracker

        self.theory_doc = self._load_doc("music_theory.md")
        self.artist_dna_doc = self._load_doc("artist_dna.md")

    def _load_doc(self, filename: str) -> str:
        """Load a grounding document."""
        doc_path = Path(__file__).parent.parent / "docs" / filename
        if doc_path.exists():
            content = doc_path.read_text()
            return content[:6000] + "\n[... truncated for context ...]"
        return ""

    @log_agent_call
    def generate(self, intent_data: Dict, user_level: str = "rusty_intermediate") -> Dict:
        """Generate a full theory output using the LLM."""
        system_prompt = self._build_system_prompt(user_level)
        user_prompt = self._build_user_prompt(intent_data)

        response = self.client.messages.create(
            model=get_model_for_task(TaskType.CHORD_SUGGESTION, self.model_config),
            max_tokens=2000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        if self.tracker:
            log_api_call(
                self.tracker,
                agent="theory_agent",
                model="sonnet",
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                request_type="chord_generation"
            )

        try:
            result = json.loads(response.content[0].text)
            return result
        except json.JSONDecodeError as e:
            logger.warning(f"Theory Agent: LLM returned unparseable JSON: {e}")
            return {"error": "Failed to parse theory output"}

    def _build_system_prompt(self, user_level: str) -> str:
        """Build the system prompt for LLM-based generation."""
        return f"""You are a Theory Agent for a music production co-pilot. You generate musically accurate chord progressions with structured output.

USER THEORY LEVEL: {user_level}

You MUST respond with valid JSON matching this exact structure:
{{
  "key": "A minor",
  "scale": "natural minor",
  "progression_name": "i–VI–III–VII",
  "chords": [
    {{ "numeral": "i", "name": "Am", "notes": ["A3", "C4", "E4"] }}
  ],
  "tempo_suggestion": "85 BPM",
  "genre_context": "melancholic lo-fi / trap",
  "theory_explanation": "Why this progression works...",
  "voice_leading_notes": "Voice leading analysis...",
  "alternatives": [
    {{ "label": "darker", "progression_name": "i–iv–VI–V", "chords": ["Am", "Dm", "F", "E"], "character": "One-line description" }},
    {{ "label": "more_movement", "progression_name": "...", "chords": [...], "character": "..." }},
    {{ "label": "unexpected", "progression_name": "...", "chords": [...], "character": "..." }}
  ],
  "melody_direction": {{
    "start_note": "C4",
    "start_note_context": "Why start here...",
    "contour": "ascending then falling",
    "rhythm_feel": "syncopated, behind the beat",
    "avoid_on_strong_beats": ["B3"],
    "avoid_context": "Why avoid these notes...",
    "suggested_range": "C4 to G5",
    "artist_reference": "Reference from artist DNA..."
  }}
}}

RULES:
- Always output exact note names with octave numbers (e.g., C4, not just C)
- Never suggest notes outside the stated scale without flagging as borrowed chord
- The primary progression gets full note-level data
- Alternatives are lighter-weight: chord names only, no note data
- Alternatives must be labeled: "darker", "more_movement", "unexpected"
- melody_direction.artist_reference should reference production techniques from real artists

ARTIST DNA CONTEXT (for melody_direction.artist_reference):
{self.artist_dna_doc[:3000]}

MUSIC THEORY CONTEXT:
{self.theory_doc[:2000]}"""

    def _build_user_prompt(self, intent_data: Dict) -> str:
        """Build the user prompt from intent data."""
        parts = ["Generate a chord progression for:"]

        moods = intent_data.get("moods", [])
        genres = intent_data.get("genres", [])
        key = intent_data.get("key")
        tempo = intent_data.get("tempo")
        artist = intent_data.get("artist")
        specific = intent_data.get("specific_request")

        if moods:
            parts.append(f"Mood: {', '.join(moods)}")
        if genres:
            parts.append(f"Genre: {', '.join(genres)}")
        if key:
            parts.append(f"Key: {key}")
        if tempo:
            parts.append(f"Tempo: {tempo} BPM")
        if artist:
            parts.append(f"Artist reference: {artist}")
        if specific:
            parts.append(f"Specific request: {specific}")

        if not any([moods, genres, key, tempo, artist, specific]):
            parts.append("Something interesting and melancholic in a minor key")

        return "\n".join(parts)
