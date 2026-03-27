#!/usr/bin/env python3
"""
API Test Script — Phase 1 Verification

Tests all API endpoints in local mode (no API key required).

Run with:
    python test_api.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from api.main import app
from fastapi.testclient import TestClient


def main():
    client = TestClient(app, raise_server_exceptions=False)

    print()
    print("=" * 70)
    print("  MUSIC CO-PILOT API — Phase 1 Test")
    print("=" * 70)
    print()

    all_passed = True

    # Test 1: Health
    print("1. Health Check")
    r = client.get('/api/health')
    if r.status_code == 200:
        print("   ✓ API is healthy")
    else:
        print(f"   ✗ Health check failed: {r.status_code}")
        all_passed = False
    print()

    # Test 2: Create Session
    print("2. Session Management")
    r = client.post('/api/session')
    if r.status_code == 200:
        session_id = r.json()['session_id']
        print(f"   ✓ Created session: {session_id[:8]}...")
    else:
        print(f"   ✗ Session creation failed")
        all_passed = False
        return
    print()

    # Test 3: Generate Chord Progression
    print("3. Generate Chord Progression")
    print("   Request: 'give me something melancholic and lo-fi'")
    r = client.post('/api/generate', json={
        'prompt': 'give me something melancholic and lo-fi',
        'session_id': session_id,
        'use_api': False,
    })
    if r.status_code == 200:
        data = r.json()
        print(f"   ✓ Intent detected: {data['intent']} ({data['confidence']:.0%})")
        if data.get('progressions'):
            prog = data['progressions'][0]
            chords = [c['name'] for c in prog['chords']]
            print(f"   ✓ Progression: {prog['name']}")
            print(f"   ✓ Chords: {' → '.join(chords)}")
        if data.get('validation', {}).get('passed'):
            print("   ✓ Theory validation passed")
        if data.get('production_steps'):
            print(f"   ✓ Production steps generated ({len(data['production_steps'])} chars)")
        if data.get('teaching_note'):
            print(f"   ✓ Teaching note generated ({len(data['teaching_note'])} chars)")
    else:
        print(f"   ✗ Generation failed: {r.status_code}")
        all_passed = False
    print()

    # Test 4: Generate Drum Pattern
    print("4. Generate Drum Pattern")
    print("   Request: 'I need a trap beat'")
    r = client.post('/api/generate', json={
        'prompt': 'I need a trap beat',
        'session_id': session_id,
        'use_api': False,
    })
    if r.status_code == 200:
        data = r.json()
        print(f"   ✓ Intent detected: {data['intent']}")
        if data.get('drum_patterns'):
            pattern = data['drum_patterns'][0]
            print(f"   ✓ Pattern: {pattern['name']}")
            print(f"   ✓ Tempo: {pattern['tempo_range'][0]}-{pattern['tempo_range'][1]} BPM")
            grid = pattern.get('grid', {})
            print(f"   ✓ Sounds: {', '.join(grid.keys())}")
    else:
        print(f"   ✗ Generation failed: {r.status_code}")
        all_passed = False
    print()

    # Test 5: Feedback
    print("5. Feedback System")
    r = client.post('/api/feedback', json={
        'session_id': session_id,
        'entry_index': -1,
        'feedback': 'thumbs_up',
    })
    if r.status_code == 200:
        print("   ✓ Feedback recorded")
    else:
        print(f"   ✗ Feedback failed: {r.status_code}")
        all_passed = False
    print()

    # Test 6: History
    print("6. Session History")
    r = client.get(f'/api/session/{session_id}/history')
    if r.status_code == 200:
        history = r.json()
        print(f"   ✓ History entries: {len(history['history'])}")
        for h in history['history']:
            feedback = h.get('feedback') or 'none'
            print(f"     - {h['intent_type']}: '{h['request'][:30]}...' [{feedback}]")
    else:
        print(f"   ✗ History retrieval failed: {r.status_code}")
        all_passed = False
    print()

    # Summary
    print("=" * 70)
    if all_passed:
        print("  ✓ ALL TESTS PASSED")
        print()
        print("  Phase 1 Complete:")
        print("    • Production Agent: Generates Ableton step-by-step instructions")
        print("    • Teaching Agent: Explains why progressions work")
        print("    • Session Memory: Persists history and feedback")
        print("    • FastAPI Backend: REST endpoints for frontend")
        print()
        print("  To start the server:")
        print("    uvicorn api.main:app --reload --port 8000")
        print()
        print("  API Docs:")
        print("    http://localhost:8000/docs")
    else:
        print("  ✗ SOME TESTS FAILED")
    print("=" * 70)
    print()

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
