"""
Artist data — profiles and blend logic.

Contains:
- ARTIST_PROFILES: 12 artist production profiles (from docs/artist_dna.md)
- generate_artist_blend_local(): deterministic blend of two artist profiles
"""

from typing import Dict, Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from theory import get_progression_chords, NAMED_PROGRESSIONS


# =============================================================================
# Artist profiles (sourced from docs/artist_dna.md)
# =============================================================================

ARTIST_PROFILES = {
    'Massive Attack': {
        'genres': ['trip-hop', 'electronic', 'ambient'],
        'moods': ['dark', 'melancholic', 'mysterious'],
        'key_type': 'minor',
        'elements': [
            'Phrygian-influenced harmony with 2-chord drones',
            'Sparse, minimal arrangements with heavy sub bass',
            'Tribal percussion and slow tempos (70-90 BPM)',
            'Dark, cinematic atmosphere with cavernous reverb',
        ],
        'tempo_range': (70, 90),
        'progression_tags': ['dark', 'tense', 'mysterious'],
    },
    'Portishead': {
        'genres': ['trip-hop', 'electronic'],
        'moods': ['dark', 'nostalgic', 'melancholic'],
        'key_type': 'minor',
        'elements': [
            'Chromatic voice leading and half-diminished chords',
            'Vinyl crackle texture and lo-fi sampling',
            'Jazz-influenced harmony with noir atmosphere',
            'Vocals as lead instrument, everything else serves the vocal',
        ],
        'tempo_range': (70, 95),
        'progression_tags': ['dark', 'noir', 'chromatic'],
    },
    'Skrillex': {
        'genres': ['dubstep', 'edm', 'electronic'],
        'moods': ['aggressive', 'epic', 'dark'],
        'key_type': 'minor',
        'elements': [
            'FM synthesis and 3-layer bass design',
            'Aggressive resampling and granular processing',
            'Extreme dynamic contrast between builds and drops',
            'Short, rhythmic melodic hooks that hit with the drop',
        ],
        'tempo_range': (140, 175),
        'progression_tags': ['aggressive', 'dark', 'epic'],
    },
    'Fred Again..': {
        'genres': ['uk-garage', 'house', 'dance'],
        'moods': ['uplifting', 'happy', 'epic'],
        'key_type': 'major',
        'elements': [
            'Radical simplicity — one melodic idea repeated and layered',
            'Voice memo sampling and found-sound production',
            'Major keys with emotional, community-focused energy',
            'Four-on-the-floor kick with UK garage shuffle',
        ],
        'tempo_range': (125, 140),
        'progression_tags': ['uplifting', 'happy', 'anthemic'],
    },
    'Ben Böhmer': {
        'genres': ['melodic-house', 'progressive', 'ambient'],
        'moods': ['dreamy', 'melancholic', 'ethereal'],
        'key_type': 'minor',
        'elements': [
            'Minor keys with extended chord voicings (9ths, 11ths)',
            'Long, sustained melodic lines that float over the harmony',
            'Soft, rounded kicks with long sub tails',
            'Organic textures blended with analog synth warmth',
        ],
        'tempo_range': (118, 125),
        'progression_tags': ['dreamy', 'melancholic', 'ethereal'],
    },
    'Hooverphonics': {
        'genres': ['dream-pop', 'trip-hop', 'orchestral'],
        'moods': ['dreamy', 'romantic', 'nostalgic'],
        'key_type': 'minor',
        'elements': [
            'Lush orchestration and cinematic string arrangements',
            'Jazz voicings (maj7, min9) with pop structure',
            'Wide stereo field and cinematic reverb',
            'Female vocal-driven with everything supporting the voice',
        ],
        'tempo_range': (80, 110),
        'progression_tags': ['dreamy', 'romantic', 'nostalgic'],
    },
    'Deftones': {
        'genres': ['alternative-metal', 'shoegaze', 'rock'],
        'moods': ['dark', 'dreamy', 'ethereal'],
        'key_type': 'minor',
        'elements': [
            'Modal ambiguity — melodies sit between major and minor',
            'Power chords layered with shoegaze pad textures',
            'Heavy low end contrasted with ethereal, floating vocals',
            'Drop tunings and detuned guitars for weight',
        ],
        'tempo_range': (80, 130),
        'progression_tags': ['dark', 'dreamy', 'ethereal'],
    },
    'Nine Inch Nails': {
        'genres': ['industrial', 'electronic', 'rock'],
        'moods': ['dark', 'tense', 'aggressive'],
        'key_type': 'minor',
        'elements': [
            'Minimalist harmony with tritone relationships',
            'Repetitive, hypnotic patterns building to climax',
            'Industrial texture: distortion, noise, granular synthesis',
            'Quiet-loud dynamics as emotional architecture',
        ],
        'tempo_range': (90, 140),
        'progression_tags': ['dark', 'tense', 'aggressive'],
    },
    'CloZee': {
        'genres': ['world-bass', 'electronic', 'glitch-hop'],
        'moods': ['epic', 'ethereal', 'mysterious'],
        'key_type': 'minor',
        'elements': [
            'World scales (Phrygian, Dorian, Arabic) adapted to electronic context',
            'Classical guitar-influenced melodic phrasing',
            'Organic instrument samples layered with synthesis',
            'Polyrhythmic percussion and world music drum patterns',
        ],
        'tempo_range': (90, 140),
        'progression_tags': ['epic', 'ethereal', 'mysterious'],
    },
    'GRiZ': {
        'genres': ['future-funk', 'electronic', 'hip-hop'],
        'moods': ['groovy', 'happy', 'uplifting'],
        'key_type': 'major',
        'elements': [
            'Mixolydian funk harmony with dominant 7th chords',
            'Live saxophone integration and bluesy melodic lines',
            'Pentatonic runs with soul inflections',
            'Heavy bass with funk guitar chops',
        ],
        'tempo_range': (100, 130),
        'progression_tags': ['groovy', 'happy', 'uplifting'],
    },
    'Deadmau5': {
        'genres': ['progressive-house', 'edm', 'techno'],
        'moods': ['chill', 'dreamy', 'epic'],
        'key_type': 'minor',
        'elements': [
            'Minimal harmonic movement — 2-4 chords maximum',
            'Arrangement-based tension (not harmonic tension)',
            'Long filter sweeps and automation-driven builds',
            'Heavy sidechain pumping as a musical effect',
        ],
        'tempo_range': (125, 130),
        'progression_tags': ['chill', 'dreamy', 'epic'],
    },
    'Sofi Tukker': {
        'genres': ['dance-pop', 'house', 'electronic'],
        'moods': ['happy', 'groovy', 'uplifting'],
        'key_type': 'major',
        'elements': [
            'Brazilian bossa nova rhythms adapted to house music',
            'Polyrhythmic percussion with organic shakers and congas',
            'Multilingual vocals and call-and-response patterns',
            'Bright, major-key harmony with Latin guitar textures',
        ],
        'tempo_range': (120, 130),
        'progression_tags': ['groovy', 'happy', 'uplifting'],
    },
}


