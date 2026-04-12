"""
Sound Engineering Agent — Local response data.

Contains:
- LOCAL_RESPONSES: 9 pre-built structured responses for common SE topics
- KEYWORD_TO_TOPIC: keyword → topic mapping
- generate_sound_engineering_local(): keyword-matched local response function
"""

from typing import Dict, Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logging import log_agent_call


# =============================================================================
# Pre-built responses (structured to match the SE contract)
# =============================================================================

LOCAL_RESPONSES = {
    'sidechain': {
        'summary': 'Sidechain compression ducks one sound (usually bass) when another (usually kick) hits, creating rhythmic pumping.',
        'steps': [
            'Create a new Return track (Cmd+Option+T) and add a Compressor',
            'Set the Compressor sidechain input to your kick track',
            'Set Ratio to 4:1, Attack to 0.1ms, Release to 100-200ms',
            'Route your bass (or pad) to this Return track',
            'Adjust the Threshold until you see 3-6dB of gain reduction on kick hits',
        ],
        'ableton_path': 'Audio Effects → Dynamics → Compressor → enable Sidechain toggle → set Audio From to your kick track',
        'principle': 'Sidechain creates space in the frequency spectrum by briefly reducing competing sounds when the kick hits. This is what gives electronic music that "pumping" feel — the bass breathes with the kick instead of fighting it.',
        'artist_reference': 'Deadmau5 — uses heavy sidechain pumping as a musical effect, not just a mixing tool. The pump IS the groove.',
    },
    'eq': {
        'summary': 'EQ carves frequency space so each element sits in its own range without masking others.',
        'steps': [
            'Add EQ Eight to the track you want to shape',
            'High-pass everything except kick and sub bass at 80-100Hz',
            'Cut before you boost — remove what sounds bad before adding what sounds good',
            'Use a narrow Q (high value) for surgical cuts, wide Q (low value) for gentle shaping',
            'A/B your changes by toggling the EQ on and off',
        ],
        'ableton_path': 'Audio Effects → EQ → EQ Eight',
        'principle': 'Every instrument has a "home" frequency range. EQ removes the frequencies where an instrument doesn\'t belong, so the mix has clarity instead of mud. Think of it as giving each sound its own lane.',
        'artist_reference': 'Massive Attack — extremely clean low-end separation. The sub bass and kick never compete because each is surgically EQ\'d to its own range.',
    },
    'compress': {
        'summary': 'Compression reduces the dynamic range of a signal — making loud parts quieter and quiet parts louder.',
        'steps': [
            'Add Compressor to your track',
            'Start with Ratio 3:1, Attack 10ms, Release 100ms',
            'Lower the Threshold until you see 3-6dB of gain reduction',
            'Use the Makeup Gain to bring the level back up',
            'Listen for the sound becoming more "glued" and consistent',
        ],
        'ableton_path': 'Audio Effects → Dynamics → Compressor',
        'principle': 'Compression controls the difference between the loudest and quietest parts of a sound. Light compression (2:1-4:1) adds consistency and polish. Heavy compression (10:1+) becomes a creative effect — punchy drums, "breathing" pads.',
        'artist_reference': 'Fred Again.. — uses compression creatively on vocal samples to make them sit right in the mix while keeping their raw, emotional quality.',
    },
    'reverb': {
        'summary': 'Reverb adds a sense of space and depth — it simulates the sound of a room, hall, or other environment.',
        'steps': [
            'Create a Return track (Cmd+Option+T) for reverb — never put reverb directly on a track as an insert',
            'Add Reverb to the Return track',
            'Set Decay Time: 1-2s for subtle room, 3-5s for hall, 6+ for ambient wash',
            'Send individual tracks to this Return using the Send knobs',
            'Roll off the low end on the reverb (high-pass at 200-300Hz) to keep the mix clean',
        ],
        'ableton_path': 'Audio Effects → Reverb → Reverb (or use Hybrid Reverb in Live 12)',
        'principle': 'Reverb on a return track (not an insert) means multiple sounds share the same "space," making the mix cohesive. Rolling off the lows on reverb prevents mud — you want the reverb to add air, not weight.',
        'artist_reference': 'Portishead — uses reverb to create cinematic space. The vocals sit in a different "room" than the drums, creating depth and isolation.',
    },
    'automate': {
        'summary': 'Automation records parameter changes over time — filter sweeps, volume rides, effect sends — bringing a static mix to life.',
        'steps': [
            'Enable Automation Mode (A) in Arrangement View',
            'Click the parameter you want to automate (e.g., filter cutoff)',
            'Draw automation curves using breakpoints or freehand',
            'Use automation on filter cutoff for builds: sweep from 200Hz to 16kHz over 4-8 bars before a drop',
            'Automate reverb wet on return tracks: increase into breakdowns, pull back for drops',
        ],
        'ableton_path': 'View → Automation (A) → select parameter from dropdown in each track',
        'principle': 'Static mixes sound lifeless. Automation creates the illusion of a live performance. The golden rule: automate what you want the listener to feel, not what you want them to notice.',
        'artist_reference': 'Ben Böhmer — master of subtle automation. His filter sweeps and reverb rides create seamless transitions that feel organic, not programmed.',
    },
    'filter': {
        'summary': 'Filters remove frequencies above (low-pass) or below (high-pass) a cutoff point, shaping the tone and energy of a sound.',
        'steps': [
            'Add Auto Filter to the track',
            'Choose filter type: Low-pass to darken/mellow, High-pass to thin/brighten',
            'Set the cutoff frequency as your starting point',
            'Add subtle resonance (10-30%) for character at the cutoff point',
            'Automate the cutoff for movement: sweep up into drops, sweep down into breakdowns',
        ],
        'ableton_path': 'Audio Effects → Filters → Auto Filter',
        'principle': 'Filters are the most fundamental sound-shaping tool after volume. A low-pass filter closing down mimics distance or introspection. Opening up mimics energy and arrival. This is why every EDM build uses a filter sweep.',
        'artist_reference': 'Deftones — use low-pass filters on guitars to create that dreamy, underwater quality. The filter IS the mood.',
    },
    'bass': {
        'summary': 'Bass needs its own dedicated frequency space (20-200Hz) and careful management to avoid muddying the entire mix.',
        'steps': [
            'High-pass everything except kick and bass at 80-100Hz',
            'Decide who owns the sub range (30-60Hz): kick or bass, not both',
            'Use sidechain compression to duck the bass when the kick hits',
            'Add subtle saturation to give bass harmonics that translate on small speakers',
            'Check your bass on headphones AND monitors — what sounds right on one may disappear on the other',
        ],
        'ableton_path': 'Use EQ Eight to carve space; use Compressor with sidechain for ducking; use Saturator for harmonics',
        'principle': 'Bass frequencies are omnidirectional and take up huge amounts of headroom. Two bass-heavy sounds playing at once = mud. Clarity in the low end comes from giving each element its own space and using sidechain to prevent overlap.',
        'artist_reference': 'Skrillex — designs bass in layers: sub bass for weight, mid-bass for aggression, and high harmonics for presence. Each layer is EQ\'d to its own range.',
    },
    'kick': {
        'summary': 'The kick drum is the foundation of your beat — it needs punch (2-5kHz), body (80-120Hz), and sub weight (40-60Hz).',
        'steps': [
            'Choose a kick sample that\'s close to your target — processing can\'t fix a bad starting point',
            'EQ: Boost around 60Hz for sub weight, 2-4kHz for click/attack, cut 200-400Hz for tightness',
            'Compress lightly (3:1, fast attack, medium release) for consistency',
            'Sidechain the bass to the kick so they don\'t compete',
            'Layer a top kick (click) with a sub kick (weight) for fullness',
        ],
        'ableton_path': 'Drum Rack → load kick sample → EQ Eight → Compressor',
        'principle': 'The kick anchors every other element. If the kick is clear and punchy, the rest of the mix has a reference point. If the kick is muddy or weak, everything above it suffers.',
        'artist_reference': 'Ben Böhmer — uses soft, rounded kicks with long sub tails. The kick IS the bass in many of his tracks, which is why his mixes feel so clean.',
    },
    'synthesis': {
        'summary': 'Synthesis is building sounds from scratch using oscillators, filters, and modulators instead of using samples.',
        'steps': [
            'Start with Operator or Wavetable in Ableton',
            'Choose a waveform: Saw for bright/rich, Square for hollow/retro, Sine for pure/sub',
            'Shape with a low-pass filter — this is where most of the character comes from',
            'Add an amplitude envelope: Attack for pluck vs pad, Release for tail length',
            'Modulate the filter cutoff with an LFO or envelope for movement',
        ],
        'ableton_path': 'Instruments → Operator (FM synthesis) or Instruments → Wavetable (wavetable synthesis)',
        'principle': 'All electronic sounds start from basic waveforms. The magic is in how you filter, modulate, and process them. Start simple — a saw wave through a low-pass filter with some resonance is the foundation of 80% of synth sounds.',
        'artist_reference': 'CloZee — layers organic textures with synthesized elements. Her sound design often starts with a simple oscillator and gets its character from world-music-inspired modulation patterns.',
    },
}

