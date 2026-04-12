"""
Theory Agent — Local generation (no API cost).

Contains all deterministic theory logic:
- generate_theory_output_local(): main entry point for local mode
- Alternatives generation (darker, more movement, unexpected)
- Melody direction generation (contour, rhythm feel, start note)
- Artist reference matching by genre/mood
"""

import logging
from typing import List, Dict, Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from theory import (
    get_progression_chords,
    NAMED_PROGRESSIONS,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Main entry point
# =============================================================================

def generate_theory_output_local(
    progressions: List[Dict],
    intent_data: Optional[Dict] = None,
) -> Dict:
    """Generate a complete theory output from local data (zero API cost)."""
    if not progressions:
        return {}

    primary = progressions[0]
    local_data = {"progressions": progressions}

    alternatives = generate_alternatives_local(primary, local_data)
    melody_direction = generate_melody_direction_local(primary, intent_data)

    return {
        "primary": primary,
        "alternatives": alternatives,
        "melody_direction": melody_direction,
    }


# =============================================================================
# Alternatives
# =============================================================================

def generate_alternatives_local(primary: Dict, local_data: Dict) -> List[Dict]:
    """Generate three alternatives from the local progression database."""
    primary_name = primary.get("name", "")
    primary_genres = set(primary.get("genres", []))
    primary_key = primary.get("key", "A minor")
    primary_key_parts = primary_key.split() if " " in primary_key else [primary_key, "minor"]
    primary_key_root = primary_key_parts[0]
    primary_key_type = primary_key_parts[-1]

    alternatives = []
    used_names = {primary_name}

    darker = _find_alternative(
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
            "chords": _progression_chord_names(darker, primary_key_root),
            "character": darker.description,
        })

    more_movement = _find_alternative_by_length(
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
            "chords": _progression_chord_names(more_movement, primary_key_root),
            "character": more_movement.description,
        })

    unexpected = _find_alternative(
        target_moods=None,
        target_key_type=primary_key_type,
        exclude_names=used_names,
        primary_genres=set(),
    )
    if unexpected:
        used_names.add(unexpected.name)
        alternatives.append({
            "label": "unexpected",
            "progression_name": " – ".join(unexpected.numerals),
            "chords": _progression_chord_names(unexpected, primary_key_root),
            "character": unexpected.description,
        })

    # Fill missing slots with fallbacks
    labels_present = {a["label"] for a in alternatives}
    for label in ["darker", "more_movement", "unexpected"]:
        if label not in labels_present:
            for name, prog in NAMED_PROGRESSIONS.items():
                if prog.name not in used_names and prog.key_type == primary_key_type:
                    used_names.add(prog.name)
                    alternatives.append({
                        "label": label,
                        "progression_name": " – ".join(prog.numerals),
                        "chords": _progression_chord_names(prog, primary_key_root),
                        "character": prog.description,
                    })
                    break

    return alternatives


def _find_alternative(target_moods, target_key_type, exclude_names, primary_genres):
    """Find a progression matching target moods and key type."""
    best = None
    best_score = -1
    for name, prog in NAMED_PROGRESSIONS.items():
        if prog.name in exclude_names or prog.key_type != target_key_type:
            continue
        score = 0
        if primary_genres & set(prog.genres):
            score += 2
        if target_moods:
            score += len(set(target_moods) & set(prog.moods))
        if score > best_score:
            best_score = score
            best = prog
    return best


def _find_alternative_by_length(min_length, exclude_names, primary_genres, primary_key_type):
    """Find a progression with more chords (more harmonic movement)."""
    best = None
    best_score = -1
    for name, prog in NAMED_PROGRESSIONS.items():
        if prog.name in exclude_names or prog.key_type != primary_key_type:
            continue
        score = len(prog.numerals)
        if score < min_length:
            continue
        if primary_genres & set(prog.genres):
            score += 1
        if score > best_score:
            best_score = score
            best = prog
    return best


def _progression_chord_names(prog, key_root: str = "A") -> List[str]:
    """Get chord names for a progression without note-level data."""
    try:
        chords = get_progression_chords(prog.numerals, key_root, prog.key_type, octave=3)
        return [c["name"] for c in chords]
    except (ValueError, KeyError):
        return prog.numerals


# =============================================================================
# Melody direction
# =============================================================================

