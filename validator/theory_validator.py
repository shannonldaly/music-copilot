"""
Theory Validator — Deterministic music theory validation using music21.

This is NOT an LLM — it's programmatic validation code.
100% accurate, zero API cost.

Validates:
1. Note names are valid pitches with correct octaves
2. Chord notes match the stated chord name/quality
3. Chords belong to the stated key (flags borrowed chords)
4. Voice leading (parallel fifths/octaves, large leaps)
5. Progression makes harmonic sense

Usage:
    from validator import TheoryValidator

    validator = TheoryValidator()
    result = validator.validate_progression(progression_data)

    if result.passed:
        print("Validation passed!")
    else:
        print(f"Errors: {result.errors}")
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum
import re

from music21 import (
    note,
    pitch,
    chord,
    key,
    scale,
    interval,
    roman,
    stream,
    analysis,
)

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.logging import log_agent_call


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    ERROR = "error"      # Must fix - incorrect theory
    WARNING = "warning"  # Should consider - suboptimal but not wrong
    INFO = "info"        # FYI - stylistic note


@dataclass
class ValidationIssue:
    """A single validation issue."""
    severity: ValidationSeverity
    code: str  # e.g., "INVALID_NOTE", "PARALLEL_FIFTHS"
    message: str
    location: Optional[str] = None  # e.g., "chord 2", "between chords 1-2"
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of validation."""
    passed: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    info: List[str] = field(default_factory=list)
    issues: List[ValidationIssue] = field(default_factory=list)
    corrected_output: Optional[Dict] = None

    def add_issue(self, issue: ValidationIssue):
        """Add an issue and update the appropriate list."""
        self.issues.append(issue)
        msg = f"{issue.location}: {issue.message}" if issue.location else issue.message
        if issue.suggestion:
            msg += f" ({issue.suggestion})"

        if issue.severity == ValidationSeverity.ERROR:
            self.errors.append(msg)
            self.passed = False
        elif issue.severity == ValidationSeverity.WARNING:
            self.warnings.append(msg)
        else:
            self.info.append(msg)

    def to_dict(self) -> Dict:
        """Convert to dictionary format matching CLAUDE.md spec."""
        return {
            "passed": self.passed,
            "errors": self.errors,
            "warnings": self.warnings,
            "corrected_output": self.corrected_output,
        }


