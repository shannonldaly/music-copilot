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

        # Keyboard-relative descriptions (middle C = C4)
        _keyboard_desc = {
            "C4": "middle C",
            "D4": "one white key above middle C",
            "E4": "two white keys above middle C",
            "F4": "three white keys above middle C",
            "F#4": "the black key between F and G above middle C",
            "G4": "a 5th above middle C (right hand, thumb on C, pinky on G)",
            "A4": "the A above middle C — concert tuning pitch",
            "B4": "just below the C one octave above middle C",
            "C5": "one octave above middle C",
            "D5": "two white keys above the C one octave up",
            "Bb4": "the black key between A and B above middle C",
            "Eb4": "the black key between D and E above middle C",
        }
        keyboard_hint = _keyboard_desc.get(start_note, "middle of the keyboard")

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
            "start_note_context": f"{start_note} — {keyboard_hint} on your keyboard. The 5th of {key_str}, a stable neutral launching point",
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


# =============================================================================
# Artist blend — local generation (no API cost)
# =============================================================================

# Artist profiles for blending (sourced from docs/artist_dna.md)
ARTIST_PROFILES = {
    'Massive Attack': {
        'genres': ['trip-hop', 'electronic', 'ambient'],
        'moods': ['dark', 'melancholic', 'mysterious'],
        'key_type': 'minor',
        'elements': [
            'Phrygian-influenced harmony with 2-chord drones',
            'Sparse, minimal arrangements with heavy sub bass',
            'Tribal percussion and slow tempos (70-90 BPM)',
            'Dark, cinematic atmosphere with cavernous reverb',
        ],
        'tempo_range': (70, 90),
        'progression_tags': ['dark', 'tense', 'mysterious'],
    },
    'Portishead': {
        'genres': ['trip-hop', 'electronic'],
        'moods': ['dark', 'nostalgic', 'melancholic'],
        'key_type': 'minor',
        'elements': [
            'Chromatic voice leading and half-diminished chords',
            'Vinyl crackle texture and lo-fi sampling',
            'Jazz-influenced harmony with noir atmosphere',
            'Vocals as lead instrument, everything else serves the vocal',
        ],
        'tempo_range': (70, 95),
        'progression_tags': ['dark', 'noir', 'chromatic'],
    },
    'Skrillex': {
        'genres': ['dubstep', 'edm', 'electronic'],
        'moods': ['aggressive', 'epic', 'dark'],
        'key_type': 'minor',
        'elements': [
            'FM synthesis and 3-layer bass design',
            'Aggressive resampling and granular processing',
            'Extreme dynamic contrast between builds and drops',
            'Short, rhythmic melodic hooks that hit with the drop',
        ],
        'tempo_range': (140, 175),
        'progression_tags': ['aggressive', 'dark', 'epic'],
    },
    'Fred Again..': {
        'genres': ['uk-garage', 'house', 'dance'],
        'moods': ['uplifting', 'happy', 'epic'],
        'key_type': 'major',
        'elements': [
            'Radical simplicity — one melodic idea repeated and layered',
            'Voice memo sampling and found-sound production',
            'Major keys with emotional, community-focused energy',
            'Four-on-the-floor kick with UK garage shuffle',
        ],
        'tempo_range': (125, 140),
        'progression_tags': ['uplifting', 'happy', 'anthemic'],
    },
    'Ben Böhmer': {
        'genres': ['melodic-house', 'progressive', 'ambient'],
        'moods': ['dreamy', 'melancholic', 'ethereal'],
        'key_type': 'minor',
        'elements': [
            'Minor keys with extended chord voicings (9ths, 11ths)',
            'Long, sustained melodic lines that float over the harmony',
            'Soft, rounded kicks with long sub tails',
            'Organic textures blended with analog synth warmth',
        ],
        'tempo_range': (118, 125),
        'progression_tags': ['dreamy', 'melancholic', 'ethereal'],
    },
    'Hooverphonics': {
        'genres': ['dream-pop', 'trip-hop', 'orchestral'],
        'moods': ['dreamy', 'romantic', 'nostalgic'],
        'key_type': 'minor',
        'elements': [
            'Lush orchestration and cinematic string arrangements',
            'Jazz voicings (maj7, min9) with pop structure',
            'Wide stereo field and cinematic reverb',
            'Female vocal-driven with everything supporting the voice',
        ],
        'tempo_range': (80, 110),
        'progression_tags': ['dreamy', 'romantic', 'nostalgic'],
    },
    'Deftones': {
        'genres': ['alternative-metal', 'shoegaze', 'rock'],
        'moods': ['dark', 'dreamy', 'ethereal'],
        'key_type': 'minor',
        'elements': [
            'Modal ambiguity — melodies sit between major and minor',
            'Power chords layered with shoegaze pad textures',
            'Heavy low end contrasted with ethereal, floating vocals',
            'Drop tunings and detuned guitars for weight',
        ],
        'tempo_range': (80, 130),
        'progression_tags': ['dark', 'dreamy', 'ethereal'],
    },
    'Nine Inch Nails': {
        'genres': ['industrial', 'electronic', 'rock'],
        'moods': ['dark', 'tense', 'aggressive'],
        'key_type': 'minor',
        'elements': [
            'Minimalist harmony with tritone relationships',
            'Repetitive, hypnotic patterns building to climax',
            'Industrial texture: distortion, noise, granular synthesis',
            'Quiet-loud dynamics as emotional architecture',
        ],
        'tempo_range': (90, 140),
        'progression_tags': ['dark', 'tense', 'aggressive'],
    },
    'CloZee': {
        'genres': ['world-bass', 'electronic', 'glitch-hop'],
        'moods': ['epic', 'ethereal', 'mysterious'],
        'key_type': 'minor',
        'elements': [
            'World scales (Phrygian, Dorian, Arabic) adapted to electronic context',
            'Classical guitar-influenced melodic phrasing',
            'Organic instrument samples layered with synthesis',
            'Polyrhythmic percussion and world music drum patterns',
        ],
        'tempo_range': (90, 140),
        'progression_tags': ['epic', 'ethereal', 'mysterious'],
    },
    'GRiZ': {
        'genres': ['future-funk', 'electronic', 'hip-hop'],
        'moods': ['groovy', 'happy', 'uplifting'],
        'key_type': 'major',
        'elements': [
            'Mixolydian funk harmony with dominant 7th chords',
            'Live saxophone integration and bluesy melodic lines',
            'Pentatonic runs with soul inflections',
            'Heavy bass with funk guitar chops',
        ],
        'tempo_range': (100, 130),
        'progression_tags': ['groovy', 'happy', 'uplifting'],
    },
    'Deadmau5': {
        'genres': ['progressive-house', 'edm', 'techno'],
        'moods': ['chill', 'dreamy', 'epic'],
        'key_type': 'minor',
        'elements': [
            'Minimal harmonic movement — 2-4 chords maximum',
            'Arrangement-based tension (not harmonic tension)',
            'Long filter sweeps and automation-driven builds',
            'Heavy sidechain pumping as a musical effect',
        ],
        'tempo_range': (125, 130),
        'progression_tags': ['chill', 'dreamy', 'epic'],
    },
    'Sofi Tukker': {
        'genres': ['dance-pop', 'house', 'electronic'],
        'moods': ['happy', 'groovy', 'uplifting'],
        'key_type': 'major',
        'elements': [
            'Brazilian bossa nova rhythms adapted to house music',
            'Polyrhythmic percussion with organic shakers and congas',
            'Multilingual vocals and call-and-response patterns',
            'Bright, major-key harmony with Latin guitar textures',
        ],
        'tempo_range': (120, 130),
        'progression_tags': ['groovy', 'happy', 'uplifting'],
    },
}


