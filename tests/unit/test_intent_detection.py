"""Unit tests for detect_intent_local.

Tests keyword matching, intent priority ordering, artist extraction,
and key extraction from prompts.
"""

import pytest

from agents.orchestrator import Orchestrator


@pytest.fixture
def o():
    return Orchestrator()


# =========================================================================
# Intent type detection
# =========================================================================

def test_mood_vibe_detected(o):
    intent, conf, ext = o.detect_intent_local("something melancholic and dark")
    assert intent == "mood_vibe"
    assert conf >= 0.8
    assert "melancholic" in ext["moods"]
    assert "dark" in ext["moods"]


def test_drum_pattern_detected(o):
    intent, conf, ext = o.detect_intent_local("give me a trap beat")
    assert intent == "drum_pattern"
    assert "trap" in ext["genres"]


def test_sound_engineering_detected(o):
    intent, conf, ext = o.detect_intent_local("how do I sidechain my bass")
    assert intent == "sound_engineering"


def test_artist_blend_detected(o):
    intent, conf, ext = o.detect_intent_local("Massive Attack meets Deadmau5")
    assert intent == "artist_blend"
    assert conf >= 0.9


def test_artist_reference_detected(o):
    intent, conf, ext = o.detect_intent_local("something like Massive Attack")
    assert intent == "artist_reference"


def test_production_question_detected(o):
    intent, conf, ext = o.detect_intent_local("how do I create a new track")
    assert intent == "production_question"


# =========================================================================
# Intent priority ordering
# =========================================================================

def test_blend_takes_priority_over_artist_reference(o):
    """Two artists + blend word → artist_blend, not artist_reference."""
    intent, _, _ = o.detect_intent_local("Massive Attack and Deadmau5")
    assert intent == "artist_blend"


def test_se_takes_priority_over_mood(o):
    """SE keywords override mood even if mood words present."""
    intent, _, _ = o.detect_intent_local("dark sidechain compression")
    assert intent == "sound_engineering"


def test_single_artist_without_blend_word(o):
    """One artist without blend trigger → artist_reference."""
    intent, _, _ = o.detect_intent_local("I want something like Portishead")
    assert intent == "artist_reference"


# =========================================================================
# Key extraction
# =========================================================================

def test_key_extraction_sharp(o):
    _, _, ext = o.detect_intent_local("something in C# minor")
    assert ext.get("key") == "C# minor"


def test_key_extraction_flat(o):
    _, _, ext = o.detect_intent_local("give me chords in Bb major")
    assert ext.get("key") == "Bb major"


def test_key_extraction_normalized(o):
    _, _, ext = o.detect_intent_local("something in d min")
    assert ext.get("key") == "D minor"


def test_no_key_when_absent(o):
    _, _, ext = o.detect_intent_local("melancholic lo-fi")
    assert "key" not in ext


# =========================================================================
# Genre extraction
# =========================================================================

def test_genre_normalized_to_underscore(o):
    _, _, ext = o.detect_intent_local("lo-fi hip-hop")
    assert "lo_fi" in ext["genres"]
    assert "hip_hop" in ext["genres"]


# =========================================================================
# Artist extraction
# =========================================================================

def test_artist_canonical_name(o):
    _, _, ext = o.detect_intent_local("something like fred again")
    assert ext["artists"] == ["Fred Again.."]


def test_multiple_artists_extracted(o):
    _, _, ext = o.detect_intent_local("Massive Attack meets Portishead")
    assert "Massive Attack" in ext["artists"]
    assert "Portishead" in ext["artists"]


def test_nin_alias_resolved(o):
    _, _, ext = o.detect_intent_local("something like nin")
    assert ext["artists"] == ["Nine Inch Nails"]


# =============================================================================
# Follow-up intents: melody direction and bass line (session-stage prefills)
# =============================================================================

def test_melody_direction_intent():
    """The melodyDir stage prefill must classify as melody_direction, not theory/mood."""
    o = Orchestrator()
    intent, conf, ext = o.detect_intent_local("Suggest a melodic direction over this progression")
    assert intent == "melody_direction"
    assert conf > 0.5


def test_bass_line_intent_keeps_extracted_genres():
    """The bass stage prefill must classify as bass_line and keep the lo-fi genre."""
    o = Orchestrator()
    intent, conf, ext = o.detect_intent_local("Give me a lo-fi bass line to match this progression")
    assert intent == "bass_line"
    assert "lo_fi" in ext["genres"]


def test_eq_bass_question_stays_sound_engineering():
    """'bass' in an EQ question must not hijack the sound_engineering route."""
    o = Orchestrator()
    intent, conf, ext = o.detect_intent_local("How should I EQ and space these chords in Ableton?")
    assert intent == "sound_engineering"


def test_drum_intent_leaves_genres_empty_for_context():
    """A genre-less drum prompt keeps genres empty so session context can fill them."""
    o = Orchestrator()
    intent, conf, ext = o.detect_intent_local("Give me a drum pattern that matches this vibe")
    assert intent == "drum_pattern"
    assert ext["genres"] == []


# =========================================================================
# Stage-aware routing bias (apply_stage_bias)
# =========================================================================

from agents.intent_detection import apply_stage_bias


def test_stage_bias_reroutes_mood_prompt_at_melody_stage():
    """'make it dreamier' on the melody stage refines the melody, not the harmony."""
    o = Orchestrator()
    intent, conf, ext = o.detect_intent_local("make it dreamier and more floaty")
    assert intent == "mood_vibe"
    intent, conf, biased = apply_stage_bias(intent, conf, ext, "melodyDir", "make it dreamier and more floaty")
    assert biased is True
    assert intent == "melody_direction"


def test_stage_bias_reroutes_bass_drums_mix_stages():
    for stage, expected in [("bass", "bass_line"), ("drums", "drum_pattern"), ("mix", "sound_engineering")]:
        intent, conf, biased = apply_stage_bias("mood_vibe", 0.9, {}, stage, "warmer and rounder please")
        assert biased is True, stage
        assert intent == expected, stage


def test_stage_bias_sets_question_for_sound_engineering():
    ext = {}
    intent, conf, biased = apply_stage_bias("mood_vibe", 0.9, ext, "mix", "warmer and rounder please")
    assert ext["question"] == "warmer and rounder please"


def test_stage_bias_respects_explicit_harmony_request():
    """Asking for a new progression at the melody stage still regenerates harmony."""
    intent, conf, biased = apply_stage_bias(
        "mood_vibe", 0.9, {"moods": ["dreamy"]}, "melodyDir", "give me a dreamier progression instead")
    assert biased is False
    assert intent == "mood_vibe"


def test_stage_bias_never_overrides_specific_intents():
    """A specific keyword verdict (bass at melody stage, drums at bass stage…) stands."""
    intent, conf, biased = apply_stage_bias("bass_line", 0.85, {}, "melodyDir", "give me a bass line")
    assert biased is False
    assert intent == "bass_line"


def test_stage_bias_noop_without_stage_or_unknown_stage():
    for stage in (None, "", "progression", "not-a-stage"):
        intent, conf, biased = apply_stage_bias("mood_vibe", 0.9, {}, stage, "something dreamy")
        assert biased is False
        assert intent == "mood_vibe"
