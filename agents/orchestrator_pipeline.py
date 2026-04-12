"""
Orchestrator pipeline — local data lookup and response assembly.

Contains:
- lookup_local(): find progressions, drums, SE responses, blends by intent
- build_response(): assemble the GenerateResponse dict from local data
- normalize_alternatives(): format alternatives for the API
- execute_local_lookup(): legacy API-mode lookup (used by process())
"""

import logging
from typing import List, Dict, Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from theory import (
    search_progressions,
    get_progressions_by_genre,
    get_progressions_by_mood,
    get_progression_chords,
    get_drum_patterns_by_genre,
)
from api.progression_utils import parse_bpm_from_tempo
from agents.production_agent import generate_chord_instructions_local, generate_drum_instructions_local
from agents.teaching_agent import generate_progression_explanation_local, generate_rhythm_explanation_local
from agents.theory_agent import generate_theory_output_local, generate_artist_blend_local, ARTIST_PROFILES
from agents.sound_engineering_agent import generate_sound_engineering_local
from validator import TheoryValidator
from agents.intent_detection import (
    MINOR_GENRES, MAJOR_GENRES, MINOR_MOODS, MAJOR_MOODS,
    DEFAULT_MINOR_KEY, DEFAULT_MAJOR_KEY, FALLBACK_KEY,
    MAX_RESULTS, DEFAULT_OCTAVE,
    IntentType, ParsedIntent, RoutingPlan,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Local data lookup
# =============================================================================

def lookup_local(intent_type: str, extracted: dict, prompt: str,
                 has_api_key: bool = False, se_api_fallback_fn=None) -> dict:
    """
    Execute local lookups based on intent type.

    Args:
        intent_type: The detected intent string
        extracted: Extracted data from intent detection
        prompt: The original user prompt (needed for SE agent)
        has_api_key: Whether an API key is available (for SE fallback)
        se_api_fallback_fn: Callable for SE API fallback (injected by Orchestrator)
    """
    logger.info(f"Routing: intent={intent_type}, moods={extracted.get('moods', [])}, "
                f"genres={extracted.get('genres', [])}, key={extracted.get('key')}")
    local_data = {}

    if intent_type in ('mood_vibe', 'theory_request'):
        local_data = _lookup_progressions(extracted)

    elif intent_type == 'drum_pattern':
        local_data = _lookup_drums(extracted)

    elif intent_type == 'sound_engineering':
        se_response = generate_sound_engineering_local(prompt)
        if se_response:
            local_data['sound_engineering_response'] = se_response
        elif has_api_key and se_api_fallback_fn:
            se_response = se_api_fallback_fn(prompt)
            if se_response:
                local_data['sound_engineering_response'] = se_response

    elif intent_type == 'artist_blend':
        artists = extracted.get('artists', [])
        if len(artists) >= 2:
            blend_result = generate_artist_blend_local(artists[0], artists[1])
            if blend_result:
                local_data['artist_blend'] = blend_result['artist_blend']
                if blend_result.get('progression'):
                    local_data['progressions'] = [blend_result['progression']]

    elif intent_type == 'artist_reference':
        local_data = _lookup_artist_reference(extracted)

    return local_data


def _lookup_progressions(extracted: dict) -> dict:
    """Look up chord progressions based on mood, genre, and key."""
    moods = extracted.get('moods', [])
    genres = extracted.get('genres', [])

    user_key = extracted.get('key')
    if user_key:
        key_parts = user_key.split()
        key_root = key_parts[0]
        key_mode = key_parts[1] if len(key_parts) > 1 else 'minor'
    else:
        genre_set = set(genres)
        if genre_set & MINOR_GENRES:
            key_root, key_mode = DEFAULT_MINOR_KEY
        elif genre_set & MAJOR_GENRES:
            key_root, key_mode = DEFAULT_MAJOR_KEY
        elif set(moods) & MINOR_MOODS:
            key_root, key_mode = DEFAULT_MINOR_KEY
        elif set(moods) & MAJOR_MOODS:
            key_root, key_mode = DEFAULT_MAJOR_KEY
        else:
            key_root, key_mode = FALLBACK_KEY

    logger.info(f"Key resolved: {key_root} {key_mode} "
                f"(source={'user' if extracted.get('key') else 'inferred'})")

    progressions = []
    for mood in moods:
        progressions.extend(search_progressions(mood=mood, key_type=key_mode))
    for genre in genres:
        progressions.extend(search_progressions(genre=genre, key_type=key_mode))

    if not progressions:
        progs = search_progressions(key_type=key_mode)
        if progs:
            progressions.extend(progs)
        elif not moods and not genres:
            progressions = search_progressions(mood='melancholic')

    unique = _dedupe(progressions)
    return {'progressions': _convert_progressions(unique[:MAX_RESULTS], key_root)}


def _lookup_drums(extracted: dict) -> dict:
    """Look up drum patterns by genre."""
    genres = extracted.get('genres', ['trap'])
    patterns = []
    for genre in genres:
        patterns.extend(get_drum_patterns_by_genre(genre))

    unique = _dedupe(patterns)
    result = []
    for pattern in unique[:MAX_RESULTS]:
        result.append({
            'name': pattern.name,
            'description': pattern.description,
            'tempo_range': pattern.tempo_range,
            'swing': pattern.swing,
            'grid': pattern.to_grid(),
            'genres': pattern.genres,
        })
    return {'drum_patterns': result}


def _lookup_artist_reference(extracted: dict) -> dict:
    """Look up progressions matching a single artist's profile."""
    artists = extracted.get('artists', [])
    if not artists:
        return {}

    profile = ARTIST_PROFILES.get(artists[0])
    if not profile:
        return {}

    key_type = profile['key_type']
    key_root = 'A' if key_type == 'minor' else 'C'

    user_key = extracted.get('key')
    if user_key:
        parts = user_key.split()
        key_root = parts[0]
        key_type = parts[1] if len(parts) > 1 else key_type

    progressions = []
    for mood in profile['moods']:
        progressions.extend(search_progressions(mood=mood, key_type=key_type))

    unique = _dedupe(progressions)
    return {'progressions': _convert_progressions(unique[:MAX_RESULTS], key_root)}


def _dedupe(items) -> list:
    """Deduplicate items by .name attribute."""
    seen = set()
    unique = []
    for item in items:
        if item.name not in seen:
            seen.add(item.name)
            unique.append(item)
    return unique


def _convert_progressions(progs, key_root: str) -> list:
    """Convert Progression objects to chord data dicts."""
    result = []
    for prog in progs:
        try:
            chords = get_progression_chords(
                prog.numerals, key_root, prog.key_type, octave=DEFAULT_OCTAVE
            )
            result.append({
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
    return result


# =============================================================================
# Response assembly
# =============================================================================

def build_response(intent_type: str, confidence: float, extracted: dict,
                   local_data: dict, generate_teaching_fn=None) -> dict:
    """
    Assemble the response dict from local data and agent outputs.

    Args:
        generate_teaching_fn: Callable(prog) -> str for teaching note generation.
            Injected by Orchestrator to allow API-first with local fallback.
    """
    response = {
        "success": True,
        "intent": intent_type,
        "confidence": confidence,
        "key_was_specified": 'key' in extracted,
    }

    if not local_data:
        return response

    # --- Progressions ---
    if "progressions" in local_data:
        response["progressions"] = local_data["progressions"]

        if local_data["progressions"]:
            prog = local_data["progressions"][0]
            validation_data = {
                "key": prog["key"],
                "chords": [
                    {"numeral": c["numeral"], "name": c["name"], "notes": c["note_names"]}
                    for c in prog["chords"]
                ]
            }
            validator = TheoryValidator()
            validation_result = validator.validate_progression(validation_data)
            response["validation"] = validation_result.to_dict()

            response["production_steps"] = generate_chord_instructions_local(prog)

            if generate_teaching_fn:
                response["teaching_note"] = generate_teaching_fn(prog)
            else:
                response["teaching_note"] = generate_progression_explanation_local(prog)

            response["progression"] = prog
            response["key"] = prog.get("key")
            response["bpm"] = parse_bpm_from_tempo(
                prog.get("tempo_range"), prog.get("tempo_suggestion"),
            )
            g = prog.get("genres")
            response["genre_context"] = (
                ", ".join(g) if isinstance(g, list) else (g if isinstance(g, str) else None)
            )
            response["progression_name"] = prog.get("name") or "–".join(
                prog.get("numerals") or []
            )

        theory_output = generate_theory_output_local(
            local_data["progressions"], intent_data=extracted,
        )
        if theory_output.get("alternatives"):
            response["alternatives"] = normalize_alternatives(theory_output["alternatives"])
        if theory_output.get("melody_direction"):
            response["melody_direction"] = theory_output["melody_direction"]

    # --- Drum patterns ---
    if "drum_patterns" in local_data:
        response["drum_patterns"] = local_data["drum_patterns"]

        if local_data["drum_patterns"]:
            pattern = local_data["drum_patterns"][0]
            response["bpm"] = parse_bpm_from_tempo(
                pattern.get("tempo_range"), pattern.get("tempo_suggestion"),
            )
            g = pattern.get("genres")
            response["genre_context"] = (
                ", ".join(g) if isinstance(g, list) else (g if isinstance(g, str) else None)
            )
            response["progression_name"] = pattern.get("name")

            if not response.get("production_steps"):
                response["production_steps"] = generate_drum_instructions_local(pattern)
            else:
                response["production_steps"] += "\n\n---\n\n" + generate_drum_instructions_local(pattern)

            if not response.get("teaching_note"):
                response["teaching_note"] = generate_rhythm_explanation_local(pattern)
            else:
                response["teaching_note"] += "\n\n---\n\n" + generate_rhythm_explanation_local(pattern)

    # --- Sound engineering ---
    if "sound_engineering_response" in local_data:
        response["sound_engineering_response"] = local_data["sound_engineering_response"]

    # --- Artist blend ---
    if "artist_blend" in local_data:
        response["artist_blend"] = local_data["artist_blend"]

    return response


def normalize_alternatives(alternatives: Optional[List[Dict]]) -> Optional[List[Dict]]:
    """Normalize alternative labels and chord format for the API response."""
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
# Legacy API-mode lookup (used by Orchestrator.process())
# =============================================================================

def execute_local_lookup_legacy(intent: ParsedIntent, routing: RoutingPlan) -> Optional[Dict]:
    """Execute local lookups for the API-mode path (process → _execute_local_lookup)."""
    extracted = intent.extracted
    result = {}

    if routing.local_lookup_type == "progression":
        moods = extracted.get("moods", [])
        genres = extracted.get("genres", [])

        progressions = []
        if moods and genres:
            for mood in moods:
                for genre in genres:
                    progressions.extend(search_progressions(mood=mood, genre=genre))
        elif moods:
            for mood in moods:
                progressions.extend(get_progressions_by_mood(mood))
        elif genres:
            for genre in genres:
                progressions.extend(get_progressions_by_genre(genre))

        unique = _dedupe(progressions)

        if unique:
            key = extracted.get("key", "A")
            if not key:
                key = "A"
            key_note = key.split()[0] if " " in key else key

            result["progressions"] = _convert_progressions(
                unique[:MAX_RESULTS], key_note
            )

    elif routing.local_lookup_type == "drums":
        genres = extracted.get("genres", [])
        patterns = []
        for genre in genres:
            patterns.extend(get_drum_patterns_by_genre(genre))

        unique = _dedupe(patterns)
        if unique:
            result["drum_patterns"] = []
            for pattern in unique[:3]:
                result["drum_patterns"].append({
                    "name": pattern.name,
                    "description": pattern.description,
                    "tempo_range": pattern.tempo_range,
                    "swing": pattern.swing,
                    "grid": pattern.to_grid(),
                    "ascii": pattern.to_ascii(),
                    "genres": pattern.genres,
                })

    return result if result else None
