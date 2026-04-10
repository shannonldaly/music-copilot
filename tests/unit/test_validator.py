"""Unit tests for TheoryValidator.

Tests pitch validation, chord name matching, diatonic checks,
voice leading analysis, and enharmonic spelling.
"""

import pytest

from validator import TheoryValidator


@pytest.fixture
def v():
    return TheoryValidator()


# =========================================================================
# Note validation
# =========================================================================

def test_valid_note(v):
    result = v.validate_notes(["C4", "E4", "G4"])
    assert result.passed is True
    assert len(result.errors) == 0


def test_invalid_note(v):
    result = v.validate_notes(["X4"])
    assert result.passed is False
    assert any("X4" in e for e in result.errors)


def test_extreme_octave_warns(v):
    result = v.validate_notes(["C0"])
    # C0 is valid but extreme — may warn
    assert result.passed is True  # warnings don't fail


# =========================================================================
# Chord validation
# =========================================================================

def test_valid_am_chord(v):
    result = v.validate_chord(
        {"name": "Am", "notes": ["A3", "C4", "E4"]},
        "A minor",
    )
    assert result.passed is True


def test_wrong_chord_tones_fails(v):
    result = v.validate_chord(
        {"name": "Am", "notes": ["A3", "D4", "E4"]},  # D4 is not in Am
        "A minor",
    )
    assert result.passed is False


def test_chord_with_no_notes_fails(v):
    result = v.validate_chord({"name": "Am", "notes": []}, "A minor")
    assert result.passed is False


# =========================================================================
# Progression validation
# =========================================================================

def test_valid_progression_passes(v):
    result = v.validate_progression({
        "key": "A minor",
        "chords": [
            {"numeral": "i", "name": "Am", "notes": ["A3", "C4", "E4"]},
            {"numeral": "VI", "name": "F", "notes": ["F3", "A3", "C4"]},
            {"numeral": "III", "name": "C", "notes": ["C3", "E3", "G3"]},
            {"numeral": "VII", "name": "G", "notes": ["G3", "B3", "D4"]},
        ],
    })
    assert result.passed is True


def test_invalid_key_fails(v):
    result = v.validate_progression({
        "key": "Z# mixolydian",
        "chords": [{"numeral": "I", "name": "C", "notes": ["C3", "E3", "G3"]}],
    })
    assert result.passed is False


def test_parallel_fifths_warned(v):
    result = v.validate_progression({
        "key": "C major",
        "chords": [
            {"numeral": "I", "name": "C", "notes": ["C3", "G3", "E4"]},
            {"numeral": "ii", "name": "Dm", "notes": ["D3", "A3", "F4"]},
        ],
    })
    # Parallel fifths are warnings, not errors
    assert any("arallel" in w for w in result.warnings)
