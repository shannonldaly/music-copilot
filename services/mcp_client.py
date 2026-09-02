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

# Ableton Core Kit pitch layout (GM-flavored): pad row starting at C1
DRUM_PITCH_MAP = {
    "kick": 36, "snare": 38, "clap": 39, "rim": 37, "snap": 39,
    "closed_hat": 42, "open_hat": 46, "shaker": 70, "perc": 43,
    "tom_low": 41, "tom_mid": 45, "tom_high": 48,
    "crash": 49, "ride": 51, "conga": 63,
}
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

        self._place_in_arrangement(track_index, 0)

        return {
            "success": True,
            "message": f"Created {len(chords)} chords ({total_notes} notes) on track {track_index + 1}",
            "track_index": track_index,
        }

    def send_arrangement_to_ableton(self, progression: Dict, bass_line: Optional[Dict] = None,
                                    drum_pattern: Optional[Dict] = None, bpm: int = 120) -> Dict:
        """
        Land the whole session foundation in Ableton: chords + bass (+ drums),
        each on its own named track with an instrument and an EQ Eight starting point.

        Expects: a full progression dict (chords with note_names); bass_line
        ({root_notes, ...}, optional — roots derived from the chords when absent);
        drum_pattern ({name, grid}, optional — the drums track is skipped without it).
        Guarantees: returns {success, message, tracks} where tracks lists what
        landed; tempo and Live's Key & Scale are set from the progression. Partial
        failures degrade (a failed bass/drums track is reported, chords stand).
        If something is missing: no chords → {success: False}; missing presets
        load nothing but the notes still land.
        Downstream: /api/send-arrangement-to-ableton returns this dict to the UI.
        """
        chords = progression.get("chords", [])
        if not chords:
            return {"success": False, "message": "No chords in progression data"}

        # Chords track (also sets tempo + song key)
        result = self.send_progression_to_ableton(progression, bpm=bpm)
        if not result["success"]:
            return result
        tracks = ["chords (piano)"]
        chord_track = result.get("track_index")
        if chord_track is not None:
            self._load_eq_eight(chord_track)

        clip_length = len(chords) * 4
        key_str = progression.get("key") or ""

        # Bass track
        bass_notes = self._build_bass_notes(chords, bass_line, progression)
        if bass_notes:
            bass_track = self._create_instrument_track(
                "Rubato Bass", [("Bass", None), ("Pad", None)])
            if bass_track is not None:
                r = self._send_command("create_clip", {
                    "track_index": bass_track, "clip_index": 0, "length": clip_length})
                if r["success"]:
                    self._send_command("add_notes_to_clip", {
                        "track_index": bass_track, "clip_index": 0, "notes": bass_notes})
                    name = "Bass roots" + (f" · {key_str}" if key_str else "")
                    self._send_command("set_clip_name", {
                        "track_index": bass_track, "clip_index": 0, "name": name})
                    self._load_eq_eight(bass_track)
                    self._place_in_arrangement(bass_track, 0)
                    tracks.append("bass")
                else:
                    logger.warning(f"MCP: bass clip failed ({r['message']})")

        # Drums track
        grid = (drum_pattern or {}).get("grid") or {}
        drum_notes = self._build_drum_notes(grid, bars=len(chords))
        if drum_notes:
            drum_track = self._create_drum_track("Rubato Drums")
            if drum_track is not None:
                r = self._send_command("create_clip", {
                    "track_index": drum_track, "clip_index": 0, "length": clip_length})
                if r["success"]:
                    self._send_command("add_notes_to_clip", {
                        "track_index": drum_track, "clip_index": 0, "notes": drum_notes})
                    self._send_command("set_clip_name", {
                        "track_index": drum_track, "clip_index": 0,
                        "name": drum_pattern.get("name", "Drums")})
                    self._load_eq_eight(drum_track)
                    self._place_in_arrangement(drum_track, 0)
                    tracks.append("drums")
                else:
                    logger.warning(f"MCP: drum clip failed ({r['message']})")

        return {
            "success": True,
            "message": f"Landed {' + '.join(tracks)}" + (f" · {key_str}" if key_str else "") + f" · {bpm} BPM",
            "tracks": tracks,
        }

    def _create_instrument_track(self, name: str, categories) -> Optional[int]:
        """
        Create a named MIDI track and load the first loadable preset from the
        given (category, prefer-substring) list. Returns the track index, or
        None when track creation fails (instrument failures degrade to a bare
        track). The arrangement send depends on the returned index for clips.
        """
        r = self._send_command("create_midi_track", {})
        if not r["success"]:
            logger.warning(f"MCP: create track '{name}' failed ({r['message']})")
            return None
        track_index = r["data"].get("index", 0)
        self._send_command("set_track_name", {"track_index": track_index, "name": name})
        for category, prefer in categories:
            uri, preset = self._resolve_from_category(f"sounds/{category}", prefer)
            if uri:
                lr = self._send_command("load_browser_item", {
                    "item_uri": uri, "track_index": track_index})
                if lr["success"]:
                    logger.info(f"MCP: {name} instrument: {preset}")
                    break
        return track_index

    def _create_drum_track(self, name: str) -> Optional[int]:
        """
        Create a named MIDI track with a drum kit (Core Kit preferred) from the
        browser's drums category. Same contract as _create_instrument_track.
        """
        r = self._send_command("create_midi_track", {})
        if not r["success"]:
            logger.warning(f"MCP: create track '{name}' failed ({r['message']})")
            return None
        track_index = r["data"].get("index", 0)
        self._send_command("set_track_name", {"track_index": track_index, "name": name})
        uri, preset = self._resolve_from_category("drums", "core kit")
        if uri:
            lr = self._send_command("load_browser_item", {
                "item_uri": uri, "track_index": track_index})
            if lr["success"]:
                logger.info(f"MCP: {name} kit: {preset}")
        return track_index

    def _place_in_arrangement(self, track_index: int, clip_index: int) -> None:
        """Mirror a session clip onto the arrangement timeline at bar 1, so the
        import is visible in both views. Unknown-command (unpatched script) or
        any failure only warns — the session clip is the source of truth."""
        r = self._send_command("clip_to_arrangement", {
            "track_index": track_index, "clip_index": clip_index, "time": 0.0})
        if not r["success"]:
            logger.warning(f"MCP: arrangement placement skipped ({r['message']})")

    def _load_eq_eight(self, track_index: int) -> None:
        """Load an EQ Eight starting point onto a track. Failures only warn —
        the notes matter more than the effect chain."""
        uri, _ = self._resolve_from_category("audio_effects", "eq eight")
        if not uri:
            logger.warning("MCP: EQ Eight not found in browser")
            return
        r = self._send_command("load_browser_item", {
            "item_uri": uri, "track_index": track_index})
        if not r["success"]:
            logger.warning(f"MCP: EQ Eight load failed ({r['message']})")

    def _build_bass_notes(self, chords, bass_line, progression) -> list:
        """
        Turn bass guidance into MIDI notes, one bar per chord.

        Expects: chords with root/name; bass_line.root_notes when present
        (falls back to chord roots at octave 2). Guarantees: a list of note
        dicts in add_notes_to_clip shape; empty when no root resolves.
        Rhythm follows the progression's genres: held notes for lo-fi/trap,
        offbeat eighths for house/EDM, roots on 1 and 3 otherwise.
        """
        roots = list((bass_line or {}).get("root_notes") or [])
        if not roots:
            for chord in chords:
                root = chord.get("root") or (chord.get("name") or "")[:1]
                if root:
                    roots.append(f"{root}2")
        if not roots:
            return []

        genres = {str(g).lower().replace("-", "_").replace(" ", "_")
                  for g in (progression.get("genres") or [])}
        if genres & {"house", "edm", "dance", "techno", "disco"}:
            hits = [(0.5 + i, 0.45) for i in range(4)]  # offbeat eighths per bar
        elif genres & {"lo_fi", "lofi", "chillhop", "jazz", "trap", "hip_hop"}:
            hits = [(0.0, 4.0)]  # let the root ring the whole bar
        else:
            hits = [(0.0, 2.0), (2.0, 2.0)]  # roots on 1 and 3

        notes = []
        for bar, root in enumerate(roots[:len(chords)]):
            pitch = _note_name_to_midi(root)
            if pitch is None:
                continue
            for offset, duration in hits:
                notes.append({"pitch": pitch, "start_time": bar * 4.0 + offset,
                              "duration": duration, "velocity": 100})
        return notes

    def _build_drum_notes(self, grid: Dict, bars: int = 4) -> list:
        """
        Turn a 16-step drum grid into MIDI notes, looped across the clip.

        Expects: grid {sound_name: [step indices 0-15]} from DrumPattern.to_grid().
        Guarantees: note dicts pitched for Ableton Core Kits (kick C1=36 etc.,
        unknown sounds fall back to generic percussion); empty for an empty grid.
        Each step is a 16th (0.25 beats); the one-bar pattern repeats every bar.
        """
        if not grid:
            return []
        notes = []
        for sound, steps in grid.items():
            pitch = DRUM_PITCH_MAP.get(sound, 37)
            velocity = 85 if "hat" in sound or sound in ("shaker", "ride") else 100
            for bar in range(max(1, bars)):
                for step in steps or []:
                    notes.append({"pitch": pitch,
                                  "start_time": bar * 4.0 + step * 0.25,
                                  "duration": 0.2, "velocity": velocity})
        return notes

    def _resolve_from_category(self, path: str, prefer: Optional[str] = None):
        """
        Resolve a loadable browser preset by category path, preferring names
        containing `prefer`. Returns (uri, name) or (None, None). Never raises —
        callers degrade to no-instrument. Results are cached per client instance.
        """
        cache = getattr(self, "_browser_cache", None)
        if cache is None:
            cache = self._browser_cache = {}
        cache_key = (path, prefer)
        if cache_key in cache:
            return cache[cache_key]
        result = self._send_command("get_browser_items_at_path", {"path": path})
        resolved = (None, None)
        if result["success"]:
            items = [i for i in (result.get("data") or {}).get("items", [])
                     if i.get("is_loadable") and i.get("uri")]
            if items:
                resolved = (items[0]["uri"], items[0].get("name", path))
                if prefer:
                    for item in items:
                        if prefer in (item.get("name") or "").lower():
                            resolved = (item["uri"], item.get("name", path))
                            break
        cache[cache_key] = resolved
        return resolved

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
            uri, name = self._resolve_from_category(f"sounds/{category}", prefer)
            if uri:
                return uri, name
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
