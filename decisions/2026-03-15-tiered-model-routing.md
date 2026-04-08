# Decision: Tiered model routing (Haiku / Sonnet / Opus)

Date: ~2026-03-15 (Phase 0)
Status: Decided

## Problem
Using the same model for all tasks wastes money on simple classification while potentially under-serving creative generation. Need cost-efficient routing.

## Options considered
| Option | Summary | Why not chosen |
|--------|---------|---------------|
| Single model for all tasks | Use Sonnet everywhere | Overpays 10x for intent detection |
| Haiku for everything | Cheapest option | Quality too low for creative chord generation |
| **Tiered routing by task type** | Haiku for classification, Sonnet for creative, Opus reserved for complex | Chosen |

## Decision
Defined `TaskType` enum in `utils/models.py` mapping each task to a model tier. Intent detection, parsing, classification, and extraction use Haiku. Chord suggestion, theory explanation, production steps, teaching, sound engineering, and vibe interpretation use Sonnet. Complex composition reserved for Opus (not yet used). `ModelConfig` allows per-task overrides and a `force_model` escape hatch.

## Tradeoffs accepted
- Haiku may misclassify ambiguous intents (mitigated by local keyword detection as default)
- Model IDs are hardcoded strings — must be updated when Anthropic releases new models
- Opus tier defined but no task currently uses it

## Deferred
- Dynamic model selection based on prompt complexity
- Cost tracking dashboard to validate savings
