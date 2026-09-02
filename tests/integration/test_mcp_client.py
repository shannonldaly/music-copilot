"""
Integration tests for the Ableton MCP Client.

Mocks the TCP socket so tests run without Ableton.
Verifies: command sequence, params shape, track index propagation,
graceful failure on connection refused and server errors.
"""

import json
import socket
from unittest.mock import patch, MagicMock

import pytest

from services.mcp_client import AbletonMCPClient, _note_name_to_midi


# =============================================================================
# Fixtures
# =============================================================================

def _make_mock_socket(responses: list):
    """
    Create a mock socket that returns pre-defined responses in order.

    Each item in `responses` is a dict that will be JSON-encoded as the
    server response. Items are consumed in order, one per send_command call.
    """
    call_index = {"i": 0}
    sent_commands = []

    def mock_recv(bufsize):
        i = call_index["i"]
        call_index["i"] += 1
        if i < len(responses):
            return json.dumps(responses[i]).encode("utf-8")
        return json.dumps({"status": "error", "message": "No more mock responses"}).encode("utf-8")

    def mock_sendall(data):
        sent_commands.append(json.loads(data.decode("utf-8")))

    mock_sock = MagicMock()
    mock_sock.recv = mock_recv
    mock_sock.sendall = mock_sendall
    mock_sock.connect = MagicMock()
    mock_sock.settimeout = MagicMock()
    mock_sock.close = MagicMock()

    return mock_sock, sent_commands


@pytest.fixture
def sample_progression():
    """Two-chord progression: Am → F in A minor."""
    return {
        "name": "Test Progression",
        "chords": [
            {"name": "Am", "numeral": "i", "note_names": ["A3", "C4", "E4"]},
            {"name": "F", "numeral": "VI", "note_names": ["F3", "A3", "C4"]},
        ],
    }


# =============================================================================
# Note conversion
# =============================================================================

def test_note_name_to_midi_middle_c():
    assert _note_name_to_midi("C4") == 60


def test_note_name_to_midi_sharp():
    assert _note_name_to_midi("F#3") == 54


def test_note_name_to_midi_flat():
    assert _note_name_to_midi("Bb4") == 70


def test_note_name_to_midi_invalid():
    assert _note_name_to_midi("X4") is None
    assert _note_name_to_midi("") is None
    assert _note_name_to_midi("C") is None


# =============================================================================
# Command sequence verification
# =============================================================================

