# Decision: music21 for deterministic theory validation

Date: ~2026-03-15 (Phase 0)
Status: Decided

## Problem
Claude has produced incorrect music theory in the past. LLM-generated chord progressions need a programmatic quality gate that catches wrong notes, incorrect chord spellings, and voice leading problems — without relying on another LLM call.

## Options considered
| Option | Summary | Why not chosen |
|--------|---------|---------------|
| LLM self-check | Ask the LLM to verify its own output | Same model makes same mistakes; costs money; not deterministic |
| Custom validation code | Write pitch/chord/scale validation from scratch | Reinventing the wheel; error-prone |
| **music21 library** | Use the established computational musicology library | Chosen |

## Decision
Theory Validator (`validator/theory_validator.py`) uses music21 for all validation: pitch parsing, chord name matching, diatonic checks, and voice leading analysis (parallel fifths/octaves, large leaps). Comparison uses `pitch.Pitch.ps` (pitch-space float values) instead of string names to handle enharmonic equivalence (Bb = A# = B-). Zero API cost per validation.

## Tradeoffs accepted
- music21 is a large dependency (~50MB installed)
- music21's `ChordSymbol` doesn't cover all chord naming conventions — fallback to custom `theory/` module
- Validator runs as synchronous Python, not a separate service — fine for v1

## Deferred
- Correction loop: CLAUDE.md specifies "retry up to 2x" but this is not implemented
- Extended chord validation (7ths, 9ths, altered chords) beyond basic triads
