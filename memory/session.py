"""
Session Memory — JSON-based persistence for user sessions.

Stores:
- User profile (theory level, production level, preferences)
- Session history (requests, outputs, feedback)
- Current project context (key, BPM, genre)

v1: JSON files stored in /memory/sessions/
v2: SQLite/Postgres for better querying
"""

import json
import logging
import os
import sys
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.logging import log_agent_call

logger = logging.getLogger(__name__)


@dataclass
class UserProfile:
    """User's skill level and preferences."""
    theory_level: str = "rusty_intermediate"  # beginner, rusty_intermediate, intermediate, advanced
    production_level: str = "beginner"  # beginner, intermediate, advanced
    preferred_genres: List[str] = field(default_factory=lambda: ["lo-fi", "trap"])
    teaching_preference: str = "explain_why_first"  # explain_why_first, just_steps, deep_theory
    daw: str = "Ableton Live 12"

    # Adaptive fields (updated based on behavior)
    skips_explanations: bool = False  # True if user often skips teaching content
    asks_followups: bool = False  # True if user asks theory follow-ups


@dataclass
class ProjectContext:
    """Current project the user is working on."""
    key: Optional[str] = None  # e.g., "A minor"
    bpm: Optional[int] = None  # e.g., 85
    genre: Optional[str] = None  # e.g., "lo-fi"
    name: Optional[str] = None  # User's name for the project


@dataclass
class HistoryEntry:
    """A single request/response in session history."""
    timestamp: str
    request: str
    intent_type: str
    output: Dict[str, Any]
    feedback: Optional[str] = None  # "thumbs_up", "thumbs_down", "regenerate", "progression_swap", None
    feedback_label: Optional[str] = None  # e.g. Also Try label when feedback is progression_swap


