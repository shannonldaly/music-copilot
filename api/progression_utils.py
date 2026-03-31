"""
Helpers for /api/generate progression payload, alternatives, and /api/progression/expand.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from theory import get_progression_chords, search_progressions
from theory.chords import get_chord_notes
from validator import TheoryValidator


def parse_bpm_from_tempo(tempo_range: Any, tempo_suggestion: Any = None) -> int:
    if tempo_suggestion is not None:
        if isinstance(tempo_suggestion, (int, float)):
            return int(tempo_suggestion)
        m = re.search(r"(\d+)", str(tempo_suggestion))
        if m:
            return int(m.group(1))
    if tempo_range is None:
        return 85
    if isinstance(tempo_range, (list, tuple)) and len(tempo_range) >= 2:
        return int(round((float(tempo_range[0]) + float(tempo_range[1])) / 2))
    s = str(tempo_range)
    m = re.search(r"(\d+)\s*[-–]\s*(\d+)", s)
    if m:
        return int(round((int(m.group(1)) + int(m.group(2))) / 2))
    m2 = re.search(r"(\d+)", s)
    return int(m2.group(1)) if m2 else 85


def infer_scale_from_key(key: str) -> str:
    kl = (key or "").lower()
    if "minor" in kl or "aeolian" in kl:
        return "natural minor"
    return "major"


def slim_alternative_from_prog(prog: Dict) -> Dict[str, Any]:
    chords = []
    for c in prog.get("chords") or []:
        chords.append({
            "name": c.get("name", ""),
            "numeral": c.get("numeral", ""),
        })
    return {
        "chords": chords,
        "progression_name": prog.get("name") or "–".join(prog.get("numerals") or []) or "",
    }


def prog_named_to_dict(p, key_note: str = "A") -> Optional[Dict]:
    try:
        chords = get_progression_chords(p.numerals, key_note, p.key_type, octave=3)
        return {
            "name": p.name,
            "numerals": p.numerals,
            "key": f"{key_note} {p.key_type}",
            "chords": chords,
            "tempo_range": p.tempo_range,
            "description": p.description,
            "moods": p.moods,
            "genres": p.genres,
        }
    except ValueError:
        return None


def fetch_dark_progression_dict(exclude_name: Optional[str]) -> Optional[Dict]:
    try:
        for p in search_progressions(mood="dark"):
            if exclude_name and p.name == exclude_name:
                continue
            d = prog_named_to_dict(p)
            if d:
                return d
    except Exception:
        pass
    return None


def build_alternatives(primary: Dict, sibling_progressions: List[Dict]) -> List[Dict[str, Any]]:
    primary_name = primary.get("name")
    pool = [p for p in sibling_progressions if p.get("name") and p.get("name") != primary_name]
    out: List[Dict[str, Any]] = []

    dark = fetch_dark_progression_dict(primary_name)
    if dark:
        slim = slim_alternative_from_prog(dark)
        slim["label"] = "darker"
        out.append(slim)
        pool = [p for p in pool if p.get("name") != dark.get("name")]

    for lbl in ("more movement", "unexpected"):
        if not pool:
            break
        p = pool.pop(0)
        slim = slim_alternative_from_prog(p)
        slim["label"] = lbl
        out.append(slim)

    return out[:3]


def melody_direction_block(key: str, progression_name: str) -> Dict[str, str]:
    root = (key or "A minor").split()[0]
    return {
        "start_note": f"E4 (the 5th of {root}m)",
        "contour": "Descend toward the tonic register by bar 3, leap up to the octave above the root on bar 4 for lift.",
        "rhythm_feel": "Mostly quarter notes; use 8th-note pairs on beats 3–4 for momentum.",
        "avoid_strong": f"F (♭6) — use as passing color, not a downbeat target in {key or 'this key'}.",
        "range": "Stay within A3–E5 for a singable, production-friendly line.",
        "reference": "docs/artist_dna.md — Massive Attack (minimal minor harmony, trip-hop space)",
    }


def expand_chords_from_names(
    chord_names: List[str],
    key: str,
    progression_name: str,
) -> Tuple[List[Dict], Dict, str]:
    numerals = [x.strip() for x in re.split(r"[-–]+", progression_name.strip()) if x.strip()]
    if len(numerals) < len(chord_names):
        numerals.extend([""] * (len(chord_names) - len(numerals)))

    chords_out: List[Dict] = []
    for i, name in enumerate(chord_names):
        name = (name or "").strip()
        if not name:
            continue
        notes = get_chord_notes(name, octave=3)
        note_names = [str(n) for n in notes]
        num = numerals[i] if i < len(numerals) else ""
        chords_out.append({
            "numeral": num,
            "name": name,
            "note_names": note_names,
        })

    scale = infer_scale_from_key(key)
    validation_data = {
        "key": key,
        "scale": scale,
        "progression_name": progression_name,
        "chords": [
            {"numeral": c["numeral"], "name": c["name"], "notes": c["note_names"]}
            for c in chords_out
        ],
    }
    validator = TheoryValidator()
    result = validator.validate_progression(validation_data)
    return chords_out, result.to_dict(), scale
