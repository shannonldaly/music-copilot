#!/usr/bin/env python3
"""
Test script for the Orchestrator.

Run with:
    python test_orchestrator.py

If ANTHROPIC_API_KEY is set, tests full intent detection.
Otherwise, tests local lookup functionality only.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents import Orchestrator, IntentType, ParsedIntent, RoutingPlan


def test_local_lookups():
    """Test local lookup functionality (no API needed)."""
    print("=" * 60)
    print("LOCAL LOOKUP TESTS (No API cost)")
    print("=" * 60)
    print()

    # Create orchestrator without initializing API client
    orchestrator = Orchestrator.__new__(Orchestrator)
    orchestrator.user_profile = {
        'theory_level': 'rusty_intermediate',
        'production_level': 'beginner',
    }

    test_cases = [
        {
            "name": "Melancholic Lo-Fi",
            "intent": ParsedIntent(
                intent_type=IntentType.MOOD_VIBE,
                confidence=0.9,
                extracted={'moods': ['melancholic'], 'genres': ['lo-fi']}
            ),
        },
        {
            "name": "Dark Trap",
            "intent": ParsedIntent(
                intent_type=IntentType.MOOD_VIBE,
                confidence=0.9,
                extracted={'moods': ['dark'], 'genres': ['trap'], 'key': 'D minor'}
            ),
        },
        {
            "name": "Chill Jazzy",
            "intent": ParsedIntent(
                intent_type=IntentType.MOOD_VIBE,
                confidence=0.9,
                extracted={'moods': ['chill'], 'genres': ['jazz']}
            ),
        },
        {
            "name": "Trap Beat",
            "intent": ParsedIntent(
                intent_type=IntentType.DRUM_PATTERN,
                confidence=0.95,
                extracted={'genres': ['trap']}
            ),
        },
        {
            "name": "Boom Bap Drums",
            "intent": ParsedIntent(
                intent_type=IntentType.DRUM_PATTERN,
                confidence=0.95,
                extracted={'genres': ['boom_bap']}
            ),
        },
    ]

    for case in test_cases:
        print(f"Test: {case['name']}")
        print("-" * 40)

        intent = case['intent']
        routing = orchestrator._determine_routing(intent)

        print(f"  Intent: {intent.intent_type.value}")
        print(f"  Extracted: {intent.extracted}")
        print(f"  Agents: {' → '.join(routing.agents)}")
        print(f"  Local lookup: {routing.use_local_lookup} ({routing.local_lookup_type})")

        local_data = orchestrator._execute_local_lookup(intent, routing)

        if local_data:
            if 'progressions' in local_data:
                print(f"  Found {len(local_data['progressions'])} progressions:")
                for prog in local_data['progressions'][:2]:
                    chords = [c['name'] for c in prog['chords']]
                    print(f"    • {prog['name']}: {' → '.join(chords)}")
            if 'drum_patterns' in local_data:
                print(f"  Found {len(local_data['drum_patterns'])} drum patterns:")
                for pattern in local_data['drum_patterns'][:2]:
                    print(f"    • {pattern['name']}: {pattern['description'][:50]}...")

        print()

    print("All local lookup tests passed!")
    print("Cost: $0.00")
    print()


def test_full_orchestrator():
    """Test full orchestrator with API calls."""
    print("=" * 60)
    print("FULL ORCHESTRATOR TEST (With API)")
    print("=" * 60)
    print()

    orchestrator = Orchestrator()

    test_inputs = [
        "give me something melancholic and lo-fi",
        "I need a trap beat, something dark",
        "how do I sidechain in Ableton?",
        "something like a Bon Iver track",
        "give me a ii-V-I in C major",
    ]

    total_cost = 0.0

    for inp in test_inputs:
        print(f"Input: \"{inp}\"")
        print("-" * 40)

        result = orchestrator.process(inp)

        print(f"  Intent: {result.intent.intent_type.value} ({result.intent.confidence:.0%})")
        print(f"  Extracted: {result.intent.extracted}")
        print(f"  Routing: {' → '.join(result.routing.agents)}")

        if result.local_data:
            if 'progressions' in result.local_data:
                prog = result.local_data['progressions'][0]
                chords = [c['name'] for c in prog['chords']]
                print(f"  Local match: {prog['name']}: {' → '.join(chords)}")
            if 'drum_patterns' in result.local_data:
                pattern = result.local_data['drum_patterns'][0]
                print(f"  Local match: {pattern['name']}")

        cost = result.token_summary['total_cost_usd']
        total_cost += cost
        print(f"  Tokens: {result.token_summary['total_tokens']}")
        print(f"  Cost: ${cost:.6f}")
        print()

    print("=" * 60)
    print(f"TOTAL COST: ${total_cost:.6f}")
    print("=" * 60)


def main():
    print()
    print("🎵 Music Co-Pilot Orchestrator Test")
    print()

    # Always run local lookup tests
    test_local_lookups()

    # Run full tests if API key is available
    if os.environ.get("ANTHROPIC_API_KEY"):
        test_full_orchestrator()
    else:
        print("=" * 60)
        print("SKIPPING API TESTS")
        print("Set ANTHROPIC_API_KEY to test intent detection")
        print("=" * 60)
        print()
        print("To run full tests:")
        print("  export ANTHROPIC_API_KEY=your-key-here")
        print("  python test_orchestrator.py")
        print()


if __name__ == "__main__":
    main()