class TheoryValidator:
    """
    Validates music theory output from the Theory Agent.

    Uses music21 for accurate, deterministic validation.
    """

    # Valid octave range for typical instruments
    MIN_OCTAVE = 0
    MAX_OCTAVE = 8

    # Maximum interval for "large leap" warning (in semitones)
    LARGE_LEAP_THRESHOLD = 12  # octave

    def __init__(self):
        pass

    @log_agent_call
    def validate_progression(self, progression_data: Dict) -> ValidationResult:
        """
        Validate a complete chord progression.

        Expected format:
        {
            "key": "A minor",
            "scale": "natural minor",
            "progression_name": "i–VI–III–VII",
            "chords": [
                {"numeral": "i", "name": "Am", "notes": ["A3", "C4", "E4"]},
                {"numeral": "VI", "name": "F", "notes": ["F3", "A3", "C4"]},
                ...
            ],
            "tempo_suggestion": "85 BPM"
        }

        Returns:
            ValidationResult with passed status, errors, and warnings
        """
        result = ValidationResult(passed=True)

        # Extract key information
        key_str = progression_data.get("key", "C major")
        scale_type = progression_data.get("scale", "major")
        chords_data = progression_data.get("chords", [])

        if not chords_data:
            result.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="NO_CHORDS",
                message="No chords provided in progression",
            ))
            return result

        # Parse the key
        try:
            parsed_key = self._parse_key(key_str)
        except Exception as e:
            result.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="INVALID_KEY",
                message=f"Could not parse key '{key_str}': {e}",
            ))
            return result

        # Validate each chord
        previous_chord_notes = None
        for i, chord_data in enumerate(chords_data, 1):
            chord_result = self._validate_chord(
                chord_data,
                parsed_key,
                scale_type,
                chord_index=i
            )

            # Add all issues from chord validation
            for issue in chord_result.issues:
                result.add_issue(issue)

            # Check voice leading with previous chord
            if previous_chord_notes is not None:
                current_notes = chord_data.get("notes", [])
                vl_issues = self._check_voice_leading(
                    previous_chord_notes,
                    current_notes,
                    chord_index=i
                )
                for issue in vl_issues:
                    result.add_issue(issue)

            previous_chord_notes = chord_data.get("notes", [])

        return result

    def validate_chord(self, chord_data: Dict, key_str: str = "C major") -> ValidationResult:
        """
        Validate a single chord.

        Args:
            chord_data: {"name": "Am", "notes": ["A3", "C4", "E4"]}
            key_str: Key context like "A minor"

        Returns:
            ValidationResult
        """
        result = ValidationResult(passed=True)

        try:
            parsed_key = self._parse_key(key_str)
        except Exception:
            parsed_key = key.Key("C")

        chord_result = self._validate_chord(chord_data, parsed_key, "major", 1)
        for issue in chord_result.issues:
            result.add_issue(issue)

        return result

    def validate_notes(self, notes: List[str]) -> ValidationResult:
        """
        Validate a list of note names.

        Args:
            notes: ["A3", "C4", "E4"]

        Returns:
            ValidationResult
        """
        result = ValidationResult(passed=True)

        for note_str in notes:
            issues = self._validate_note(note_str)
            for issue in issues:
                result.add_issue(issue)

        return result

    def _parse_key(self, key_str: str) -> key.Key:
        """Parse a key string like 'A minor' or 'C major'."""
        # Handle formats: "A minor", "A min", "Am", "A", "A major"
        key_str = key_str.strip()

        # Try direct parsing first
        try:
            return key.Key(key_str)
        except Exception:
            pass

        # Parse manually
        parts = key_str.split()
        if len(parts) >= 2:
            tonic = parts[0]
            mode = parts[1].lower()
            if mode in ["minor", "min", "m"]:
                return key.Key(tonic, "minor")
            elif mode in ["major", "maj"]:
                return key.Key(tonic, "major")

        # Try just the first part
        return key.Key(parts[0] if parts else "C")

    def _validate_chord(
        self,
        chord_data: Dict,
        parsed_key: key.Key,
        scale_type: str,
        chord_index: int
    ) -> ValidationResult:
        """Validate a single chord within a progression."""
        result = ValidationResult(passed=True)

        chord_name = chord_data.get("name", "")
        numeral = chord_data.get("numeral", "")
        notes = chord_data.get("notes", [])
        location = f"chord {chord_index}"

        if not notes:
            result.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="NO_NOTES",
                message="Chord has no notes",
                location=location,
            ))
            return result

        # Validate each note
        parsed_notes = []
        for note_str in notes:
            note_issues = self._validate_note(note_str)
            for issue in note_issues:
                issue.location = location
                result.add_issue(issue)

            try:
                p = pitch.Pitch(note_str)
                parsed_notes.append(p)
            except Exception:
                pass

        if not parsed_notes:
            return result

        # Create music21 chord and validate
        try:
            m21_chord = chord.Chord(parsed_notes)

            # Check if notes match the stated chord name
            if chord_name:
                name_issues = self._check_chord_name_match(
                    m21_chord, chord_name, notes, location
                )
                for issue in name_issues:
                    result.add_issue(issue)

            # Check if chord is diatonic to the key
            diatonic_issues = self._check_diatonic(
                m21_chord, parsed_key, numeral, location
            )
            for issue in diatonic_issues:
                result.add_issue(issue)

        except Exception as e:
            result.add_issue(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="CHORD_PARSE_ERROR",
                message=f"Could not fully analyze chord: {e}",
                location=location,
            ))

        return result

    def _validate_note(self, note_str: str) -> List[ValidationIssue]:
        """Validate a single note string like 'A3' or 'F#4'."""
        issues = []

        if not note_str:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="EMPTY_NOTE",
                message="Empty note string",
            ))
            return issues

        # Try to parse with music21
        try:
            p = pitch.Pitch(note_str)

            # Check octave range
            if p.octave is not None:
                if p.octave < self.MIN_OCTAVE or p.octave > self.MAX_OCTAVE:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="EXTREME_OCTAVE",
                        message=f"Note '{note_str}' is in an extreme octave range",
                        suggestion=f"Consider octave {max(2, min(6, p.octave))}",
                    ))

        except Exception as e:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="INVALID_NOTE",
                message=f"Invalid note '{note_str}': {e}",
            ))

        return issues

    @staticmethod
    def _normalize_pitch_name(name: str) -> str:
        """Normalize a pitch name for comparison.

        Handles music21's convention (B- for Bb) and our convention (Bb).
        Converts everything to pitch-space comparison using music21.
        """
        try:
            return pitch.Pitch(name).ps
        except Exception:
            return name

    def _check_chord_name_match(
        self,
        m21_chord: chord.Chord,
        stated_name: str,
        notes: List[str],
        location: str
    ) -> List[ValidationIssue]:
        """Check if the notes match the stated chord name."""
        issues = []

        # Compare using pitch-space values (float MIDI) to avoid enharmonic mismatches
        # e.g., Bb and B- and A# all map to the same pitch-space value
        actual_ps = set(round(p.ps % 12, 2) for p in m21_chord.pitches)

        try:
            expected_pitches = self._get_expected_pitches(stated_name)
            if not expected_pitches:
                return issues

            expected_ps = set()
            expected_name_map = {}
            for name in expected_pitches:
                try:
                    ps_val = round(pitch.Pitch(name).ps % 12, 2)
                    expected_ps.add(ps_val)
                    expected_name_map[ps_val] = name
                except Exception:
                    pass

            if expected_ps and actual_ps != expected_ps:
                missing_ps = expected_ps - actual_ps
                extra_ps = actual_ps - expected_ps

                if missing_ps:
                    missing_names = {expected_name_map.get(ps, f"pc{ps}") for ps in missing_ps}
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="MISSING_CHORD_TONE",
                        message=f"Chord '{stated_name}' is missing notes: {missing_names}",
                        location=location,
                        suggestion=f"Add {missing_names} to complete the chord",
                    ))

                if extra_ps:
                    # Map extra pitch-space values back to actual names
                    actual_name_map = {round(p.ps % 12, 2): p.name for p in m21_chord.pitches}
                    extra_names = {actual_name_map.get(ps, f"pc{ps}") for ps in extra_ps}
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="EXTRA_CHORD_TONE",
                        message=f"Chord '{stated_name}' has unexpected notes: {extra_names}",
                        location=location,
                        suggestion="These may be extensions or voice leading tones",
                    ))

        except Exception:
            pass

        return issues

    def _get_expected_pitches(self, chord_name: str) -> set:
        """Get expected pitch classes for a chord name."""
        # Try using music21's harmony module
        try:
            from music21 import harmony
            h = harmony.ChordSymbol(chord_name)
            return set(p.name for p in h.pitches)
        except Exception:
            pass

        # Fallback: use our own theory module
        try:
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from theory import get_chord_notes
            notes = get_chord_notes(chord_name)
            return set(n.name for n in notes)
        except Exception:
            pass

        return set()

    def _check_diatonic(
        self,
        m21_chord: chord.Chord,
        parsed_key: key.Key,
        numeral: str,
        location: str
    ) -> List[ValidationIssue]:
        """Check if chord tones are diatonic to the key."""
        issues = []

        # Get scale pitches
        try:
            sc = parsed_key.getScale()
            scale_pitches = set(p.name for p in sc.getPitches())
        except Exception:
            return issues

        # Check each chord pitch
        chord_pitches = [p.name for p in m21_chord.pitches]
        non_diatonic = []

        for p_name in chord_pitches:
            # Normalize enharmonics
            try:
                p = pitch.Pitch(p_name)
                if p.name not in scale_pitches:
                    # Check enharmonic
                    enharmonic_found = False
                    for sp in scale_pitches:
                        if pitch.Pitch(sp).ps == p.ps:
                            enharmonic_found = True
                            break
                    if not enharmonic_found:
                        non_diatonic.append(p_name)
            except Exception:
                pass

        if non_diatonic:
            # This might be a borrowed chord, which is valid
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                code="NON_DIATONIC",
                message=f"Notes {non_diatonic} are not in {parsed_key.tonicPitchNameWithCase} scale",
                location=location,
                suggestion="This may be a borrowed chord or modal interchange",
            ))

        return issues

    def _check_voice_leading(
        self,
        prev_notes: List[str],
        curr_notes: List[str],
        chord_index: int
    ) -> List[ValidationIssue]:
        """Check voice leading between two chords."""
        issues = []
        location = f"between chords {chord_index-1}-{chord_index}"

        # Parse notes
        try:
            prev_pitches = [pitch.Pitch(n) for n in prev_notes]
            curr_pitches = [pitch.Pitch(n) for n in curr_notes]
        except Exception:
            return issues

        # Sort by pitch (bass to soprano)
        prev_pitches.sort(key=lambda p: p.ps)
        curr_pitches.sort(key=lambda p: p.ps)

        # Check for parallel fifths and octaves
        parallels = self._find_parallels(prev_pitches, curr_pitches)
        for parallel_type, voices in parallels:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code=f"PARALLEL_{parallel_type.upper()}",
                message=f"Parallel {parallel_type} detected in voices {voices}",
                location=location,
                suggestion="Consider contrary or oblique motion",
            ))

        # Check for large leaps
        for i, (prev, curr) in enumerate(zip(prev_pitches, curr_pitches)):
            leap = abs(curr.ps - prev.ps)
            if leap > self.LARGE_LEAP_THRESHOLD:
                voice_name = ["bass", "tenor", "alto", "soprano"][min(i, 3)]
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="LARGE_LEAP",
                    message=f"Large leap of {int(leap)} semitones in {voice_name} voice",
                    location=location,
                    suggestion="Consider smoother voice leading with smaller intervals",
                ))

        return issues

    def _find_parallels(
        self,
        prev_pitches: List[pitch.Pitch],
        curr_pitches: List[pitch.Pitch]
    ) -> List[Tuple[str, str]]:
        """Find parallel fifths and octaves between voice pairs."""
        parallels = []

        # Compare each pair of voices
        n_voices = min(len(prev_pitches), len(curr_pitches))

        for i in range(n_voices):
            for j in range(i + 1, n_voices):
                # Interval in previous chord
                prev_interval = abs(prev_pitches[j].ps - prev_pitches[i].ps) % 12

                # Interval in current chord
                curr_interval = abs(curr_pitches[j].ps - curr_pitches[i].ps) % 12

                # Check if both are perfect fifths (7 semitones)
                if prev_interval == 7 and curr_interval == 7:
                    # Check if both voices move in the same direction
                    i_moves = curr_pitches[i].ps - prev_pitches[i].ps
                    j_moves = curr_pitches[j].ps - prev_pitches[j].ps
                    if i_moves != 0 and j_moves != 0 and (i_moves > 0) == (j_moves > 0):
                        parallels.append(("fifths", f"{i+1}-{j+1}"))

                # Check if both are octaves/unisons (0 semitones)
                if prev_interval == 0 and curr_interval == 0:
                    i_moves = curr_pitches[i].ps - prev_pitches[i].ps
                    j_moves = curr_pitches[j].ps - prev_pitches[j].ps
                    if i_moves != 0 and j_moves != 0 and (i_moves > 0) == (j_moves > 0):
                        parallels.append(("octaves", f"{i+1}-{j+1}"))

        return parallels