def generate_artist_blend_local(artist_1: str, artist_2: str) -> Optional[Dict]:
    """
    Generate an artist blend response from two artist profiles.

    Returns the artist_blend contract:
    {artist_1, artist_2, blend_description, from_artist_1, from_artist_2, production_direction}

    Also returns a progression and melody_direction for the blended result.
    """
    profile_1 = ARTIST_PROFILES.get(artist_1)
    profile_2 = ARTIST_PROFILES.get(artist_2)

    if not profile_1 or not profile_2:
        return None

    # Pick elements from each artist (first 2 from each for the blend)
    from_1 = profile_1['elements'][:2]
    from_2 = profile_2['elements'][:2]

    # Blend description
    genres_1 = ', '.join(profile_1['genres'][:2])
    genres_2 = ', '.join(profile_2['genres'][:2])
    moods_combined = list(set(profile_1['moods'] + profile_2['moods']))[:4]

    blend_description = (
        f"A fusion of {artist_1}'s {genres_1} sensibility with {artist_2}'s "
        f"{genres_2} approach. The result is {', '.join(moods_combined[:3])} — "
        f"taking {profile_1['elements'][0].lower().split(' — ')[0] if ' — ' in profile_1['elements'][0] else profile_1['elements'][0].lower()} "
        f"from {artist_1} and combining it with "
        f"{profile_2['elements'][0].lower().split(' — ')[0] if ' — ' in profile_2['elements'][0] else profile_2['elements'][0].lower()} "
        f"from {artist_2}."
    )

    # Production direction — concrete guidance
    # Calculate tempo range as the overlap, or midpoint ±10 if no overlap
    tempo_low = max(profile_1['tempo_range'][0], profile_2['tempo_range'][0])
    tempo_high = min(profile_1['tempo_range'][1], profile_2['tempo_range'][1])
    if tempo_low >= tempo_high:
        # No meaningful overlap — use midpoint of all four values ±10
        midpoint = (
            profile_1['tempo_range'][0] + profile_1['tempo_range'][1] +
            profile_2['tempo_range'][0] + profile_2['tempo_range'][1]
        ) // 4
        tempo_low = midpoint - 10
        tempo_high = midpoint + 10

    # Key type: if both agree, use that; otherwise default to minor
    key_type = profile_1['key_type'] if profile_1['key_type'] == profile_2['key_type'] else 'minor'

    production_direction = (
        f"Target tempo: {tempo_low}-{tempo_high} BPM. "
        f"Work in a {key_type} key. "
        f"Start with {profile_1['elements'][0].split('—')[0].strip() if '—' in profile_1['elements'][0] else profile_1['elements'][0]} "
        f"as your harmonic foundation, then layer {profile_2['elements'][1].lower()} on top. "
        f"For the low end, lean toward {'heavy sub bass' if any(m in profile_1['moods'] for m in ['dark', 'aggressive']) else 'clean, rounded bass'}. "
        f"Use {'sparse, minimal' if any(m in profile_1['moods'] for m in ['dark', 'mysterious']) else 'layered, textured'} arrangement."
    )

    # Find a matching progression
    combined_tags = list(set(profile_1['progression_tags'] + profile_2['progression_tags']))
    best_prog = None
    best_score = -1
    for name, prog in NAMED_PROGRESSIONS.items():
        if prog.key_type != key_type:
            continue
        score = len(set(prog.moods) & set(combined_tags))
        if score > best_score:
            best_score = score
            best_prog = prog

    progression_data = None
    if best_prog:
        try:
            chords = get_progression_chords(best_prog.numerals, 'A', best_prog.key_type, octave=3)
            progression_data = {
                'name': best_prog.name,
                'numerals': best_prog.numerals,
                'key': f'A {best_prog.key_type}',
                'chords': chords,
                'tempo_range': (tempo_low, tempo_high),
                'description': best_prog.description,
                'moods': moods_combined,
                'genres': list(set(profile_1['genres'] + profile_2['genres'])),
            }
        except ValueError:
            pass

    return {
        'artist_blend': {
            'artist_1': artist_1,
            'artist_2': artist_2,
            'blend_description': blend_description,
            'from_artist_1': from_1,
            'from_artist_2': from_2,
            'production_direction': production_direction,
        },
        'progression': progression_data,
        'key_type': key_type,
        'tempo_range': (tempo_low, tempo_high),
        'moods': moods_combined,
    }
