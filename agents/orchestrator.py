"""
Orchestrator — Entry point for all user requests.

Delegates to:
- intent_detection.py for intent classification
- orchestrator_pipeline.py for local lookup and response assembly
- Teaching Agent / SE Agent for API-powered enhancements
"""

import logging
import os
from typing import List, Dict, Optional

from anthropic import Anthropic

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.tokens import TokenTracker
from utils.models import ModelConfig
from utils.logging import log_agent_call
from agents.intent_detection import (
    IntentType, ParsedIntent, RoutingPlan, OrchestratorResult,
    detect_intent_local as _detect_intent_local,
    parse_intent_with_llm, determine_routing,
)
from agents.orchestrator_pipeline import (
    lookup_local, build_response, execute_local_lookup_legacy,
)
from agents.production_agent import ProductionAgent
from agents.teaching_agent import (
    TeachingAgent, generate_progression_explanation_local,
)
from agents.sound_engineering_agent import SoundEngineeringAgent

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Main orchestrator for the Music Co-Pilot.

    Routes user requests to appropriate agents while minimizing API costs.
    Two entry points:
    - execute(): full pipeline, returns dict for GenerateResponse
    - process(): API-mode entry point, returns OrchestratorResult
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_config: Optional[ModelConfig] = None,
        token_budget: int = 4000,
    ):
        self._api_key = api_key
        self._client = None
        self._has_api_key = bool(api_key or os.environ.get("ANTHROPIC_API_KEY"))
        self.model_config = model_config or ModelConfig()
        self.tracker = TokenTracker(request_budget=token_budget)

        if self._has_api_key:
            logger.info("Orchestrator: API key found — Teaching Agent uses Sonnet, SE Agent has API fallback")
        else:
            logger.info("Orchestrator: no API key — Teaching Agent uses local templates, SE Agent local only")

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

    # =========================================================================
    # Public API
    # =========================================================================

    @log_agent_call
    def detect_intent_local(self, prompt: str) -> tuple:
        """Keyword-based intent detection. Delegates to intent_detection module."""
        return _detect_intent_local(prompt)

    @log_agent_call
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
            local_data = lookup_local(
                intent_type, extracted, prompt,
                has_api_key=self._has_api_key,
                se_api_fallback_fn=self._se_api_fallback,
            )

        response = build_response(
            intent_type, confidence, extracted, local_data,
            generate_teaching_fn=self._generate_teaching_note,
        )

        if use_api and local_data:
            self._enhance_with_api(response, local_data)

        summary = self.tracker.summary()
        response["tokens_used"] = summary.get("total_tokens", 0)
        response["cost_usd"] = summary.get("total_cost_usd", 0.0)

        return response

    def process(self, user_input: str, session_history: Optional[List[Dict]] = None) -> OrchestratorResult:
        """API-mode entry point. Uses Haiku for intent detection."""
        self.tracker.reset_for_request()

        intent = parse_intent_with_llm(self.client, self.tracker, user_input)

        if intent.intent_type == IntentType.CLARIFICATION_NEEDED:
            return OrchestratorResult(
                success=True,
                intent=intent,
                routing=RoutingPlan(agents=[]),
                clarification_needed=True,
                clarification_question=intent.clarification_question,
                token_summary=self.tracker.summary(),
            )

        routing = determine_routing(intent, self.user_profile)

        local_data = None
        if routing.use_local_lookup:
            local_data = execute_local_lookup_legacy(intent, routing)

        return OrchestratorResult(
            success=True,
            intent=intent,
            routing=routing,
            local_data=local_data,
            token_summary=self.tracker.summary(),
        )

    # =========================================================================
    # Agent wiring (API-first with fallbacks)
    # =========================================================================

    def _generate_teaching_note(self, prog: dict) -> str:
        """Teaching note — Sonnet API if key available, local fallback."""
        if self._has_api_key:
            try:
                teaching_agent = TeachingAgent(tracker=self.tracker)
                result = teaching_agent.explain_progression(
                    prog,
                    user_level=self.user_profile.get("theory_level", "rusty_intermediate"),
                )
                if result.get("explanation"):
                    return result["explanation"]
            except Exception as e:
                logger.warning(f"Teaching Agent API failed, using local fallback: {e}")
        return generate_progression_explanation_local(prog)

    def _se_api_fallback(self, question: str) -> Optional[Dict]:
        """SE Agent API fallback when local keyword matching returns no result."""
        try:
            se_agent = SoundEngineeringAgent(tracker=self.tracker)
            result = se_agent.answer_question_structured(question, user_level="beginner")
            return result
        except Exception as e:
            logger.warning(f"SE Agent API fallback failed: {e}")
            return None

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

        except Exception as e:
            logger.warning(f"API enhancement failed, keeping local output: {e}")


# =============================================================================
# Convenience function
# =============================================================================

def quick_process(user_input: str, api_key: Optional[str] = None) -> OrchestratorResult:
    """Quick way to process a request."""
    orchestrator = Orchestrator(api_key=api_key)
    return orchestrator.process(user_input)
