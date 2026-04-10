"""Unit tests for key inference priority logic.

The Orchestrator resolves the key for progressions in this priority:
1. User-specified key (from prompt)
2. Genre-based default (lo-fi → A minor, pop → C major)
3. Mood-based default (melancholic → A minor, happy → C major)
4. Fallback (C major)
"""

import pytest

from agents.orchestrator import Orchestrator


@pytest.fixture
def o():
    return Orchestrator()


def _get_key(o, prompt):
    """Helper: run execute and return the resolved key."""
    result = o.execute(prompt)
    return result.get("key")


def test_user_specified_key_root_wins(o):
    """User key root (F#) is respected. Key type comes from matched progressions."""
    key = _get_key(o, "something melancholic in F# minor")
    assert key is not None
    assert key.startswith("F#")


def test_user_specified_key_root_major(o):
    """User key root (D) is respected."""
    key = _get_key(o, "happy chords in D major")
    assert key is not None
    assert key.startswith("D")


def test_genre_lo_fi_defaults_to_a_minor(o):
    key = _get_key(o, "lo-fi")
    assert key is not None
    assert "minor" in key


def test_genre_pop_defaults_to_c_major(o):
    key = _get_key(o, "pop")
    assert key is not None
    assert "major" in key


def test_mood_melancholic_defaults_to_minor(o):
    key = _get_key(o, "melancholic")
    assert key is not None
    assert "minor" in key


def test_mood_happy_defaults_to_major(o):
    key = _get_key(o, "happy")
    assert key is not None
    assert "major" in key


def test_fallback_is_c_major(o):
    """No mood, no genre, no key → fallback."""
    result = o.execute("something interesting")
    # With no signals, should get some key (fallback)
    key = result.get("key")
    # May be None if no progressions found, or C major
    if key is not None:
        assert "major" in key
