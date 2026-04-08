# Decision: Artist blend as local-only feature

Date: 2026-03-31 (Phase 2)
Status: Decided
Commit: 740503d

## Problem
Users want to say "Massive Attack meets Deadmau5" and get a blended creative direction. This requires combining knowledge from two artist profiles to suggest tempo, key type, production approach, and a matching progression.

## Options considered
| Option | Summary | Why not chosen |
|--------|---------|---------------|
| LLM-powered blend | Send both artist profiles to Sonnet, ask it to blend | Costs money, non-deterministic, harder to test |
| **Local deterministic blend** | Hardcode 12 artist profiles, compute blend from overlapping attributes | Chosen |
| Hybrid (local + LLM polish) | Compute blend locally, use LLM to write the description | Added cost for marginal quality improvement |

## Decision
12 artist profiles defined in `ARTIST_PROFILES` dict in `theory_agent.py`, sourced from `docs/artist_dna.md`. Each profile has genres, moods, key_type, elements (production techniques), tempo_range, and progression_tags. `generate_artist_blend_local()` computes tempo overlap (or midpoint ±10 if no overlap), resolves key type, picks elements from each artist, generates a blend description, and finds a matching progression from `NAMED_PROGRESSIONS`.

## Tradeoffs accepted
- Limited to 12 hardcoded artists — any artist not in ARTIST_PROFILES returns None
- Blend description is formulaic (template string), not creative prose
- No API-mode artist blend exists — feature is local-only
- Progression matching uses mood tags, not actual harmonic analysis of artist catalogs

## Deferred
- Expanding artist roster beyond 12
- LLM-enhanced blend descriptions for API mode
- Artist-specific chord voicing preferences (e.g., Portishead uses half-diminished chords)
