"""
Core music theory primitives: notes, intervals, transposition.

All calculations are deterministic — no LLM calls, 100% accurate.
"""

from dataclasses import dataclass
from typing import Optional
import re

# Chromatic scale with enharmonic mappings
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# Map flats to sharps for internal consistency
ENHARMONIC_MAP = {
    'Db': 'C#', 'Eb': 'D#', 'Fb': 'E', 'Gb': 'F#', 'Ab': 'G#', 'Bb': 'A#', 'Cb': 'B',
    'E#': 'F', 'B#': 'C',
}

# Interval semitones (from root)
INTERVAL_SEMITONES = {
    'P1': 0, 'unison': 0,
    'm2': 1, 'minor 2nd': 1,
    'M2': 2, 'major 2nd': 2,
    'm3': 3, 'minor 3rd': 3,
    'M3': 4, 'major 3rd': 4,
    'P4': 5, 'perfect 4th': 5,
    'A4': 6, 'augmented 4th': 6, 'd5': 6, 'diminished 5th': 6, 'tritone': 6,
    'P5': 7, 'perfect 5th': 7,
    'A5': 8, 'augmented 5th': 8, 'm6': 8, 'minor 6th': 8,
    'M6': 9, 'major 6th': 9,
    'm7': 10, 'minor 7th': 10,
    'M7': 11, 'major 7th': 11,
    'P8': 12, 'octave': 12,
    'm9': 13, 'minor 9th': 13,
    'M9': 14, 'major 9th': 14,
    'm10': 15, 'minor 10th': 15,
    'M10': 16, 'major 10th': 16,
    'P11': 17, 'perfect 11th': 17,
    'A11': 18, 'augmented 11th': 18,
    'P12': 19, 'perfect 12th': 19,
    'm13': 20, 'minor 13th': 20,
    'M13': 21, 'major 13th': 21,
}


@dataclass
class Note:
    """A musical note with pitch class and octave."""
    name: str  # e.g., 'C', 'F#', 'Bb'
    octave: int  # e.g., 4 for middle C

    def __post_init__(self):
        # Normalize enharmonics
        if self.name in ENHARMONIC_MAP:
            self.name = ENHARMONIC_MAP[self.name]

    @classmethod
    def from_string(cls, s: str) -> 'Note':
        """Parse 'C4', 'F#3', 'Bb5' etc."""
        match = re.match(r'^([A-Ga-g][#b]?)(-?\d+)$', s.strip())
        if not match:
            raise ValueError(f"Invalid note format: {s}")
        name = match.group(1).upper()
        if len(name) == 2:
            name = name[0].upper() + name[1]
        octave = int(match.group(2))
        return cls(name=name, octave=octave)

    def __str__(self) -> str:
        return f"{self.name}{self.octave}"

    def to_midi(self) -> int:
        """Convert to MIDI note number (C4 = 60)."""
        pitch_class = NOTE_NAMES.index(self.normalized_name)
        return (self.octave + 1) * 12 + pitch_class

    @classmethod
    def from_midi(cls, midi: int) -> 'Note':
        """Create from MIDI note number."""
        octave = (midi // 12) - 1
        pitch_class = midi % 12
        return cls(name=NOTE_NAMES[pitch_class], octave=octave)

    @property
    def normalized_name(self) -> str:
        """Get the sharp-normalized pitch class name."""
        return ENHARMONIC_MAP.get(self.name, self.name)

    @property
    def pitch_class(self) -> int:
        """Get pitch class (0-11, C=0)."""
        return NOTE_NAMES.index(self.normalized_name)


@dataclass
class Interval:
    """A musical interval (distance between two notes)."""
    semitones: int

    @classmethod
    def from_name(cls, name: str) -> 'Interval':
        """Create from interval name like 'P5', 'm3', 'major 3rd'."""
        if name not in INTERVAL_SEMITONES:
            raise ValueError(f"Unknown interval: {name}")
        return cls(semitones=INTERVAL_SEMITONES[name])

    @property
    def name(self) -> str:
        """Get short interval name."""
        for name, semis in INTERVAL_SEMITONES.items():
            if semis == self.semitones % 12 and len(name) <= 3:
                return name
        return f"{self.semitones} semitones"


def transpose(note: Note, semitones: int) -> Note:
    """Transpose a note by a number of semitones."""
    new_midi = note.to_midi() + semitones
    return Note.from_midi(new_midi)


def interval_between(note1: Note, note2: Note) -> Interval:
    """Calculate the interval between two notes."""
    semitones = note2.to_midi() - note1.to_midi()
    return Interval(semitones=semitones)