# =============================================================================
# Artist blend
# =============================================================================

def generate_artist_blend_local(artist_1: str, artist_2: str) -> Optional[Dict]:
    """
    Generate an artist blend response from two artist profiles.

    Returns {artist_blend, progression, key_type, tempo_range, moods} or None.
    """
    profile_1 = ARTIST_PROFILES.get(artist_1)
    profile_2 = ARTIST_PROFILES.get(artist_2)

    if not profile_1 or not profile_2:
        return None

    from_1 = profile_1['elements'][:2]
    from_2 = profile_2['elements'][:2]

    genres_1 = ', '.join(profile_1['genres'][:2])
    genres_2 = ', '.join(profile_2['genres'][:2])
    moods_combined = list(set(profile_1['moods'] + profile_2['moods']))[:4]

    blend_description = (
        f"A fusion of {artist_1}'s {genres_1} sensibility with {artist_2}'s "
        f"{genres_2} approach. The result is {', '.join(moods_combined[:3])} — "
        f"taking {profile_1['elements'][0].lower().split(' — ')[0] if ' — ' in profile_1['elements'][0] else profile_1['elements'][0].lower()} "
        f"from {artist_1} and combining it with "
        f"{profile_2['elements'][0].lower().split(' — ')[0] if ' — ' in profile_2['elements'][0] else profile_2['elements'][0].lower()} "
        f"from {artist_2}."
    )

    tempo_low = max(profile_1['tempo_range'][0], profile_2['tempo_range'][0])
    tempo_high = min(profile_1['tempo_range'][1], profile_2['tempo_range'][1])
    if tempo_low >= tempo_high:
        midpoint = (
            profile_1['tempo_range'][0] + profile_1['tempo_range'][1] +
            profile_2['tempo_range'][0] + profile_2['tempo_range'][1]
        ) // 4
        tempo_low = midpoint - 10
        tempo_high = midpoint + 10

    key_type = profile_1['key_type'] if profile_1['key_type'] == profile_2['key_type'] else 'minor'

    production_direction = (
        f"Target tempo: {tempo_low}-{tempo_high} BPM. "
        f"Work in a {key_type} key. "
        f"Start with {profile_1['elements'][0].split('—')[0].strip() if '—' in profile_1['elements'][0] else profile_1['elements'][0]} "
        f"as your harmonic foundation, then layer {profile_2['elements'][1].lower()} on top. "
        f"For the low end, lean toward {'heavy sub bass' if any(m in profile_1['moods'] for m in ['dark', 'aggressive']) else 'clean, rounded bass'}. "
        f"Use {'sparse, minimal' if any(m in profile_1['moods'] for m in ['dark', 'mysterious']) else 'layered, textured'} arrangement."
    )

    combined_tags = list(set(profile_1['progression_tags'] + profile_2['progression_tags']))
    best_prog = None
    best_score = -1
    for name, prog in NAMED_PROGRESSIONS.items():
        if prog.key_type != key_type:
            continue
        score = len(set(prog.moods) & set(combined_tags))
        if score > best_score:
            best_score = score
            best_prog = prog

    progression_data = None
    if best_prog:
        try:
            chords = get_progression_chords(best_prog.numerals, 'A', best_prog.key_type, octave=3)
            progression_data = {
                'name': best_prog.name,
                'numerals': best_prog.numerals,
                'key': f'A {best_prog.key_type}',
                'chords': chords,
                'tempo_range': (tempo_low, tempo_high),
                'description': best_prog.description,
                'moods': moods_combined,
                'genres': list(set(profile_1['genres'] + profile_2['genres'])),
            }
        except ValueError:
            pass

    return {
        'artist_blend': {
            'artist_1': artist_1,
            'artist_2': artist_2,
            'blend_description': blend_description,
            'from_artist_1': from_1,
            'from_artist_2': from_2,
            'production_direction': production_direction,
        },
        'progression': progression_data,
        'key_type': key_type,
        'tempo_range': (tempo_low, tempo_high),
        'moods': moods_combined,
    }
