"""
Integration tests for POST /api/send-to-ableton and /api/health ableton_connected.

Patches AbletonMCPClient methods directly to avoid real socket connections.
"""

import json
from unittest.mock import patch, MagicMock

import pytest


@pytest.fixture
def sample_ableton_request():
    return {
        "progression": {
            "name": "Test",
            "chords": [
                {"name": "Am", "numeral": "i", "note_names": ["A3", "C4", "E4"]},
                {"name": "F", "numeral": "VI", "note_names": ["F3", "A3", "C4"]},
            ],
        },
        "bpm": 85,
    }


# =============================================================================
# /api/send-to-ableton
# =============================================================================

def test_send_to_ableton_success(client, sample_ableton_request):
    """Successful send returns success with chord count."""
    mock_result = {"success": True, "message": "Created 2 chords (6 notes) on track 4"}

    with patch("api.main.AbletonMCPClient") as MockClient:
        MockClient.return_value.send_progression_to_ableton.return_value = mock_result
        r = client.post("/api/send-to-ableton", json=sample_ableton_request)

    assert r.status_code == 200
    d = r.json()
    assert d["success"] is True
    assert "2 chords" in d["message"]


def test_send_to_ableton_connection_refused(client, sample_ableton_request):
    """When Ableton isn't running, returns graceful failure."""
    mock_result = {"success": False, "message": "Ableton not connected"}

    with patch("api.main.AbletonMCPClient") as MockClient:
        MockClient.return_value.send_progression_to_ableton.return_value = mock_result
        r = client.post("/api/send-to-ableton", json=sample_ableton_request)

    assert r.status_code == 200
    d = r.json()
    assert d["success"] is False
    assert "not connected" in d["message"]


def test_send_to_ableton_empty_chords(client):
    """Empty chords returns failure."""
    mock_result = {"success": False, "message": "No chords in progression data"}

    with patch("api.main.AbletonMCPClient") as MockClient:
        MockClient.return_value.send_progression_to_ableton.return_value = mock_result
        r = client.post("/api/send-to-ableton", json={
            "progression": {"chords": []},
            "bpm": 120,
        })

    assert r.status_code == 200
    d = r.json()
    assert d["success"] is False
    assert "No chords" in d["message"]


def test_send_to_ableton_server_error(client, sample_ableton_request):
    """Server error mid-sequence returns failure."""
    mock_result = {"success": False, "message": "Failed to create track: Ableton: Track creation failed"}

    with patch("api.main.AbletonMCPClient") as MockClient:
        MockClient.return_value.send_progression_to_ableton.return_value = mock_result
        r = client.post("/api/send-to-ableton", json=sample_ableton_request)

    assert r.status_code == 200
    d = r.json()
    assert d["success"] is False
    assert "create track" in d["message"]


def test_send_to_ableton_calls_with_correct_args(client, sample_ableton_request):
    """Verify the endpoint passes progression and bpm to the client."""
    with patch("api.main.AbletonMCPClient") as MockClient:
        mock_instance = MockClient.return_value
        mock_instance.send_progression_to_ableton.return_value = {"success": True, "message": "OK"}
        client.post("/api/send-to-ableton", json=sample_ableton_request)

    mock_instance.send_progression_to_ableton.assert_called_once()
    call_args = mock_instance.send_progression_to_ableton.call_args
    assert call_args[0][0]["chords"] == sample_ableton_request["progression"]["chords"]
    assert call_args[1]["bpm"] == 85 or call_args[0][1] == 85


# =============================================================================
# /api/health includes ableton_connected
# =============================================================================

def test_health_includes_ableton_connected_false(client):
    """Health check includes ableton_connected: false when not connected."""
    with patch("api.main.AbletonMCPClient") as MockClient:
        MockClient.return_value.is_connected.return_value = False
        r = client.get("/api/health")

    assert r.status_code == 200
    d = r.json()
    assert "ableton_connected" in d
    assert d["ableton_connected"] is False


def test_health_includes_ableton_connected_true(client):
    """Health check includes ableton_connected: true when connected."""
    with patch("api.main.AbletonMCPClient") as MockClient:
        MockClient.return_value.is_connected.return_value = True
        r = client.get("/api/health")

    assert r.status_code == 200
    d = r.json()
    assert d["ableton_connected"] is True