def test_send_progression_command_sequence(sample_progression):
    """Verify the exact command sequence: set_tempo → create_track → name track →
    resolve instrument → load instrument → create_clip → name clip → add_notes × 2."""
    responses = [
        {"status": "success", "result": {"tempo": 80.0}},
        {"status": "success", "result": {"index": 3, "name": "4-MIDI"}},
        {"status": "success", "result": {"name": "Rubato Chords"}},
        {"status": "success", "result": {"items": [
            {"name": "Ac Piano Upright.adg", "is_loadable": True, "uri": "query:Sounds#Piano%20&%20Keys:1"},
        ]}},
        {"status": "success", "result": {"loaded": True, "item_name": "Ac Piano Upright.adg"}},
        {"status": "success", "result": {"name": "", "length": 8.0}},
        {"status": "success", "result": {"name": "Am F"}},
        {"status": "success", "result": {"note_count": 3}},
        {"status": "success", "result": {"note_count": 3}},
        {"status": "success", "result": {"placed_at": 0.0}},
    ]
    mock_sock, sent_commands = _make_mock_socket(responses)

    with patch("socket.socket", return_value=mock_sock):
        client = AbletonMCPClient()
        result = client.send_progression_to_ableton(sample_progression, bpm=80)

    assert result["success"] is True
    assert "2 chords" in result["message"]
    assert "6 notes" in result["message"]

    assert len(sent_commands) == 10
    # Session clip mirrored onto the arrangement timeline
    assert sent_commands[9] == {
        "type": "clip_to_arrangement",
        "params": {"track_index": 3, "clip_index": 0, "time": 0.0},
    }

    assert sent_commands[0] == {"type": "set_tempo", "params": {"tempo": 80}}
    # No key on the fixture → no set_song_key command
    assert all(c["type"] != "set_song_key" for c in sent_commands)

    assert sent_commands[1]["type"] == "create_midi_track"

    assert sent_commands[2] == {
        "type": "set_track_name",
        "params": {"track_index": 3, "name": "Rubato Chords"},
    }

    # Instrument resolution: piano category first, then load the resolved preset
    assert sent_commands[3] == {
        "type": "get_browser_items_at_path",
        "params": {"path": "sounds/Piano & Keys"},
    }
    assert sent_commands[4] == {
        "type": "load_browser_item",
        "params": {"item_uri": "query:Sounds#Piano%20&%20Keys:1", "track_index": 3},
    }

    assert sent_commands[5] == {
        "type": "create_clip",
        "params": {"track_index": 3, "clip_index": 0, "length": 8},
    }

    # Clip is named with the actual chord sequence
    assert sent_commands[6] == {
        "type": "set_clip_name",
        "params": {"track_index": 3, "clip_index": 0, "name": "Am F"},
    }

    # add_notes — chord 1 (Am: A3=57, C4=60, E4=64)
    cmd = sent_commands[7]
    assert cmd["type"] == "add_notes_to_clip"
    assert cmd["params"]["track_index"] == 3
    assert cmd["params"]["clip_index"] == 0
    notes_1 = cmd["params"]["notes"]
    assert len(notes_1) == 3
    assert notes_1[0] == {"pitch": 57, "start_time": 0.0, "duration": 4.0, "velocity": 100}
    assert notes_1[1] == {"pitch": 60, "start_time": 0.0, "duration": 4.0, "velocity": 100}
    assert notes_1[2] == {"pitch": 64, "start_time": 0.0, "duration": 4.0, "velocity": 100}

    # add_notes — chord 2 (F: F3=53, A3=57, C4=60), start_time=4.0
    notes_2 = sent_commands[8]["params"]["notes"]
    assert len(notes_2) == 3
    assert notes_2[0] == {"pitch": 53, "start_time": 4.0, "duration": 4.0, "velocity": 100}


def test_send_progression_sets_song_key():
    """A progression with a key sets Live's Key & Scale and names the clip with the key."""
    progression = {
        "name": "Minor Plagal",
        "key": "A minor",
        "chords": [
            {"name": "Am", "numeral": "i", "note_names": ["A3", "C4", "E4"]},
        ],
    }
    responses = [
        {"status": "success", "result": {"tempo": 80.0}},
        {"status": "success", "result": {"root_note": 9, "scale_name": "Minor"}},
        {"status": "success", "result": {"index": 0, "name": "1-MIDI"}},
        {"status": "success", "result": {"name": "Rubato Chords"}},
        {"status": "success", "result": {"items": [
            {"name": "Ac Piano Upright.adg", "is_loadable": True, "uri": "uri:piano"},
        ]}},
        {"status": "success", "result": {"loaded": True}},
        {"status": "success", "result": {"length": 4.0}},
        {"status": "success", "result": {"name": "Am · A minor"}},
        {"status": "success", "result": {"note_count": 3}},
        {"status": "success", "result": {"placed_at": 0.0}},
    ]
    mock_sock, sent_commands = _make_mock_socket(responses)

    with patch("socket.socket", return_value=mock_sock):
        client = AbletonMCPClient()
        result = client.send_progression_to_ableton(progression, bpm=80)

    assert result["success"] is True
    assert sent_commands[1] == {
        "type": "set_song_key",
        "params": {"root_note": 9, "scale_name": "Minor"},
    }
    clip_names = [c for c in sent_commands if c["type"] == "set_clip_name"]
    assert clip_names[0]["params"]["name"] == "Am · A minor"


