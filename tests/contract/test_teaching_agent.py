"""Contract tests for the Teaching Agent.

Verifies: generate_progression_explanation_local() returns a string,
generate_rhythm_explanation_local() returns a string,
both contain the expected sections.
"""

from agents.teaching_agent import (
    generate_progression_explanation_local,
    generate_rhythm_explanation_local,
)


def test_progression_explanation_returns_string():
    prog = {
        "name": "Epic Minor",
        "numerals": ["i", "VI", "III", "VII"],
        "key": "A minor",
        "moods": ["epic", "melancholic"],
        "description": "The viral progression.",
    }
    result = generate_progression_explanation_local(prog)
    assert isinstance(result, str)
    assert len(result) > 50


def test_progression_explanation_contains_why():
    prog = {
        "name": "Epic Minor",
        "numerals": ["i", "VI", "III", "VII"],
        "key": "A minor",
        "moods": ["epic"],
        "description": "Test.",
    }
    result = generate_progression_explanation_local(prog)
    assert "Why It Works" in result


def test_progression_explanation_contains_try_this():
    prog = {
        "name": "Epic Minor",
        "numerals": ["i", "VI", "III", "VII"],
        "key": "A minor",
        "moods": ["epic"],
        "description": "Test.",
    }
    result = generate_progression_explanation_local(prog)
    assert "Try This" in result


def test_rhythm_explanation_returns_string():
    pattern = {
        "name": "Trap Rolling Hats",
        "description": "Trap with 16th-note hi-hats",
        "tempo_range": (130, 160),
        "swing": 0,
        "grid": {
            "kick": [0, 7, 10],
            "snare": [4, 12],
            "closed_hat": list(range(16)),
        },
    }
    result = generate_rhythm_explanation_local(pattern)
    assert isinstance(result, str)
    assert "Trap Rolling Hats" in result


def test_rhythm_explanation_has_swing_section_when_swing():
    pattern = {
        "name": "Lo-fi Boom Bap",
        "description": "Lo-fi with swing",
        "tempo_range": (80, 90),
        "swing": 60,
        "grid": {"kick": [0, 10], "snare": [4, 12]},
    }
    result = generate_rhythm_explanation_local(pattern)
    assert "Swing" in result
    assert "60%" in result
