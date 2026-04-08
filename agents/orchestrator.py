"""
Orchestrator Agent — Entry point for all user requests.

Responsibilities:
1. Parse user intent
2. Route to appropriate agents
3. Manage token budget
4. Coordinate agent responses

Cost efficiency strategy:
- Use Haiku for intent detection (10x cheaper than Sonnet)
- Check local lookups BEFORE calling LLM for theory
- Only invoke agents that are needed
- Track all token usage
"""

import json
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum

from anthropic import Anthropic

# Local imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from theory import (
    search_progressions,
    get_progressions_by_genre,
    get_progressions_by_mood,
    get_progression_chords,
    get_drum_patterns_by_genre,
    get_drum_pattern,
)
from utils.tokens import TokenTracker, log_api_call
from utils.models import ModelConfig, TaskType, get_model_for_task, HAIKU, SONNET


# =============================================================================
# Intent detection helpers (moved from api/main.py)
# =============================================================================

# Known artists from artist_dna.md (lowercase for matching)
KNOWN_ARTISTS = [
    'massive attack', 'portishead', 'skrillex', 'fred again',
    'ben böhmer', 'ben bohmer', 'hooverphonics', 'deftones',
    'nine inch nails', 'trent reznor', 'nin', 'clozee',
    'griz', 'deadmau5', 'sofi tukker',
]

# Canonical display names for matched artists
ARTIST_DISPLAY_NAMES = {
    'massive attack': 'Massive Attack', 'portishead': 'Portishead',
    'skrillex': 'Skrillex', 'fred again': 'Fred Again..',
    'ben böhmer': 'Ben Böhmer', 'ben bohmer': 'Ben Böhmer',
    'hooverphonics': 'Hooverphonics', 'deftones': 'Deftones',
    'nine inch nails': 'Nine Inch Nails', 'trent reznor': 'Nine Inch Nails',
    'nin': 'Nine Inch Nails', 'clozee': 'CloZee', 'griz': 'GRiZ',
    'deadmau5': 'Deadmau5', 'sofi tukker': 'Sofi Tukker',
}

# Blend trigger words — patterns like "X meets Y", "X and Y", "X x Y"
BLEND_PATTERNS = [' meets ', ' x ', ' and ', ' + ', ' with ', ' vs ']


def _extract_key_from_prompt(prompt: str) -> Optional[str]:
    """
    Extract an explicit key signature from a prompt.

    Matches patterns like: "in C major", "in C# minor", "in Db major", "in F# minor",
    "C major", "Bb minor", etc.

    Returns a string like "C# major" or None if no key found.
    """
    # Match note letter (A-G), optional sharp/flat (# or b), then major/minor
    pattern = r'\b([A-Ga-g][#b]?)\s+(major|minor|maj|min)\b'
    match = re.search(pattern, prompt, re.IGNORECASE)
    if match:
        note = match.group(1)
        # Normalize: uppercase first letter, preserve sharp/flat
        note = note[0].upper() + note[1:]
        mode = match.group(2).lower()
        # Normalize mode names
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
    confidence: float  # 0-1
    extracted: Dict[str, Any] = field(default_factory=dict)
    # Extracted fields may include:
    # - moods: List[str]
    # - genres: List[str]
    # - key: str (e.g., "A minor")
    # - tempo: int
    # - artist: str
    # - specific_request: str
    # - question: str
    clarification_question: Optional[str] = None


@dataclass
class RoutingPlan:
    """Plan for which agents to invoke."""
    agents: List[str]  # In order of execution
    use_local_lookup: bool = False
    local_lookup_type: Optional[str] = None  # 'progression', 'drums', etc.
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrchestratorResult:
    """Result from the Orchestrator."""
    success: bool
    intent: ParsedIntent
    routing: RoutingPlan
    local_data: Optional[Dict] = None  # Data from local lookups
    agent_outputs: Dict[str, Any] = field(default_factory=dict)
    clarification_needed: bool = False
    clarification_question: Optional[str] = None
    token_summary: Optional[Dict] = None
    error: Optional[str] = None