@dataclass
class Session:
    """Complete session data."""
    session_id: str
    created_at: str
    updated_at: str
    user_profile: UserProfile
    current_project: ProjectContext
    history: List[HistoryEntry] = field(default_factory=list)
    session_mode: Optional[str] = None  # chords | drums | mixing | full

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "user_profile": asdict(self.user_profile),
            "current_project": asdict(self.current_project),
            "history": [asdict(h) for h in self.history],
            "session_mode": self.session_mode,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Session":
        """Create from dictionary."""
        hist = []
        for h in data.get("history", []):
            hd = dict(h)
            hd.setdefault("feedback_label", None)
            hist.append(HistoryEntry(**hd))
        return cls(
            session_id=data["session_id"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            user_profile=UserProfile(**data.get("user_profile", {})),
            current_project=ProjectContext(**data.get("current_project", {})),
            history=hist,
            session_mode=data.get("session_mode"),
        )


class SessionManager:
    """
    Manages session persistence.

    Usage:
        manager = SessionManager()

        # Create or load session
        session = manager.create_session()
        # or
        session = manager.load_session("session-uuid")

        # Add to history
        manager.add_to_history(session, request, intent_type, output)

        # Record feedback
        manager.record_feedback(session, -1, "thumbs_up")  # -1 = last entry

        # Save
        manager.save_session(session)
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        if storage_dir is None:
            storage_dir = Path(__file__).parent / "sessions"
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    @log_agent_call
    def create_session(
        self,
        user_profile: Optional[UserProfile] = None,
        project_context: Optional[ProjectContext] = None,
        session_mode: Optional[str] = None,
    ) -> Session:
        """Create a new session."""
        now = datetime.now().isoformat()
        session = Session(
            session_id=str(uuid.uuid4()),
            created_at=now,
            updated_at=now,
            user_profile=user_profile or UserProfile(),
            current_project=project_context or ProjectContext(),
            session_mode=session_mode,
        )
        self.save_session(session)
        return session

    def load_session(self, session_id: str) -> Optional[Session]:
        """Load a session by ID."""
        path = self.storage_dir / f"{session_id}.json"
        if not path.exists():
            return None

        with open(path, "r") as f:
            data = json.load(f)
        return Session.from_dict(data)

    def save_session(self, session: Session) -> None:
        """Save a session to disk."""
        session.updated_at = datetime.now().isoformat()
        path = self.storage_dir / f"{session.session_id}.json"

        with open(path, "w") as f:
            json.dump(session.to_dict(), f, indent=2)

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        path = self.storage_dir / f"{session_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    def list_sessions(self) -> List[Dict]:
        """List all sessions with basic info."""
        sessions = []
        for path in self.storage_dir.glob("*.json"):
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                sessions.append({
                    "session_id": data["session_id"],
                    "created_at": data["created_at"],
                    "updated_at": data["updated_at"],
                    "history_count": len(data.get("history", [])),
                })
            except Exception as e:
                logger.warning(f"Skipped corrupt session file {path.name}: {e}")
        return sorted(sessions, key=lambda x: x["updated_at"], reverse=True)

    @log_agent_call
    def add_to_history(
        self,
        session: Session,
        request: str,
        intent_type: str,
        output: Dict[str, Any],
    ) -> None:
        """Add a request/response to session history."""
        entry = HistoryEntry(
            timestamp=datetime.now().isoformat(),
            request=request,
            intent_type=intent_type,
            output=output,
        )
        session.history.append(entry)
        self.save_session(session)

    def record_feedback(
        self,
        session: Session,
        entry_index: int,
        feedback: str,  # "thumbs_up", "thumbs_down", "regenerate", "progression_swap"
        feedback_label: Optional[str] = None,
    ) -> bool:
        """Record feedback on a history entry."""
        try:
            session.history[entry_index].feedback = feedback
            session.history[entry_index].feedback_label = feedback_label
            self.save_session(session)

            # Update user profile based on feedback patterns
            self._update_profile_from_feedback(session)

            return True
        except IndexError:
            return False

    def update_project_context(
        self,
        session: Session,
        key: Optional[str] = None,
        bpm: Optional[int] = None,
        genre: Optional[str] = None,
        name: Optional[str] = None,
    ) -> None:
        """Update the current project context."""
        if key is not None:
            session.current_project.key = key
        if bpm is not None:
            session.current_project.bpm = bpm
        if genre is not None:
            session.current_project.genre = genre
        if name is not None:
            session.current_project.name = name
        self.save_session(session)

    def get_recent_history(
        self,
        session: Session,
        count: int = 5,
    ) -> List[HistoryEntry]:
        """Get the most recent history entries."""
        return session.history[-count:]

    def get_history_summary(self, session: Session) -> Dict:
        """Get a summary of session history for context."""
        if not session.history:
            return {"count": 0, "recent_requests": [], "feedback_summary": {}}

        # Count feedback
        feedback_counts = {"thumbs_up": 0, "thumbs_down": 0, "regenerate": 0, "none": 0}
        for entry in session.history:
            if entry.feedback:
                feedback_counts[entry.feedback] = feedback_counts.get(entry.feedback, 0) + 1
            else:
                feedback_counts["none"] += 1

        # Get recent requests (just the text, for context)
        recent = [e.request for e in session.history[-5:]]

        return {
            "count": len(session.history),
            "recent_requests": recent,
            "feedback_summary": feedback_counts,
        }

    def _update_profile_from_feedback(self, session: Session) -> None:
        """Update user profile based on feedback patterns."""
        # Count recent feedback
        recent = session.history[-10:]

        # Check if user often skips explanations (placeholder for v2)
        # This would be tracked by frontend engagement events

        # Check feedback ratio
        thumbs_up = sum(1 for e in recent if e.feedback == "thumbs_up")
        thumbs_down = sum(1 for e in recent if e.feedback == "thumbs_down")

        # Could adjust recommendations based on this
        # For v1, just track the data


def get_or_create_session(
    manager: SessionManager,
    session_id: Optional[str] = None,
) -> Session:
    """Get existing session or create new one."""
    if session_id:
        session = manager.load_session(session_id)
        if session:
            return session

    return manager.create_session()


if __name__ == "__main__":
    import shutil

    print("=" * 60)
    print("Session Memory — Test")
    print("=" * 60)
    print()

    # Use a temp directory for testing
    test_dir = Path(__file__).parent / "test_sessions"
    test_dir.mkdir(exist_ok=True)

    try:
        manager = SessionManager(storage_dir=test_dir)

        # Create a session
        print("Creating session...")
        session = manager.create_session()
        print(f"  Session ID: {session.session_id}")
        print(f"  User profile: {session.user_profile.theory_level} theory, {session.user_profile.production_level} production")
        print()

        # Add some history
        print("Adding history entries...")
        manager.add_to_history(
            session,
            request="give me something melancholic and lo-fi",
            intent_type="mood_vibe",
            output={
                "progression": "Sad Lo-Fi",
                "chords": ["Am", "F", "Dm", "G"],
            },
        )
        manager.add_to_history(
            session,
            request="I need a trap beat",
            intent_type="drum_pattern",
            output={
                "pattern": "Trap Basic",
                "tempo": "140 BPM",
            },
        )
        print(f"  History count: {len(session.history)}")
        print()

        # Record feedback
        print("Recording feedback...")
        manager.record_feedback(session, -1, "thumbs_up")
        print(f"  Last entry feedback: {session.history[-1].feedback}")
        print()

        # Update project context
        print("Updating project context...")
        manager.update_project_context(session, key="A minor", bpm=85, genre="lo-fi")
        print(f"  Current project: {session.current_project}")
        print()

        # Load session from disk
        print("Reloading session from disk...")
        loaded = manager.load_session(session.session_id)
        print(f"  Loaded session ID: {loaded.session_id}")
        print(f"  History count: {len(loaded.history)}")
        print(f"  Last request: {loaded.history[-1].request}")
        print()

        # Get summary
        print("History summary:")
        summary = manager.get_history_summary(loaded)
        print(f"  {summary}")
        print()

        # List sessions
        print("All sessions:")
        for s in manager.list_sessions():
            print(f"  {s['session_id'][:8]}... - {s['history_count']} entries")
        print()

        print("=" * 60)
        print("All tests passed!")
        print("=" * 60)

    finally:
        # Cleanup
        shutil.rmtree(test_dir, ignore_errors=True)
