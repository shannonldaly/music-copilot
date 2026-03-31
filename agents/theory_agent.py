"""
Theory Agent — Generates musically accurate chord progressions.

Role: Produces structured chord data with full note-level detail,
generates lighter-weight alternatives (darker, more movement, unexpected),
and provides melody direction guidance.

Grounded in: /docs/music_theory.md, /docs/artist_dna.md (for melody artist references)

Output contract:
- Primary progression: full note-level data (key, scale, chords with octave numbers)
- Alternatives: 3 lighter-weight objects (label, progression_name, chords as names, character)
- Melody direction: structured guidance for melodic composition

The primary progression goes through the Theory Validator.
Alternatives bypass validation — they get validated on expand via POST /api/progression/expand.
"""

import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from pathlib import Path

from anthropic import Anthropic

# Local imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from theory import (
    search_progressions,
    get_progressions_by_genre,
    get_progressions_by_mood,
    get_progression_chords,
    NAMED_PROGRESSIONS,
)
from utils.tokens import TokenTracker, log_api_call
from utils.models import ModelConfig, TaskType, get_model_for_task, SONNET


# =============================================================================
# Data classes
# =============================================================================

@dataclass
class Alternative:
    """A lighter-weight progression alternative."""
    label: str  # "darker", "more_movement", "unexpected"
    progression_name: str
    chords: List[str]  # Chord names only, no note-level data
    character: str  # One-line description


@dataclass
class MelodyDirection:
    """Structured guidance for melodic composition."""
    start_note: str  # e.g. "C4"
    start_note_context: str  # Why this starting note
    contour: str  # e.g. "ascending then falling", "arch shape"
    rhythm_feel: str  # e.g. "syncopated, behind the beat"
    avoid_on_strong_beats: List[str]  # Notes to avoid on beats 1 and 3
    avoid_context: str  # Why those notes should be avoided
    suggested_range: str  # e.g. "C4 to G5"
    artist_reference: str  # Pulled from artist_dna.md


@dataclass
class TheoryOutput:
    """Complete Theory Agent output."""
    key: str
    scale: str
    progression_name: str
    chords: List[Dict]  # Full note-level data
    tempo_suggestion: str
    genre_context: str
    theory_explanation: str
    voice_leading_notes: str
    alternatives: List[Alternative]
    melody_direction: MelodyDirection


# =============================================================================
# Theory Agent
# =============================================================================