class Orchestrator:
    """
    Main orchestrator for the Music Co-Pilot.

    Routes user requests to appropriate agents while minimizing API costs.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_config: Optional[ModelConfig] = None,
        token_budget: int = 4000,
    ):
        self._api_key = api_key
        self._client = None  # Lazy — created on first API call
        self.model_config = model_config or ModelConfig()
        self.tracker = TokenTracker(request_budget=token_budget)

        # User profile (hardcoded for v1, will be dynamic in v2)
        self.user_profile = {
            "theory_level": "rusty_intermediate",
            "production_level": "beginner",
            "daw": "Ableton Live 12",
            "preferred_genres": ["lo-fi", "trap", "electronic"],
            "teaching_preference": "explain_why_first_then_how",
        }

    @property
    def client(self):
        """Lazy Anthropic client — only created on first API call."""
        if self._client is None:
            self._client = Anthropic(api_key=self._api_key) if self._api_key else Anthropic()
        return self._client

    def detect_intent_local(self, prompt: str) -> tuple:
        """
        Keyword-based intent detection (no API needed).

        Returns (intent_type, confidence, extracted_data).
        """
        prompt_lower = prompt.lower()

        # Keywords for each intent
        mood_keywords = ['melancholic', 'happy', 'sad', 'dark', 'chill', 'uplifting',
                         'epic', 'dreamy', 'nostalgic', 'aggressive', 'romantic']
        genre_keywords = ['lo-fi', 'lofi', 'trap', 'jazz', 'rock', 'pop', 'edm',
                          'house', 'hip-hop', 'hip hop', 'r&b', 'classical', 'ambient']
        drum_keywords = ['beat', 'drum', 'rhythm', 'pattern', 'groove']
        sound_engineering_keywords = [
            'mix', 'eq', 'compress', 'reverb', 'automate', 'automation',
            'filter', 'frequency', 'sidechain', 'oscillator', 'synthesis',
            'sound design', 'plugin', 'bass eq', 'kick eq', 'high-pass',
            'low-pass', 'gain staging', 'lufs', 'mastering',
        ]
        production_keywords = ['how do i', 'how to']

        extracted = {'moods': [], 'genres': []}

        # Extract explicit key if specified
        key = _extract_key_from_prompt(prompt)
        if key:
            extracted['key'] = key

        # Extract artists
        artists = _extract_artists(prompt)
        if artists:
            extracted['artists'] = artists

        # Check for moods
        for mood in mood_keywords:
            if mood in prompt_lower:
                extracted['moods'].append(mood)

        # Check for genres
        for genre in genre_keywords:
            if genre in prompt_lower:
                extracted['genres'].append(genre.replace('-', '_'))

        # --- Determine intent type (order matters: most specific first) ---

        # Artist blend: two or more artists + a blend trigger word
        if len(artists) >= 2 and any(bp in prompt_lower for bp in BLEND_PATTERNS):
            return ('artist_blend', 0.95, extracted)

        # Sound engineering: specific mixing/production technique questions
        if any(kw in prompt_lower for kw in sound_engineering_keywords):
            extracted['question'] = prompt
            return ('sound_engineering', 0.9, extracted)

        # General production question (how-to without a specific SE keyword)
        if any(kw in prompt_lower for kw in production_keywords):
            return ('production_question', 0.8, extracted)

        # Drum patterns
        if any(kw in prompt_lower for kw in drum_keywords):
            extracted['genres'] = extracted['genres'] or ['trap']
            return ('drum_pattern', 0.85, extracted)

        # Single artist reference (not a blend)
        if len(artists) == 1:
            return ('artist_reference', 0.9, extracted)

        # Mood/genre/key
        if extracted['moods'] or extracted['genres'] or extracted.get('key'):
            return ('mood_vibe', 0.9, extracted)

        # Default
        return ('mood_vibe', 0.5, {'moods': [], 'genres': []})

    def process(self, user_input: str, session_history: Optional[List[Dict]] = None) -> OrchestratorResult:
        """
        Main entry point. Process a user request.

        Args:
            user_input: The user's message
            session_history: Optional list of previous interactions

        Returns:
            OrchestratorResult with all outputs
        """
        # Reset token tracking for this request
        self.tracker.reset_for_request()

        # Step 1: Parse intent (uses Haiku - cheap)
        intent = self._parse_intent(user_input)

        # Step 2: Check if clarification needed
        if intent.intent_type == IntentType.CLARIFICATION_NEEDED:
            return OrchestratorResult(
                success=True,
                intent=intent,
                routing=RoutingPlan(agents=[]),
                clarification_needed=True,
                clarification_question=intent.clarification_question,
                token_summary=self.tracker.summary(),
            )

        # Step 3: Determine routing
        routing = self._determine_routing(intent)

        # Step 4: Execute local lookups if applicable (FREE)
        local_data = None
        if routing.use_local_lookup:
            local_data = self._execute_local_lookup(intent, routing)

        # Step 5: If local data is sufficient, we may skip some agents
        # For now, we'll still call agents but pass them the local data

        return OrchestratorResult(
            success=True,
            intent=intent,
            routing=routing,
            local_data=local_data,
            token_summary=self.tracker.summary(),
        )

    def _parse_intent(self, user_input: str) -> ParsedIntent:
        """
        Parse user intent using Haiku (cheap, fast).

        This is a classification task - perfect for a smaller model.
        """
        system_prompt = """You are an intent classifier for a music production assistant.

