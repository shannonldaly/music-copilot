"""
Ableton MCP Client — JSON over TCP to the Ableton socket server.

Connects to localhost:9877 (the ableton-mcp socket server).
All methods are defensive: never raise to the caller, always return
a status dict {success: bool, message: str}.

Protocol (verified against live server):
  - Commands: {'type': '...', 'params': {...}}
  - Responses: {'status': 'success'|'error', 'result': {...}, 'message'?: '...'}
  - Commands: set_tempo, create_midi_track, create_clip, add_notes_to_clip
  - Note format: {pitch: int (MIDI), start_time: float, duration: float, velocity: int}

Usage:
    from services.mcp_client import AbletonMCPClient

    client = AbletonMCPClient()
    if client.is_connected():
        result = client.send_progression_to_ableton(progression_data, bpm=85)
"""

import json
import logging
import socket
from typing import Dict, List, Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logging import log_agent_call

logger = logging.getLogger(__name__)

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 9877
SOCKET_TIMEOUT = 5.0
BUFFER_SIZE = 65536


class AbletonMCPClient:
    """
    Thin client for the Ableton MCP socket server.

    Every public method returns {success: bool, message: str}.
    No exceptions escape to the caller.
    """

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.host = host
        self.port = port

    # =========================================================================
    # Public API
    # =========================================================================

    @log_agent_call
    def is_connected(self) -> bool:
        """Check if Ableton is reachable by sending get_session_info."""
        result = self._send_command("get_session_info")
        return result["success"]

    @log_agent_call
    def send_progression_to_ableton(self, progression_data: Dict, bpm: int = 120) -> Dict:
        """
        Create a MIDI track in Ableton and populate it with chord notes.

        Sequence:
        1. set_tempo
        2. create_midi_track (capture returned index)
        3. create_clip (on returned track, clip_index 0, length = chords × 4)
        4. add_notes_to_clip (one call per chord, notes batched)

        Args:
            progression_data: Dict with 'chords' list. Each chord has
                'name', 'numeral', 'note_names' (e.g. ['A3', 'C4', 'E4'])
            bpm: Tempo in BPM

        Returns:
            {success: bool, message: str}
        """
        # DEBUG: log exactly what the MCP client receives
        logger.warning(f"DEBUG MCP input: keys={list(progression_data.keys())}, bpm={bpm}")
        chords = progression_data.get("chords", [])
        logger.warning(f"DEBUG MCP chords: count={len(chords)}")
        for i, ch in enumerate(chords):
            logger.warning(f"DEBUG MCP chord {i}: name={ch.get('name')}, note_names={ch.get('note_names')}, notes={ch.get('notes')}, keys={list(ch.keys())}")

        if not chords:
            return {"success": False, "message": "No chords in progression data"}

        # Step 1: Set tempo
        result = self._send_command("set_tempo", {"tempo": bpm})
        if not result["success"]:
            return {"success": False, "message": f"Failed to set tempo: {result['message']}"}
        logger.info(f"MCP: tempo set to {bpm} BPM")

        # Step 2: Create MIDI track
        result = self._send_command("create_midi_track", {"name": "Rubato Chords"})
        if not result["success"]:
            return {"success": False, "message": f"Failed to create track: {result['message']}"}

        track_index = result["data"].get("index", 0)
        logger.info(f"MCP: created track at index {track_index}")

        # Step 3: Create clip
        clip_length = len(chords) * 4  # 4 beats per chord (1 bar each)
        result = self._send_command("create_clip", {
            "track_index": track_index,
            "clip_index": 0,
            "length": clip_length,
        })
        if not result["success"]:
            return {"success": False, "message": f"Failed to create clip: {result['message']}"}
        logger.info(f"MCP: created clip with length {clip_length} beats")

        # Step 4: Add notes — one call per chord, all notes batched
        total_notes = 0
        for i, chord in enumerate(chords):
            note_names = chord.get("note_names", chord.get("notes", []))
            if not note_names:
                logger.warning(f"MCP: chord {i+1} ({chord.get('name', '?')}) has no notes, skipping")
                continue

            start_time = float(i * 4)  # Each chord at a new bar
            duration = 4.0             # One bar

            notes_batch = []
            for note_name in note_names:
                midi_note = _note_name_to_midi(note_name)
                if midi_note is None:
                    logger.warning(f"MCP: could not convert '{note_name}' to MIDI, skipping")
                    continue
                notes_batch.append({
                    "pitch": midi_note,
                    "start_time": start_time,
                    "duration": duration,
                    "velocity": 100,
                })

            if not notes_batch:
                continue

            result = self._send_command("add_notes_to_clip", {
                "track_index": track_index,
                "clip_index": 0,
                "notes": notes_batch,
            })
            if not result["success"]:
                return {
                    "success": False,
                    "message": f"Failed to add chord {i+1} ({chord.get('name', '?')}): {result['message']}",
                }
            total_notes += len(notes_batch)

        if total_notes == 0:
            return {"success": False, "message": "No notes were added to Ableton"}

        return {
            "success": True,
            "message": f"Created {len(chords)} chords ({total_notes} notes) on track {track_index + 1}",
        }

    # =========================================================================
    # Transport — JSON over TCP
    # =========================================================================

    def _send_command(self, command_type: str, params: Optional[Dict] = None) -> Dict:
        """
        Send a JSON command to the Ableton socket server.

        Args:
            command_type: The command type string (e.g. 'set_tempo')
            params: Optional parameter dict (wrapped in 'params' key)

        Returns:
            {success: bool, message: str, data?: dict}
        """
        command = {"type": command_type}
        if params:
            command["params"] = params

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(SOCKET_TIMEOUT)
            sock.connect((self.host, self.port))

            payload = json.dumps(command).encode("utf-8") + b"\n"
            sock.sendall(payload)

            response_bytes = sock.recv(BUFFER_SIZE)
            sock.close()

            if not response_bytes:
                return {"success": False, "message": "Empty response from Ableton"}

            response = json.loads(response_bytes.decode("utf-8"))

            if response.get("status") == "error":
                error_msg = response.get("message", "Unknown error")
                return {"success": False, "message": f"Ableton: {error_msg}", "data": response}

            return {
                "success": True,
                "message": "OK",
                "data": response.get("result", {}),
            }

        except ConnectionRefusedError:
            logger.warning("Ableton MCP: connection refused — is Ableton running with the MCP server?")
            return {"success": False, "message": "Ableton not connected"}

        except socket.timeout:
            logger.warning(f"Ableton MCP: timed out after {SOCKET_TIMEOUT}s")
            return {"success": False, "message": "Ableton connection timed out"}

        except json.JSONDecodeError as e:
            logger.warning(f"Ableton MCP: invalid JSON response: {e}")
            return {"success": False, "message": f"Invalid response from Ableton: {e}"}

        except Exception as e:
            logger.warning(f"Ableton MCP: {type(e).__name__}: {e}")
            return {"success": False, "message": f"MCP error: {type(e).__name__}: {e}"}


# =============================================================================
# Note conversion
# =============================================================================

# MIDI note numbers: C4 (middle C) = 60
_NOTE_MAP = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}


def _note_name_to_midi(note_name: str) -> Optional[int]:
    """Convert 'C4', 'F#3', 'Bb4' etc. to MIDI note number. Returns None on failure."""
    if not note_name or len(note_name) < 2:
        return None
    try:
        base = note_name[0].upper()
        if base not in _NOTE_MAP:
            return None
        midi = _NOTE_MAP[base]

        rest = note_name[1:]
        if rest.startswith('#'):
            midi += 1
            rest = rest[1:]
        elif rest.startswith('b'):
            midi -= 1
            rest = rest[1:]

        octave = int(rest)
        return midi + (octave + 1) * 12
    except (ValueError, IndexError):
        return None
