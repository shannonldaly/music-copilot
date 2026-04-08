# Decision: Enharmonic spelling — pitch-space comparison

Date: 2026-03-31 (Phase 2)
Status: Decided
Commit: e46d39f

## Problem
Theory Validator was failing valid chords in flat keys because music21 uses `B-` internally while our theory module uses `Bb`. String comparison (`"Bb" != "B-"`) caused false positives on chord name mismatch errors.

## Options considered
| Option | Summary | Why not chosen |
|--------|---------|---------------|
| String normalization | Map all flat/sharp variants to canonical names | Fragile, many edge cases (double sharps, double flats) |
| **Pitch-space comparison** | Compare `pitch.Pitch.ps % 12` (float MIDI value) instead of string names | Chosen |
| Disable validation for flat keys | Skip validation when key contains flats | Loses the quality gate entirely |

## Decision
Changed `_check_chord_name_match()` to compare using `round(p.ps % 12, 2)` for both actual and expected pitches. This maps all enharmonic equivalents (Bb, A#, B-) to the same float value. Also updated the theory module's note generation: flat keys produce flat note names, sharp keys produce sharp note names.

## Tradeoffs accepted
- Loses ability to flag enharmonic "style" issues (using sharps in a flat key) — treated as equivalent
- Rounding to 2 decimal places could theoretically lose precision on microtonal pitches (not relevant for 12-TET)

## Deferred
- None — this was a targeted bug fix