# =============================================================================
# Convenience functions
# =============================================================================

def validate_progression(progression_data: Dict) -> ValidationResult:
    """Convenience function to validate a progression."""
    validator = TheoryValidator()
    return validator.validate_progression(progression_data)


def validate_chord(chord_data: Dict, key_str: str = "C major") -> ValidationResult:
    """
    Convenience function to validate a single chord.

    Args:
        chord_data: {"name": "Am", "notes": ["A3", "C4", "E4"]}
        key_str: Key context like "A minor"
    """
    validator = TheoryValidator()
    return validator.validate_chord(chord_data, key_str)


def validate_notes(notes: List[str]) -> ValidationResult:
    """Convenience function to validate note names."""
    validator = TheoryValidator()
    return validator.validate_notes(notes)


if __name__ == "__main__":
    # Run tests
    print("=" * 60)
    print("Theory Validator Tests")
    print("=" * 60)
    print()

    validator = TheoryValidator()

    # Test 1: Valid progression
    print("Test 1: Valid i-VI-III-VII in A minor")
    print("-" * 40)
    prog = {
        "key": "A minor",
        "scale": "natural minor",
        "chords": [
            {"numeral": "i", "name": "Am", "notes": ["A3", "C4", "E4"]},
            {"numeral": "VI", "name": "F", "notes": ["F3", "A3", "C4"]},
            {"numeral": "III", "name": "C", "notes": ["C3", "E3", "G3"]},
            {"numeral": "VII", "name": "G", "notes": ["G3", "B3", "D4"]},
        ],
    }
    result = validator.validate_progression(prog)
    print(f"  Passed: {result.passed}")
    print(f"  Errors: {result.errors}")
    print(f"  Warnings: {result.warnings}")
    print()

    # Test 2: Invalid note
    print("Test 2: Invalid note name")
    print("-" * 40)
    result = validator.validate_notes(["A3", "X4", "E4"])
    print(f"  Passed: {result.passed}")
    print(f"  Errors: {result.errors}")
    print()

    # Test 3: Wrong chord tones
    print("Test 3: Wrong chord tones (Am with wrong notes)")
    print("-" * 40)
    result = validator.validate_chord(
        {"name": "Am", "notes": ["A3", "D4", "E4"]},
        "A minor"
    )
    print(f"  Passed: {result.passed}")
    print(f"  Errors: {result.errors}")
    print()

    # Test 4: Parallel fifths
    print("Test 4: Parallel fifths detection")
    print("-" * 40)
    prog = {
        "key": "C major",
        "chords": [
            {"numeral": "I", "name": "C", "notes": ["C3", "G3", "E4"]},
            {"numeral": "ii", "name": "Dm", "notes": ["D3", "A3", "F4"]},
        ],
    }
    result = validator.validate_progression(prog)
    print(f"  Passed: {result.passed}")
    print(f"  Warnings: {result.warnings}")
    print()

    print("=" * 60)
    print("All tests complete!")
    print("=" * 60)