# Keyboard-relative descriptions (middle C = C4)
KEYBOARD_DESCRIPTIONS = {
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

SCALE_FIFTHS = {
    "C": "G4", "D": "A4", "E": "B4", "F": "C5",
    "G": "D5", "A": "E4", "B": "F#4",
}

AVOID_NOTES_MAP = {
    "A": (["D4"], "the 4th degree creates unresolved tension on strong beats in this context"),
    "C": (["F4"], "the 4th degree sits uncomfortably against major chords on downbeats"),
    "D": (["G4"], "the 4th degree clashes with the major V chord"),
    "E": (["A4"], "the 4th degree creates unwanted suspension on strong beats"),
    "F": (["Bb4"], "the 4th degree pulls toward resolution too strongly"),
    "G": (["C5"], "the 4th degree sounds like it belongs to the IV chord, not the tonic"),
    "B": (["E4"], "the 4th degree undermines the tonic on downbeats"),
}


def generate_melody_direction_local(primary: Dict, intent_data: Optional[Dict] = None) -> Dict:
    """Generate melody direction from the primary progression using deterministic rules."""
    key_str = primary.get("key", "A minor")
    parts = key_str.split()
    root = parts[0] if parts else "A"
    key_type = parts[1] if len(parts) > 1 else "minor"

    genres = primary.get("genres", [])
    moods = primary.get("moods", [])

    start_note = SCALE_FIFTHS.get(root, "E4")
    keyboard_hint = KEYBOARD_DESCRIPTIONS.get(start_note, "middle of the keyboard")

    # Contour based on mood
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

    avoid_notes, avoid_context = AVOID_NOTES_MAP.get(root, (["D4"], "tension on strong beats"))

    return {
        "start_note": start_note,
        "start_note_context": f"{start_note} — {keyboard_hint} on your keyboard. The 5th of {key_str}, a stable neutral launching point",
        "contour": contour,
        "rhythm_feel": rhythm_feel,
        "avoid_on_strong_beats": avoid_notes,
        "avoid_context": avoid_context,
        "suggested_range": f"{root}3 to E5",
        "artist_reference": get_artist_reference(genres, moods),
    }


# =============================================================================
# Artist reference matching
# =============================================================================

ARTIST_REFERENCES = [
    {"genres": {"trip_hop", "lo_fi", "ambient"}, "moods": {"dark", "melancholic", "mysterious"},
     "ref": "Massive Attack — sparse, Phrygian-influenced melodies that hover around 2-3 notes. Let the space between notes carry as much weight as the notes themselves."},
    {"genres": {"trip_hop", "lo_fi"}, "moods": {"dark", "nostalgic", "melancholic"},
     "ref": "Portishead — chromatic voice leading in the melody, half-step movement creates tension. Think of the vocal line as another instrument, not the lead."},
    {"genres": {"edm", "dubstep"}, "moods": {"aggressive", "epic"},
     "ref": "Skrillex — melodic hooks are short, rhythmic, and repetitive. The melody IS the rhythm. Design it to hit with the drop."},
    {"genres": {"edm", "house", "dance"}, "moods": {"uplifting", "happy", "epic"},
     "ref": "Fred Again.. — radical simplicity. One melodic idea, repeated and layered. The emotion comes from the production around it, not complexity."},
    {"genres": {"house", "edm", "ambient"}, "moods": {"dreamy", "melancholic", "ethereal"},
     "ref": "Ben Böhmer — long, sustained melodic lines over minor chords with extended voicings. Melody should feel like it's floating, not driving."},
    {"genres": {"rock", "metal", "alternative"}, "moods": {"dark", "dreamy", "ethereal"},
     "ref": "Deftones — modal ambiguity in the melody. Let the vocal line sit between major and minor, creating that shoegaze-meets-heavy contrast."},
    {"genres": {"industrial", "electronic"}, "moods": {"dark", "tense", "aggressive"},
     "ref": "Trent Reznor — minimalist melodic approach. Repetitive, hypnotic phrases with tritone relationships. The melody should feel obsessive."},
    {"genres": {"world_bass", "electronic"}, "moods": {"epic", "ethereal", "mysterious"},
     "ref": "CloZee — world scales and melodic ornamentation. Classical guitar-style phrasing adapted to electronic context. Let the melody breathe."},
    {"genres": {"funk", "electronic", "hip_hop"}, "moods": {"groovy", "happy", "uplifting"},
     "ref": "GRiZ — Mixolydian funk melody, pentatonic runs with soul inflections. Think saxophone phrasing: call and response, bluesy bends."},
    {"genres": {"house", "edm", "progressive"}, "moods": {"chill", "dreamy"},
     "ref": "Deadmau5 — minimal harmonic movement in melody. One or two notes shifting over long periods. The arrangement creates tension, not the melody."},
    {"genres": {"trap", "hip_hop", "emo_rap"}, "moods": {"melancholic", "dark", "nostalgic"},
     "ref": "Melodic trap convention — pentatonic minor melody, sparse phrasing with rhythmic gaps. The melody should feel like it's floating over the beat, not locked to it."},
    {"genres": {"lo_fi", "chillhop", "jazz"}, "moods": {"chill", "nostalgic", "dreamy"},
     "ref": "Lo-fi production convention — jazz-influenced melodic fragments, chromatic passing tones, lazy behind-the-beat phrasing. Think Rhodes solo through a vinyl filter."},
]


def get_artist_reference(genres: List[str], moods: List[str]) -> str:
    """Return an artist reference based on genre/mood overlap."""
    genre_set = set(g.lower().replace("-", "_").replace(" ", "_") for g in genres)
    mood_set = set(m.lower() for m in moods)

    best_ref = None
    best_score = -1
    for r in ARTIST_REFERENCES:
        score = len(genre_set & r["genres"]) * 2 + len(mood_set & r["moods"])
        if score > best_score:
            best_score = score
            best_ref = r["ref"]

    return best_ref or (
        "Start with the pentatonic scale of the key for a safe, musical foundation. "
        "Add chromatic passing tones between chord tones for movement."
    )
