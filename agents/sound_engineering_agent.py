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
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from pathlib import Path

from anthropic import Anthropic

# Local imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.tokens import TokenTracker, log_api_call
from utils.models import ModelConfig, TaskType, get_model_for_task
from utils.logging import log_agent_call

# Re-export for facade compatibility
from agents.se_local_data import generate_sound_engineering_local  # noqa: F401

logger = logging.getLogger(__name__)


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

    @log_agent_call
    def answer_question_structured(
        self,
        question: str,
        user_level: str = "beginner",
        context: Optional[Dict] = None,
    ) -> Dict:
        """
        Answer a sound engineering question, returning the unified structured shape:
        {summary, steps, ableton_path, principle, artist_reference}

        This matches the local-mode contract so the frontend renders both
        API and local responses identically.
        """
        system_prompt = self._build_structured_system_prompt(user_level, question)
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
                request_type="engineering_question_structured"
            )

        # Parse structured JSON response
        try:
            result = json.loads(response.content[0].text)
            # Validate required keys are present
            required = {'summary', 'steps', 'ableton_path', 'principle', 'artist_reference'}
            if required.issubset(result.keys()):
                return result
        except (json.JSONDecodeError, AttributeError) as e:
            logger.warning(f"SE Agent: structured JSON parse failed, using text fallback: {e}")

        # Fallback: build structured response from raw text
        raw = response.content[0].text
        return {
            "summary": raw[:200].split("\n")[0] if raw else "See details below.",
            "steps": [line.strip("- ") for line in raw.split("\n") if line.strip().startswith(("-", "1", "2", "3", "4", "5"))][:5] or ["See the full explanation above."],
            "ableton_path": "See steps above for Ableton-specific paths.",
            "principle": raw[:500] if raw else "No explanation available.",
            "artist_reference": "",
        }

    def _build_structured_system_prompt(self, user_level: str, question: str) -> str:
        """Build system prompt that requests JSON output matching the local contract."""
        level_guidance = {
            "beginner": "Explain *why* before *how*. Define any technical term the first time you use it.",
            "intermediate": "Assume basic DAW knowledge. Focus on the reasoning behind specific settings.",
            "advanced": "Be concise. Focus on nuance and advanced techniques.",
        }

        question_lower = question.lower()
        grounding_sections = []

        automation_keywords = ["automate", "automation", "filter sweep", "build", "drop",
                               "intro", "outro", "breakdown", "arrangement", "lfo",
                               "section", "transition"]
        if any(kw in question_lower for kw in automation_keywords):
            grounding_sections.append(
                f"AUTOMATION PLAYBOOK:\n{self.grounding_docs.get('automation', '')[:2500]}"
            )

        artist_keywords = ["like", "style", "sound like", "reference", "artist"]
        if any(kw in question_lower for kw in artist_keywords):
            grounding_sections.append(
                f"ARTIST DNA:\n{self.grounding_docs.get('artist_dna', '')[:2500]}"
            )

        grounding_sections.append(
            f"MIXING REFERENCE:\n{self.grounding_docs.get('mixing', '')[:2000]}"
        )

        grounding_text = "\n\n".join(grounding_sections)

        return f"""You are a Sound Engineering Agent for a music production co-pilot.

USER LEVEL: {user_level}
{level_guidance.get(user_level, level_guidance["beginner"])}

You MUST respond with valid JSON matching this exact structure:
{{
  "summary": "One-sentence summary of the concept and what it does.",
  "steps": [
    "Step 1: ...",
    "Step 2: ...",
    "Step 3: ..."
  ],
  "ableton_path": "Audio Effects → Category → Effect Name (the Ableton menu path)",
  "principle": "A paragraph explaining *why* this matters and the underlying concept. Explain before instructing.",
  "artist_reference": "ArtistName — one sentence about how they use this technique."
}}

RULES:
- Give specific numbers (frequencies in Hz, ratios, ms values), not vague advice
- steps should be 3-6 concrete actions in Ableton Live 12
- ableton_path should be the actual Ableton browser path to the relevant effect
- principle should explain *why* before *how*
- artist_reference should name one artist and their specific use of this technique
- Respond with valid JSON only — no markdown, no explanation outside the JSON

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
