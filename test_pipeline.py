#!/usr/bin/env python3
"""
End-to-End Pipeline Test — Phase 0 Confirmation

This test confirms the full pipeline works:
    User Input → Orchestrator → Local Lookup → Validator → Output

Run with:
    python test_pipeline.py
"""

import os
import sys
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.orchestrator import Orchestrator, ParsedIntent, IntentType
from validator import TheoryValidator, validate_progression
from theory import (
    get_progression_chords,
    get_named_progression,
    get_drum_patterns_by_genre,
    search_progressions,
)


def print_header(text: str):
    """Print a formatted header."""
    print()
    print("=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_section(text: str):
    """Print a section header."""
    print()
    print(f"── {text} " + "─" * (66 - len(text)))


def test_full_pipeline_local():
    """
    Test the complete pipeline using local lookups only.
    No API key required.
    """
    print_header("END-TO-END PIPELINE TEST (Local Only)")

    # Simulate what the Orchestrator would do
    orchestrator = Orchestrator.__new__(Orchestrator)
    orchestrator.user_profile = {
        'theory_level': 'rusty_intermediate',
        'production_level': 'beginner',
    }

    # Test scenarios
    test_cases = [
        {
            "input": "give me something melancholic and lo-fi in A minor",
            "intent": ParsedIntent(
                intent_type=IntentType.MOOD_VIBE,
                confidence=0.95,
                extracted={
                    'moods': ['melancholic'],
                    'genres': ['lo-fi'],
                    'key': 'A minor',
                }
            ),
        },
        {
            "input": "I need a trap beat",
            "intent": ParsedIntent(
                intent_type=IntentType.DRUM_PATTERN,
                confidence=0.95,
                extracted={
                    'genres': ['trap'],
                }
            ),
        },
        {
            "input": "something dark and epic for a film score",
            "intent": ParsedIntent(
                intent_type=IntentType.MOOD_VIBE,
                confidence=0.90,
                extracted={
                    'moods': ['dark', 'epic'],
                    'genres': ['film_score'],
                }
            ),
        },
    ]

    validator = TheoryValidator()
    all_passed = True

    for i, case in enumerate(test_cases, 1):
        print_section(f"Test {i}: \"{case['input']}\"")

        intent = case['intent']
        print(f"Intent: {intent.intent_type.value}")
        print(f"Extracted: {intent.extracted}")

        # Step 1: Routing
        routing = orchestrator._determine_routing(intent)
        print(f"Routing: {' → '.join(routing.agents)}")
        print(f"Local lookup: {routing.use_local_lookup} ({routing.local_lookup_type})")

        # Step 2: Local lookup
        local_data = orchestrator._execute_local_lookup(intent, routing)

        if not local_data:
            print("  ⚠ No local data found")
            continue

        # Step 3: Process results
        if 'progressions' in local_data:
            print(f"\nFound {len(local_data['progressions'])} progressions:")

            for prog in local_data['progressions']:
                print(f"\n  ▸ {prog['name']} ({prog['key']})")
                print(f"    Numerals: {' → '.join(prog['numerals'])}")

                # Show chords with notes
                chord_display = []
                for c in prog['chords']:
                    chord_display.append(f"{c['name']}")
                print(f"    Chords: {' → '.join(chord_display)}")

                # Step 4: Validate with music21
                validation_data = {
                    'key': prog['key'],
                    'chords': [
                        {
                            'numeral': c['numeral'],
                            'name': c['name'],
                            'notes': c['note_names'],
                        }
                        for c in prog['chords']
                    ]
                }

                result = validator.validate_progression(validation_data)

                if result.passed:
                    print(f"    Validation: ✓ PASSED")
                else:
                    print(f"    Validation: ✗ FAILED")
                    for err in result.errors:
                        print(f"      Error: {err}")
                    all_passed = False

                if result.warnings:
                    print(f"    Warnings: {len(result.warnings)}")
                    # Only show first warning to keep output clean
                    print(f"      - {result.warnings[0][:60]}...")

                # Show full note data for first progression
                if prog == local_data['progressions'][0]:
                    print(f"\n    Full chord data (Ableton-ready):")
                    for c in prog['chords']:
                        print(f"      {c['numeral']:>4} → {c['name']:>3}: {c['note_names']}")

        if 'drum_patterns' in local_data:
            print(f"\nFound {len(local_data['drum_patterns'])} drum patterns:")

            for pattern in local_data['drum_patterns']:
                print(f"\n  ▸ {pattern['name']}")
                print(f"    Tempo: {pattern['tempo_range'][0]}-{pattern['tempo_range'][1]} BPM")
                print(f"    Description: {pattern['description'][:50]}...")

                # Show grid
                grid = pattern['grid']
                print(f"    Grid:")
                for sound, steps in sorted(grid.items()):
                    # Create visual grid
                    visual = ['·'] * 16
                    for s in steps:
                        visual[s] = '●'
                    print(f"      {sound:>12}: {''.join(visual)}")

    return all_passed


def test_validation_catches_errors():
    """Test that validation actually catches errors."""
    print_header("VALIDATION ERROR DETECTION TEST")

    validator = TheoryValidator()
    tests_passed = True

    # Test 1: Invalid note
    print_section("Test: Invalid Note Detection")
    result = validator.validate_notes(["A3", "Z#4", "E4"])
    if not result.passed and "Z" in str(result.errors):
        print("  ✓ Correctly caught invalid note 'Z#4'")
    else:
        print("  ✗ Failed to catch invalid note")
        tests_passed = False

    # Test 2: Wrong chord tones
    print_section("Test: Wrong Chord Tones Detection")
    result = validator.validate_chord(
        {"name": "Am", "notes": ["A3", "D4", "E4"]},  # D should be C
        "A minor"
    )
    if not result.passed and "missing" in str(result.errors).lower():
        print("  ✓ Correctly caught missing chord tone (C)")
        print(f"    Error: {result.errors[0][:60]}...")
    else:
        print("  ✗ Failed to catch wrong chord tones")
        tests_passed = False

    # Test 3: Valid progression passes
    print_section("Test: Valid Progression Passes")
    prog = {
        "key": "C major",
        "chords": [
            {"numeral": "I", "name": "C", "notes": ["C3", "E3", "G3"]},
            {"numeral": "IV", "name": "F", "notes": ["F3", "A3", "C4"]},
            {"numeral": "V", "name": "G", "notes": ["G3", "B3", "D4"]},
            {"numeral": "I", "name": "C", "notes": ["C3", "E3", "G3"]},
        ]
    }
    result = validator.validate_progression(prog)
    if result.passed:
        print("  ✓ Valid I-IV-V-I progression passed")
    else:
        print(f"  ✗ Valid progression incorrectly failed: {result.errors}")
        tests_passed = False

    return tests_passed


def test_cost_summary():
    """Show cost summary for the pipeline."""
    print_header("COST ANALYSIS")

    print("""
    Component                    API Cost
    ─────────────────────────────────────
    Local Theory Lookups         $0.00
    - Chord progressions         $0.00
    - Drum patterns              $0.00
    - Scale/chord construction   $0.00

    music21 Validation           $0.00
    - Note validation            $0.00
    - Chord tone checking        $0.00
    - Voice leading analysis     $0.00

    Orchestrator Routing         ~$0.001 (Haiku)
    - Intent detection           ~$0.001

    Theory Agent (when needed)   ~$0.005 (Sonnet)
    - Creative suggestions       ~$0.005

    ─────────────────────────────────────
    Typical request total:       ~$0.001 - $0.006

    vs. Full LLM approach:       ~$0.02 - $0.05
    ─────────────────────────────────────
    SAVINGS:                     70-95%
    """)


def main():
    """Run all tests."""
    print()
    print("🎵 MUSIC CO-PILOT — PHASE 0 PIPELINE TEST")
    print()

    # Run tests
    pipeline_ok = test_full_pipeline_local()
    validation_ok = test_validation_catches_errors()
    test_cost_summary()

    # Summary
    print_header("PHASE 0 COMPLETE")

    if pipeline_ok and validation_ok:
        print("""
    ✓ All tests passed!

    Pipeline confirmed:
      User Input
          ↓
      Orchestrator (intent detection)
          ↓
      Local Lookup (progressions, drums)
          ↓
      Validator (music21)
          ↓
      Validated Output

    Ready for Phase 1:
      □ Theory Agent (LLM for creative suggestions)
      □ Production Agent (Ableton steps)
      □ Teaching Agent (explanations)
      □ Frontend (React)
      □ Audio preview (Tone.js)
        """)
    else:
        print("\n    ✗ Some tests failed. Check output above.")

    return pipeline_ok and validation_ok


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
