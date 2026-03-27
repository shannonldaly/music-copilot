"""
Model configuration and tiered routing.

Cost-efficiency strategy:
- Use Haiku for simple tasks (routing, parsing, classification)
- Use Sonnet for creative/complex tasks (generation, explanation)
- Reserve Opus for only the most demanding tasks

This can reduce costs by 10-20x compared to using Sonnet for everything.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class TaskType(Enum):
    """Types of tasks with different model requirements."""
    # Simple tasks — Haiku is sufficient
    INTENT_DETECTION = "intent_detection"
    INPUT_PARSING = "input_parsing"
    CLASSIFICATION = "classification"
    EXTRACTION = "extraction"
    VALIDATION_ASSIST = "validation_assist"

    # Creative/complex tasks — use Sonnet
    CHORD_SUGGESTION = "chord_suggestion"
    THEORY_EXPLANATION = "theory_explanation"
    PRODUCTION_STEPS = "production_steps"
    TEACHING = "teaching"
    SOUND_ENGINEERING = "sound_engineering"
    VIBE_INTERPRETATION = "vibe_interpretation"
    ARTIST_MATCHING = "artist_matching"

    # Most demanding — Opus (rarely needed)
    COMPLEX_COMPOSITION = "complex_composition"


# Model IDs
MODELS = {
    'haiku': 'claude-haiku-4-5-20251001',
    'sonnet': 'claude-sonnet-4-5-20250929',
    'opus': 'claude-opus-4-5-20251101',
}

# Default model assignments by task type
TASK_MODEL_MAP: Dict[TaskType, str] = {
    # Haiku tasks (cheap, fast)
    TaskType.INTENT_DETECTION: 'haiku',
    TaskType.INPUT_PARSING: 'haiku',
    TaskType.CLASSIFICATION: 'haiku',
    TaskType.EXTRACTION: 'haiku',
    TaskType.VALIDATION_ASSIST: 'haiku',

    # Sonnet tasks (balanced)
    TaskType.CHORD_SUGGESTION: 'sonnet',
    TaskType.THEORY_EXPLANATION: 'sonnet',
    TaskType.PRODUCTION_STEPS: 'sonnet',
    TaskType.TEACHING: 'sonnet',
    TaskType.SOUND_ENGINEERING: 'sonnet',
    TaskType.VIBE_INTERPRETATION: 'sonnet',
    TaskType.ARTIST_MATCHING: 'sonnet',

    # Opus tasks (expensive, powerful)
    TaskType.COMPLEX_COMPOSITION: 'opus',
}


@dataclass
class ModelConfig:
    """
    Configuration for model selection.

    Allows overriding defaults for testing or specific use cases.
    """
    # Override map (task_type -> model_tier)
    overrides: Dict[TaskType, str] = None

    # Force all tasks to use a specific model (for testing)
    force_model: Optional[str] = None

    # Maximum tokens per call (for budget control)
    max_output_tokens: int = 1024

    def __post_init__(self):
        if self.overrides is None:
            self.overrides = {}

    def get_model(self, task_type: TaskType) -> str:
        """Get the model ID for a task type."""
        if self.force_model:
            return MODELS.get(self.force_model, self.force_model)

        tier = self.overrides.get(task_type) or TASK_MODEL_MAP.get(task_type, 'sonnet')
        return MODELS.get(tier, MODELS['sonnet'])

    def get_tier(self, task_type: TaskType) -> str:
        """Get the model tier name for a task type."""
        if self.force_model:
            return self.force_model
        return self.overrides.get(task_type) or TASK_MODEL_MAP.get(task_type, 'sonnet')


def get_model_for_task(task_type: TaskType, config: Optional[ModelConfig] = None) -> str:
    """
    Get the appropriate model ID for a task type.

    Args:
        task_type: The type of task to perform
        config: Optional ModelConfig for overrides

    Returns:
        Model ID string like 'claude-sonnet-4-5-20250929'
    """
    if config:
        return config.get_model(task_type)
    return MODELS.get(TASK_MODEL_MAP.get(task_type, 'sonnet'), MODELS['sonnet'])


# Convenience exports
HAIKU = MODELS['haiku']
SONNET = MODELS['sonnet']
OPUS = MODELS['opus']
