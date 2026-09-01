"""Unit tests for the arrangement note builders (bass + drums → MIDI notes)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.mcp_client import AbletonMCPClient, DRUM_PITCH_MAP


def _client():
    return AbletonMCPClient()


CHORDS = [
    {"name": "Am", "root": "A", "note_names": ["A3", "C4", "E4"]},
    {"name": "Dm", "root": "D", "note_names": ["D4", "F4", "A4"]},
]


def test_bass_notes_from_guidance_lofi_holds_roots():
    prog = {"genres": ["lo-fi"], "chords": CHORDS}
    bass = {"root_notes": ["A2", "D2"]}
    notes = _client()._build_bass_notes(CHORDS, bass, prog)
    assert len(notes) == 2  # one held root per bar
    assert notes[0] == {"pitch": 45, "start_time": 0.0, "duration": 4.0, "velocity": 100}
    assert notes[1]["pitch"] == 38 and notes[1]["start_time"] == 4.0  # D2 (C4=60 convention)


def test_bass_notes_house_offbeats():
    prog = {"genres": ["house"], "chords": CHORDS}
    notes = _client()._build_bass_notes(CHORDS, {"root_notes": ["A2", "D2"]}, prog)
    assert len(notes) == 8  # four offbeat eighths per bar
    assert notes[0]["start_time"] == 0.5


def test_bass_notes_derive_roots_without_guidance():
    prog = {"genres": [], "chords": CHORDS}
    notes = _client()._build_bass_notes(CHORDS, None, prog)
    assert notes and notes[0]["pitch"] == 45  # A2 derived from chord root


def test_drum_notes_loop_across_bars():
    grid = {"kick": [0, 8], "closed_hat": [0, 4, 8, 12]}
    notes = _client()._build_drum_notes(grid, bars=2)
    kicks = [n for n in notes if n["pitch"] == DRUM_PITCH_MAP["kick"]]
    hats = [n for n in notes if n["pitch"] == DRUM_PITCH_MAP["closed_hat"]]
    assert len(kicks) == 4 and len(hats) == 8
    assert kicks[0]["start_time"] == 0.0 and kicks[1]["start_time"] == 2.0
    assert kicks[2]["start_time"] == 4.0  # second bar
    assert hats[0]["velocity"] < kicks[0]["velocity"]  # hats softer


def test_drum_notes_empty_grid():
    assert _client()._build_drum_notes({}, bars=4) == []
