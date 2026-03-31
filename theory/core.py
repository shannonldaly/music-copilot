"""
Core music theory primitives: notes, intervals, transposition.

All calculations are deterministic — no LLM calls, 100% accurate.
"""

from dataclasses import dataclass
from typing import Optional
import re

# Chromatic scale with enharmonic mappings
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# Map flats to sharps for internal consistency (used by MIDI/pitch-class logic)
ENHARMONIC_MAP = {
    'Db': 'C#', 'Eb': 'D#', 'Fb': 'E', 'Gb': 'F#', 'Ab': 'G#', 'Bb': 'A#', 'Cb': 'B',
    'E#': 'F', 'B#': 'C',
}

# Letter names and their natural pitch classes (semitones from C)
LETTER_NAMES = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
LETTER_PITCH_CLASS = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}

# For each chord interval (semitones), how many letter names above the root.
# This determines correct enharmonic spelling in chord contexts.
# e.g., major 3rd (4 semitones) = 2 letters up, so C→E, C#→E#, Db→Fb
CHORD_INTERVAL_LETTER_OFFSET = {
    0: 0,   # unison
    1: 1,   # minor 2nd
    2: 1,   # major 2nd
    3: 2,   # minor 3rd
    4: 2,   # major 3rd
    5: 3,   # perfect 4th
    6: 4,   # diminished 5th (tritone treated as b5 in chord context)
    7: 4,   # perfect 5th
    8: 4,   # augmented 5th
    9: 5,   # major 6th
    10: 6,  # minor 7th
    11: 6,  # major 7th
    12: 7,  # octave
    13: 8,  # minor 9th
    14: 8,  # major 9th
    15: 9,  # augmented 9th / minor 10th
    16: 9,  # major 10th
    17: 10, # perfect 11th
    18: 10, # augmented 11th
    19: 11, # perfect 12th
    20: 12, # minor 13th
    21: 12, # major 13th
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
    """A musical note with pitch class and octave.

    Note names preserve their enharmonic spelling (Bb stays Bb, E# stays E#).
    Use normalized_name to get the sharp-only form when needed for lookup.
    """
    name: str  # e.g., 'C', 'F#', 'Bb', 'E#'
    octave: int  # e.g., 4 for middle C

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
        """Convert to MIDI note number (C4 = 60).

        Handles enharmonics correctly: B#3 = C4 = 60, Cb4 = B3 = 59.
        """
        letter = self.name[0]
        acc = self.name[1:] if len(self.name) > 1 else ''
        acc_semitones = acc.count('#') - acc.count('b')
        natural_pc = LETTER_PITCH_CLASS[letter]
        return (self.octave + 1) * 12 + natural_pc + acc_semitones

    @classmethod
    def from_midi(cls, midi: int) -> 'Note':
        """Create from MIDI note number (uses sharp spelling by default)."""
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
        letter = self.name[0]
        acc = self.name[1:] if len(self.name) > 1 else ''
        acc_semitones = acc.count('#') - acc.count('b')
        return (LETTER_PITCH_CLASS[letter] + acc_semitones) % 12


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


def _parse_root_letter(name: str):
    """Parse a note name into (letter, accidental_semitones).

    'C' → ('C', 0), 'C#' → ('C', 1), 'Db' → ('D', -1), 'E#' → ('E', 1)
    """
    letter = name[0].upper()
    acc = name[1:] if len(name) > 1 else ''
    acc_semitones = acc.count('#') - acc.count('b')
    return letter, acc_semitones


def spell_note_for_interval(root_name: str, root_octave: int, semitones: int) -> Note:
    """
    Spell a note that is `semitones` above the root, using correct enharmonic spelling.

    Uses letter-name arithmetic: a major 3rd (4 semitones) is always 2 letter names
    above the root. C# + M3 = E# (not F). Db + M3 = F (not E#).

    Args:
        root_name: Root note name (e.g., 'C#', 'Db', 'F#')
        root_octave: Octave of the root
        semitones: Interval in semitones

    Returns:
        Note with correctly spelled name and octave
    """
    letter_offset = CHORD_INTERVAL_LETTER_OFFSET.get(semitones)
    if letter_offset is None:
        # Fallback for unknown intervals: use MIDI transposition
        root_note = Note.__new__(Note)
        root_note.name = ENHARMONIC_MAP.get(root_name, root_name)
        root_note.octave = root_octave
        return transpose(root_note, semitones)

    root_letter, root_acc = _parse_root_letter(root_name)
    root_letter_idx = LETTER_NAMES.index(root_letter)

    # Target letter (wrapping around the 7 letter names)
    target_letter_idx = (root_letter_idx + letter_offset) % 7
    target_letter = LETTER_NAMES[target_letter_idx]

    # Compute octave offset from letter wrapping
    octave_offset = (root_letter_idx + letter_offset) // 7

    # Compute the natural pitch class of root and target
    root_natural_pc = LETTER_PITCH_CLASS[root_letter]
    target_natural_pc = LETTER_PITCH_CLASS[target_letter]

    # The actual pitch class we need
    target_actual_pc = (root_natural_pc + root_acc + semitones) % 12

    # What accidental do we need on the target letter?
    acc_needed = (target_actual_pc - target_natural_pc) % 12
    # Normalize: if acc_needed > 2, it's actually a negative (flat) accidental
    if acc_needed > 2:
        acc_needed -= 12

    # Build the note name
    if acc_needed > 0:
        target_name = target_letter + '#' * acc_needed
    elif acc_needed < 0:
        target_name = target_letter + 'b' * (-acc_needed)
    else:
        target_name = target_letter

    target_octave = root_octave + octave_offset

    # Create Note without __post_init__ normalization destroying the spelling
    note = Note.__new__(Note)
    note.name = target_name
    note.octave = target_octave
    return note