# Map trigger keywords to response keys
KEYWORD_TO_TOPIC = {
    'sidechain': 'sidechain', 'side-chain': 'sidechain', 'side chain': 'sidechain',
    'eq': 'eq', 'equaliz': 'eq', 'frequency': 'eq',
    'compress': 'compress', 'compressor': 'compress', 'dynamics': 'compress',
    'reverb': 'reverb', 'space': 'reverb', 'room': 'reverb', 'hall': 'reverb',
    'automate': 'automate', 'automation': 'automate', 'lfo': 'automate',
    'filter': 'filter', 'low-pass': 'filter', 'high-pass': 'filter', 'cutoff': 'filter',
    'bass': 'bass', 'sub': 'bass', 'low end': 'bass', 'low-end': 'bass',
    'kick': 'kick',
    'synthesis': 'synthesis', 'synthesiz': 'synthesis', 'synth': 'synthesis',
    'oscillator': 'synthesis', 'sound design': 'synthesis', 'wavetable': 'synthesis',
}


# =============================================================================
# Local response function
# =============================================================================

@log_agent_call
def generate_sound_engineering_local(question: str) -> Optional[Dict]:
    """
    Generate a structured sound engineering response without an API call.

    Returns {summary, steps, ableton_path, principle, artist_reference} or None.
    """
    question_lower = question.lower()

    for keyword, topic in KEYWORD_TO_TOPIC.items():
        if keyword in question_lower:
            response = LOCAL_RESPONSES.get(topic)
            if response:
                return dict(response)

    return None