Analyze the user's message and extract:
1. intent_type: One of:
   - mood_vibe: User describes a feeling, genre, atmosphere (e.g., "something melancholic", "rainy day vibes")
   - artist_reference: User names an artist or track (e.g., "something like Bon Iver")
   - theory_request: User asks for specific music theory (e.g., "give me a ii-V-I in C major")
   - production_question: User asks about Ableton or production techniques
   - feedback_loop: User reacts to previous output (e.g., "I like that but darker")
   - drum_pattern: User asks for drum/beat patterns (e.g., "give me a trap beat")
   - clarification_needed: Input is too vague or contradictory

2. confidence: 0-1 how confident you are

3. extracted: A dict with any of:
   - moods: List of mood words (melancholic, happy, dark, chill, etc.)
   - genres: List of genres (lo-fi, trap, jazz, house, etc.)
   - key: Key signature if mentioned (e.g., "A minor", "C major")
   - tempo: BPM if mentioned
   - artist: Artist name if mentioned
   - specific_request: Any specific theory request (e.g., "ii-V-I", "sus4 chords")
   - question: The actual question if production_question

4. clarification_question: If clarification_needed, provide ONE short clarifying question

Respond with valid JSON only."""

        user_prompt = f"Classify this request: \"{user_input}\""

        response = self.client.messages.create(
            model=HAIKU,
            max_tokens=500,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        # Log the API call
        log_api_call(
            self.tracker,
            agent="orchestrator",
            model="haiku",
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            request_type="intent_detection"
        )

        # Parse the response
        try:
            result = json.loads(response.content[0].text)
            return ParsedIntent(
                intent_type=IntentType(result.get("intent_type", "unknown")),
                confidence=result.get("confidence", 0.5),
                extracted=result.get("extracted", {}),
                clarification_question=result.get("clarification_question"),
            )
        except (json.JSONDecodeError, ValueError) as e:
            # Fallback if parsing fails
            return ParsedIntent(
                intent_type=IntentType.UNKNOWN,
                confidence=0.0,
                extracted={"raw_input": user_input},
            )

    def _determine_routing(self, intent: ParsedIntent) -> RoutingPlan:
        """
        Determine which agents to invoke based on intent.

        Routing rules (from CLAUDE.md):
        - Simple theory request → Theory Agent + Validator + Teaching Agent
        - Production question → Production Agent + Teaching Agent
        - Mood/vibe/artist → Theory Agent + Validator + Production Agent + Teaching Agent
        - Drum pattern → Local lookup + Production Agent + Teaching Agent
        """
        agents = []
        use_local = False
        local_type = None
        context = {}

        if intent.intent_type == IntentType.THEORY_REQUEST:
            # Check if we can use local lookup
            extracted = intent.extracted
            if extracted.get("specific_request") in ["chord", "progression", "scale"]:
                use_local = True
                local_type = "progression"
            agents = ["theory_agent", "validator", "teaching_agent"]

        elif intent.intent_type == IntentType.PRODUCTION_QUESTION:
            agents = ["production_agent", "teaching_agent"]

        elif intent.intent_type in [IntentType.MOOD_VIBE, IntentType.ARTIST_REFERENCE]:
            # These can often use local lookups for progressions
            use_local = True
            local_type = "progression"
            agents = ["theory_agent", "validator", "production_agent", "teaching_agent"]

        elif intent.intent_type == IntentType.DRUM_PATTERN:
            use_local = True
            local_type = "drums"
            agents = ["production_agent", "teaching_agent"]

        elif intent.intent_type == IntentType.FEEDBACK_LOOP:
            # Needs previous context
            agents = ["theory_agent", "validator", "teaching_agent"]

        else:
            # Unknown - try theory agent
            agents = ["theory_agent", "teaching_agent"]

        # Add extracted data to context
        context["intent"] = intent.intent_type.value
        context["extracted"] = intent.extracted
        context["user_profile"] = self.user_profile

        return RoutingPlan(
            agents=agents,
            use_local_lookup=use_local,
            local_lookup_type=local_type,
            context=context,
        )

    def _execute_local_lookup(self, intent: ParsedIntent, routing: RoutingPlan) -> Optional[Dict]:
        """
        Execute local lookups (FREE - no API cost).

        This is where we save the most money - by not calling the LLM
        for things we can compute deterministically.
        """
        extracted = intent.extracted
        result = {}

        if routing.local_lookup_type == "progression":
            # Try to find matching progressions
            moods = extracted.get("moods", [])
            genres = extracted.get("genres", [])

            # Use our local progression database
            progressions = []

            if moods and genres:
                # Search with both filters
                for mood in moods:
                    for genre in genres:
                        progs = search_progressions(mood=mood, genre=genre)
                        progressions.extend(progs)
            elif moods:
                for mood in moods:
                    progs = get_progressions_by_mood(mood)
                    progressions.extend(progs)
            elif genres:
                for genre in genres:
                    progs = get_progressions_by_genre(genre)
                    progressions.extend(progs)

            # Deduplicate
            seen = set()
            unique_progressions = []
            for p in progressions:
                if p.name not in seen:
                    seen.add(p.name)
                    unique_progressions.append(p)

            if unique_progressions:
                # Take top 3
                top_progressions = unique_progressions[:3]

                # Determine key (default to A minor for minor progressions)
                key = extracted.get("key", "A")
                if not key:
                    key = "A"
                # Extract just the note
                key_note = key.split()[0] if " " in key else key

                result["progressions"] = []
                for prog in top_progressions:
                    try:
                        # Convert to actual chords
                        chords = get_progression_chords(
                            prog.numerals,
                            key_note,
                            prog.key_type,
                            octave=3
                        )
                        result["progressions"].append({
                            "name": prog.name,
                            "numerals": prog.numerals,
                            "key": f"{key_note} {prog.key_type}",
                            "chords": chords,
                            "tempo_range": prog.tempo_range,
                            "description": prog.description,
                            "moods": prog.moods,
                            "genres": prog.genres,
                        })
                    except ValueError:
                        # Skip progressions with unsupported numerals
                        # (e.g., very extended jazz chords)
                        pass

        elif routing.local_lookup_type == "drums":
            # Look up drum patterns
            genres = extracted.get("genres", [])

            patterns = []
            for genre in genres:
                genre_patterns = get_drum_patterns_by_genre(genre)
                patterns.extend(genre_patterns)

            # Deduplicate
            seen = set()
            unique_patterns = []
            for p in patterns:
                if p.name not in seen:
                    seen.add(p.name)
                    unique_patterns.append(p)

            if unique_patterns:
                result["drum_patterns"] = []
                for pattern in unique_patterns[:3]:
                    result["drum_patterns"].append({
                        "name": pattern.name,
                        "description": pattern.description,
                        "tempo_range": pattern.tempo_range,
                        "swing": pattern.swing,
                        "grid": pattern.to_grid(),
                        "ascii": pattern.to_ascii(),
                        "genres": pattern.genres,
                    })

        return result if result else None


# =============================================================================
# Convenience function for quick testing
# =============================================================================

def quick_process(user_input: str, api_key: Optional[str] = None) -> OrchestratorResult:
    """Quick way to process a request without setting up an Orchestrator instance."""
    orchestrator = Orchestrator(api_key=api_key)
    return orchestrator.process(user_input)


if __name__ == "__main__":
    # Simple test
    import os

    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Note: ANTHROPIC_API_KEY not set. Intent detection will fail.")
        print("Testing local lookup only...\n")

        # Test local lookups directly
        from theory import search_progressions, get_drum_patterns_by_genre

        print("=== Local Lookup Test ===\n")

        print("Searching: melancholic + lo-fi")
        progs = search_progressions(mood="melancholic", genre="lo-fi")
        for p in progs[:2]:
            print(f"  • {p.name}: {p.numerals}")

        print("\nSearching: trap drums")
        patterns = get_drum_patterns_by_genre("trap")
        for p in patterns[:2]:
            print(f"  • {p.name}")
            print(f"    {p.description}")

    else:
        print("=== Orchestrator Test ===\n")

        orchestrator = Orchestrator()

        test_inputs = [
            "give me something melancholic and lo-fi",
            "I need a trap beat",
            "how do I sidechain my bass to the kick in Ableton?",
        ]

        for inp in test_inputs:
            print(f"Input: \"{inp}\"")
            result = orchestrator.process(inp)
            print(f"  Intent: {result.intent.intent_type.value}")
            print(f"  Confidence: {result.intent.confidence}")
            print(f"  Extracted: {result.intent.extracted}")
            print(f"  Routing: {result.routing.agents}")
            print(f"  Local lookup: {result.routing.use_local_lookup}")
            if result.local_data:
                print(f"  Local data keys: {list(result.local_data.keys())}")
            print(f"  Tokens used: {result.token_summary['total_tokens']}")
            print(f"  Cost: ${result.token_summary['total_cost_usd']:.6f}")
            print()
