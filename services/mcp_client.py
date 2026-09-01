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
        chords = progression_data.get("chords", [])
        if not chords:
            return {"success": False, "message": "No chords in progression data"}

        # Step 1: Set tempo
        result = self._send_command("set_tempo", {"tempo": bpm})
        if not result["success"]:
            return {"success": False, "message": f"Failed to set tempo: {result['message']}"}
        logger.info(f"MCP: tempo set to {bpm} BPM")

        # Step 1b: Match Live's Key & Scale to the progression key. Needs the
        # set_song_key command in the remote script — degrade gracefully without it.
        key_str = progression_data.get("key") or ""
        root_note, scale_name = _parse_key(key_str)
        if root_note is not None:
            result = self._send_command("set_song_key", {
                "root_note": root_note,
                "scale_name": scale_name,
            })
            if result["success"]:
                logger.info(f"MCP: song key set to {key_str}")
            else:
                logger.warning(f"MCP: song key not set ({result['message']}) — remote script may predate set_song_key")

        # Step 2: Create MIDI track
        result = self._send_command("create_midi_track", {"name": "Rubato Chords"})
        if not result["success"]:
            return {"success": False, "message": f"Failed to create track: {result['message']}"}

        track_index = result["data"].get("index", 0)
        logger.info(f"MCP: created track at index {track_index}")

        # create_midi_track ignores the name param in the remote script — name explicitly
        result = self._send_command("set_track_name", {
            "track_index": track_index,
            "name": "Rubato Chords",
        })
        if not result["success"]:
            logger.warning(f"MCP: track rename failed ({result['message']}), continuing")

        # Step 3: Load instrument — piano by default so the chords are immediately
        # audible and readable. Category URIs (query:Sounds#…) are folders and
        # load_item on a folder silently no-ops, so resolve a loadable preset.
        inst_uri, inst_name = self._resolve_instrument()
        if inst_uri:
            result = self._send_command("load_browser_item", {
                "item_uri": inst_uri,
                "track_index": track_index,
            })
            if not result["success"]:
                logger.warning(f"MCP: instrument load failed ({result['message']}), continuing without instrument")
            else:
                logger.info(f"MCP: loaded instrument: {inst_name}")
        else:
            logger.warning("MCP: no loadable instrument preset found, continuing without instrument")

        # Step 4: Create clip
        clip_length = len(chords) * 4  # 4 beats per chord (1 bar each)
        result = self._send_command("create_clip", {
            "track_index": track_index,
            "clip_index": 0,
            "length": clip_length,
        })
        if not result["success"]:
            return {"success": False, "message": f"Failed to create clip: {result['message']}"}
        logger.info(f"MCP: created clip with length {clip_length} beats")

        # Clip name carries the actual chords — the point of the import is that
        # you can read the progression right off the session view.
        chord_names = [c.get("name") for c in chords if c.get("name")]
        clip_name = " ".join(chord_names) if chord_names else (progression_data.get("name") or "Rubato")
        if key_str:
            clip_name = f"{clip_name} · {key_str}"
        result = self._send_command("set_clip_name", {
            "track_index": track_index,
            "clip_index": 0,
            "name": clip_name,
        })
        if not result["success"]:
            logger.warning(f"MCP: clip rename failed ({result['message']}), continuing")

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

    def _resolve_instrument(self):
        """
        Pick a loadable instrument preset for the chord track.

        Expects: a connected Ableton with the MCP remote script (browser commands).
        Guarantees: returns (uri, name) of a loadable preset, piano preferred
        (Piano & Keys category, "piano" in the name when available), falling back
        to the first loadable Pad preset; (None, None) when nothing resolves.
        Missing/failed browser queries degrade to the next category, never raise.
        The send flow depends on this so the imported chords are audible.
        """
        for category, prefer in (("Piano & Keys", "piano"), ("Pad", None)):
            result = self._send_command("get_browser_items_at_path", {"path": f"sounds/{category}"})
            if not result["success"]:
                continue
            items = [i for i in (result.get("data") or {}).get("items", [])
                     if i.get("is_loadable") and i.get("uri")]
            if not items:
                continue
            if prefer:
                for item in items:
                    if prefer in (item.get("name") or "").lower():
                        return item["uri"], item.get("name", category)
            return items[0]["uri"], items[0].get("name", category)
        return None, None

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


_KEY_ROOTS = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5,
    "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11,
}


def _parse_key(key_str: str):
    """
    Parse a progression key like "A minor" into Live's Key & Scale terms.

    Expects: a key string of the form "<root> <mode>" (e.g. "A minor", "Bb major").
    Guarantees: returns (root_note 0-11, scale_name "Major"/"Minor"); (None, None)
    for an empty or unparseable string — callers skip the key call in that case.
    The send flow depends on this to set Live's Key & Scale to match the import.
    """
    parts = (key_str or "").strip().split()
    if not parts:
        return None, None
    root = _KEY_ROOTS.get(parts[0])
    if root is None:
        return None, None
    mode = parts[1].lower() if len(parts) > 1 else "major"
    scale_name = "Minor" if mode.startswith("min") else "Major"
    return root, scale_name


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
