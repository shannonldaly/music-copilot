"""
Teaching Agent — Explains the "why" behind music theory.

Role: Provides educational context that helps the user understand
music theory concepts, not just follow instructions blindly.

Adapts to user level:
- Beginner: Explain everything, use analogies
- Intermediate: Focus on the interesting parts
- Advanced: Brief notes, focus on nuance

Adapts over time:
- If user skips explanations → shorten them
- If user asks follow-ups → go deeper
"""

import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from pathlib import Path

from anthropic import Anthropic

# Local imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.tokens import TokenTracker, log_api_call
from utils.models import ModelConfig, TaskType, get_model_for_task, SONNET


@dataclass
class TeachingNote:
    """A teaching explanation."""
    title: str
    explanation: str
    key_concepts: List[str]
    why_it_works: str
    try_this: Optional[str] = None  # Interactive suggestion
    go_deeper: Optional[str] = None  # For curious users


class TeachingAgent:
    """
    Generates educational explanations for music theory concepts.

    Explains:
    - Why a progression sounds the way it does
    - The theory behind chord choices
    - How to think about music, not just execute it
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_config: Optional[ModelConfig] = None,
        tracker: Optional[TokenTracker] = None,
    ):
        self.client = Anthropic(api_key=api_key) if api_key else Anthropic()
        self.model_config = model_config or ModelConfig()
        self.tracker = tracker

        # Load grounding document
        self.grounding_doc = self._load_grounding_doc()

    def _load_grounding_doc(self) -> str:
        """Load music theory doc for grounding."""
        doc_path = Path(__file__).parent.parent / "docs" / "music_theory.md"
        if doc_path.exists():
            content = doc_path.read_text()
            return content[:4000] + "\n[... truncated for context ...]"
        return ""

    def explain_progression(
        self,
        progression_data: Dict,
        user_level: str = "beginner",
        detail_level: str = "normal",  # "brief", "normal", "deep"
    ) -> Dict:
        """
        Explain why a chord progression works.

        Args:
            progression_data: The progression with chords and metadata
            user_level: User's theory level
            detail_level: How much detail to provide

        Returns:
            Dict with explanation and teaching points
        """
        system_prompt = self._build_system_prompt(user_level, detail_level)
        user_prompt = self._build_progression_prompt(progression_data)

        response = self.client.messages.create(
            model=get_model_for_task(TaskType.TEACHING, self.model_config),
            max_tokens=800,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        if self.tracker:
            log_api_call(
                self.tracker,
                agent="teaching_agent",
                model="sonnet",
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                request_type="explain_progression"
            )

        return {
            "explanation": response.content[0].text,
            "progression": progression_data.get("name", ""),
            "detail_level": detail_level,
        }

    def explain_concept(
        self,
        concept: str,
        context: Optional[Dict] = None,
        user_level: str = "beginner",
    ) -> Dict:
        """
        Explain a music theory concept.

        Args:
            concept: The concept to explain (e.g., "voice leading", "modal interchange")
            context: Optional context (current key, progression, etc.)
            user_level: User's theory level

        Returns:
            Dict with explanation
        """
        system_prompt = self._build_system_prompt(user_level, "normal")

        context_str = ""
        if context:
            context_str = f"\nContext: {json.dumps(context)}"

        user_prompt = f"""Explain this music theory concept: "{concept}"
{context_str}

Keep it practical and relevant to production. Use examples the user can try in their DAW."""

        response = self.client.messages.create(
            model=get_model_for_task(TaskType.TEACHING, self.model_config),
            max_tokens=600,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        if self.tracker:
            log_api_call(
                self.tracker,
                agent="teaching_agent",
                model="sonnet",
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                request_type="explain_concept"
            )

        return {
            "concept": concept,
            "explanation": response.content[0].text,
        }

    def explain_from_local_data(
        self,
        local_data: Dict,
        user_level: str = "beginner",
        detail_level: str = "normal",
    ) -> Dict:
        """
        Generate teaching content from orchestrator's local data.

        Main entry point when called from orchestrator.
        """
        results = {}

        if "progressions" in local_data and local_data["progressions"]:
            prog = local_data["progressions"][0]
            results["progression_explanation"] = self.explain_progression(
                prog, user_level, detail_level
            )

        if "drum_patterns" in local_data and local_data["drum_patterns"]:
            pattern = local_data["drum_patterns"][0]
            results["rhythm_explanation"] = self._explain_rhythm_local(pattern)

        return results

    def _explain_rhythm_local(self, pattern_data: Dict) -> Dict:
        """Generate local rhythm explanation (no API)."""
        name = pattern_data.get("name", "Pattern")
        description = pattern_data.get("description", "")
        swing = pattern_data.get("swing", 0)
        grid = pattern_data.get("grid", {})

        explanation = generate_rhythm_explanation_local(pattern_data)

        return {
            "pattern": name,
            "explanation": explanation,
        }

    def _build_system_prompt(self, user_level: str, detail_level: str) -> str:
        """Build system prompt for teaching."""
        level_style = {
            "beginner": """
