"""
Drum patterns — genre-based rhythm lookup tables.

Patterns are defined on a 16th-note grid (16 steps per bar).
Each step is numbered 0-15:
  - Steps 0, 4, 8, 12 = quarter notes (1, 2, 3, 4)
  - Steps 0, 8 = half notes (1, 3)
  - Step 0 = downbeat

This is deterministic data — zero API cost.

Usage:
    # Get patterns for a genre
    patterns = get_patterns_by_genre('trap')

    # Get a specific named pattern
    pattern = get_drum_pattern('trap_basic')

    # Get the hits for a specific instrument
    kicks = pattern.get_hits('kick')
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Union
from enum import Enum


class DrumSound(Enum):
    """Standard drum kit sounds."""
    KICK = "kick"
    SNARE = "snare"
    CLAP = "clap"
    CLOSED_HAT = "closed_hat"
    OPEN_HAT = "open_hat"
    RIM = "rim"
    TOM_HIGH = "tom_high"
    TOM_MID = "tom_mid"
    TOM_LOW = "tom_low"
    CRASH = "crash"
    RIDE = "ride"
    SHAKER = "shaker"
    PERC = "perc"  # Generic percussion
    SNAP = "snap"
    CONGA = "conga"
    BONGO = "bongo"
    COWBELL = "cowbell"


# MIDI note mappings (General MIDI standard)
DRUM_MIDI_NOTES = {
    DrumSound.KICK: 36,        # C1
    DrumSound.SNARE: 38,       # D1
    DrumSound.CLAP: 39,        # D#1
    DrumSound.CLOSED_HAT: 42,  # F#1
    DrumSound.OPEN_HAT: 46,    # A#1
    DrumSound.RIM: 37,         # C#1
    DrumSound.TOM_HIGH: 50,    # D2
    DrumSound.TOM_MID: 47,     # B1
    DrumSound.TOM_LOW: 45,     # A1
    DrumSound.CRASH: 49,       # C#2
    DrumSound.RIDE: 51,        # D#2
    DrumSound.SHAKER: 70,      # A#2
    DrumSound.PERC: 67,        # G2
    DrumSound.SNAP: 40,        # E1
    DrumSound.CONGA: 63,       # D#2
    DrumSound.BONGO: 61,       # C#2
    DrumSound.COWBELL: 56,     # G#1
}


@dataclass
class DrumHit:
    """A single drum hit."""
    sound: DrumSound
    step: int  # 0-15 for 16th notes in one bar
    velocity: int = 100  # 0-127

    @property
    def beat(self) -> float:
        """Get the beat number (1-based, with decimals for subdivisions)."""
        return 1 + (self.step / 4)

    @property
    def beat_str(self) -> str:
        """Human-readable beat position."""
        beat = self.step // 4 + 1
        sixteenth = self.step % 4
        if sixteenth == 0:
            return str(beat)
        elif sixteenth == 2:
            return f"{beat} &"
        elif sixteenth == 1:
            return f"{beat} e"
        else:
            return f"{beat} a"


@dataclass
class DrumPattern:
    """A complete drum pattern."""
    name: str
    hits: List[DrumHit]
    bars: int = 1  # Pattern length in bars
    genres: List[str] = field(default_factory=list)
    tempo_range: tuple = (80, 140)
    swing: int = 0  # 0-100, amount of swing
    description: str = ""
    tags: List[str] = field(default_factory=list)

    def get_hits(self, sound: Union[str, DrumSound]) -> List[DrumHit]:
        """Get all hits for a specific drum sound."""
        if isinstance(sound, str):
            sound = DrumSound(sound)
        return [h for h in self.hits if h.sound == sound]

    def get_steps(self, sound: Union[str, DrumSound]) -> List[int]:
        """Get step numbers where a sound hits."""
        return [h.step for h in self.get_hits(sound)]

    def get_sounds_at_step(self, step: int) -> List[DrumHit]:
        """Get all sounds that hit at a specific step."""
        return [h for h in self.hits if h.step == step]

    @property
    def sounds_used(self) -> Set[DrumSound]:
        """Get all drum sounds used in this pattern."""
        return set(h.sound for h in self.hits)

    def to_grid(self) -> Dict[str, List[int]]:
        """Convert to a grid format showing which steps each sound hits."""
        grid = {}
        for sound in self.sounds_used:
            grid[sound.value] = self.get_steps(sound)
        return grid

    def to_ascii(self) -> str:
        """Generate ASCII visualization of the pattern."""
        lines = []
        lines.append(f"Pattern: {self.name}")
        lines.append("Step:    |1   2   3   4   |")
        lines.append("         |0123456789012345|")

        # Order sounds for display
        sound_order = [
            DrumSound.CLOSED_HAT, DrumSound.OPEN_HAT,
            DrumSound.SNARE, DrumSound.CLAP, DrumSound.RIM,
            DrumSound.KICK,
            DrumSound.TOM_HIGH, DrumSound.TOM_MID, DrumSound.TOM_LOW,
            DrumSound.PERC, DrumSound.SHAKER
        ]

        for sound in sound_order:
            if sound in self.sounds_used:
                steps = self.get_steps(sound)
                row = ""
                for i in range(16 * self.bars):
                    if i in steps:
                        # Get velocity for shading
                        hit = next(h for h in self.hits if h.sound == sound and h.step == i)
                        if hit.velocity >= 100:
                            row += "X"
                        elif hit.velocity >= 70:
                            row += "x"
                        else:
                            row += "."
                    else:
                        row += "-"
                name = sound.value[:10].ljust(10)
                lines.append(f"{name}|{row}|")

        return "\n".join(lines)


def _h(sound: DrumSound, step: int, velocity: int = 100) -> DrumHit:
    """Shorthand for creating a DrumHit."""
    return DrumHit(sound=sound, step=step, velocity=velocity)


# Shortcuts for readability
K = DrumSound.KICK
S = DrumSound.SNARE
C = DrumSound.CLAP
CH = DrumSound.CLOSED_HAT
OH = DrumSound.OPEN_HAT
R = DrumSound.RIM
P = DrumSound.PERC


# =============================================================================
# NAMED DRUM PATTERNS
# =============================================================================

DRUM_PATTERNS: Dict[str, DrumPattern] = {

    # -------------------------------------------------------------------------
    # TRAP / MODERN HIP-HOP
    # -------------------------------------------------------------------------

    'trap_basic': DrumPattern(
        name="Trap Basic",
        hits=[
            # Kick - sparse, syncopated
            _h(K, 0), _h(K, 6), _h(K, 10),
            # Snare on 2 and 4
            _h(S, 4), _h(S, 12),
            # Hi-hats - rolling
            _h(CH, 0), _h(CH, 2), _h(CH, 4), _h(CH, 6),
            _h(CH, 8), _h(CH, 10), _h(CH, 12), _h(CH, 14),
        ],
        genres=['trap', 'hip_hop', 'rap'],
        tempo_range=(130, 170),
        description="Basic trap pattern. Sparse kicks, snare on 2/4, rolling hats.",
        tags=['trap', 'basic', 'rolling_hats']
    ),

    'trap_rolling_hats': DrumPattern(
        name="Trap Rolling Hats",
        hits=[
            # Kick
            _h(K, 0), _h(K, 7), _h(K, 10),
            # Snare
            _h(S, 4), _h(S, 12),
            # Hi-hats - every 16th with accents
            _h(CH, 0, 100), _h(CH, 1, 60), _h(CH, 2, 80), _h(CH, 3, 60),
            _h(CH, 4, 100), _h(CH, 5, 60), _h(CH, 6, 80), _h(CH, 7, 60),
            _h(CH, 8, 100), _h(CH, 9, 60), _h(CH, 10, 80), _h(CH, 11, 60),
            _h(CH, 12, 100), _h(CH, 13, 60), _h(CH, 14, 80), _h(CH, 15, 60),
        ],
        genres=['trap', 'hip_hop'],
        tempo_range=(130, 160),
        description="Trap with continuous 16th-note hi-hats. Velocity creates groove.",
        tags=['trap', 'rolling', '16ths']
    ),

    'trap_triplet_hats': DrumPattern(
        name="Trap Triplet Hats",
        hits=[
            # Kick
            _h(K, 0), _h(K, 6), _h(K, 10),
            # Snare
            _h(S, 4), _h(S, 12),
            # Triplet feel on hats (approximated on 16th grid)
            _h(CH, 0), _h(CH, 3), _h(CH, 5), _h(CH, 8), _h(CH, 11), _h(CH, 13),
            _h(OH, 7),  # Open hat for variation
        ],
        genres=['trap', 'hip_hop'],
        tempo_range=(130, 160),
        description="Trap with triplet hi-hat feel. Creates bounce.",
        tags=['trap', 'triplet', 'bounce']
    ),

    # -------------------------------------------------------------------------
    # BOOM BAP / 90s HIP-HOP
    # -------------------------------------------------------------------------

    'boom_bap_basic': DrumPattern(
        name="Boom Bap Basic",
        hits=[
            # Classic kick pattern
            _h(K, 0), _h(K, 10),
            # Snare on 2 and 4
            _h(S, 4), _h(S, 12),
            # Hats - 8th notes
            _h(CH, 0), _h(CH, 2), _h(CH, 4), _h(CH, 6),
            _h(CH, 8), _h(CH, 10), _h(CH, 12), _h(CH, 14),
        ],
        genres=['boom_bap', 'hip_hop', 'old_school'],
        tempo_range=(85, 100),
        swing=40,
        description="Classic 90s hip-hop. Kick on 1 and 3-and, snare on 2 and 4.",
        tags=['90s', 'classic', 'swing']
    ),

    'boom_bap_syncopated': DrumPattern(
        name="Boom Bap Syncopated",
        hits=[
            # Syncopated kicks
            _h(K, 0), _h(K, 5), _h(K, 10), _h(K, 15),
            # Snare
            _h(S, 4), _h(S, 12),
            # Hats with swing feel
            _h(CH, 0), _h(CH, 2), _h(CH, 4), _h(CH, 6),
            _h(CH, 8), _h(CH, 10), _h(CH, 12), _h(CH, 14),
        ],
        genres=['boom_bap', 'hip_hop'],
        tempo_range=(85, 100),
        swing=50,
        description="More syncopated boom bap with extra kick hits.",
        tags=['syncopated', 'groove', 'swing']
    ),

    # -------------------------------------------------------------------------
    # LO-FI
    # -------------------------------------------------------------------------

    'lofi_basic': DrumPattern(
        name="Lo-Fi Basic",
        hits=[
            # Laid-back kick
            _h(K, 0), _h(K, 10),
            # Snare/rim on 2 and 4
            _h(R, 4), _h(R, 12),
            # Hats - soft
            _h(CH, 0, 70), _h(CH, 2, 50), _h(CH, 4, 70), _h(CH, 6, 50),
            _h(CH, 8, 70), _h(CH, 10, 50), _h(CH, 12, 70), _h(CH, 14, 50),
        ],
        genres=['lo-fi', 'chillhop', 'jazz_hop'],
        tempo_range=(70, 90),
        swing=60,
        description="Mellow lo-fi beat. Rim instead of snare, soft hats, heavy swing.",
        tags=['lofi', 'chill', 'rim']
    ),

    'lofi_dusty': DrumPattern(
        name="Lo-Fi Dusty",
        hits=[
            # Kick with ghost note
            _h(K, 0, 100), _h(K, 7, 60), _h(K, 10, 100),
            # Rim/snare
            _h(R, 4), _h(S, 12, 80),
            # Sparse hats
            _h(CH, 0, 60), _h(CH, 4, 70), _h(CH, 8, 60), _h(CH, 12, 70),
            _h(OH, 14, 50),  # Open hat for breath
        ],
        genres=['lo-fi', 'chillhop'],
        tempo_range=(75, 85),
        swing=70,
        description="Dusty lo-fi with ghost kicks and sparse hits. Very laid back.",
        tags=['lofi', 'dusty', 'sparse']
    ),

    # -------------------------------------------------------------------------
    # HOUSE / ELECTRONIC
    # -------------------------------------------------------------------------

    'house_basic': DrumPattern(
        name="House Basic (Four on the Floor)",
        hits=[
            # Kick on every quarter note
            _h(K, 0), _h(K, 4), _h(K, 8), _h(K, 12),
            # Clap on 2 and 4
            _h(C, 4), _h(C, 12),
            # Off-beat hats
            _h(CH, 2), _h(CH, 6), _h(CH, 10), _h(CH, 14),
        ],
        genres=['house', 'edm', 'disco'],
        tempo_range=(120, 130),
        description="Classic four-on-the-floor. Kick every beat, claps on 2/4, off-beat hats.",
        tags=['four_on_floor', 'club', 'classic']
    ),

    'house_groovy': DrumPattern(
        name="House Groovy",
        hits=[
            # Four on floor
            _h(K, 0), _h(K, 4), _h(K, 8), _h(K, 12),
            # Clap
            _h(C, 4), _h(C, 12),
            # Hats - 16ths with open hat accent
            _h(CH, 0, 80), _h(CH, 2, 100), _h(CH, 4, 80), _h(CH, 6, 100),
            _h(CH, 8, 80), _h(CH, 10, 100), _h(CH, 12, 80),
            _h(OH, 14),  # Open hat before downbeat
        ],
        genres=['house', 'deep_house'],
        tempo_range=(120, 128),
        description="Groovy house with 16th hats and open hat accent.",
        tags=['groovy', '16ths', 'deep']
    ),

    'techno_driving': DrumPattern(
        name="Techno Driving",
        hits=[
            # Pounding kick
            _h(K, 0), _h(K, 4), _h(K, 8), _h(K, 12),
            # Clap on 2 and 4
            _h(C, 4), _h(C, 12),
            # Relentless hats
            _h(CH, 0), _h(CH, 2), _h(CH, 4), _h(CH, 6),
            _h(CH, 8), _h(CH, 10), _h(CH, 12), _h(CH, 14),
            # Ride for texture
            _h(DrumSound.RIDE, 0, 60), _h(DrumSound.RIDE, 8, 60),
        ],
        genres=['techno', 'industrial'],
        tempo_range=(130, 150),
        description="Driving techno. Relentless four-on-floor with 16th hats.",
        tags=['driving', 'hard', 'relentless']
    ),

    # -------------------------------------------------------------------------
    # DRILL
    # -------------------------------------------------------------------------

    'uk_drill': DrumPattern(
        name="UK Drill",
        hits=[
            # Syncopated kicks
            _h(K, 0), _h(K, 5), _h(K, 10), _h(K, 14),
            # Snare with slides
            _h(S, 4), _h(S, 11), _h(S, 12),
            # Hats - 8ths with some 16ths
            _h(CH, 0), _h(CH, 2), _h(CH, 4), _h(CH, 6),
            _h(CH, 8), _h(CH, 10), _h(CH, 12), _h(CH, 14),
            _h(CH, 7, 70),  # Ghost hat
        ],
        genres=['drill', 'uk_drill', 'grime'],
        tempo_range=(140, 145),
        description="UK drill pattern. Syncopated kicks, snare slides.",
        tags=['drill', 'uk', 'dark']
    ),

    'chicago_drill': DrumPattern(
        name="Chicago Drill",
        hits=[
            # Kicks
            _h(K, 0), _h(K, 7), _h(K, 10),
            # Snare
            _h(S, 4), _h(S, 12),
            # Hats - steady 8ths
            _h(CH, 0), _h(CH, 2), _h(CH, 4), _h(CH, 6),
            _h(CH, 8), _h(CH, 10), _h(CH, 12), _h(CH, 14),
        ],
        genres=['drill', 'chicago_drill', 'hip_hop'],
        tempo_range=(60, 70),  # Half-time feel, written as if 130-140
        description="Chicago drill. Slower, more menacing.",
        tags=['drill', 'chicago', 'dark']
    ),

    # -------------------------------------------------------------------------
    # ROCK / ACOUSTIC
    # -------------------------------------------------------------------------

    'rock_basic': DrumPattern(
        name="Rock Basic",
        hits=[
            # Kick on 1 and 3
            _h(K, 0), _h(K, 8),
            # Snare on 2 and 4
            _h(S, 4), _h(S, 12),
            # Hats - 8ths
            _h(CH, 0), _h(CH, 2), _h(CH, 4), _h(CH, 6),
            _h(CH, 8), _h(CH, 10), _h(CH, 12), _h(CH, 14),
        ],
        genres=['rock', 'pop', 'indie'],
        tempo_range=(100, 140),
        description="Standard rock beat. Kick 1/3, snare 2/4.",
        tags=['rock', 'basic', 'standard']
    ),

    'rock_driving': DrumPattern(
        name="Rock Driving",
        hits=[
            # Kick on every beat
            _h(K, 0), _h(K, 4), _h(K, 8), _h(K, 12),
            # Snare on 2 and 4
            _h(S, 4), _h(S, 12),
            # Hats - 8ths, accented
            _h(CH, 0, 100), _h(CH, 2, 70), _h(CH, 4, 100), _h(CH, 6, 70),
            _h(CH, 8, 100), _h(CH, 10, 70), _h(CH, 12, 100), _h(CH, 14, 70),
        ],
        genres=['rock', 'punk', 'alt_rock'],
        tempo_range=(140, 180),
        description="Driving rock beat. Four-on-floor kick for energy.",
        tags=['driving', 'energetic', 'punk']
    ),

    # -------------------------------------------------------------------------
    # R&B / NEO-SOUL
    # -------------------------------------------------------------------------

    'rnb_groove': DrumPattern(
        name="R&B Groove",
        hits=[
            # Syncopated kick
            _h(K, 0), _h(K, 6), _h(K, 10),
            # Snare on 2 and 4
            _h(S, 4), _h(S, 12),
            # Ghost snares
            _h(S, 7, 40), _h(S, 15, 40),
            # Hats - 16ths with accents
            _h(CH, 0, 90), _h(CH, 2, 100), _h(CH, 4, 90), _h(CH, 6, 100),
            _h(CH, 8, 90), _h(CH, 10, 100), _h(CH, 12, 90), _h(CH, 14, 100),
        ],
        genres=['r&b', 'neo_soul', 'soul'],
        tempo_range=(85, 110),
        swing=30,
        description="Groovy R&B beat with ghost snares and syncopated kick.",
        tags=['groovy', 'ghost_notes', 'smooth']
    ),

    # -------------------------------------------------------------------------
    # REGGAETON / DEMBOW
    # -------------------------------------------------------------------------

    'dembow': DrumPattern(
        name="Dembow (Reggaeton)",
        hits=[
            # Kick
            _h(K, 0), _h(K, 6), _h(K, 8), _h(K, 14),
            # Snare on the &'s
            _h(S, 3), _h(S, 7), _h(S, 11), _h(S, 15),
            # Hats
            _h(CH, 0), _h(CH, 4), _h(CH, 8), _h(CH, 12),
        ],
        genres=['reggaeton', 'latin', 'dembow'],
        tempo_range=(90, 100),
        description="Classic dembow riddim. The reggaeton rhythm.",
        tags=['reggaeton', 'latin', 'dembow']
    ),

    # -------------------------------------------------------------------------
    # HALFTIME / EXPERIMENTAL
    # -------------------------------------------------------------------------

    'halftime': DrumPattern(
        name="Halftime",
        hits=[
            # Kick on 1 only
            _h(K, 0),
            # Snare on 3 (halftime feel)
            _h(S, 8),
            # Sparse hats
            _h(CH, 0), _h(CH, 4), _h(CH, 8), _h(CH, 12),
        ],
        genres=['halftime', 'experimental', 'dnb'],
        tempo_range=(140, 170),
        description="Halftime feel. Snare on 3 instead of 2/4.",
        tags=['halftime', 'sparse', 'heavy']
    ),

    'breakbeat': DrumPattern(
        name="Breakbeat",
        hits=[
            # Kick
            _h(K, 0), _h(K, 10),
            # Snare
            _h(S, 4), _h(S, 14),
            # Ghost kicks/snares
            _h(K, 6, 60),
            _h(S, 7, 50),
            # Hats
            _h(CH, 0), _h(CH, 2), _h(CH, 4), _h(CH, 6),
            _h(CH, 8), _h(CH, 10), _h(CH, 12), _h(CH, 14),
        ],
        genres=['breakbeat', 'jungle', 'dnb'],
        tempo_range=(130, 170),
        description="Breakbeat pattern with syncopation.",
        tags=['breaks', 'syncopated', 'funky']
    ),
}


# =============================================================================
# GENRE COLLECTIONS
# =============================================================================

GENRE_DRUM_PATTERNS: Dict[str, List[str]] = {
    'trap': ['trap_basic', 'trap_rolling_hats', 'trap_triplet_hats'],
    'hip_hop': ['boom_bap_basic', 'boom_bap_syncopated', 'trap_basic'],
    'boom_bap': ['boom_bap_basic', 'boom_bap_syncopated'],
    'lo-fi': ['lofi_basic', 'lofi_dusty', 'boom_bap_basic'],
    'lofi': ['lofi_basic', 'lofi_dusty', 'boom_bap_basic'],
    'chillhop': ['lofi_basic', 'lofi_dusty'],
    'house': ['house_basic', 'house_groovy'],
    'deep_house': ['house_groovy', 'house_basic'],
    'techno': ['techno_driving', 'house_basic'],
    'edm': ['house_basic', 'house_groovy', 'techno_driving'],
    'drill': ['uk_drill', 'chicago_drill'],
    'uk_drill': ['uk_drill'],
    'rock': ['rock_basic', 'rock_driving'],
    'pop': ['rock_basic', 'house_basic'],
    'r&b': ['rnb_groove', 'lofi_basic'],
    'neo_soul': ['rnb_groove', 'lofi_dusty'],
    'reggaeton': ['dembow'],
    'latin': ['dembow'],
    'dnb': ['halftime', 'breakbeat'],
    'breakbeat': ['breakbeat'],
    'halftime': ['halftime'],
}


# =============================================================================
# LOOKUP FUNCTIONS
# =============================================================================

def _normalize_key(key: str) -> List[str]:
    """Return possible key variations to try."""
    key = key.lower().strip()
    variations = [
        key,
        key.replace(' ', '_'),
        key.replace(' ', '-'),
        key.replace('-', '_'),
        key.replace('_', '-'),
    ]
    return list(dict.fromkeys(variations))


def get_drum_pattern(name: str) -> Optional[DrumPattern]:
    """Get a specific named drum pattern."""
    key = name.lower().replace(' ', '_').replace('-', '_')
    return DRUM_PATTERNS.get(key)


def get_patterns_by_genre(genre: str) -> List[DrumPattern]:
    """Get all drum patterns suitable for a genre."""
    for key in _normalize_key(genre):
        if key in GENRE_DRUM_PATTERNS:
            pattern_names = GENRE_DRUM_PATTERNS[key]
            return [DRUM_PATTERNS[name] for name in pattern_names if name in DRUM_PATTERNS]
    return []


def list_all_drum_patterns() -> List[str]:
    """Get all named drum pattern names."""
    return sorted(DRUM_PATTERNS.keys())


def list_drum_genres() -> List[str]:
    """Get all available genres for drum patterns."""
    return sorted(GENRE_DRUM_PATTERNS.keys())


def get_pattern_for_tempo(tempo: int, genre: Optional[str] = None) -> List[DrumPattern]:
    """Find patterns suitable for a specific tempo."""
    results = []
    patterns = get_patterns_by_genre(genre) if genre else DRUM_PATTERNS.values()

    for pattern in patterns:
        if pattern.tempo_range[0] <= tempo <= pattern.tempo_range[1]:
            results.append(pattern)

    return results


def explain_pattern(pattern: DrumPattern) -> Dict:
    """
    Get a detailed explanation of a drum pattern.

    Returns a dict with:
    - Human-readable description of each element
    - Which beats each sound hits
    - Suggested feel/groove notes
    """
    explanation = {
        'name': pattern.name,
        'description': pattern.description,
        'tempo': f"{pattern.tempo_range[0]}-{pattern.tempo_range[1]} BPM",
        'swing': f"{pattern.swing}%" if pattern.swing else "None (straight)",
        'elements': {}
    }

    for sound in pattern.sounds_used:
        hits = pattern.get_hits(sound)
        beat_positions = [h.beat_str for h in hits]

        # Describe the role
        if sound == DrumSound.KICK:
            role = "Foundation - drives the groove"
        elif sound == DrumSound.SNARE:
            role = "Backbeat - creates rhythmic tension"
        elif sound == DrumSound.CLAP:
            role = "Accents the backbeat"
        elif sound == DrumSound.CLOSED_HAT:
            role = "Time-keeping - subdivides the beat"
        elif sound == DrumSound.OPEN_HAT:
            role = "Accent/transition marker"
        elif sound == DrumSound.RIM:
            role = "Subtle backbeat (softer than snare)"
        else:
            role = "Percussion texture"

        explanation['elements'][sound.value] = {
            'beats': beat_positions,
            'role': role,
            'hits': len(hits),
            'velocity_range': f"{min(h.velocity for h in hits)}-{max(h.velocity for h in hits)}"
        }

    return explanation