def test_track_index_propagated_from_server(sample_progression):
    """Track index from create_midi_track response must be used in all subsequent commands."""
    responses = [
        {"status": "success", "result": {"tempo": 85.0}},
        {"status": "success", "result": {"index": 7, "name": "8-MIDI"}},  # Track 7
        {"status": "success", "result": {"name": "Rubato Chords"}},
        {"status": "success", "result": {"items": [
            {"name": "Ac Piano Upright.adg", "is_loadable": True, "uri": "uri:piano"},
        ]}},
        {"status": "success", "result": {"loaded": True}},
        {"status": "success", "result": {"name": "", "length": 8.0}},
        {"status": "success", "result": {"name": "Am F"}},
        {"status": "success", "result": {"note_count": 3}},
        {"status": "success", "result": {"note_count": 3}},
    ]
    mock_sock, sent_commands = _make_mock_socket(responses)

    with patch("socket.socket", return_value=mock_sock):
        client = AbletonMCPClient()
        client.send_progression_to_ableton(sample_progression, bpm=85)

    by_type = {c["type"]: c for c in sent_commands}
    assert by_type["set_track_name"]["params"]["track_index"] == 7
    assert by_type["load_browser_item"]["params"]["track_index"] == 7
    assert by_type["create_clip"]["params"]["track_index"] == 7
    add_notes = [c for c in sent_commands if c["type"] == "add_notes_to_clip"]
    assert all(c["params"]["track_index"] == 7 for c in add_notes)


# =============================================================================
# Graceful failure
# =============================================================================

def test_connection_refused_returns_failure():
    """When Ableton isn't running, is_connected returns False and send returns failure."""
    mock_sock = MagicMock()
    mock_sock.connect = MagicMock(side_effect=ConnectionRefusedError())

    with patch("socket.socket", return_value=mock_sock):
        client = AbletonMCPClient()

        assert client.is_connected() is False

        result = client.send_progression_to_ableton(
            {"chords": [{"name": "C", "note_names": ["C3", "E3", "G3"]}]},
            bpm=120,
        )
        assert result["success"] is False
        assert "not connected" in result["message"]


def test_server_error_stops_sequence(sample_progression):
    """If any command returns error, the sequence stops and returns failure."""
    responses = [
        {"status": "success", "result": {"tempo": 80.0}},
        {"status": "error", "result": {}, "message": "Cannot create track"},
    ]
    mock_sock, sent_commands = _make_mock_socket(responses)

    with patch("socket.socket", return_value=mock_sock):
        client = AbletonMCPClient()
        result = client.send_progression_to_ableton(sample_progression, bpm=80)

    assert result["success"] is False
    assert "create track" in result["message"]
    # Should have stopped after 2 commands (tempo + failed track creation)
    assert len(sent_commands) == 2


def test_timeout_returns_failure():
    """Socket timeout returns a clean failure message."""
    mock_sock = MagicMock()
    mock_sock.connect = MagicMock(side_effect=socket.timeout("timed out"))

    with patch("socket.socket", return_value=mock_sock):
        client = AbletonMCPClient()
        result = client.send_progression_to_ableton(
            {"chords": [{"name": "C", "note_names": ["C3"]}]},
            bpm=120,
        )
        assert result["success"] is False
        assert "timed out" in result["message"]


def test_empty_chords_returns_failure():
    """Progression with no chords returns failure without connecting."""
    client = AbletonMCPClient()
    result = client.send_progression_to_ableton({"chords": []}, bpm=120)
    assert result["success"] is False
    assert "No chords" in result["message"]


# =============================================================================
# is_connected
# =============================================================================

def test_is_connected_true():
    """is_connected returns True when server responds successfully."""
    responses = [{"status": "success", "result": {"tempo": 120.0}}]
    mock_sock, _ = _make_mock_socket(responses)

    with patch("socket.socket", return_value=mock_sock):
        client = AbletonMCPClient()
        assert client.is_connected() is True


def test_is_connected_false_on_error():
    """is_connected returns False when server returns error."""
    responses = [{"status": "error", "message": "Not ready"}]
    mock_sock, _ = _make_mock_socket(responses)

    with patch("socket.socket", return_value=mock_sock):
        client = AbletonMCPClient()
        assert client.is_connected() is False
