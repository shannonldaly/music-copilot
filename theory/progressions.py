"""
Chord progression utilities — Roman numeral to chord mapping.

Maps Roman numerals (i, IV, V7, etc.) to actual chords in a given key.
This is deterministic music theory — no LLM needed.
"""

from dataclasses import dataclass
from typing import List, Dict, Tuple
from .core import Note
from .scales import Scale, get_scale_degree_note
from .chords import Chord, CHORD_PATTERNS

# Roman numeral patterns
# Uppercase = major, lowercase = minor, ° = diminished, + = augmented
ROMAN_NUMERALS = {
    'I': (1, 'major'),
    'i': (1, 'minor'),
    'II': (2, 'major'),
    'ii': (2, 'minor'),
    'III': (3, 'major'),
    'iii': (3, 'minor'),
    'IV': (4, 'major'),
    'iv': (4, 'minor'),
    'V': (5, 'major'),
    'v': (5, 'minor'),
    'VI': (6, 'major'),
    'vi': (6, 'minor'),
    'VII': (7, 'major'),
    'vii': (7, 'minor'),
    'vii°': (7, 'diminished'),
    'viio': (7, 'diminished'),
    'bVII': (7, 'major'),  # Flat VII (common in minor)
    'bVI': (6, 'major'),   # Flat VI (common in minor)
    'bIII': (3, 'major'),  # Flat III (common in minor)

    # Extended numerals - 7th chords
    'I7': (1, 'major7'),
    'Imaj7': (1, 'major7'),
    'IM7': (1, 'major7'),
    'i7': (1, 'minor7'),
    'II7': (2, 'dominant7'),
    'ii7': (2, 'minor7'),
    'iii7': (3, 'minor7'),
    'IV7': (4, 'major7'),
    'IVmaj7': (4, 'major7'),
    'iv7': (4, 'minor7'),
    'V7': (5, 'dominant7'),
    'v7': (5, 'minor7'),
    'vi7': (6, 'minor7'),
    'vii°7': (7, 'half-diminished7'),
    'viio7': (7, 'half-diminished7'),
    'VII7': (7, 'dominant7'),
    'bVII7': (7, 'dominant7'),

    # Minor with major 7 (line cliché chords)
    'iM7': (1, 'minmaj7'),
    'imaj7': (1, 'minmaj7'),
    'iM6': (1, 'm6'),
    'i6': (1, 'm6'),
    'IM6': (1, '6'),
    'I6': (1, '6'),

    # Suspended chords
    'Isus4': (1, 'sus4'),
    'Vsus4': (5, 'sus4'),
    'IVsus2': (4, 'sus2'),

    # Add9 chords
    'Iadd9': (1, 'add9'),
    'iadd9': (1, 'madd9'),
    'IVadd9': (4, 'add9'),
}

# Diatonic chord qualities for each scale degree in major and minor
DIATONIC_CHORDS_MAJOR = {
    1: 'major', 2: 'minor', 3: 'minor', 4: 'major',
    5: 'major', 6: 'minor', 7: 'diminished'
}

DIATONIC_CHORDS_NATURAL_MINOR = {
    1: 'minor', 2: 'diminished', 3: 'major', 4: 'minor',
    5: 'minor', 6: 'major', 7: 'major'
}

DIATONIC_CHORDS_HARMONIC_MINOR = {
    1: 'minor', 2: 'diminished', 3: 'augmented', 4: 'minor',
    5: 'major', 6: 'major', 7: 'diminished'
}


