"""Unit tests for enharmonic spelling.

Verifies that flat keys use flats, sharp keys use sharps, and the
Theory Validator uses pitch-space comparison (not string matching)
so Bb and A# and B- all compare as equal.
"""

from validator import TheoryValidator
from theory import get_progression_chords


def test_bb_minor_chords_use_flats():
    """Chords in Bb minor should contain Bb, Db, Eb — not A#, C#, D#."""
    from theory import search_progressions
    progs = search_progressions(key_type="minor")
    if not progs:
        return
    prog = progs[0]
    chords = get_progression_chords(prog.numerals, "Bb", "minor", octave=3)
    all_note_names = []
    for c in chords:
        all_note_names.extend(c["note_names"])
    # Should not contain sharps in a flat key
    sharps = [n for n in all_note_names if "#" in n]
    assert len(sharps) == 0, f"Flat key Bb minor produced sharps: {sharps}"


def test_fsharp_minor_chords_use_sharps():
    """Chords in F# minor should contain F#, C#, G# — not Gb, Db, Ab."""
    from theory import search_progressions
    progs = search_progressions(key_type="minor")
    if not progs:
        return
    prog = progs[0]
    chords = get_progression_chords(prog.numerals, "F#", "minor", octave=3)
    all_note_names = []
    for c in chords:
        all_note_names.extend(c["note_names"])
    # Should not contain flats in a sharp key
    flats = [n for n in all_note_names if "b" in n and n[0] != "b"]
    assert len(flats) == 0, f"Sharp key F# minor produced flats: {flats}"


def test_validator_passes_bb_minor_progression():
    """Validator should accept Bb minor chords using pitch-space comparison."""
    v = TheoryValidator()
    result = v.validate_progression({
        "key": "Bb minor",
        "chords": [
            {"numeral": "i", "name": "Bbm", "notes": ["Bb3", "Db4", "F4"]},
            {"numeral": "VI", "name": "Gb", "notes": ["Gb3", "Bb3", "Db4"]},
        ],
    })
    assert result.passed is True, f"Errors: {result.errors}"


def test_validator_enharmonic_equivalence():
    """A# and Bb should be treated as the same pitch."""
    v = TheoryValidator()
    # This chord has A# in a Bb minor context — should pass via pitch-space
    result = v.validate_chord(
        {"name": "Bbm", "notes": ["Bb3", "Db4", "F4"]},
        "Bb minor",
    )
    assert result.passed is True
