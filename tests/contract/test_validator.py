"""Contract tests for the Theory Validator.

Verifies: validate_progression() returns ValidationResult with
passed, errors, warnings. to_dict() has the right shape.
"""

from validator import TheoryValidator


def test_validation_result_has_required_fields():
    v = TheoryValidator()
    result = v.validate_progression({
        "key": "A minor",
        "chords": [
            {"numeral": "i", "name": "Am", "notes": ["A3", "C4", "E4"]},
        ],
    })
    assert hasattr(result, "passed")
    assert hasattr(result, "errors")
    assert hasattr(result, "warnings")
    assert isinstance(result.passed, bool)
    assert isinstance(result.errors, list)
    assert isinstance(result.warnings, list)


def test_to_dict_shape():
    v = TheoryValidator()
    result = v.validate_progression({
        "key": "C major",
        "chords": [
            {"numeral": "I", "name": "C", "notes": ["C3", "E3", "G3"]},
        ],
    })
    d = result.to_dict()
    assert "passed" in d
    assert "errors" in d
    assert "warnings" in d
    assert "corrected_output" in d


def test_empty_chords_returns_error():
    v = TheoryValidator()
    result = v.validate_progression({"key": "C major", "chords": []})
    assert result.passed is False
    assert len(result.errors) > 0
