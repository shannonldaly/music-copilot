"""
Sound Engineering Agent — Handles mixing, EQ, compression, sidechain,
spatial, sound design, and automation questions.

Role: Answers production/engineering questions grounded in best practices
for electronic music production.

Grounded in:
- /docs/electronic_music_production.md (history, how-to, best practices)
- /docs/mixing_cheat_sheet.md (instrument-specific EQ, compression, reverb)
- /docs/automation_playbook.md (when and what to automate by song section)
- /docs/artist_dna.md (artist-specific production techniques and signatures)

Always explains *why* before *how*. Never assumes prior knowledge
without a one-sentence explanation.
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
class EngineeringAdvice:
    """Structured sound engineering output."""
    title: str
    explanation: str  # The "why"
    steps: List[str]  # The "how"
    settings: Dict[str, str]  # Specific parameter values
    common_mistakes: List[str]
    related_topics: List[str]


class SoundEngineeringAgent:
    """
    Answers sound engineering and mixing questions for electronic music.

    Covers:
    - Frequency spectrum decisions (what lives where, what to cut)
    - Compression settings for specific use cases
    - Sidechain setup and pump effect
    - Reverb and delay routing (always returns, never inserts)
    - Gain staging and headroom for export
    - LUFS targets by platform and genre
    - Synthesis and sound design guidance
    - Automation strategies by song section
    - Artist-specific production techniques
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

        # Load grounding documents
        self.grounding_docs = self._load_grounding_docs()

    def _load_grounding_docs(self) -> Dict[str, str]:
        """Load all grounding documents for this agent."""
        docs_dir = Path(__file__).parent.parent / "docs"
        doc_files = {
            "electronic_music": "electronic_music_production.md",
            "mixing": "mixing_cheat_sheet.md",
            "automation": "automation_playbook.md",
            "artist_dna": "artist_dna.md",
        }

        loaded = {}
        for key, filename in doc_files.items():
            path = docs_dir / filename
            if path.exists():
                content = path.read_text()
                # Truncate to manage context size
                loaded[key] = content[:5000] + "\n[... truncated for context ...]"
            else:
                loaded[key] = ""

        return loaded

    def answer_question(
        self,
        question: str,
        user_level: str = "beginner",
        context: Optional[Dict] = None,
    ) -> Dict:
        """
        Answer a sound engineering question using the LLM.

        Args:
            question: The user's production/engineering question
            user_level: "beginner", "intermediate", "advanced"
            context: Optional context (current project key, genre, etc.)

        Returns:
            Dict with explanation, steps, and settings
        """
        system_prompt = self._build_system_prompt(user_level, question)
        user_prompt = self._build_user_prompt(question, context)

        response = self.client.messages.create(
            model=get_model_for_task(TaskType.SOUND_ENGINEERING, self.model_config),
            max_tokens=1500,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        if self.tracker:
            log_api_call(
                self.tracker,
                agent="sound_engineering_agent",
                model="sonnet",
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                request_type="engineering_question"
            )

        return {
            "markdown": response.content[0].text,
            "question": question,
        }

    def _build_system_prompt(self, user_level: str, question: str) -> str:
        """Build the system prompt with relevant grounding context."""
        level_guidance = {
            "beginner": "Explain *why* before *how*. Define any technical term the first time you use it. Use analogies.",
            "intermediate": "Assume basic DAW knowledge. Focus on the reasoning behind specific settings.",
            "advanced": "Be concise. Focus on nuance, edge cases, and advanced techniques.",
        }

        # Select relevant grounding docs based on question content
        question_lower = question.lower()
        grounding_sections = []

        # Always include automation playbook for relevant questions
        automation_keywords = ["automate", "automation", "filter sweep", "build", "drop",
                               "intro", "outro", "breakdown", "arrangement", "lfo",
                               "section", "transition"]
        if any(kw in question_lower for kw in automation_keywords):
            grounding_sections.append(
                f"AUTOMATION PLAYBOOK:\n{self.grounding_docs.get('automation', '')[:2500]}"
            )

        # Include artist DNA for style/reference questions
        artist_keywords = ["like", "style", "sound like", "reference", "artist",
                           "massive attack", "portishead", "skrillex", "fred again",
                           "deadmau5", "deftones", "nin", "reznor", "clozee", "griz",
                           "böhmer", "hooverphonics", "sofi tukker"]
        if any(kw in question_lower for kw in artist_keywords):
            grounding_sections.append(
                f"ARTIST DNA (production techniques):\n{self.grounding_docs.get('artist_dna', '')[:2500]}"
            )

        # Always include mixing basics
        grounding_sections.append(
            f"MIXING REFERENCE:\n{self.grounding_docs.get('mixing', '')[:2000]}"
        )

        grounding_text = "\n\n".join(grounding_sections)

        return f"""You are a Sound Engineering Agent for a music production co-pilot. You help a music producer with mixing, mastering, EQ, compression, sidechain, spatial effects, sound design, and automation.

USER LEVEL: {user_level}
{level_guidance.get(user_level, level_guidance["beginner"])}

OUTPUT FORMAT:
Use markdown with clear sections:
1. **Why** — Explain the concept and why it matters
2. **How** — Step-by-step in Ableton Live 12
3. **Settings** — Specific parameter values to start with
4. **Common Mistakes** — What beginners get wrong
5. **Related** — What to explore next

RULES:
- Always explain *why* before *how*
- Give specific numbers (frequencies, ratios, ms values), not vague advice
- Reverb and delay go on return tracks, never inserts (for this genre context)
- Include Ableton-specific paths when referencing effects or instruments
- Reference automation strategies by song section when relevant
- Reference artist-specific techniques when the question relates to a particular style

GROUNDING CONTEXT:
{grounding_text}"""

    def _build_user_prompt(self, question: str, context: Optional[Dict] = None) -> str:
        """Build the user prompt."""
        parts = [question]

        if context:
            ctx_parts = []
            if context.get("key"):
                ctx_parts.append(f"Key: {context['key']}")
            if context.get("genre"):
                ctx_parts.append(f"Genre: {context['genre']}")
            if context.get("bpm"):
                ctx_parts.append(f"BPM: {context['bpm']}")

            if ctx_parts:
                parts.append(f"\nCurrent project context: {', '.join(ctx_parts)}")

        return "\n".join(parts)
