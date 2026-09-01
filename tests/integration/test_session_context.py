"""
Integration tests for session-context-aware follow-ups.

The stage flow depends on this: melody/bass/drum follow-ups must answer over
the progression already on screen, not regenerate from scratch (the pre-fix
bug sent every stage prefill back to a fresh C-major/mood-vibe progression).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents.orchestrator import Orchestrator
from agents.theory_local import generate_bass_line_local


def _ctx_from(result):
    prog = result["progressions"][0]
    return {"progression": prog, "key": prog.get("key"),
            "genres": prog.get("genres") or [], "bpm": None}


def test_melody_followup_keeps_progression():
    o = Orchestrator()
    first = o.execute("melancholic lo-fi in A minor")
    ctx = _ctx_from(first)
    followup = o.execute("Suggest a melodic direction over this progression",
                         session_context=ctx)
    assert followup["intent"] == "melody_direction"
    assert followup["key"] == first["key"]
    assert followup["progression"]["name"] == first["progression"]["name"]
    assert followup["melody_direction"]


def test_bass_followup_returns_bass_over_same_progression():
    o = Orchestrator()
    first = o.execute("melancholic lo-fi in A minor")
    ctx = _ctx_from(first)
    followup = o.execute("Give me a lo-fi bass line to match this progression",
                         session_context=ctx)
    assert followup["intent"] == "bass_line"
    assert followup["key"] == first["key"]
    assert followup["bass_line"]["root_notes"]
    roots = {c["root"] for c in first["progression"]["chords"]}
    assert {n[:-1] for n in followup["bass_line"]["root_notes"]} <= roots


def test_drum_followup_inherits_session_genres():
    o = Orchestrator()
    first = o.execute("melancholic lo-fi in A minor")
    ctx = _ctx_from(first)
    followup = o.execute("Give me a drum pattern that matches this vibe",
                         session_context=ctx)
    assert followup["intent"] == "drum_pattern"
    genres = {g for p in followup["drum_patterns"] for g in p["genres"]}
    assert "trap" not in genres or "lo-fi" in genres


def test_explicit_trap_still_works_without_context():
    o = Orchestrator()
    result = o.execute("give me a trap drum pattern")
    assert result["intent"] == "drum_pattern"
    assert any("trap" in p["genres"] for p in result["drum_patterns"])


def test_bass_generator_shape():
    """Contract: the bass panel renders exactly these fields."""
    o = Orchestrator()
    first = o.execute("melancholic lo-fi in A minor")
    bass = generate_bass_line_local(first["progressions"][0])
    for field in ("root_notes", "pattern", "rhythm_feel", "register", "tip", "artist_reference"):
        assert bass[field], f"missing {field}"
    assert all(n.endswith("2") for n in bass["root_notes"])


def test_followup_without_context_still_generates():
    """No session context (fresh session) degrades to the old generate-a-progression path."""
    o = Orchestrator()
    result = o.execute("Suggest a melodic direction over this progression")
    assert result["success"]
    assert result.get("progression") or result.get("melody_direction")
