"""Regression tests — converted from 7 manual curl verification tests.

These are the exact tests that were run manually after each commit
in the B+ refactor (Phase 3a). They verify the GenerateResponse shape
has not changed.
"""


def test_curl_1_mood_vibe(client):
    """curl test 1: melancholic lo-fi → full chord response."""
    r = client.post("/api/generate", json={
        "prompt": "give me something melancholic and lo-fi",
    })
    assert r.status_code == 200
    d = r.json()
    assert d["intent"] == "mood_vibe"
    assert d["confidence"] == 0.9
    assert d["progressions"] is not None
    assert d["validation"] is not None
    assert d["production_steps"] is not None
    assert d["teaching_note"] is not None
    assert d["alternatives"] is not None
    assert d["melody_direction"] is not None
    assert d["key"] == "A minor"


def test_curl_2_drum_pattern(client):
    """curl test 2: trap beat → drum pattern response."""
    r = client.post("/api/generate", json={
        "prompt": "give me a trap beat",
    })
    assert r.status_code == 200
    d = r.json()
    assert d["intent"] == "drum_pattern"
    assert d["drum_patterns"] is not None
    assert d["production_steps"] is not None
    assert d["teaching_note"] is not None


def test_curl_3_sound_engineering(client):
    """curl test 3: sidechain → SE structured response."""
    r = client.post("/api/generate", json={
        "prompt": "how do I sidechain my bass to the kick",
    })
    assert r.status_code == 200
    d = r.json()
    assert d["intent"] == "sound_engineering"
    assert d["sound_engineering_response"] is not None
    se = d["sound_engineering_response"]
    assert sorted(se.keys()) == ["ableton_path", "artist_reference", "principle", "steps", "summary"]


def test_curl_4_artist_blend(client):
    """curl test 4: artist blend → blend + progression."""
    r = client.post("/api/generate", json={
        "prompt": "Massive Attack meets Deadmau5",
    })
    assert r.status_code == 200
    d = r.json()
    assert d["intent"] == "artist_blend"
    assert d["artist_blend"] is not None
    assert d["progressions"] is not None


def test_curl_5_key_extraction(client):
    """curl test 5: explicit key in prompt → key_was_specified."""
    r = client.post("/api/generate", json={
        "prompt": "something dark in Bb minor",
    })
    assert r.status_code == 200
    d = r.json()
    assert d["intent"] == "mood_vibe"
    assert d["key"] == "Bb minor"
    assert d["key_was_specified"] is True


def test_curl_6_artist_reference_minor(client):
    """curl test 6: single artist (Massive Attack) → minor key progression."""
    r = client.post("/api/generate", json={
        "prompt": "something like Massive Attack",
    })
    assert r.status_code == 200
    d = r.json()
    assert d["intent"] == "artist_reference"
    assert d["progressions"] is not None
    assert d["validation"] is not None
    assert d["key"] is not None
    assert "minor" in d["key"]


def test_curl_7_artist_reference_major(client):
    """curl test 7: single artist (Fred Again..) → major key progression."""
    r = client.post("/api/generate", json={
        "prompt": "something like Fred Again..",
    })
    assert r.status_code == 200
    d = r.json()
    assert d["intent"] == "artist_reference"
    assert d["key"] is not None
    assert "major" in d["key"]
