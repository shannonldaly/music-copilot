"""Contract tests for the Production Agent.

Verifies: generate_chord_instructions_local() returns a string,
generate_drum_instructions_local() returns a string,
both contain MCP v2 comments.
"""

from agents.production_agent import (
    generate_chord_instructions_local,
    generate_drum_instructions_local,
)


def _sample_progression():
    return {
        "name": "Epic Minor",
        "key": "A minor",
        "tempo_range": (75, 85),
        "chords": [
            {"name": "Am", "numeral": "i", "note_names": ["A3", "C4", "E4"]},
            {"name": "F", "numeral": "VI", "note_names": ["F3", "A3", "C4"]},
        ],
    }


def _sample_drum_pattern():
    return {
        "name": "Trap Basic",
        "description": "Standard trap pattern",
        "tempo_range": (130, 160),
        "swing": 0,
        "grid": {"kick": [0, 10], "snare": [4, 12], "closed_hat": [0, 2, 4, 6, 8, 10, 12, 14]},
    }


def test_chord_instructions_returns_string():
    result = generate_chord_instructions_local(_sample_progression())
    assert isinstance(result, str)
    assert len(result) > 100


def test_chord_instructions_contains_mcp_comments():
    result = generate_chord_instructions_local(_sample_progression())
    assert "# MCP v2:" in result


def test_chord_instructions_uses_actual_bpm():
    result = generate_chord_instructions_local(_sample_progression())
    assert "80 BPM" in result  # midpoint of (75, 85)
    assert "120 BPM" not in result


def test_drum_instructions_returns_string():
    result = generate_drum_instructions_local(_sample_drum_pattern())
    assert isinstance(result, str)
    assert len(result) > 100


def test_drum_instructions_contains_mcp_comments():
    result = generate_drum_instructions_local(_sample_drum_pattern())
    assert "# MCP v2:" in result
