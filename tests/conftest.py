"""
Shared test fixtures for the Music Co-Pilot test suite.

Key fixture: mock_anthropic strips the API key so no real API calls
are made in any test. Teaching Agent falls back to local templates.
"""

import os
import sys
from pathlib import Path

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from api.main import app


@pytest.fixture(autouse=True)
def mock_anthropic(monkeypatch):
    """Prevent real API calls in all tests by stripping the API key."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture
def session_id(client):
    """Create a session and return its ID."""
    r = client.post("/api/session")
    assert r.status_code == 200
    return r.json()["session_id"]


# --- Sample data fixtures ---

@pytest.fixture
def sample_mood_prompt():
    return "give me something melancholic and lo-fi"


@pytest.fixture
def sample_drum_prompt():
    return "give me a trap beat"


@pytest.fixture
def sample_se_prompt():
    return "how do I sidechain my bass to the kick"


@pytest.fixture
def sample_blend_prompt():
    return "Massive Attack meets Deadmau5"


@pytest.fixture
def sample_artist_prompt():
    return "something like Massive Attack"


@pytest.fixture
def sample_key_prompt():
    return "something dark in Bb minor"