- Use simple language, avoid jargon
- Use analogies and real-world comparisons
- Explain terms before using them
- Focus on the emotional effect, then the theory
- Give one "try this" suggestion they can do in their DAW""",
            "intermediate": """
- Assume basic chord and scale knowledge
- Focus on the interesting/non-obvious aspects
- Connect to genres and artists they might know
- Include one deeper concept they can explore""",
            "advanced": """
- Be concise, focus on nuance
- Mention advanced concepts (voice leading, modal interchange)
- Reference theory that might inform creative choices
- Skip basics, highlight what's unique""",
        }

        detail_guidance = {
            "brief": "Keep it to 2-3 sentences. Hit the key point only.",
            "normal": "Provide a balanced explanation. 1-2 paragraphs.",
            "deep": "Go into detail. Explain the theory thoroughly with examples.",
        }

        return f"""You are a Teaching Agent for a music co-pilot. Your job is to explain the "why" behind music theory — helping a music producer understand, not just execute.

USER LEVEL: {user_level}
{level_style.get(user_level, level_style["beginner"])}

DETAIL LEVEL: {detail_level}
{detail_guidance.get(detail_level, detail_guidance["normal"])}

TONE:
- Encouraging, not condescending
- Practical, not academic
- Connected to real music and production
- Always explain *why* before *what*

Never say "simply" or "just" — these words minimize the user's learning process.

GROUNDING (Music Theory):
{self.grounding_doc[:1500] if self.grounding_doc else "Standard music theory principles."}
"""

    def _build_progression_prompt(self, progression_data: Dict) -> str:
        """Build prompt for progression explanation."""
        name = progression_data.get("name", progression_data.get("progression_name", ""))
        key = progression_data.get("key", "")
        numerals = progression_data.get("numerals", [])
        moods = progression_data.get("moods", [])
        description = progression_data.get("description", "")
        chords = progression_data.get("chords", [])

        chord_names = [c.get("name", "") for c in chords] if chords else []

        return f"""Explain why this chord progression works:

**Progression**: {name}
**Key**: {key}
**Numerals**: {' → '.join(numerals) if numerals else 'N/A'}
**Chords**: {' → '.join(chord_names) if chord_names else 'N/A'}
**Moods**: {', '.join(moods) if moods else 'N/A'}
**Description**: {description}

Explain:
1. Why does this progression create the mood it does?
2. What's the theory behind the chord choices?
3. One thing to try: a variation or experiment

Keep it practical and encouraging."""


# =============================================================================
# Local generation (no API) for simple explanations
# =============================================================================

def generate_progression_explanation_local(progression_data: Dict) -> str:
    """
    Generate a basic progression explanation without API call.

    Use for common progressions where we have pre-written explanations.
    """
    name = progression_data.get("name", "")
    numerals = progression_data.get("numerals", [])
    key = progression_data.get("key", "")
    moods = progression_data.get("moods", [])
    description = progression_data.get("description", "")

    # Pre-written explanations for common progressions
    explanations = {
        "epic_minor": """
**Why It Works**

This is one of the most emotionally powerful progressions in modern music. Starting on the minor i chord establishes a melancholic foundation, then moving to the VI (major) creates an unexpected lift — your ear expects minor but gets major, which feels like hope breaking through.

The III chord continues this major-key brightness, and the VII keeps the energy elevated without resolving back home. That's the magic: *it never fully resolves*. Your ear keeps waiting for the i to return, which creates that looping, hypnotic quality perfect for lo-fi, trap, and emotional pop.

**Key Concept**: The progression avoids the V chord entirely, which would create a strong pull back to i. By using VII instead, tension stays suspended.

**Try This**: Play just the first two chords (i → VI) repeatedly. Notice how emotional that single change feels? That's the heart of the progression.
""",
        "sad_lo-fi": """
**Why It Works**

This progression uses the plagal relationship (i → iv) which has been associated with sadness and introspection for centuries — it's the "Amen" cadence from church music, but in a minor key.

The VI chord (major) provides a moment of brightness, but it's fleeting. The VII chord creates forward motion without the strong resolution a V chord would provide. The result is a progression that feels like it's searching for something but never quite finding it — perfect for lo-fi's nostalgic, contemplative mood.

**Key Concept**: The iv chord (minor subdominant) is what makes this feel particularly wistful. Compare it to IV (major) — the minor version adds melancholy.

**Try This**: Slow the tempo to 70 BPM and add a vinyl crackle effect. Notice how the same chords feel different at different tempos.
""",
        "andalusian": """
**Why It Works**

The Andalusian cadence is centuries old, originating in Spanish flamenco music. It's a descending bass line: i → VII → VI → V, walking down the scale step by step. That stepwise motion creates a sense of inevitability, like falling slowly.

The final V chord creates strong tension that wants to resolve back to i, making this perfect for looping. In modern production, you'll hear this in everything from metal (Metallica) to hip-hop.

**Key Concept**: The descending bass line is what gives this progression its dramatic, almost fatalistic quality. Each chord feels like a step down a staircase.

**Try This**: Play just the bass notes (root of each chord) descending. That's the skeleton of the progression's power.
""",
    }

    # Check for matching explanation
    name_key = name.lower().replace(" ", "_").replace("-", "_")
    if name_key in explanations:
        return explanations[name_key]

    # Generate a generic explanation
    numeral_str = " → ".join(numerals) if numerals else "the chords"
    mood_str = ", ".join(moods) if moods else "its characteristic"

    return f"""
**Why It Works**

This {name} progression ({numeral_str}) creates a {mood_str} feeling through its specific chord choices.

{description}

The movement between these chords creates emotional tension and release in ways that resonate with listeners — this is why you've heard similar progressions in countless songs across genres.

**Key Concept**: Each chord has a "function" — some feel stable (like the i or I), some create tension (like V or VII), and some add color (like VI or iv). This progression balances these functions to create its mood.

**Try This**: Play the progression slowly, holding each chord for 4 beats. Notice which transitions feel smooth and which create more tension. That's voice leading and harmonic rhythm at work.
"""


