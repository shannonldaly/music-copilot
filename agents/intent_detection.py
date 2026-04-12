"""
Intent detection — keyword-based and LLM-based intent classification.

Contains:
- IntentType enum and data classes (ParsedIntent, RoutingPlan, OrchestratorResult)
- All detection constants (keywords, confidence scores, key inference defaults)
- Local keyword detection (detect_intent_local)
- LLM-based detection (parse_intent_with_llm)
- Helper functions (_extract_key_from_prompt, _extract_artists)
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

# Known artists from artist_dna.md (lowercase for matching)
KNOWN_ARTISTS = [
    'massive attack', 'portishead', 'skrillex', 'fred again',
    'ben böhmer', 'ben bohmer', 'hooverphonics', 'deftones',
    'nine inch nails', 'trent reznor', 'nin', 'clozee',
    'griz', 'deadmau5', 'sofi tukker',
]

ARTIST_DISPLAY_NAMES = {
    'massive attack': 'Massive Attack', 'portishead': 'Portishead',
    'skrillex': 'Skrillex', 'fred again': 'Fred Again..',
    'ben böhmer': 'Ben Böhmer', 'ben bohmer': 'Ben Böhmer',
    'hooverphonics': 'Hooverphonics', 'deftones': 'Deftones',
    'nine inch nails': 'Nine Inch Nails', 'trent reznor': 'Nine Inch Nails',
    'nin': 'Nine Inch Nails', 'clozee': 'CloZee', 'griz': 'GRiZ',
    'deadmau5': 'Deadmau5', 'sofi tukker': 'Sofi Tukker',
}

BLEND_PATTERNS = [' meets ', ' x ', ' and ', ' + ', ' with ', ' vs ']

# Intent detection keyword lists
MOOD_KEYWORDS = ['melancholic', 'happy', 'sad', 'dark', 'chill', 'uplifting',
                 'epic', 'dreamy', 'nostalgic', 'aggressive', 'romantic']
GENRE_KEYWORDS = ['lo-fi', 'lofi', 'trap', 'jazz', 'rock', 'pop', 'edm',
                  'house', 'hip-hop', 'hip hop', 'r&b', 'classical', 'ambient']
DRUM_KEYWORDS = ['beat', 'drum', 'rhythm', 'pattern', 'groove']
SOUND_ENGINEERING_KEYWORDS = [
    'mix', 'eq', 'compress', 'reverb', 'automate', 'automation',
    'filter', 'frequency', 'sidechain', 'oscillator', 'synthesis',
    'sound design', 'plugin', 'bass eq', 'kick eq', 'high-pass',
    'low-pass', 'gain staging', 'lufs', 'mastering',
]
PRODUCTION_KEYWORDS = ['how do i', 'how to']

# Confidence scores
CONFIDENCE_ARTIST_BLEND = 0.95
CONFIDENCE_SOUND_ENGINEERING = 0.9
CONFIDENCE_PRODUCTION = 0.8
CONFIDENCE_DRUM = 0.85
CONFIDENCE_ARTIST_REF = 0.9
CONFIDENCE_MOOD_VIBE = 0.9
CONFIDENCE_FALLBACK = 0.5

# Key inference defaults
MINOR_GENRES = {'lo_fi', 'lofi', 'trap', 'hip_hop', 'emo_rap', 'ambient'}
MAJOR_GENRES = {'pop', 'edm', 'house', 'dance', 'k_pop', 'j_pop'}
MINOR_MOODS = {'melancholic', 'sad', 'dark', 'nostalgic', 'aggressive'}
MAJOR_MOODS = {'happy', 'uplifting', 'epic', 'romantic'}
DEFAULT_MINOR_KEY = ('A', 'minor')
DEFAULT_MAJOR_KEY = ('C', 'major')
FALLBACK_KEY = ('C', 'major')

# Query limits
MAX_RESULTS = 3
DEFAULT_OCTAVE = 3


# =============================================================================
# Enums and data classes
# =============================================================================

class IntentType(Enum):
    """Types of user requests."""
    MOOD_VIBE = "mood_vibe"
    ARTIST_REFERENCE = "artist_reference"
    ARTIST_BLEND = "artist_blend"
    THEORY_REQUEST = "theory_request"
    PRODUCTION_QUESTION = "production_question"
    SOUND_ENGINEERING = "sound_engineering"
    FEEDBACK_LOOP = "feedback_loop"
    CLARIFICATION_NEEDED = "clarification_needed"
    DRUM_PATTERN = "drum_pattern"
    UNKNOWN = "unknown"


@dataclass
class ParsedIntent:
    """Result of intent parsing."""
    intent_type: IntentType
    confidence: float
    extracted: Dict[str, Any] = field(default_factory=dict)
    clarification_question: Optional[str] = None


@dataclass
class RoutingPlan:
    """Plan for which agents to invoke."""
    agents: List[str]
    use_local_lookup: bool = False
    local_lookup_type: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrchestratorResult:
    """Result from the Orchestrator."""
    success: bool
    intent: ParsedIntent
    routing: RoutingPlan
    local_data: Optional[Dict] = None
    agent_outputs: Dict[str, Any] = field(default_factory=dict)
    clarification_needed: bool = False
    clarification_question: Optional[str] = None
    token_summary: Optional[Dict] = None
    error: Optional[str] = None


# =============================================================================
# Helper functions
# =============================================================================

def _extract_key_from_prompt(prompt: str) -> Optional[str]:
    """Extract an explicit key signature from a prompt (e.g., 'in C# minor')."""
    pattern = r'\b([A-Ga-g][#b]?)\s+(major|minor|maj|min)\b'
    match = re.search(pattern, prompt, re.IGNORECASE)
    if match:
        note = match.group(1)
        note = note[0].upper() + note[1:]
        mode = match.group(2).lower()
        if mode == 'maj':
            mode = 'major'
        elif mode == 'min':
            mode = 'minor'
        return f"{note} {mode}"
    return None


def _extract_artists(prompt: str) -> List[str]:
    """Extract known artist names from a prompt. Returns canonical display names."""
    prompt_lower = prompt.lower()
    found = []
    for artist in KNOWN_ARTISTS:
        if artist in prompt_lower:
            display = ARTIST_DISPLAY_NAMES.get(artist, artist.title())
            if display not in found:
                found.append(display)
    return found


# =============================================================================
# Local intent detection
# =============================================================================

def detect_intent_local(prompt: str) -> tuple:
    """
    Keyword-based intent detection (no API needed).

    Returns (intent_type, confidence, extracted_data).
    """
    prompt_lower = prompt.lower()
    extracted = {'moods': [], 'genres': []}

    key = _extract_key_from_prompt(prompt)
    if key:
        extracted['key'] = key

    artists = _extract_artists(prompt)
    if artists:
        extracted['artists'] = artists

    for mood in MOOD_KEYWORDS:
        if mood in prompt_lower:
            extracted['moods'].append(mood)

    for genre in GENRE_KEYWORDS:
        if genre in prompt_lower:
            extracted['genres'].append(genre.replace('-', '_'))

    # Priority order: most specific first
    if len(artists) >= 2 and any(bp in prompt_lower for bp in BLEND_PATTERNS):
        return ('artist_blend', CONFIDENCE_ARTIST_BLEND, extracted)

    if any(kw in prompt_lower for kw in SOUND_ENGINEERING_KEYWORDS):
        extracted['question'] = prompt
        return ('sound_engineering', CONFIDENCE_SOUND_ENGINEERING, extracted)

    if any(kw in prompt_lower for kw in PRODUCTION_KEYWORDS):
        return ('production_question', CONFIDENCE_PRODUCTION, extracted)

    if any(kw in prompt_lower for kw in DRUM_KEYWORDS):
        extracted['genres'] = extracted['genres'] or ['trap']
        return ('drum_pattern', CONFIDENCE_DRUM, extracted)

    if len(artists) == 1:
        return ('artist_reference', CONFIDENCE_ARTIST_REF, extracted)

    if extracted['moods'] or extracted['genres'] or extracted.get('key'):
        return ('mood_vibe', CONFIDENCE_MOOD_VIBE, extracted)

    return ('mood_vibe', CONFIDENCE_FALLBACK, {'moods': [], 'genres': []})


# =============================================================================
# LLM intent detection (Haiku)
# =============================================================================

def parse_intent_with_llm(client, tracker, user_input: str) -> ParsedIntent:
    """Parse user intent using Haiku LLM. Called by Orchestrator.process()."""
    from utils.tokens import log_api_call
    from utils.models import HAIKU

    system_prompt = """You are an intent classifier for a music production assistant.

