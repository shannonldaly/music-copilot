"""
Headless Claude access for local mode — bills the Claude subscription via the
Claude Code CLI (`claude -p`), no API key involved.

Expects: the `claude` binary at CLAUDE_BIN. Guarantees: helpers never raise —
they return None on any failure so callers can fall back to local behavior.
Missing binary: headless_available() is False and callers skip the LLM path.
Next consumer: the orchestrator's intent-enrichment fallback.
"""
import json
import re
import subprocess
from pathlib import Path

CLAUDE_BIN = "/Users/shannondaly/.local/bin/claude"

_INTENT_SYSTEM = """You are an intent classifier for a music production assistant.

Analyze the user's message and extract:
1. intent_type: one of mood_vibe, artist_reference, theory_request,
   production_question, drum_pattern, sound_engineering
2. extracted: a dict with any of: moods (list), genres (list),
   key (e.g. "A minor"), tempo (int), artists (list)

Moods/genres should map toward: melancholic, sad, dark, nostalgic, aggressive,
happy, uplifting, epic, romantic / lo-fi, trap, hip_hop, ambient, pop, edm,
house, synthwave, r&b, soul.

Respond with valid JSON only: {"intent_type": ..., "extracted": {...}}"""


def headless_available() -> bool:
    return Path(CLAUDE_BIN).exists()


def call_headless(prompt: str, system: str = None, timeout_seconds: int = 90):
    """One prompt through `claude -p`; returns text or None (never raises)."""
    try:
        full = f"{system}\n\n{prompt}" if system else prompt
        result = subprocess.run(
            [CLAUDE_BIN, "-p", "--output-format", "text"],
            input=full, capture_output=True, text=True, timeout=timeout_seconds,
        )
        if result.returncode != 0:
            return None
        text = (result.stdout or "").strip()
        return text or None
    except Exception:
        return None


def classify_intent_headless(prompt: str):
    """
    LLM intent classification for prompts the keyword lists can't read.
    Returns (intent_type, confidence, extracted) or None on any failure.
    """
    text = call_headless(f'Classify this request: "{prompt}"', system=_INTENT_SYSTEM)
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        data = json.loads(m.group())
    except json.JSONDecodeError:
        return None
    intent_type = data.get("intent_type") or "mood_vibe"
    extracted = data.get("extracted") or {}
    if not isinstance(extracted, dict):
        return None
    for k in ("moods", "genres", "artists"):
        if k in extracted and not isinstance(extracted[k], list):
            extracted[k] = [extracted[k]]
    return (intent_type, 0.85, extracted)
