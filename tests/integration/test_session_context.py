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


def test_stage_biased_mood_prompt_refines_melody_not_harmony():
    """A keyword-free-of-'melody' mood prompt at the melodyDir stage answers over
    the current progression instead of regenerating it (2026-09-02 shoot bug)."""
    o = Orchestrator()
    first = o.execute("melancholic lo-fi in A minor")
    ctx = _ctx_from(first)
    followup = o.execute("make it dreamier and more floaty",
                         session_context=ctx, active_stage="melodyDir")
    assert followup["intent"] == "melody_direction"
    assert followup["progression"]["name"] == first["progression"]["name"]
    assert followup["melody_direction"]


def test_stage_biased_bass_prompt_answers_over_progression():
    o = Orchestrator()
    first = o.execute("melancholic lo-fi in A minor")
    ctx = _ctx_from(first)
    followup = o.execute("something rounder and warmer underneath",
                         session_context=ctx, active_stage="bass")
    assert followup["intent"] == "bass_line"
    assert followup["bass_line"]["root_notes"]


def test_stage_bias_yields_to_explicit_harmony_request():
    o = Orchestrator()
    first = o.execute("melancholic lo-fi in A minor")
    ctx = _ctx_from(first)
    followup = o.execute("give me a darker progression instead",
                         session_context=ctx, active_stage="melodyDir")
    assert followup["intent"] == "mood_vibe"
    assert followup["progressions"]


def test_melody_direction_respects_prompt_mood():
    """'dreamy melody' and 'epic melody' over the same progression must differ
    (2026-09-02 shoot bug: intent_data was accepted but never used)."""
    o = Orchestrator()
    first = o.execute("melancholic lo-fi in A minor")
    ctx = _ctx_from(first)
    dreamy = o.execute("dreamy melody", session_context=ctx)
    epic = o.execute("epic melody", session_context=ctx)
    assert dreamy["melody_direction"]["contour"] != epic["melody_direction"]["contour"]
    assert "wave" in dreamy["melody_direction"]["contour"]
    assert "ascending" in epic["melody_direction"]["contour"]


def test_melody_direction_prompt_genre_sets_rhythm():
    o = Orchestrator()
    first = o.execute("melancholic lo-fi in A minor")
    ctx = _ctx_from(first)
    trap = o.execute("trap melody", session_context=ctx)
    assert "sparse" in trap["melody_direction"]["rhythm_feel"]


def test_melody_direction_falls_back_to_progression_tags():
    """A prompt with no mood/genre keeps the progression-derived direction."""
    o = Orchestrator()
    first = o.execute("melancholic lo-fi in A minor")
    ctx = _ctx_from(first)
    plain = o.execute("give me a melody", session_context=ctx)
    assert "descending" in plain["melody_direction"]["contour"]
    assert "behind the beat" in plain["melody_direction"]["rhythm_feel"]


def test_bass_line_respects_prompt_genre():
    """'house bass line' in a lo-fi session must not return the lo-fi pattern
    (the union let the session tag win the first-match rule)."""
    o = Orchestrator()
    first = o.execute("melancholic lo-fi in A minor")
    ctx = _ctx_from(first)
    house = o.execute("house bass line", session_context=ctx)
    lofi = o.execute("give me a bass line", session_context=ctx)
    assert "offbeat" in house["bass_line"]["pattern"]
    assert "passing note" in lofi["bass_line"]["pattern"]
    assert house["bass_line"]["root_notes"] == lofi["bass_line"]["root_notes"]


def test_sub_bass_gets_sub_style_not_melody_reference():
    """'sub bass' names the style: held sub roots, and a bass reference —
    never the melody artist table (Deftones on a bass panel, 2026-09-02)."""
    o = Orchestrator()
    first = o.execute("dark and moody")
    ctx = _ctx_from(first)
    sub = o.execute("sub bass", session_context=ctx)
    b = sub["bass_line"]
    assert "held root" in b["pattern"]
    assert "Sub-bass" in b["artist_reference"]
    assert "Deftones" not in b["artist_reference"]
    assert "melod" not in b["artist_reference"].lower()


def test_808_bass_gets_trap_style():
    o = Orchestrator()
    first = o.execute("melancholic lo-fi in A minor")
    ctx = _ctx_from(first)
    r = o.execute("808 bass", session_context=ctx)
    assert "808" in r["bass_line"]["pattern"]
    assert "808" in r["bass_line"]["artist_reference"]


def test_walking_bass_gets_walking_style():
    o = Orchestrator()
    first = o.execute("melancholic lo-fi in A minor")
    ctx = _ctx_from(first)
    r = o.execute("walking bass", session_context=ctx)
    assert "walking" in r["bass_line"]["pattern"]
