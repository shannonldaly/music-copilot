# Music Theory Module — Deterministic Lookups (Zero API Cost)
#
# This module provides 100% accurate music theory calculations.
# These are mathematical facts, not LLM interpretations.
#
# Use this for: chord spellings, scale construction, interval math, genre progressions
# Use LLM for: creative suggestions, emotional interpretation, teaching

from .core import Note, Interval, transpose, interval_between
from .scales import Scale, SCALE_PATTERNS, get_scale_notes
from .chords import Chord, CHORD_PATTERNS, build_chord, get_chord_notes
from .progressions import roman_to_chord, get_progression_chords
from .genre_progressions import (
    Progression,
    get_named_progression,
    get_progressions_by_genre,
    get_progressions_by_mood,
    get_progressions_by_mood_and_genre,
    search_progressions,
    list_all_genres,
    list_all_moods,
    list_all_progressions,
    NAMED_PROGRESSIONS,
)
from .drum_patterns import (
    DrumPattern,
    DrumHit,
    DrumSound,
    DRUM_MIDI_NOTES,
    get_drum_pattern,
    get_patterns_by_genre as get_drum_patterns_by_genre,
    list_all_drum_patterns,
    list_drum_genres,
    get_pattern_for_tempo,
    explain_pattern,
)

__all__ = [
    # Core
    'Note', 'Interval', 'transpose', 'interval_between',
    # Scales
    'Scale', 'SCALE_PATTERNS', 'get_scale_notes',
    # Chords
    'Chord', 'CHORD_PATTERNS', 'build_chord', 'get_chord_notes',
    # Progressions (Roman numerals)
    'roman_to_chord', 'get_progression_chords',
    # Genre progressions
    'Progression', 'get_named_progression', 'get_progressions_by_genre',
    'get_progressions_by_mood', 'get_progressions_by_mood_and_genre',
    'search_progressions', 'list_all_genres', 'list_all_moods',
    'list_all_progressions', 'NAMED_PROGRESSIONS',
    # Drum patterns
    'DrumPattern', 'DrumHit', 'DrumSound', 'DRUM_MIDI_NOTES',
    'get_drum_pattern', 'get_drum_patterns_by_genre',
    'list_all_drum_patterns', 'list_drum_genres',
    'get_pattern_for_tempo', 'explain_pattern',
]
