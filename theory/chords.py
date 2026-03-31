"""
Chord definitions and construction.

All chords are defined as interval patterns (semitones from root).
This is deterministic — no LLM needed.
"""

from dataclasses import dataclass
from typing import List, Optional
from .core import Note, transpose, spell_note_for_interval

# Chord patterns as semitones from root
CHORD_PATTERNS = {
    # Triads
    'major': [0, 4, 7],
    'M': [0, 4, 7],
    '': [0, 4, 7],  # Default major
    'minor': [0, 3, 7],
    'm': [0, 3, 7],
    'min': [0, 3, 7],
    'diminished': [0, 3, 6],
    'dim': [0, 3, 6],
    '°': [0, 3, 6],
    'augmented': [0, 4, 8],
    'aug': [0, 4, 8],
    '+': [0, 4, 8],
    'sus2': [0, 2, 7],
    'sus4': [0, 5, 7],
    'sus': [0, 5, 7],  # sus4 by default

    # Seventh chords
    'major7': [0, 4, 7, 11],
    'maj7': [0, 4, 7, 11],
    'M7': [0, 4, 7, 11],
    'Δ7': [0, 4, 7, 11],
    'minor7': [0, 3, 7, 10],
    'm7': [0, 3, 7, 10],
    'min7': [0, 3, 7, 10],
    '-7': [0, 3, 7, 10],
    'dominant7': [0, 4, 7, 10],
    '7': [0, 4, 7, 10],
    'dom7': [0, 4, 7, 10],
    'diminished7': [0, 3, 6, 9],
    'dim7': [0, 3, 6, 9],
    '°7': [0, 3, 6, 9],
    'half-diminished7': [0, 3, 6, 10],
    'm7b5': [0, 3, 6, 10],
    'ø7': [0, 3, 6, 10],
    'minmaj7': [0, 3, 7, 11],
    'mM7': [0, 3, 7, 11],
    'augmented7': [0, 4, 8, 10],
    'aug7': [0, 4, 8, 10],
    '+7': [0, 4, 8, 10],

    # Extended chords
    'add9': [0, 4, 7, 14],
    'madd9': [0, 3, 7, 14],
    '9': [0, 4, 7, 10, 14],
    'maj9': [0, 4, 7, 11, 14],
    'm9': [0, 3, 7, 10, 14],
    '11': [0, 4, 7, 10, 14, 17],
    'm11': [0, 3, 7, 10, 14, 17],
    '13': [0, 4, 7, 10, 14, 21],
    'maj13': [0, 4, 7, 11, 14, 21],
    'm13': [0, 3, 7, 10, 14, 21],

    # Altered dominants
    '7b9': [0, 4, 7, 10, 13],
    '7#9': [0, 4, 7, 10, 15],
    '7b5': [0, 4, 6, 10],
    '7#5': [0, 4, 8, 10],
    '7alt': [0, 4, 8, 10, 13],  # Common alt voicing

    # 6th chords
    '6': [0, 4, 7, 9],
    'maj6': [0, 4, 7, 9],
    'm6': [0, 3, 7, 9],
    'min6': [0, 3, 7, 9],

    # Power chord
    '5': [0, 7],
    'power': [0, 7],
}


@dataclass
class Chord:
    """A chord with root and quality."""
    root: str  # e.g., 'A', 'F#', 'Bb'
    quality: str  # e.g., 'minor', 'm7', 'maj7'

    def __post_init__(self):
        if self.quality not in CHORD_PATTERNS:
            raise ValueError(f"Unknown chord quality: {self.quality}")

    @property
    def intervals(self) -> List[int]:
        """Get the interval pattern (semitones from root)."""
        return CHORD_PATTERNS[self.quality]

    def get_notes(self, octave: int = 4) -> List[Note]:
        """Get all notes in the chord at given octave, with correct enharmonic spelling."""
        return [spell_note_for_interval(self.root, octave, interval) for interval in self.intervals]

    def get_note_names(self) -> List[str]:
        """Get just the note names (no octave)."""
        return [n.name for n in self.get_notes()]

    @property
    def name(self) -> str:
        """Get the chord name like 'Am' or 'Fmaj7'."""
        if self.quality in ['major', 'M', '']:
            return self.root
        elif self.quality in ['minor', 'min']:
            return f"{self.root}m"
        else:
            return f"{self.root}{self.quality}"

    @classmethod
    def from_name(cls, chord_name: str) -> 'Chord':
        """
        Parse a chord name like 'Am', 'F#maj7', 'Bbm7'.

        Handles common formats:
        - C, Cm, Cdim, Caug
        - Cmaj7, Cm7, C7, Cdim7
        - C#m, Bbmaj7, etc.
        """
        import re

        # Match root note (with optional sharp/flat) and quality
        match = re.match(r'^([A-Ga-g][#b]?)(.*)$', chord_name.strip())
        if not match:
            raise ValueError(f"Cannot parse chord: {chord_name}")

        root = match.group(1)
        root = root[0].upper() + root[1:] if len(root) > 1 else root.upper()
        quality = match.group(2)

        # Handle empty quality as major
        if quality == '':
            quality = 'major'
        # Handle 'm' as minor (but not maj, m7, etc.)
        elif quality == 'm':
            quality = 'minor'

        return cls(root=root, quality=quality)


def build_chord(root: str, quality: str, octave: int = 4) -> List[Note]:
    """
    Build a chord from root and quality.

    Args:
        root: Root note name (e.g., 'A', 'F#')
        quality: Chord quality (e.g., 'minor', 'm7', 'maj7')
        octave: Base octave (default 4)

    Returns:
        List of Note objects
    """
    chord = Chord(root=root, quality=quality)
    return chord.get_notes(octave=octave)


def get_chord_notes(chord_name: str, octave: int = 4) -> List[Note]:
    """
    Get notes from a chord name string.

    Args:
        chord_name: Chord name like 'Am', 'F#maj7', 'Bbm7'
        octave: Base octave (default 4)

    Returns:
        List of Note objects
    """
    chord = Chord.from_name(chord_name)
    return chord.get_notes(octave=octave)
