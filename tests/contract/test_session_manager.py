"""Contract tests for the Session Manager.

Verifies: create_session returns a Session, load_session returns
Optional[Session], add_to_history and record_feedback work.
"""

import tempfile
from pathlib import Path

from memory import SessionManager, UserProfile, ProjectContext


def _make_manager():
    """Create a SessionManager with a temp directory."""
    tmp = tempfile.mkdtemp()
    return SessionManager(storage_dir=Path(tmp))


def test_create_session_returns_session_with_id():
    mgr = _make_manager()
    session = mgr.create_session(
        user_profile=UserProfile(),
        project_context=ProjectContext(name="Test"),
    )
    assert session.session_id is not None
    assert len(session.session_id) > 0
    assert session.current_project.name == "Test"


def test_load_session_returns_none_for_missing():
    mgr = _make_manager()
    result = mgr.load_session("nonexistent-id")
    assert result is None


def test_load_session_roundtrips():
    mgr = _make_manager()
    session = mgr.create_session(
        user_profile=UserProfile(theory_level="advanced"),
        project_context=ProjectContext(name="Roundtrip"),
    )
    loaded = mgr.load_session(session.session_id)
    assert loaded is not None
    assert loaded.session_id == session.session_id
    assert loaded.user_profile.theory_level == "advanced"
    assert loaded.current_project.name == "Roundtrip"


def test_add_to_history_increments():
    mgr = _make_manager()
    session = mgr.create_session(
        user_profile=UserProfile(),
        project_context=ProjectContext(),
    )
    assert len(session.history) == 0
    mgr.add_to_history(session, request="test", intent_type="mood_vibe", output={})
    assert len(session.history) == 1


def test_record_feedback_returns_true():
    mgr = _make_manager()
    session = mgr.create_session(
        user_profile=UserProfile(),
        project_context=ProjectContext(),
    )
    mgr.add_to_history(session, request="test", intent_type="mood_vibe", output={})
    result = mgr.record_feedback(session, entry_index=-1, feedback="thumbs_up")
    assert result is True
    assert session.history[-1].feedback == "thumbs_up"


def test_record_feedback_returns_false_for_bad_index():
    mgr = _make_manager()
    session = mgr.create_session(
        user_profile=UserProfile(),
        project_context=ProjectContext(),
    )
    result = mgr.record_feedback(session, entry_index=0, feedback="thumbs_up")
    assert result is False


def test_list_sessions_returns_list():
    mgr = _make_manager()
    mgr.create_session(user_profile=UserProfile(), project_context=ProjectContext())
    mgr.create_session(user_profile=UserProfile(), project_context=ProjectContext())
    sessions = mgr.list_sessions()
    assert isinstance(sessions, list)
    assert len(sessions) == 2