class TheoryAgent:
    """
    Generates chord progressions with full note data, alternatives, and melody direction.

    Supports both API mode (LLM-powered creative output) and local mode
    (deterministic lookup from curated progression database).
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

        # Load grounding docs
        self.theory_doc = self._load_doc("music_theory.md")
        self.artist_dna_doc = self._load_doc("artist_dna.md")

    def _load_doc(self, filename: str) -> str:
        """Load a grounding document."""
        doc_path = Path(__file__).parent.parent / "docs" / filename
        if doc_path.exists():
            content = doc_path.read_text()
            return content[:6000] + "\n[... truncated for context ...]"
        return ""

    def generate(
        self,
        intent_data: Dict,
        user_level: str = "rusty_intermediate",
    ) -> Dict:
        """
        Generate a full theory output using the LLM.

        Args:
            intent_data: Parsed intent with moods, genres, key, tempo, etc.
            user_level: User's theory level

        Returns:
            Dict with primary progression, alternatives, and melody_direction
        """
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
        except json.JSONDecodeError:
            return {"error": "Failed to parse theory output"}

    def generate_from_local_data(
        self,
        local_data: Dict,
        intent_data: Optional[Dict] = None,
    ) -> Dict:
        """
        Enhance local lookup data with alternatives and melody direction.

        This is the main entry point when called from the orchestrator
        with local progression data already available.
        """
        if not local_data or "progressions" not in local_data:
            return {}

        primary = local_data["progressions"][0]

        # Build alternatives from other local matches
        alternatives = self._generate_alternatives_local(primary, local_data)

        # Build melody direction from the primary progression
        melody_direction = self._generate_melody_direction_local(primary, intent_data)

        return {
            "primary": primary,
            "alternatives": alternatives,
            "melody_direction": melody_direction,
        }

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

    # =========================================================================
    # Local generation (no API cost)
    # =========================================================================

    def _generate_alternatives_local(
        self,
        primary: Dict,
        local_data: Dict,
    ) -> List[Dict]:
        """
        Generate three alternatives from the local progression database.

        Labels: darker, more_movement, unexpected
        """
        primary_name = primary.get("name", "")
        primary_moods = set(primary.get("moods", []))
        primary_genres = set(primary.get("genres", []))
        primary_key = primary.get("key", "A minor")
        primary_key_parts = primary_key.split() if " " in primary_key else [primary_key, "minor"]
        primary_key_root = primary_key_parts[0]  # e.g. "C#"
        primary_key_type = primary_key_parts[-1]  # e.g. "major"

        alternatives = []
        used_names = {primary_name}

        # --- DARKER ---
        darker = self._find_alternative(
            target_moods=["dark", "melancholic", "tense", "mysterious"],
            target_key_type=primary_key_type,
            exclude_names=used_names,
            primary_genres=primary_genres,
        )
        if darker:
            used_names.add(darker.name)
            alternatives.append({
                "label": "darker",
                "progression_name": " – ".join(darker.numerals),
                "chords": self._progression_chord_names(darker, primary_key_root),
                "character": darker.description,
            })

        # --- MORE MOVEMENT ---
        more_movement = self._find_alternative_by_length(
            min_length=4,
            exclude_names=used_names,
            primary_genres=primary_genres,
            primary_key_type=primary_key_type,
        )
        if more_movement:
            used_names.add(more_movement.name)
            alternatives.append({
                "label": "more_movement",
                "progression_name": " – ".join(more_movement.numerals),
                "chords": self._progression_chord_names(more_movement, primary_key_root),
                "character": more_movement.description,
            })

        # --- UNEXPECTED ---
        # Stay in the same key type but find something with unusual mood/genre overlap
        unexpected = self._find_alternative(
            target_moods=None,
            target_key_type=primary_key_type,
            exclude_names=used_names,
            primary_genres=set(),  # Ignore genre overlap to find something outside the box
        )
        if unexpected:
            used_names.add(unexpected.name)
            alternatives.append({
                "label": "unexpected",
                "progression_name": " – ".join(unexpected.numerals),
                "chords": self._progression_chord_names(unexpected, primary_key_root),
                "character": unexpected.description,
            })

        # Fill any missing slots with fallbacks (same key type)
        labels_present = {a["label"] for a in alternatives}
        for label in ["darker", "more_movement", "unexpected"]:
            if label not in labels_present:
                for name, prog in NAMED_PROGRESSIONS.items():
                    if prog.name not in used_names and prog.key_type == primary_key_type:
                        used_names.add(prog.name)
                        alternatives.append({
                            "label": label,
                            "progression_name": " – ".join(prog.numerals),
                            "chords": self._progression_chord_names(prog, primary_key_root),
                            "character": prog.description,
                        })
                        break

        return alternatives

    def _find_alternative(
        self,
        target_moods: Optional[List[str]],
        target_key_type: str,
        exclude_names: set,
        primary_genres: set,
    ):
        """Find a progression matching target moods and key type."""
        best = None
        best_score = -1

        for name, prog in NAMED_PROGRESSIONS.items():
            if prog.name in exclude_names:
                continue
            if prog.key_type != target_key_type:
                continue

            score = 0
            # Prefer genre overlap
            if primary_genres & set(prog.genres):
                score += 2
            # Prefer mood match
            if target_moods:
                mood_overlap = set(target_moods) & set(prog.moods)
                score += len(mood_overlap)

            if score > best_score:
                best_score = score
                best = prog

        return best

    def _find_alternative_by_length(
        self,
        min_length: int,
        exclude_names: set,
        primary_genres: set,
        primary_key_type: str,
    ):
        """Find a progression with more chords (more harmonic movement)."""
        best = None
        best_score = -1

        for name, prog in NAMED_PROGRESSIONS.items():
            if prog.name in exclude_names:
                continue
            if prog.key_type != primary_key_type:
                continue

            score = len(prog.numerals)  # More chords = more movement
            if score < min_length:
                continue
            # Prefer genre overlap
            if primary_genres & set(prog.genres):
                score += 1

            if score > best_score:
                best_score = score
                best = prog

        return best

    def _progression_chord_names(self, prog, key_root: str = "A") -> List[str]:
        """Get chord names for a progression without note-level data."""
        try:
            chords = get_progression_chords(prog.numerals, key_root, prog.key_type, octave=3)
            return [c["name"] for c in chords]
        except (ValueError, KeyError):
            # Fallback: return numerals as names
            return prog.numerals

    def _generate_melody_direction_local(
        self,
        primary: Dict,
        intent_data: Optional[Dict] = None,
    ) -> Dict:
        """
        Generate melody direction from the primary progression.

        Uses deterministic rules based on key, scale, and genre context.
        """
        key_str = primary.get("key", "A minor")
        parts = key_str.split()
        root = parts[0] if parts else "A"
        key_type = parts[1] if len(parts) > 1 else "minor"

        chords = primary.get("chords", [])
        genres = primary.get("genres", [])
        moods = primary.get("moods", [])

        # Determine start note: 5th of the key in octave 4
        scale_fifths = {
            "C": "G4", "D": "A4", "E": "B4", "F": "C5",
            "G": "D5", "A": "E4", "B": "F#4",
        }
        start_note = scale_fifths.get(root, "E4")

        # Determine contour based on mood
        if any(m in moods for m in ["melancholic", "sad", "dark"]):
            contour = "descending with brief upward reaches"
        elif any(m in moods for m in ["uplifting", "epic", "happy"]):
            contour = "ascending arch — rises through the phrase then resolves down"
        elif any(m in moods for m in ["dreamy", "ethereal", "chill"]):
            contour = "gentle wave — small intervals, stays within a narrow range"
        else:
            contour = "arch shape — rises to a peak near the phrase midpoint, then descends"

        # Rhythm feel based on genre
        if any(g in genres for g in ["lo-fi", "chillhop", "jazz"]):
            rhythm_feel = "behind the beat, syncopated, lazy triplet feel"
        elif any(g in genres for g in ["trap", "hip_hop"]):
            rhythm_feel = "sparse, rhythmic gaps, half-time melodic phrasing"
        elif any(g in genres for g in ["edm", "house", "trance"]):
            rhythm_feel = "on the grid, repetitive motif with gradual variation"
        else:
            rhythm_feel = "relaxed, mostly on the beat with occasional syncopation"

        # Notes to avoid on strong beats (the 4th of the key in minor is tense)
        avoid_map = {
            "A": (["D4"], "the 4th degree creates unresolved tension on strong beats in this context"),
            "C": (["F4"], "the 4th degree sits uncomfortably against major chords on downbeats"),
            "D": (["G4"], "the 4th degree clashes with the major V chord"),
            "E": (["A4"], "the 4th degree creates unwanted suspension on strong beats"),
            "F": (["Bb4"], "the 4th degree pulls toward resolution too strongly"),
            "G": (["C5"], "the 4th degree sounds like it belongs to the IV chord, not the tonic"),
            "B": (["E4"], "the 4th degree undermines the tonic on downbeats"),
        }
        avoid_notes, avoid_context = avoid_map.get(root, (["D4"], "tension on strong beats"))

        # Suggested range — singable mid range default
        suggested_range = f"{root}3 to E5"

        # Artist reference based on genre/mood overlap with artist_dna.md
        artist_reference = self._get_artist_reference(genres, moods)

        return {
            "start_note": start_note,
            "start_note_context": f"The 5th of {key_str} — a stable, neutral launching point that doesn't commit to happy or sad",
            "contour": contour,
            "rhythm_feel": rhythm_feel,
            "avoid_on_strong_beats": avoid_notes,
            "avoid_context": avoid_context,
            "suggested_range": suggested_range,
            "artist_reference": artist_reference,
        }

    def _get_artist_reference(self, genres: List[str], moods: List[str]) -> str:
        """
        Return an artist reference based on genre/mood, drawing from artist_dna.md knowledge.
        """
        genre_set = set(g.lower().replace("-", "_").replace(" ", "_") for g in genres)
        mood_set = set(m.lower() for m in moods)

        # Artist references mapped to genres and moods (from artist_dna.md)
        references = [
            {
                "genres": {"trip_hop", "lo_fi", "ambient"},
                "moods": {"dark", "melancholic", "mysterious"},
                "ref": "Massive Attack — sparse, Phrygian-influenced melodies that hover around "
                       "2-3 notes. Let the space between notes carry as much weight as the notes themselves.",
            },
            {
                "genres": {"trip_hop", "lo_fi"},
                "moods": {"dark", "nostalgic", "melancholic"},
                "ref": "Portishead — chromatic voice leading in the melody, half-step movement "
                       "creates tension. Think of the vocal line as another instrument, not the lead.",
            },
            {
                "genres": {"edm", "dubstep"},
                "moods": {"aggressive", "epic"},
                "ref": "Skrillex — melodic hooks are short, rhythmic, and repetitive. "
                       "The melody IS the rhythm. Design it to hit with the drop.",
            },
            {
                "genres": {"edm", "house", "dance"},
                "moods": {"uplifting", "happy", "epic"},
                "ref": "Fred Again.. — radical simplicity. One melodic idea, repeated and layered. "
                       "The emotion comes from the production around it, not complexity.",
            },
            {
                "genres": {"house", "edm", "ambient"},
                "moods": {"dreamy", "melancholic", "ethereal"},
                "ref": "Ben Böhmer — long, sustained melodic lines over minor chords with extended "
                       "voicings. Melody should feel like it's floating, not driving.",
            },
            {
                "genres": {"rock", "metal", "alternative"},
                "moods": {"dark", "dreamy", "ethereal"},
                "ref": "Deftones — modal ambiguity in the melody. Let the vocal line sit between "
                       "major and minor, creating that shoegaze-meets-heavy contrast.",
            },
            {
                "genres": {"industrial", "electronic"},
                "moods": {"dark", "tense", "aggressive"},
                "ref": "Trent Reznor — minimalist melodic approach. Repetitive, hypnotic phrases "
                       "with tritone relationships. The melody should feel obsessive.",
            },
            {
                "genres": {"world_bass", "electronic"},
                "moods": {"epic", "ethereal", "mysterious"},
                "ref": "CloZee — world scales and melodic ornamentation. Classical guitar-style "
                       "phrasing adapted to electronic context. Let the melody breathe.",
            },
            {
                "genres": {"funk", "electronic", "hip_hop"},
                "moods": {"groovy", "happy", "uplifting"},
                "ref": "GRiZ — Mixolydian funk melody, pentatonic runs with soul inflections. "
                       "Think saxophone phrasing: call and response, bluesy bends.",
            },
            {
                "genres": {"house", "edm", "progressive"},
                "moods": {"chill", "dreamy"},
                "ref": "Deadmau5 — minimal harmonic movement in melody. One or two notes shifting "
                       "over long periods. The arrangement creates tension, not the melody.",
            },
            {
                "genres": {"trap", "hip_hop", "emo_rap"},
                "moods": {"melancholic", "dark", "nostalgic"},
                "ref": "Melodic trap convention — pentatonic minor melody, sparse phrasing with "
                       "rhythmic gaps. The melody should feel like it's floating over the beat, "
                       "not locked to it.",
            },
            {
                "genres": {"lo_fi", "chillhop", "jazz"},
                "moods": {"chill", "nostalgic", "dreamy"},
                "ref": "Lo-fi production convention — jazz-influenced melodic fragments, chromatic "
                       "passing tones, lazy behind-the-beat phrasing. Think Rhodes solo "
                       "through a vinyl filter.",
            },
        ]

        # Score each reference against the request
        best_ref = None
        best_score = -1

        for r in references:
            score = 0
            score += len(genre_set & r["genres"]) * 2
            score += len(mood_set & r["moods"])
            if score > best_score:
                best_score = score
                best_ref = r["ref"]

        return best_ref or (
            "Start with the pentatonic scale of the key for a safe, musical foundation. "
            "Add chromatic passing tones between chord tones for movement."
        )


# =============================================================================
# Local generation functions (no API cost)
# =============================================================================

def generate_theory_output_local(
    progressions: List[Dict],
    intent_data: Optional[Dict] = None,
) -> Dict:
    """
    Generate a complete theory output from local data.

    This is the zero-cost path used when use_api is False.
    """
    agent = TheoryAgent.__new__(TheoryAgent)
    agent.tracker = None

    if not progressions:
        return {}

    primary = progressions[0]
    local_data = {"progressions": progressions}

    alternatives = agent._generate_alternatives_local(primary, local_data)
    melody_direction = agent._generate_melody_direction_local(primary, intent_data)

    return {
        "primary": primary,
        "alternatives": alternatives,
        "melody_direction": melody_direction,
    }
