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
from api.progression_utils import parse_bpm_from_tempo
from agents.production_agent import (
    generate_chord_instructions_local,
    generate_drum_instructions_local,
    ProductionAgent,
)
from agents.teaching_agent import (
    generate_progression_explanation_local,
    generate_rhythm_explanation_local,
    TeachingAgent,
)
from agents.theory_agent import generate_theory_output_local, generate_artist_blend_local
from agents.sound_engineering_agent import generate_sound_engineering_local
from validator import TheoryValidator


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

    # =========================================================================
    # execute() — full pipeline: intent → lookup → agents → response dict
    # =========================================================================

    def execute(self, prompt: str, use_api: bool = False) -> dict:
        """
        Full pipeline entry point. Returns a dict ready for GenerateResponse.

        Local mode (default): keyword intent → local lookup → local agents.
        API mode: Haiku intent → local lookup → LLM agents.
        """
        self.tracker.reset_for_request()

        if use_api:
            orch_result = self.process(prompt)
            intent_type = orch_result.intent.intent_type.value
            confidence = orch_result.intent.confidence
            extracted = orch_result.intent.extracted or {}

            if orch_result.clarification_needed:
                return {
                    "success": True,
                    "intent": intent_type,
                    "confidence": confidence,
                    "clarification_needed": True,
                    "clarification_question": orch_result.clarification_question,
                }

            local_data = orch_result.local_data or {}
        else:
            intent_type, confidence, extracted = self.detect_intent_local(prompt)
            local_data = self._lookup_local(intent_type, extracted, prompt)

        response = self._build_response(intent_type, confidence, extracted, local_data)

        if use_api and local_data:
            self._enhance_with_api(response, local_data)

        summary = self.tracker.summary()
        response["tokens_used"] = summary.get("total_tokens", 0)
        response["cost_usd"] = summary.get("total_cost_usd", 0.0)

        return response

    def _lookup_local(self, intent_type: str, extracted: dict, prompt: str) -> dict:
        """Execute local lookups based on intent type."""
        local_data = {}

        if intent_type in ('mood_vibe', 'theory_request'):
            moods = extracted.get('moods', [])
            genres = extracted.get('genres', [])

            # Key priority: user-specified > genre default > mood default > fallback
            user_key = extracted.get('key')
            if user_key:
                key_parts = user_key.split()
                key_root = key_parts[0]
                key_mode = key_parts[1] if len(key_parts) > 1 else 'minor'
            else:
                minor_genres = {'lo_fi', 'lofi', 'trap', 'hip_hop', 'emo_rap', 'ambient'}
                major_genres = {'pop', 'edm', 'house', 'dance', 'k_pop', 'j_pop'}
                genre_set = set(genres)

                minor_moods = {'melancholic', 'sad', 'dark', 'nostalgic', 'aggressive'}
                major_moods = {'happy', 'uplifting', 'epic', 'romantic'}

                if genre_set & minor_genres:
                    key_root, key_mode = 'A', 'minor'
                elif genre_set & major_genres:
                    key_root, key_mode = 'C', 'major'
                elif set(moods) & minor_moods:
                    key_root, key_mode = 'A', 'minor'
                elif set(moods) & major_moods:
                    key_root, key_mode = 'C', 'major'
                else:
                    key_root, key_mode = 'C', 'major'

            progressions = []
            for mood in moods:
                progs = search_progressions(mood=mood, key_type=key_mode)
                progressions.extend(progs)
            for genre in genres:
                progs = search_progressions(genre=genre, key_type=key_mode)
                progressions.extend(progs)

            if not progressions:
                progs = search_progressions(key_type=key_mode)
                if progs:
                    progressions.extend(progs)
                elif not moods and not genres:
                    progressions = search_progressions(mood='melancholic')

            seen = set()
            unique = []
            for p in progressions:
                if p.name not in seen:
                    seen.add(p.name)
                    unique.append(p)

            local_data['progressions'] = []
            for prog in unique[:3]:
                try:
                    chords = get_progression_chords(prog.numerals, key_root, prog.key_type, octave=3)
                    local_data['progressions'].append({
                        'name': prog.name,
                        'numerals': prog.numerals,
                        'key': f'{key_root} {prog.key_type}',
                        'chords': chords,
                        'tempo_range': prog.tempo_range,
                        'description': prog.description,
                        'moods': prog.moods,
                        'genres': prog.genres,
                    })
                except ValueError:
                    pass

        elif intent_type == 'drum_pattern':
            genres = extracted.get('genres', ['trap'])
            patterns = []
            for genre in genres:
                genre_patterns = get_drum_patterns_by_genre(genre)
                patterns.extend(genre_patterns)

            seen = set()
            unique = []
            for p in patterns:
                if p.name not in seen:
                    seen.add(p.name)
                    unique.append(p)

            local_data['drum_patterns'] = []
            for pattern in unique[:3]:
                local_data['drum_patterns'].append({
                    'name': pattern.name,
                    'description': pattern.description,
                    'tempo_range': pattern.tempo_range,
                    'swing': pattern.swing,
                    'grid': pattern.to_grid(),
                    'genres': pattern.genres,
                })

        elif intent_type == 'sound_engineering':
            se_response = generate_sound_engineering_local(prompt)
            if se_response:
                local_data['sound_engineering_response'] = se_response

        elif intent_type == 'artist_blend':
            artists = extracted.get('artists', [])
            if len(artists) >= 2:
                blend_result = generate_artist_blend_local(artists[0], artists[1])
                if blend_result:
                    local_data['artist_blend'] = blend_result['artist_blend']
                    if blend_result.get('progression'):
                        local_data['progressions'] = [blend_result['progression']]

        return local_data

    @staticmethod
    def _normalize_alternatives(alternatives: Optional[List[Dict]]) -> Optional[List[Dict]]:
        """Normalize alternative labels and chord format for the API response."""
        if not alternatives:
            return alternatives
        out: List[Dict] = []
        for a in alternatives:
            b = dict(a)
            lab = b.get("label") or ""
            b["label"] = lab.replace("_", " ") if isinstance(lab, str) else lab
            ch = b.get("chords") or []
            if ch and isinstance(ch[0], str):
                b["chords"] = [{"name": x, "numeral": ""} for x in ch]
            out.append(b)
        return out

    def _build_response(self, intent_type: str, confidence: float,
                        extracted: dict, local_data: dict) -> dict:
        """Assemble the response dict from local data and agent outputs."""
        response = {
            "success": True,
            "intent": intent_type,
            "confidence": confidence,
            "key_was_specified": 'key' in extracted,
        }

        if not local_data:
            return response

        # --- Progressions ---
        if "progressions" in local_data:
            response["progressions"] = local_data["progressions"]

            if local_data["progressions"]:
                prog = local_data["progressions"][0]
                validation_data = {
                    "key": prog["key"],
                    "chords": [
                        {
                            "numeral": c["numeral"],
                            "name": c["name"],
                            "notes": c["note_names"],
                        }
                        for c in prog["chords"]
                    ]
                }
                validator = TheoryValidator()
                validation_result = validator.validate_progression(validation_data)
                response["validation"] = validation_result.to_dict()

                response["production_steps"] = generate_chord_instructions_local(prog)
                response["teaching_note"] = generate_progression_explanation_local(prog)

                response["progression"] = prog
                response["key"] = prog.get("key")
                response["bpm"] = parse_bpm_from_tempo(
                    prog.get("tempo_range"),
                    prog.get("tempo_suggestion"),
                )
                g = prog.get("genres")
                response["genre_context"] = (
                    ", ".join(g) if isinstance(g, list) else (g if isinstance(g, str) else None)
                )
                response["progression_name"] = prog.get("name") or "–".join(
                    prog.get("numerals") or []
                )

            theory_output = generate_theory_output_local(
                local_data["progressions"],
                intent_data=extracted,
            )
            if theory_output.get("alternatives"):
                response["alternatives"] = self._normalize_alternatives(
                    theory_output["alternatives"]
                )
            if theory_output.get("melody_direction"):
                response["melody_direction"] = theory_output["melody_direction"]

        # --- Drum patterns ---
        if "drum_patterns" in local_data:
            response["drum_patterns"] = local_data["drum_patterns"]

            if local_data["drum_patterns"]:
                pattern = local_data["drum_patterns"][0]

                response["bpm"] = parse_bpm_from_tempo(
                    pattern.get("tempo_range"),
                    pattern.get("tempo_suggestion"),
                )
                g = pattern.get("genres")
                response["genre_context"] = (
                    ", ".join(g) if isinstance(g, list) else (g if isinstance(g, str) else None)
                )
                response["progression_name"] = pattern.get("name")

                if not response.get("production_steps"):
                    response["production_steps"] = generate_drum_instructions_local(pattern)
                else:
                    response["production_steps"] += "\n\n---\n\n" + generate_drum_instructions_local(pattern)

                if not response.get("teaching_note"):
                    response["teaching_note"] = generate_rhythm_explanation_local(pattern)
                else:
                    response["teaching_note"] += "\n\n---\n\n" + generate_rhythm_explanation_local(pattern)

        # --- Sound engineering ---
        if "sound_engineering_response" in local_data:
            response["sound_engineering_response"] = local_data["sound_engineering_response"]

        # --- Artist blend ---
        if "artist_blend" in local_data:
            response["artist_blend"] = local_data["artist_blend"]

        return response

    def _enhance_with_api(self, response: dict, local_data: dict) -> None:
        """Overlay API-powered agent outputs when use_api is True."""
        try:
            production_agent = ProductionAgent(tracker=self.tracker)
            production_result = production_agent.generate_from_local_data(
                local_data,
                user_level=self.user_profile.get("production_level", "beginner"),
            )
            if "chord_instructions" in production_result:
                response["production_steps"] = production_result["chord_instructions"]["markdown"]

            teaching_agent = TeachingAgent(tracker=self.tracker)
            teaching_result = teaching_agent.explain_from_local_data(
                local_data,
                user_level=self.user_profile.get("theory_level", "rusty_intermediate"),
            )
            if "progression_explanation" in teaching_result:
                response["teaching_note"] = teaching_result["progression_explanation"]["explanation"]

        except Exception:
            pass  # Fall back to local output already in response

    # =========================================================================
    # process() — API-mode entry point (Haiku intent detection)
    # =========================================================================

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
