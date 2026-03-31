"""
Scale definitions and construction.

All scales are defined as interval patterns (semitones from root).
This is deterministic — no LLM needed.
"""

from dataclasses import dataclass
from typing import List
from .core import Note, transpose, spell_note_for_interval, NOTE_NAMES, LETTER_NAMES, LETTER_PITCH_CLASS

# Scale patterns as semitones from root
# Format: list of semitones for each scale degree
SCALE_PATTERNS = {
    # Major modes
    'major': [0, 2, 4, 5, 7, 9, 11],
    'ionian': [0, 2, 4, 5, 7, 9, 11],
    'dorian': [0, 2, 3, 5, 7, 9, 10],
    'phrygian': [0, 1, 3, 5, 7, 8, 10],
    'lydian': [0, 2, 4, 6, 7, 9, 11],
    'mixolydian': [0, 2, 4, 5, 7, 9, 10],
    'aeolian': [0, 2, 3, 5, 7, 8, 10],
    'natural minor': [0, 2, 3, 5, 7, 8, 10],
    'minor': [0, 2, 3, 5, 7, 8, 10],
    'locrian': [0, 1, 3, 5, 6, 8, 10],

    # Other minor scales
    'harmonic minor': [0, 2, 3, 5, 7, 8, 11],
    'melodic minor': [0, 2, 3, 5, 7, 9, 11],  # ascending form

    # Pentatonic
    'major pentatonic': [0, 2, 4, 7, 9],
    'minor pentatonic': [0, 3, 5, 7, 10],

    # Blues
    'blues': [0, 3, 5, 6, 7, 10],
    'major blues': [0, 2, 3, 4, 7, 9],

    # Other common scales
    'whole tone': [0, 2, 4, 6, 8, 10],
    'diminished': [0, 2, 3, 5, 6, 8, 9, 11],  # whole-half
    'diminished half-whole': [0, 1, 3, 4, 6, 7, 9, 10],
    'chromatic': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
}


@dataclass
class Scale:
    """A musical scale with root and pattern."""
    root: str  # e.g., 'A', 'F#'
    pattern_name: str  # e.g., 'natural minor', 'major'

    def __post_init__(self):
        if self.pattern_name not in SCALE_PATTERNS:
            raise ValueError(f"Unknown scale: {self.pattern_name}")

    @property
    def intervals(self) -> List[int]:
        """Get the interval pattern (semitones from root)."""
        return SCALE_PATTERNS[self.pattern_name]

    def get_notes(self, octave: int = 4) -> List[Note]:
        """Get all notes in the scale starting at given octave.

        Uses letter-name arithmetic so Bb minor gives Bb,C,Db,Eb,F,Gb,Ab
        and F# minor gives F#,G#,A,B,C#,D,E (correct enharmonic spelling).
        """
        notes = []
        for i, semitones in enumerate(self.intervals):
            # For 7-note scales, each degree is one letter name apart.
            # For pentatonic/blues, use chord-interval letter offsets as fallback.
            if len(self.intervals) == 7:
                # Standard 7-note scale: degree i uses letter offset i
                note = _spell_scale_note(self.root, octave, semitones, letter_offset=i)
            else:
                note = spell_note_for_interval(self.root, octave, semitones)
            notes.append(note)
        return notes

    def get_note_names(self) -> List[str]:
        """Get just the note names (no octave)."""
        return [n.name for n in self.get_notes()]

    def contains_pitch_class(self, note_name: str) -> bool:
        """Check if a pitch class is in this scale."""
        scale_notes = self.get_note_names()
        # Normalize the input
        from .core import ENHARMONIC_MAP
        normalized = ENHARMONIC_MAP.get(note_name, note_name)
        return normalized in scale_notes

    def degree_of(self, note_name: str) -> int:
        """Get the scale degree (1-7) of a note, or 0 if not in scale."""
        from .core import ENHARMONIC_MAP
        normalized = ENHARMONIC_MAP.get(note_name, note_name)
        scale_notes = self.get_note_names()
        if normalized in scale_notes:
            return scale_notes.index(normalized) + 1
        return 0


def _spell_scale_note(root_name: str, root_octave: int, semitones: int, letter_offset: int) -> Note:
    """Spell a scale note with the correct letter name for its degree.

    In a 7-note scale, degree 0 is the root (letter_offset=0),
    degree 1 is 1 letter up, degree 2 is 2 letters up, etc.
    """
    from .core import _parse_root_letter

    root_letter, root_acc = _parse_root_letter(root_name)
    root_letter_idx = LETTER_NAMES.index(root_letter)

    target_letter_idx = (root_letter_idx + letter_offset) % 7
    target_letter = LETTER_NAMES[target_letter_idx]
    octave_offset = (root_letter_idx + letter_offset) // 7

    root_natural_pc = LETTER_PITCH_CLASS[root_letter]
    target_natural_pc = LETTER_PITCH_CLASS[target_letter]
    target_actual_pc = (root_natural_pc + root_acc + semitones) % 12

    acc_needed = (target_actual_pc - target_natural_pc) % 12
    if acc_needed > 2:
        acc_needed -= 12

    if acc_needed > 0:
        target_name = target_letter + '#' * acc_needed
    elif acc_needed < 0:
        target_name = target_letter + 'b' * (-acc_needed)
    else:
        target_name = target_letter

    note = Note.__new__(Note)
    note.name = target_name
    note.octave = root_octave + octave_offset
    return note


def get_scale_notes(root: str, scale_type: str, octave: int = 4) -> List[Note]:
    """
    Get all notes in a scale.

    Args:
        root: Root note name (e.g., 'A', 'F#')
        scale_type: Scale pattern name (e.g., 'natural minor', 'major')
        octave: Starting octave (default 4)

    Returns:
        List of Note objects
    """
    scale = Scale(root=root, pattern_name=scale_type)
    return scale.get_notes(octave=octave)


def get_scale_degree_note(root: str, scale_type: str, degree: int, octave: int = 4) -> Note:
    """
    Get a specific scale degree note.

    Args:
        root: Root note name
        scale_type: Scale pattern name
        degree: Scale degree (1-7)
        octave: Base octave

    Returns:
        The note at that scale degree
    """
    notes = get_scale_notes(root, scale_type, octave)
    # Handle degrees > 7 (octave displacement)
    octave_offset = (degree - 1) // len(notes)
    index = (degree - 1) % len(notes)
    note = notes[index]
    return Note(name=note.name, octave=note.octave + octave_offset)
