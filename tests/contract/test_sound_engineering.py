"""Contract tests for the Sound Engineering Agent.

Verifies: generate_sound_engineering_local() returns the unified structured
shape {summary, steps, ableton_path, principle, artist_reference} or None.
"""

from agents.sound_engineering_agent import generate_sound_engineering_local

REQUIRED_KEYS = {"summary", "steps", "ableton_path", "principle", "artist_reference"}


def test_local_returns_structured_dict_for_known_topic():
    result = generate_sound_engineering_local("how do I sidechain my bass")
    assert result is not None
    assert isinstance(result, dict)
    assert REQUIRED_KEYS.issubset(result.keys()), f"Missing keys: {REQUIRED_KEYS - result.keys()}"


def test_local_steps_is_list():
    result = generate_sound_engineering_local("how do I use compression")
    assert isinstance(result["steps"], list)
    assert len(result["steps"]) > 0


def test_local_returns_none_for_unknown_topic():
    result = generate_sound_engineering_local("what is the meaning of life")
    assert result is None


def test_all_nine_local_topics_return_valid_shape():
    topics = [
        "sidechain", "eq", "compression", "reverb", "automation",
        "filter", "bass", "kick", "synthesis",
    ]
    for topic in topics:
        result = generate_sound_engineering_local(topic)
        assert result is not None, f"Topic '{topic}' returned None"
        assert REQUIRED_KEYS.issubset(result.keys()), f"Topic '{topic}' missing keys"