Analyze the user's message and extract:
1. intent_type: One of:
   - mood_vibe, artist_reference, theory_request, production_question,
     feedback_loop, drum_pattern, clarification_needed
2. confidence: 0-1
3. extracted: A dict with any of: moods, genres, key, tempo, artist,
   specific_request, question
4. clarification_question: If clarification_needed, ONE short question

Respond with valid JSON only."""

    user_prompt = f'Classify this request: "{user_input}"'

    response = client.messages.create(
        model=HAIKU,
        max_tokens=500,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
        timeout=30.0,
    )

    log_api_call(
        tracker,
        agent="orchestrator",
        model="haiku",
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        request_type="intent_detection",
    )

    try:
        result = json.loads(response.content[0].text)
        return ParsedIntent(
            intent_type=IntentType(result.get("intent_type", "unknown")),
            confidence=result.get("confidence", 0.5),
            extracted=result.get("extracted", {}),
            clarification_question=result.get("clarification_question"),
        )
    except (json.JSONDecodeError, ValueError):
        return ParsedIntent(
            intent_type=IntentType.UNKNOWN,
            confidence=0.0,
            extracted={"raw_input": user_input},
        )


def determine_routing(intent: ParsedIntent, user_profile: dict) -> RoutingPlan:
    """Determine which agents to invoke based on intent."""
    agents = []
    use_local = False
    local_type = None

    if intent.intent_type == IntentType.THEORY_REQUEST:
        extracted = intent.extracted
        if extracted.get("specific_request") in ["chord", "progression", "scale"]:
            use_local = True
            local_type = "progression"
        agents = ["theory_agent", "validator", "teaching_agent"]

    elif intent.intent_type == IntentType.PRODUCTION_QUESTION:
        agents = ["production_agent", "teaching_agent"]

    elif intent.intent_type in [IntentType.MOOD_VIBE, IntentType.ARTIST_REFERENCE]:
        use_local = True
        local_type = "progression"
        agents = ["theory_agent", "validator", "production_agent", "teaching_agent"]

    elif intent.intent_type == IntentType.DRUM_PATTERN:
        use_local = True
        local_type = "drums"
        agents = ["production_agent", "teaching_agent"]

    elif intent.intent_type == IntentType.FEEDBACK_LOOP:
        agents = ["theory_agent", "validator", "teaching_agent"]

    else:
        agents = ["theory_agent", "teaching_agent"]

    context = {
        "intent": intent.intent_type.value,
        "extracted": intent.extracted,
        "user_profile": user_profile,
    }

    return RoutingPlan(
        agents=agents,
        use_local_lookup=use_local,
        local_lookup_type=local_type,
        context=context,
    )
