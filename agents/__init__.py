# Music Co-Pilot Agent Modules
#
# Facade: external callers import from this package, never from sub-modules.
# Internal module structure may change without breaking external imports.

from .orchestrator import Orchestrator, quick_process
from .intent_detection import (
    IntentType,
    ParsedIntent,
    RoutingPlan,
    OrchestratorResult,
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
from .theory_agent import (
    TheoryAgent,
    generate_theory_output_local,
    generate_artist_blend_local,
)
from .sound_engineering_agent import (
    SoundEngineeringAgent,
    generate_sound_engineering_local,
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
    # Theory Agent
    'TheoryAgent',
    'generate_theory_output_local',
    'generate_artist_blend_local',
    # Sound Engineering Agent
    'SoundEngineeringAgent',
    'generate_sound_engineering_local',
]