def generate_rhythm_explanation_local(pattern_data: Dict) -> str:
    """Generate a basic rhythm explanation without API call."""
    name = pattern_data.get("name", "Pattern")
    description = pattern_data.get("description", "")
    swing = pattern_data.get("swing", 0)
    grid = pattern_data.get("grid", {})
    tempo_range = pattern_data.get("tempo_range", (120, 120))

    # Analyze the pattern
    kick_steps = grid.get("kick", [])
    snare_steps = grid.get("snare", grid.get("rim", grid.get("clap", [])))
    hat_steps = grid.get("closed_hat", [])

    # Determine feel
    if 0 in kick_steps and 4 in kick_steps and 8 in kick_steps and 12 in kick_steps:
        feel = "four-on-the-floor"
        feel_desc = "This is a four-on-the-floor pattern — kick on every beat. It's the foundation of house, disco, and electronic dance music. The steady pulse creates an irresistible urge to move."
    elif 0 in kick_steps and 8 not in kick_steps:
        feel = "half-time"
        feel_desc = "This pattern has a half-time feel — kick on beat 1, snare on beat 3. It creates a slower, heavier groove even at higher tempos. Common in trap, dubstep, and modern hip-hop."
    elif len(hat_steps) >= 8:
        feel = "driving"
        feel_desc = "The continuous hi-hats create forward momentum and energy. They subdivide the beat, making it feel faster and more urgent."
    else:
        feel = "sparse"
        feel_desc = "This pattern uses space effectively. What's *not* played is as important as what is — the silence creates anticipation."

    swing_desc = ""
    if swing > 0:
        swing_desc = f"\n\n**Swing ({swing}%)**: The swing pushes some notes slightly late, creating a human, groovy feel instead of robotic precision. This is essential for lo-fi, boom bap, and jazz-influenced beats."

    return f"""
**{name}**

{description}

**The Feel**: {feel_desc}{swing_desc}

**Tempo Range**: {tempo_range[0]}-{tempo_range[1]} BPM is ideal for this pattern. Slower tempos let the groove breathe; faster tempos add energy.

**Why the Kick Pattern Matters**: The kick drum is the heartbeat. Where you place it determines whether the groove feels driving, laid-back, or syncopated.

**Why the Snare/Clap Placement Matters**: The backbeat (usually beats 2 and 4) is what makes you nod your head. Moving it even slightly changes the entire feel.

**Try This**: Once you've programmed the pattern, vary the hi-hat velocities randomly between 70-100. This small change makes the pattern feel alive instead of mechanical.
"""


if __name__ == "__main__":
    # Test local generation
    print("=" * 60)
    print("Teaching Agent — Local Generation Test")
    print("=" * 60)
    print()

    # Test progression explanation
    test_prog = {
        "name": "Epic Minor",
        "numerals": ["i", "VI", "III", "VII"],
        "key": "A minor",
        "moods": ["epic", "uplifting", "anthemic"],
        "description": "The viral progression. Endless loop that never resolves.",
    }

    print("### Progression Explanation")
    print(generate_progression_explanation_local(test_prog))
    print()

    # Test rhythm explanation
    test_pattern = {
        "name": "Trap Rolling Hats",
        "description": "Trap with continuous 16th-note hi-hats",
        "tempo_range": (130, 160),
        "swing": 0,
        "grid": {
            "kick": [0, 7, 10],
            "snare": [4, 12],
            "closed_hat": list(range(16)),  # All 16 steps
        },
    }

    print("### Rhythm Explanation")
    print(generate_rhythm_explanation_local(test_pattern))
