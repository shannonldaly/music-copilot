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