def roman_to_chord(
    numeral: str,
    key: str,
    scale_type: str = 'major',
    octave: int = 3
) -> Tuple[Chord, List[Note]]:
    """
    Convert a Roman numeral to a chord in a given key.

    Args:
        numeral: Roman numeral like 'vi', 'IV', 'V7'
        key: Key root like 'C', 'A', 'F#'
        scale_type: 'major', 'natural minor', 'harmonic minor'
        octave: Base octave for the chord

    Returns:
        Tuple of (Chord object, list of Notes)
    """
    # Handle flat numerals
    flat_modifier = 0
    clean_numeral = numeral
    if numeral.startswith('b'):
        flat_modifier = -1
        clean_numeral = numeral[1:]
    elif numeral.startswith('#'):
        flat_modifier = 1
        clean_numeral = numeral[1:]

    # Look up the numeral
    if numeral in ROMAN_NUMERALS:
        degree, quality = ROMAN_NUMERALS[numeral]
    elif clean_numeral in ROMAN_NUMERALS:
        degree, quality = ROMAN_NUMERALS[clean_numeral]
    else:
        # Try to parse it
        base_numeral = ''.join(c for c in clean_numeral if c.isalpha() and c not in '°+')
        suffix = clean_numeral.replace(base_numeral, '')

        if base_numeral.upper() in ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII']:
            degree = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII'].index(base_numeral.upper()) + 1
            # Determine quality from case and suffix
            is_minor = base_numeral.islower()
            if '°' in suffix or 'o' in suffix:
                quality = 'diminished'
            elif '+' in suffix:
                quality = 'augmented'
            elif '7' in suffix:
                if is_minor:
                    quality = 'minor7'
                else:
                    quality = 'dominant7' if degree == 5 else 'major7'
            else:
                quality = 'minor' if is_minor else 'major'
        else:
            raise ValueError(f"Unknown Roman numeral: {numeral}")

    # Get the root note for this scale degree
    scale = Scale(root=key, pattern_name=scale_type)
    scale_notes = scale.get_notes(octave=octave)

    # Adjust for flat/sharp modifiers
    root_note = scale_notes[degree - 1]
    if flat_modifier != 0:
        from .core import transpose
        root_note = transpose(root_note, flat_modifier)

    # Build the chord
    chord = Chord(root=root_note.name, quality=quality)
    notes = chord.get_notes(octave=root_note.octave)

    return chord, notes


def get_progression_chords(
    progression: List[str],
    key: str,
    scale_type: str = 'major',
    octave: int = 3
) -> List[Dict]:
    """
    Convert a list of Roman numerals to chords.

    Args:
        progression: List of Roman numerals like ['i', 'VI', 'III', 'VII']
        key: Key root like 'A', 'C'
        scale_type: 'major', 'natural minor', etc.
        octave: Base octave

    Returns:
        List of dicts with chord info:
        {
            'numeral': 'i',
            'name': 'Am',
            'root': 'A',
            'quality': 'minor',
            'notes': [Note objects]
        }
    """
    result = []
    for numeral in progression:
        chord, notes = roman_to_chord(numeral, key, scale_type, octave)
        result.append({
            'numeral': numeral,
            'name': chord.name,
            'root': chord.root,
            'quality': chord.quality,
            'notes': notes,
            'note_names': [str(n) for n in notes]
        })
    return result


def analyze_chord_in_key(chord_name: str, key: str, scale_type: str = 'major') -> Dict:
    """
    Analyze what Roman numeral a chord represents in a given key.

    Args:
        chord_name: Chord name like 'Am', 'F', 'G7'
        key: Key root like 'C'
        scale_type: 'major', 'natural minor', etc.

    Returns:
        Dict with analysis:
        {
            'numeral': 'vi',
            'diatonic': True,
            'function': 'tonic substitute'
        }
    """
    from .chords import Chord
    chord = Chord.from_name(chord_name)

    scale = Scale(root=key, pattern_name=scale_type)
    scale_notes = scale.get_note_names()

    # Find which degree this chord root is
    if chord.root not in scale_notes:
        # Check for borrowed chord
        return {
            'numeral': None,
            'diatonic': False,
            'function': 'borrowed/chromatic'
        }

    degree = scale_notes.index(chord.root) + 1

    # Determine expected quality for this degree
    if scale_type in ['major', 'ionian']:
        expected = DIATONIC_CHORDS_MAJOR[degree]
    elif scale_type in ['natural minor', 'minor', 'aeolian']:
        expected = DIATONIC_CHORDS_NATURAL_MINOR[degree]
    elif scale_type == 'harmonic minor':
        expected = DIATONIC_CHORDS_HARMONIC_MINOR[degree]
    else:
        expected = None

    # Build numeral
    numeral_base = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII'][degree - 1]
    if chord.quality in ['minor', 'm', 'min', 'minor7', 'm7']:
        numeral_base = numeral_base.lower()
    if chord.quality in ['diminished', 'dim', '°']:
        numeral_base = numeral_base.lower() + '°'

    # Add 7 if needed
    if '7' in chord.quality:
        numeral_base += '7'

    return {
        'numeral': numeral_base,
        'diatonic': chord.quality == expected,
        'degree': degree,
        'function': _get_harmonic_function(degree, scale_type)
    }


def _get_harmonic_function(degree: int, scale_type: str) -> str:
    """Get the harmonic function of a scale degree."""
    if degree == 1:
        return 'tonic'
    elif degree == 4:
        return 'subdominant'
    elif degree == 5:
        return 'dominant'
    elif degree == 2:
        return 'supertonic (subdominant family)'
    elif degree == 6:
        return 'submediant (tonic substitute)'
    elif degree == 3:
        return 'mediant (tonic family)'
    elif degree == 7:
        return 'leading tone (dominant family)'
    return 'unknown'
