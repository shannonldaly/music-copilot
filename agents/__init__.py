# Music Co-Pilot Agent Modules

from .orchestrator import (
    Orchestrator,
    IntentType,
    ParsedIntent,
    RoutingPlan,
    OrchestratorResult,
    quick_process,
)
from .production_agent import (
    ProductionAgent,
    generate_chord_instructions_local,
    generate_drum_instructions_local,
)
from .teaching_agent import (
    TeachingAgent,
    generate_progression_explanation_local,
    generate_rhythm_explanation_local,
)

__all__ = [
    # Orchestrator
    'Orchestrator',
    'IntentType',
    'ParsedIntent',
    'RoutingPlan',
    'OrchestratorResult',
    'quick_process',
    # Production Agent
    'ProductionAgent',
    'generate_chord_instructions_local',
    'generate_drum_instructions_local',
    # Teaching Agent
    'TeachingAgent',
    'generate_progression_explanation_local',
    'generate_rhythm_explanation_local',
]
