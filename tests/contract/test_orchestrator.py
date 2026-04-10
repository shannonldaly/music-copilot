"""Contract tests for the Orchestrator.

Verifies: detect_intent_local() returns (str, float, dict),
execute() returns a dict with required GenerateResponse fields.
"""

from agents.orchestrator import Orchestrator


def test_detect_intent_local_returns_tuple():
    o = Orchestrator()
    result = o.detect_intent_local("something melancholic")
    assert isinstance(result, tuple)
    assert len(result) == 3
    intent_type, confidence, extracted = result
    assert isinstance(intent_type, str)
    assert isinstance(confidence, float)
    assert isinstance(extracted, dict)


def test_detect_intent_local_extracted_has_moods_genres():
    o = Orchestrator()
    _, _, extracted = o.detect_intent_local("dark lo-fi trap")
    assert "moods" in extracted
    assert "genres" in extracted
    assert isinstance(extracted["moods"], list)
    assert isinstance(extracted["genres"], list)


def test_execute_returns_required_fields():
    o = Orchestrator()
    result = o.execute("melancholic lo-fi")
    assert isinstance(result, dict)
    assert "success" in result
    assert "intent" in result
    assert "confidence" in result
    assert result["success"] is True
    assert isinstance(result["intent"], str)
    assert isinstance(result["confidence"], float)


def test_execute_mood_vibe_has_progression_fields():
    o = Orchestrator()
    result = o.execute("melancholic lo-fi")
    assert "progressions" in result
    assert "validation" in result
    assert "production_steps" in result
    assert "teaching_note" in result
    assert "alternatives" in result
    assert "melody_direction" in result
    assert "key" in result
    assert "bpm" in result


def test_execute_returns_token_tracking():
    o = Orchestrator()
    result = o.execute("melancholic lo-fi")
    assert "tokens_used" in result
    assert "cost_usd" in result
    assert isinstance(result["tokens_used"], (int, float))
    assert isinstance(result["cost_usd"], (int, float))
