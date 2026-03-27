"""
Genre-based chord progressions — curated lookup tables.

This is deterministic data, not LLM generation.
100% accurate, zero API cost.

Usage:
    # Get progressions for a genre
    progressions = get_progressions_by_genre('lo-fi')

    # Get progressions matching a mood
    progressions = get_progressions_by_mood('melancholic')

    # Get a specific named progression
    progression = get_named_progression('andalusian')
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from enum import Enum


class Mood(Enum):
    """Emotional qualities of progressions."""
    MELANCHOLIC = "melancholic"
    HAPPY = "happy"
    UPLIFTING = "uplifting"
    DARK = "dark"
    DREAMY = "dreamy"
    NOSTALGIC = "nostalgic"
    EPIC = "epic"
    CHILL = "chill"
    TENSE = "tense"
    HOPEFUL = "hopeful"
    BITTERSWEET = "bittersweet"
    AGGRESSIVE = "aggressive"
    ETHEREAL = "ethereal"
    GROOVY = "groovy"
    ROMANTIC = "romantic"
    MYSTERIOUS = "mysterious"


@dataclass
class Progression:
    """A chord progression with metadata."""
    name: str
    numerals: List[str]  # Roman numerals: ['i', 'VI', 'III', 'VII']
    key_type: str  # 'major' or 'minor'
    genres: List[str]
    moods: List[str]
    tempo_range: tuple  # (min_bpm, max_bpm)
    description: str
    famous_examples: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


# =============================================================================
# NAMED PROGRESSIONS — Classic patterns with history
# =============================================================================

NAMED_PROGRESSIONS: Dict[str, Progression] = {
    # ---------- Minor Key Progressions ----------
    'andalusian': Progression(
        name="Andalusian Cadence",
        numerals=['i', 'VII', 'VI', 'V'],
        key_type='minor',
        genres=['flamenco', 'classical', 'metal', 'rock'],
        moods=['dark', 'dramatic', 'tense', 'epic'],
        tempo_range=(80, 140),
        description="Descending bass line from tonic to dominant. Spanish/Flamenco flavor.",
        famous_examples=["Hit the Road Jack", "Sultans of Swing intro"],
        tags=['descending', 'spanish', 'dramatic']
    ),

    'minor_plagal': Progression(
        name="Minor Plagal",
        numerals=['i', 'iv', 'i', 'iv'],
        key_type='minor',
        genres=['soul', 'r&b', 'gospel', 'lo-fi'],
        moods=['melancholic', 'soulful', 'introspective'],
        tempo_range=(60, 100),
        description="Simple minor with plagal motion. Deeply emotional.",
        famous_examples=["Many gospel songs"],
        tags=['simple', 'emotional', 'soulful']
    ),

    'minor_line_cliche': Progression(
        name="Minor Line Cliché",
        numerals=['i', 'iM7', 'i7', 'iM6'],
        key_type='minor',
        genres=['jazz', 'film_score', 'musical_theatre'],
        moods=['mysterious', 'noir', 'sophisticated'],
        tempo_range=(60, 120),
        description="Chromatic descending line in minor. James Bond / noir sound.",
        famous_examples=["My Funny Valentine", "Stairway to Heaven intro"],
        tags=['chromatic', 'sophisticated', 'noir']
    ),

    'epic_minor': Progression(
        name="Epic Minor",
        numerals=['i', 'VI', 'III', 'VII'],
        key_type='minor',
        genres=['pop', 'rock', 'edm', 'lo-fi', 'trap'],
        moods=['epic', 'uplifting', 'anthemic', 'nostalgic'],
        tempo_range=(70, 140),
        description="The viral progression. Endless loop that never resolves.",
        famous_examples=["Someone Like You", "Forever Young", "Despacito"],
        tags=['viral', 'loop', 'anthemic', 'unresolved']
    ),

    'tragic': Progression(
        name="Tragic Progression",
        numerals=['i', 'V', 'VI', 'iv'],
        key_type='minor',
        genres=['ballad', 'classical', 'film_score'],
        moods=['melancholic', 'tragic', 'bittersweet'],
        tempo_range=(50, 90),
        description="Deeply sad with the unexpected major V creating tension.",
        famous_examples=["Mad World"],
        tags=['sad', 'dramatic', 'emotional']
    ),

    # ---------- Major Key Progressions ----------
    'axis': Progression(
        name="Axis of Awesome / 4-Chord",
        numerals=['I', 'V', 'vi', 'IV'],
        key_type='major',
        genres=['pop', 'rock', 'country'],
        moods=['uplifting', 'happy', 'anthemic'],
        tempo_range=(80, 140),
        description="The most common pop progression. Works for everything.",
        famous_examples=["Let It Be", "No Woman No Cry", "With or Without You"],
        tags=['universal', 'pop', 'commercial']
    ),

    'pop_punk': Progression(
        name="Pop Punk",
        numerals=['I', 'V', 'vi', 'iii', 'IV'],
        key_type='major',
        genres=['pop_punk', 'emo', 'rock'],
        moods=['energetic', 'nostalgic', 'youthful'],
        tempo_range=(140, 180),
        description="Extended axis with the iii adding momentum.",
        famous_examples=["Blink-182 songs"],
        tags=['energetic', 'driving', 'youthful']
    ),

    '50s': Progression(
        name="50s Doo-Wop",
        numerals=['I', 'vi', 'IV', 'V'],
        key_type='major',
        genres=['oldies', 'doo_wop', 'pop'],
        moods=['nostalgic', 'happy', 'romantic'],
        tempo_range=(80, 130),
        description="Classic 50s sound. Innocent, romantic feel.",
        famous_examples=["Stand By Me", "Earth Angel", "Every Breath You Take"],
        tags=['classic', 'romantic', 'innocent']
    ),

    'pachelbel': Progression(
        name="Pachelbel's Canon",
        numerals=['I', 'V', 'vi', 'iii', 'IV', 'I', 'IV', 'V'],
        key_type='major',
        genres=['classical', 'wedding', 'pop'],
        moods=['uplifting', 'romantic', 'hopeful'],
        tempo_range=(60, 100),
        description="The wedding progression. Timeless and elegant.",
        famous_examples=["Canon in D", "Graduation", "Basket Case"],
        tags=['classical', 'elegant', 'timeless']
    ),

    'sensitive_female': Progression(
        name="Sensitive Female Chord Progression",
        numerals=['vi', 'IV', 'I', 'V'],
        key_type='major',
        genres=['pop', 'singer_songwriter', 'folk'],
        moods=['introspective', 'emotional', 'bittersweet'],
        tempo_range=(70, 110),
        description="Minor start gives depth, but major chords keep it hopeful.",
        famous_examples=["One of Us", "Complicated", "Numb"],
        tags=['emotional', 'singer_songwriter', 'introspective']
    ),

    'royal_road': Progression(
        name="Royal Road / Yon-Go-Roku-San",
        numerals=['IV', 'V', 'iii', 'vi'],
        key_type='major',
        genres=['j-pop', 'anime', 'k-pop'],
        moods=['emotional', 'dramatic', 'nostalgic'],
        tempo_range=(80, 140),
        description="The J-pop/anime emotional climax progression.",
        famous_examples=["Many anime openings/endings"],
        tags=['japanese', 'emotional', 'climactic']
    ),

    'jazz_turnaround': Progression(
        name="Jazz Turnaround",
        numerals=['I', 'vi', 'ii', 'V'],
        key_type='major',
        genres=['jazz', 'r&b', 'neo_soul'],
        moods=['sophisticated', 'smooth', 'groovy'],
        tempo_range=(80, 140),
        description="Classic jazz ending. Circle of fifths motion.",
        famous_examples=["Countless jazz standards"],
        tags=['jazz', 'sophisticated', 'circle_of_fifths']
    ),

    'two_five_one_major': Progression(
        name="ii-V-I Major",
        numerals=['ii', 'V', 'I'],
        key_type='major',
        genres=['jazz', 'neo_soul', 'r&b'],
        moods=['sophisticated', 'smooth', 'resolved'],
        tempo_range=(70, 180),
        description="The jazz resolution. Strong sense of coming home.",
        famous_examples=["Almost every jazz song"],
        tags=['jazz', 'resolution', 'classic']
    ),

    'two_five_one_minor': Progression(
        name="ii-V-i Minor",
        numerals=['ii°', 'V', 'i'],
        key_type='minor',
        genres=['jazz', 'neo_soul', 'bebop'],
        moods=['sophisticated', 'dark', 'tense'],
        tempo_range=(70, 200),
        description="Minor jazz resolution. More tension than major.",
        famous_examples=["Autumn Leaves", "Blue Bossa"],
        tags=['jazz', 'minor', 'tension']
    ),

    'blues': Progression(
        name="12-Bar Blues (simplified)",
        numerals=['I', 'I', 'IV', 'I', 'V', 'IV', 'I', 'V'],
        key_type='major',
        genres=['blues', 'rock', 'jazz'],
        moods=['groovy', 'soulful', 'raw'],
        tempo_range=(70, 140),
        description="The foundation of popular music. Simplified 8-bar version.",
        famous_examples=["Every blues song ever"],
        tags=['blues', 'foundation', 'classic']
    ),

    # ---------- EDM / Electronic ----------
    'edm_anthem': Progression(
        name="EDM Anthem",
        numerals=['vi', 'IV', 'I', 'V'],
        key_type='major',
        genres=['edm', 'house', 'trance', 'future_bass'],
        moods=['uplifting', 'euphoric', 'anthemic'],
        tempo_range=(125, 150),
        description="Festival anthem progression. Maximum uplift.",
        famous_examples=["Wake Me Up", "Levels"],
        tags=['festival', 'euphoric', 'drop']
    ),

    'trance': Progression(
        name="Classic Trance",
        numerals=['i', 'VI', 'VII', 'i'],
        key_type='minor',
        genres=['trance', 'edm', 'uplifting_trance'],
        moods=['uplifting', 'ethereal', 'epic'],
        tempo_range=(130, 145),
        description="Uplifting trance with VII creating lift.",
        famous_examples=["Adagio for Strings"],
        tags=['trance', 'uplifting', 'euphoric']
    ),

    # ---------- Hip-Hop / Trap / Lo-Fi ----------
    'trap_emotional': Progression(
        name="Emotional Trap",
        numerals=['i', 'VI', 'III', 'VII'],
        key_type='minor',
        genres=['trap', 'hip_hop', 'emo_rap'],
        moods=['melancholic', 'dark', 'introspective'],
        tempo_range=(130, 160),
        description="Melodic trap with emotional depth. Half-time feel.",
        famous_examples=["XO Tour Llif3", "Lucid Dreams"],
        tags=['trap', 'melodic', 'emotional']
    ),

    'lofi_chill': Progression(
        name="Lo-Fi Chill",
        numerals=['ii7', 'V7', 'I7', 'vi7'],
        key_type='major',
        genres=['lo-fi', 'chillhop', 'jazz_hop'],
        moods=['chill', 'nostalgic', 'dreamy'],
        tempo_range=(70, 90),
        description="Jazz-influenced lo-fi. 7th chords add warmth.",
        famous_examples=["ChilledCow streams"],
        tags=['lofi', 'jazzy', 'relaxed']
    ),

    'lofi_sad': Progression(
        name="Sad Lo-Fi",
        numerals=['i', 'VI', 'iv', 'VII'],
        key_type='minor',
        genres=['lo-fi', 'chillhop', 'sad_hop'],
        moods=['melancholic', 'nostalgic', 'bittersweet'],
        tempo_range=(70, 85),
        description="Minor lo-fi with melancholic loop. Rainy day vibes.",
        famous_examples=["Lofi hip hop radio"],
        tags=['lofi', 'sad', 'nostalgic']
    ),

    'boom_bap': Progression(
        name="Boom Bap",
        numerals=['i', 'iv', 'i', 'VII'],
        key_type='minor',
        genres=['hip_hop', 'boom_bap', 'old_school'],
        moods=['groovy', 'head-nodding', 'classic'],
        tempo_range=(85, 100),
        description="90s hip-hop foundation. Simple and hard.",
        famous_examples=["Many 90s hip-hop beats"],
        tags=['90s', 'classic', 'sample-based']
    ),
}


# =============================================================================
# GENRE-SPECIFIC COLLECTIONS
# =============================================================================

GENRE_PROGRESSIONS: Dict[str, List[str]] = {
    # Lo-fi / Chill
    'lo-fi': ['lofi_chill', 'lofi_sad', 'epic_minor', 'minor_plagal', 'jazz_turnaround'],
    'chillhop': ['lofi_chill', 'lofi_sad', 'two_five_one_major'],
    'chill': ['lofi_chill', 'lofi_sad', '50s', 'jazz_turnaround'],

    # Hip-Hop / Trap
    'trap': ['trap_emotional', 'epic_minor', 'lofi_sad', 'andalusian'],
    'hip_hop': ['boom_bap', 'trap_emotional', 'lofi_chill', 'minor_plagal'],
    'emo_rap': ['trap_emotional', 'epic_minor', 'tragic', 'lofi_sad'],

    # Electronic / EDM
    'edm': ['edm_anthem', 'axis', 'epic_minor', 'trance'],
    'house': ['edm_anthem', 'axis', 'sensitive_female'],
    'trance': ['trance', 'edm_anthem', 'epic_minor'],
    'future_bass': ['edm_anthem', 'epic_minor', 'royal_road'],

    # Pop / Rock
    'pop': ['axis', '50s', 'sensitive_female', 'pachelbel', 'royal_road'],
    'rock': ['axis', 'andalusian', 'blues', 'pop_punk'],
    'indie': ['sensitive_female', 'epic_minor', '50s'],

    # R&B / Soul
    'r&b': ['jazz_turnaround', 'two_five_one_major', 'lofi_chill', 'minor_plagal'],
    'neo_soul': ['two_five_one_major', 'jazz_turnaround', 'lofi_chill'],
    'soul': ['minor_plagal', 'jazz_turnaround', '50s'],

    # Jazz
    'jazz': ['two_five_one_major', 'two_five_one_minor', 'jazz_turnaround', 'blues'],

    # Other
    'classical': ['pachelbel', 'andalusian', 'minor_line_cliche'],
    'film_score': ['minor_line_cliche', 'tragic', 'epic_minor', 'andalusian'],
    'anime': ['royal_road', 'epic_minor', 'sensitive_female'],
    'j-pop': ['royal_road', 'axis', 'pachelbel'],
    'k-pop': ['royal_road', 'edm_anthem', 'axis'],
}


# =============================================================================
# MOOD-BASED COLLECTIONS
# =============================================================================

MOOD_PROGRESSIONS: Dict[str, List[str]] = {
    'melancholic': ['lofi_sad', 'tragic', 'epic_minor', 'trap_emotional', 'minor_plagal'],
    'happy': ['axis', '50s', 'pop_punk', 'edm_anthem'],
    'uplifting': ['edm_anthem', 'axis', 'trance', 'pachelbel'],
    'dark': ['andalusian', 'minor_line_cliche', 'two_five_one_minor', 'trap_emotional'],
    'dreamy': ['lofi_chill', 'lofi_sad', 'trance', 'sensitive_female'],
    'nostalgic': ['50s', 'lofi_chill', 'lofi_sad', 'epic_minor', 'boom_bap'],
    'epic': ['epic_minor', 'trance', 'andalusian', 'edm_anthem'],
    'chill': ['lofi_chill', 'lofi_sad', 'jazz_turnaround', 'two_five_one_major'],
    'tense': ['andalusian', 'two_five_one_minor', 'minor_line_cliche'],
    'hopeful': ['axis', 'pachelbel', 'sensitive_female', '50s'],
    'bittersweet': ['sensitive_female', 'tragic', 'lofi_sad', 'epic_minor'],
    'aggressive': ['andalusian', 'boom_bap', 'pop_punk'],
    'ethereal': ['trance', 'lofi_chill', 'minor_line_cliche'],
    'groovy': ['jazz_turnaround', 'blues', 'boom_bap', 'lofi_chill'],
    'romantic': ['50s', 'pachelbel', 'sensitive_female'],
    'mysterious': ['minor_line_cliche', 'andalusian', 'two_five_one_minor'],
}


# =============================================================================
# LOOKUP FUNCTIONS
# =============================================================================

def get_named_progression(name: str) -> Optional[Progression]:
    """Get a specific named progression."""
    return NAMED_PROGRESSIONS.get(name.lower().replace(' ', '_').replace('-', '_'))


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
    return list(dict.fromkeys(variations))  # Dedupe while preserving order


def get_progressions_by_genre(genre: str) -> List[Progression]:
    """Get all progressions suitable for a genre."""
    for key in _normalize_key(genre):
        if key in GENRE_PROGRESSIONS:
            progression_names = GENRE_PROGRESSIONS[key]
            return [NAMED_PROGRESSIONS[name] for name in progression_names if name in NAMED_PROGRESSIONS]
    return []


def get_progressions_by_mood(mood: str) -> List[Progression]:
    """Get all progressions matching a mood."""
    for key in _normalize_key(mood):
        if key in MOOD_PROGRESSIONS:
            progression_names = MOOD_PROGRESSIONS[key]
            return [NAMED_PROGRESSIONS[name] for name in progression_names if name in NAMED_PROGRESSIONS]
    return []


def get_progressions_by_mood_and_genre(mood: str, genre: str) -> List[Progression]:
    """Get progressions matching both mood and genre."""
    mood_progs = set(p.name for p in get_progressions_by_mood(mood))
    genre_progs = set(p.name for p in get_progressions_by_genre(genre))
    matching = mood_progs & genre_progs
    return [p for p in NAMED_PROGRESSIONS.values() if p.name in matching]


def search_progressions(
    mood: Optional[str] = None,
    genre: Optional[str] = None,
    key_type: Optional[str] = None,
    tempo: Optional[int] = None,
    tags: Optional[List[str]] = None
) -> List[Progression]:
    """
    Search progressions with multiple filters.

    Args:
        mood: Mood to match (e.g., 'melancholic')
        genre: Genre to match (e.g., 'lo-fi')
        key_type: 'major' or 'minor'
        tempo: BPM to match (must be in tempo_range)
        tags: Tags to match (any match counts)

    Returns:
        List of matching Progressions, sorted by relevance
    """
    results = []

    for prog in NAMED_PROGRESSIONS.values():
        score = 0

        # Genre match
        if genre:
            genre_key = genre.lower().replace(' ', '_').replace('-', '_')
            if genre_key in [g.lower() for g in prog.genres]:
                score += 3
            elif genre_key in GENRE_PROGRESSIONS:
                if any(p == prog for p in get_progressions_by_genre(genre_key)):
                    score += 2

        # Mood match
        if mood:
            mood_key = mood.lower()
            if mood_key in [m.lower() for m in prog.moods]:
                score += 3
            elif mood_key in MOOD_PROGRESSIONS:
                if any(p == prog for p in get_progressions_by_mood(mood_key)):
                    score += 2

        # Key type match
        if key_type:
            if prog.key_type == key_type.lower():
                score += 1

        # Tempo match
        if tempo:
            if prog.tempo_range[0] <= tempo <= prog.tempo_range[1]:
                score += 1

        # Tag match
        if tags:
            matching_tags = set(t.lower() for t in tags) & set(t.lower() for t in prog.tags)
            score += len(matching_tags)

        if score > 0:
            results.append((score, prog))

    # Sort by score descending
    results.sort(key=lambda x: -x[0])
    return [prog for _, prog in results]


def list_all_genres() -> List[str]:
    """Get all available genres."""
    return sorted(GENRE_PROGRESSIONS.keys())


def list_all_moods() -> List[str]:
    """Get all available moods."""
    return sorted(MOOD_PROGRESSIONS.keys())


def list_all_progressions() -> List[str]:
    """Get all named progression names."""
    return sorted(NAMED_PROGRESSIONS.keys())
