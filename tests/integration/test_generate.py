"""Integration tests for POST /api/generate.

Tests the full pipeline through the API for each intent type.
All tests use local mode (no API key) via the mock_anthropic fixture.
"""


def test_mood_vibe_returns_full_response(client):
    r = client.post("/api/generate", json={"prompt": "melancholic lo-fi"})
    assert r.status_code == 200
    d = r.json()
    assert d["intent"] == "mood_vibe"
    assert d["success"] is True
    assert d["progressions"] is not None
    assert len(d["progressions"]) > 0
    assert d["validation"] is not None
    assert d["validation"]["passed"] is True
    assert d["production_steps"] is not None
    assert d["teaching_note"] is not None
    assert d["alternatives"] is not None
    assert d["melody_direction"] is not None
    assert d["key"] is not None
    assert d["bpm"] is not None


def test_mood_vibe_progression_has_chord_structure(client):
    r = client.post("/api/generate", json={"prompt": "melancholic lo-fi"})
    prog = r.json()["progressions"][0]
    assert "name" in prog
    assert "numerals" in prog
    assert "key" in prog
    assert "chords" in prog
    chord = prog["chords"][0]
    assert "name" in chord
    assert "numeral" in chord
    assert "note_names" in chord


def test_drum_pattern_returns_full_response(client):
    r = client.post("/api/generate", json={"prompt": "give me a trap beat"})
    assert r.status_code == 200
    d = r.json()
    assert d["intent"] == "drum_pattern"
    assert d["drum_patterns"] is not None
    assert len(d["drum_patterns"]) > 0
    assert d["production_steps"] is not None
    assert d["teaching_note"] is not None


def test_drum_pattern_has_grid(client):
    r = client.post("/api/generate", json={"prompt": "trap beat"})
    pattern = r.json()["drum_patterns"][0]
    assert "name" in pattern
    assert "grid" in pattern
    assert "tempo_range" in pattern
    assert isinstance(pattern["grid"], dict)


def test_sound_engineering_returns_structured_response(client):
    r = client.post("/api/generate", json={"prompt": "how do I sidechain my bass to the kick"})
    assert r.status_code == 200
    d = r.json()
    assert d["intent"] == "sound_engineering"
    assert d["sound_engineering_response"] is not None
    se = d["sound_engineering_response"]
    assert "summary" in se
    assert "steps" in se
    assert "ableton_path" in se
    assert "principle" in se
    assert "artist_reference" in se


def test_artist_blend_returns_blend_and_progression(client):
    r = client.post("/api/generate", json={"prompt": "Massive Attack meets Deadmau5"})
    assert r.status_code == 200
    d = r.json()
    assert d["intent"] == "artist_blend"
    assert d["artist_blend"] is not None
    blend = d["artist_blend"]
    assert "artist_1" in blend
    assert "artist_2" in blend
    assert "blend_description" in blend
    assert d["progressions"] is not None


def test_artist_reference_returns_progression(client):
    r = client.post("/api/generate", json={"prompt": "something like Massive Attack"})
    assert r.status_code == 200
    d = r.json()
    assert d["intent"] == "artist_reference"
    assert d["progressions"] is not None
    assert d["validation"] is not None
    assert d["production_steps"] is not None
    assert d["teaching_note"] is not None
    assert d["key"] is not None
    # Massive Attack is minor
    assert "minor" in d["key"]


def test_artist_reference_major_key(client):
    r = client.post("/api/generate", json={"prompt": "something like Fred Again.."})
    assert r.status_code == 200
    d = r.json()
    assert d["intent"] == "artist_reference"
    assert "major" in d["key"]


def test_key_extraction_respects_user_key(client):
    r = client.post("/api/generate", json={"prompt": "something dark in Bb minor"})
    assert r.status_code == 200
    d = r.json()
    assert d["key_was_specified"] is True
    assert d["key"] == "Bb minor"


def test_session_id_returned(client):
    r = client.post("/api/generate", json={"prompt": "melancholic lo-fi"})
    assert r.status_code == 200
    assert "session_id" in r.json()
    assert len(r.json()["session_id"]) > 0


def test_empty_prompt_rejected(client):
    r = client.post("/api/generate", json={"prompt": ""})
    assert r.status_code == 422  # Validation error
