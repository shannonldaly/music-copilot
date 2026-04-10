"""Contract tests for the Theory Agent.

Verifies: generate_theory_output_local() returns {primary, alternatives, melody_direction},
alternatives have the right labels, melody_direction has all required fields.
"""

from agents.theory_agent import generate_theory_output_local, generate_artist_blend_local


def _make_progression(key="A minor", name="Epic Minor"):
    """Helper to build a minimal valid progression dict."""
    from theory import search_progressions, get_progression_chords

    key_parts = key.split()
    key_root, key_type = key_parts[0], key_parts[1]
    progs = search_progressions(mood="melancholic", key_type=key_type)
    if not progs:
        progs = search_progressions(key_type=key_type)
    prog = progs[0]
    chords = get_progression_chords(prog.numerals, key_root, prog.key_type, octave=3)
    return {
        "name": prog.name,
        "numerals": prog.numerals,
        "key": key,
        "chords": chords,
        "tempo_range": prog.tempo_range,
        "description": prog.description,
        "moods": prog.moods,
        "genres": prog.genres,
    }


def test_theory_output_local_returns_required_keys():
    prog = _make_progression()
    result = generate_theory_output_local([prog])
    assert "primary" in result
    assert "alternatives" in result
    assert "melody_direction" in result


def test_alternatives_have_correct_labels():
    prog = _make_progression()
    result = generate_theory_output_local([prog])
    labels = {a["label"] for a in result["alternatives"]}
    assert "darker" in labels
    assert "more_movement" in labels
    assert "unexpected" in labels


def test_alternative_shape():
    prog = _make_progression()
    result = generate_theory_output_local([prog])
    for alt in result["alternatives"]:
        assert "label" in alt
        assert "progression_name" in alt
        assert "chords" in alt
        assert "character" in alt
        assert isinstance(alt["chords"], list)


def test_melody_direction_has_all_fields():
    prog = _make_progression()
    result = generate_theory_output_local([prog])
    md = result["melody_direction"]
    required = [
        "start_note", "start_note_context", "contour", "rhythm_feel",
        "avoid_on_strong_beats", "avoid_context", "suggested_range",
        "artist_reference",
    ]
    for field in required:
        assert field in md, f"Missing melody_direction field: {field}"


def test_melody_direction_start_note_has_keyboard_hint():
    prog = _make_progression()
    result = generate_theory_output_local([prog])
    ctx = result["melody_direction"]["start_note_context"]
    assert "on your keyboard" in ctx


def test_empty_progressions_returns_empty_dict():
    result = generate_theory_output_local([])
    assert result == {}


def test_artist_blend_returns_required_keys():
    result = generate_artist_blend_local("Massive Attack", "Deadmau5")
    assert result is not None
    assert "artist_blend" in result
    blend = result["artist_blend"]
    assert "artist_1" in blend
    assert "artist_2" in blend
    assert "blend_description" in blend
    assert "from_artist_1" in blend
    assert "from_artist_2" in blend
    assert "production_direction" in blend


def test_artist_blend_unknown_artist_returns_none():
    result = generate_artist_blend_local("Unknown Artist", "Deadmau5")
    assert result is None
