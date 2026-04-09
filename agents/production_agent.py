"""
Production Agent — Translates theory into Ableton Live instructions.

Role: Takes validated chord/drum data and outputs concrete, step-by-step
Ableton Live instructions that a beginner can follow.

Grounded in: /docs/ableton_guide.md

Key features:
- DAW-agnostic design (daw_target parameter)
- MCP-ready comments for v2 automation
- Beginner-friendly language
- Version-aware (defaults to Live 12)
"""

import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from pathlib import Path

from anthropic import Anthropic

# Local imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.tokens import TokenTracker, log_api_call
from utils.models import ModelConfig, TaskType, get_model_for_task, SONNET


@dataclass
class ProductionStep:
    """A single production step."""
    step_number: int
    action: str
    details: str
    mcp_command: Optional[str] = None  # For v2 automation


@dataclass
class ProductionInstructions:
    """Complete production instructions."""
    title: str
    track_setup: List[str]
    steps: List[ProductionStep]
    suggested_next: List[str]
    tips: List[str] = field(default_factory=list)
    daw: str = "Ableton Live 12"


class ProductionAgent:
    """
    Generates step-by-step DAW instructions from theory data.

    Supports:
    - Chord progression entry
    - Drum pattern programming
    - Basic mixing suggestions
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_config: Optional[ModelConfig] = None,
        tracker: Optional[TokenTracker] = None,
        daw_target: str = "ableton",  # Future: "logic", "flstudio", etc.
    ):
        self.client = Anthropic(api_key=api_key) if api_key else Anthropic()
        self.model_config = model_config or ModelConfig()
        self.tracker = tracker
        self.daw_target = daw_target

        # Load grounding document
        self.grounding_doc = self._load_grounding_doc()

    def _load_grounding_doc(self) -> str:
        """Load the Ableton guide for grounding."""
        doc_path = Path(__file__).parent.parent / "docs" / "ableton_guide.md"
        if doc_path.exists():
            # Load first 4000 chars to stay within context limits
            content = doc_path.read_text()
            return content[:4000] + "\n[... truncated for context ...]"
        return ""

    def generate_chord_instructions(
        self,
        progression_data: Dict,
        user_level: str = "beginner",
    ) -> Dict:
        """
        Generate Ableton instructions for entering a chord progression.

        Args:
            progression_data: Validated progression with chords and notes
            user_level: "beginner", "intermediate", "advanced"

        Returns:
            Dict with markdown instructions and structured data
        """
        # Extract data
        key = progression_data.get("key", "C major")
        tempo = progression_data.get("tempo_suggestion", "120 BPM")
        chords = progression_data.get("chords", [])
        progression_name = progression_data.get("progression_name", "")

        # Build the prompt
        system_prompt = self._build_system_prompt(user_level)
        user_prompt = self._build_chord_prompt(key, tempo, chords, progression_name)

        # Call the API
        response = self.client.messages.create(
            model=get_model_for_task(TaskType.PRODUCTION_STEPS, self.model_config),
            max_tokens=1500,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        # Log tokens
        if self.tracker:
            log_api_call(
                self.tracker,
                agent="production_agent",
                model="sonnet",
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                request_type="chord_instructions"
            )

        # Parse response
        content = response.content[0].text

        return {
            "markdown": content,
            "daw": self.daw_target,
            "progression_data": progression_data,
        }

    def generate_drum_instructions(
        self,
        pattern_data: Dict,
        user_level: str = "beginner",
    ) -> Dict:
        """
        Generate Ableton instructions for programming a drum pattern.

        Args:
            pattern_data: Drum pattern with grid data
            user_level: "beginner", "intermediate", "advanced"

        Returns:
            Dict with markdown instructions
        """
        system_prompt = self._build_system_prompt(user_level)
        user_prompt = self._build_drum_prompt(pattern_data)

        response = self.client.messages.create(
            model=get_model_for_task(TaskType.PRODUCTION_STEPS, self.model_config),
            max_tokens=1500,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        if self.tracker:
            log_api_call(
                self.tracker,
                agent="production_agent",
                model="sonnet",
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                request_type="drum_instructions"
            )

        return {
            "markdown": response.content[0].text,
            "daw": self.daw_target,
            "pattern_data": pattern_data,
        }

    def generate_from_local_data(
        self,
        local_data: Dict,
        user_level: str = "beginner",
    ) -> Dict:
        """
        Generate instructions from orchestrator's local lookup data.

        This is the main entry point when called from the orchestrator.
        """
        results = {}

        if "progressions" in local_data and local_data["progressions"]:
            # Use the first/best progression
            prog = local_data["progressions"][0]
            progression_data = {
                "key": prog["key"],
                "tempo_suggestion": f"{prog['tempo_range'][0]}-{prog['tempo_range'][1]} BPM",
                "progression_name": prog["name"],
                "chords": prog["chords"],
            }
            results["chord_instructions"] = self.generate_chord_instructions(
                progression_data, user_level
            )

        if "drum_patterns" in local_data and local_data["drum_patterns"]:
            # Use the first/best pattern
            pattern = local_data["drum_patterns"][0]
            results["drum_instructions"] = self.generate_drum_instructions(
                pattern, user_level
            )

        return results

    def _build_system_prompt(self, user_level: str) -> str:
        """Build the system prompt for the production agent."""
        level_guidance = {
            "beginner": "Explain every step in detail. Don't assume knowledge of keyboard shortcuts. Include exact menu paths.",
            "intermediate": "Include keyboard shortcuts. Skip obvious steps but explain non-obvious ones.",
            "advanced": "Be concise. Focus on efficiency tips and advanced techniques.",
        }

        return f"""You are a Production Agent for a music co-pilot. Your job is to translate music theory (chords, progressions, drum patterns) into concrete, step-by-step Ableton Live 12 instructions.

USER LEVEL: {user_level}
{level_guidance.get(user_level, level_guidance["beginner"])}

OUTPUT FORMAT:
Use markdown with clear sections:
1. **Track Setup** - Creating tracks, loading instruments
2. **Entering the Notes** - Numbered steps for each chord/hit
3. **Suggested Next Steps** - What to do after the basics are in

RULES:
- Always specify exact note names with octaves (e.g., A3, C4, E4)
- Include keyboard shortcuts in parentheses
- For each step that could be automated, add a comment: `# MCP v2: command_name(params)`
- Default to Live 12 but note when features are version-specific
- Suggest instruments from Ableton's Core Library (always available)
- Keep instructions concise but complete

GROUNDING (Ableton knowledge):
{self.grounding_doc[:2000] if self.grounding_doc else "Refer to standard Ableton Live 12 workflows."}
"""

    def _build_chord_prompt(
        self,
        key: str,
        tempo: str,
        chords: List[Dict],
        progression_name: str
    ) -> str:
        """Build the user prompt for chord instructions."""
        chord_details = []
        for i, chord in enumerate(chords, 1):
            name = chord.get("name", "")
            numeral = chord.get("numeral", "")
            notes = chord.get("note_names", chord.get("notes", []))
            chord_details.append(f"Chord {i} ({numeral}): {name} — Notes: {', '.join(notes)}")

        return f"""Generate Ableton Live instructions for this chord progression:

**Progression**: {progression_name}
**Key**: {key}
**Suggested Tempo**: {tempo}

**Chords to enter**:
{chr(10).join(chord_details)}

Create step-by-step instructions for:
1. Setting up a MIDI track with an appropriate instrument
2. Entering each chord with exact note positions
3. Suggested next steps (bass, drums, effects)

Make it beginner-friendly but complete."""

    def _build_drum_prompt(self, pattern_data: Dict) -> str:
        """Build the user prompt for drum instructions."""
        name = pattern_data.get("name", "Drum Pattern")
        tempo_range = pattern_data.get("tempo_range", (120, 120))
        grid = pattern_data.get("grid", {})
        description = pattern_data.get("description", "")

        # Format grid for the prompt
        grid_text = []
        for sound, steps in grid.items():
            step_str = ", ".join(str(s + 1) for s in steps)  # 1-indexed for humans
            grid_text.append(f"- {sound}: hits on steps {step_str}")

        return f"""Generate Ableton Live instructions for this drum pattern:

**Pattern**: {name}
**Description**: {description}
**Suggested Tempo**: {tempo_range[0]}-{tempo_range[1]} BPM

**Pattern Grid** (16 steps per bar):
{chr(10).join(grid_text)}

Create step-by-step instructions for:
1. Setting up a Drum Rack track
2. Programming each sound in the pattern
3. Suggested velocity adjustments for groove
4. Next steps (swing, effects, layering)

Use 606/808/909 sounds from Ableton's Core Library. Make it beginner-friendly."""


# =============================================================================
# Local generation (no API) for simple cases
# =============================================================================

def generate_chord_instructions_local(
    progression_data: Dict,
    daw: str = "Ableton Live 12"
) -> str:
    """
    Generate basic chord instructions without API call.

    Use this for simple cases where LLM creativity isn't needed.
    """
    key = progression_data.get("key", "C major")
    chords = progression_data.get("chords", [])
    name = progression_data.get("progression_name", progression_data.get("name", "Progression"))

    # Resolve BPM: tempo_range tuple > tempo_suggestion string > fallback
    tempo_range = progression_data.get("tempo_range")
    tempo_suggestion = progression_data.get("tempo_suggestion")
    if tempo_range and isinstance(tempo_range, (list, tuple)) and len(tempo_range) >= 2:
        bpm = (tempo_range[0] + tempo_range[1]) // 2
        tempo_display = f"{tempo_range[0]}-{tempo_range[1]} BPM"
    elif tempo_suggestion:
        tempo_display = str(tempo_suggestion)
        # Extract number from strings like "85 BPM"
        digits = ''.join(c for c in str(tempo_suggestion) if c.isdigit())
        bpm = int(digits) if digits else 120
    else:
        bpm = 120
        tempo_display = "120 BPM"

    lines = [
        f"## Building This in {daw}",
        "",
        f"**Progression**: {name}",
        f"**Key**: {key}",
        f"**Tempo**: {tempo_display}",
        "",
        "### Track Setup",
        "1. Create a new MIDI track (Cmd+Shift+T)",
        "   `# MCP v2: create_midi_track()`",
        "2. Load an instrument: Instruments → Keys → Grand Piano",
        "   `# MCP v2: load_instrument('grand_piano')`",
        f"3. Set tempo to {bpm} BPM",
        f"   `# MCP v2: set_tempo({bpm})`",
        "",
        "### Entering the Notes",
        "1. Double-click the clip slot to create a MIDI clip",
        "   `# MCP v2: create_midi_clip(track=1, length=4)`",
        f"2. Set clip length to {len(chords)} bars (one bar per chord)",
        "3. Enable Draw Mode (B) in the Piano Roll",
        "",
    ]

    # Add each chord
    for i, chord in enumerate(chords, 1):
        chord_name = chord.get("name", f"Chord {i}")
        numeral = chord.get("numeral", "")
        notes = chord.get("note_names", chord.get("notes", []))

        lines.append(f"**Chord {i} — {chord_name} ({numeral})**")
        lines.append(f"- Notes: {', '.join(notes)}")
        lines.append(f"- Place at Bar {i}, Beat 1")
        lines.append(f"- Duration: 1 bar each note")
        lines.append(f"  `# MCP v2: add_notes(track=1, clip=1, notes={notes}, start={i-1}, duration=1)`")
        lines.append("")

    lines.extend([
        "### Suggested Next Steps",
        "- Add a bass track doubling root notes one octave lower",
        "- Layer with a pad for fuller sound",
        "- Add reverb send for space",
        "- Consider sidechain compression to a kick",
    ])

    return "\n".join(lines)


def generate_drum_instructions_local(
    pattern_data: Dict,
    daw: str = "Ableton Live 12"
) -> str:
    """
    Generate basic drum instructions without API call.
    """
    name = pattern_data.get("name", "Drum Pattern")
    tempo_range = pattern_data.get("tempo_range", (120, 120))
    grid = pattern_data.get("grid", {})
    description = pattern_data.get("description", "")
    swing = pattern_data.get("swing", 0)

    lines = [
        f"## Programming Drums in {daw}",
        "",
        f"**Pattern**: {name}",
        f"**Description**: {description}",
        f"**Tempo**: {tempo_range[0]}-{tempo_range[1]} BPM",
        "",
        "### Track Setup",
        "1. Create a new MIDI track (Cmd+Shift+T)",
        "   `# MCP v2: create_midi_track()`",
        "2. Load a Drum Rack: Drums → Drum Rack → 808 Core Kit",
        "   `# MCP v2: load_drum_rack('808_core')`",
        "",
        "### Programming the Pattern",
        "1. Create a 1-bar MIDI clip (Cmd+Shift+M)",
        "   `# MCP v2: create_midi_clip(track=1, length=1)`",
        "2. Set grid to 1/16 notes",
        "",
    ]

    # MIDI note mappings
    midi_notes = {
        "kick": "C1 (MIDI 36)",
        "snare": "D1 (MIDI 38)",
        "clap": "D#1 (MIDI 39)",
        "closed_hat": "F#1 (MIDI 42)",
        "open_hat": "A#1 (MIDI 46)",
        "rim": "C#1 (MIDI 37)",
        "tom_high": "D2 (MIDI 50)",
        "tom_mid": "B1 (MIDI 47)",
        "tom_low": "A1 (MIDI 45)",
    }

    for sound, steps in grid.items():
        midi = midi_notes.get(sound, sound)
        step_str = ", ".join(str(s + 1) for s in steps)
        lines.append(f"**{sound.replace('_', ' ').title()}** ({midi})")
        lines.append(f"- Place hits on steps: {step_str}")
        lines.append(f"  `# MCP v2: add_drum_hits('{sound}', [{', '.join(str(s) for s in steps)}])`")
        lines.append("")

    if swing:
        lines.append(f"### Groove")
        lines.append(f"- Add {swing}% swing for human feel")
        lines.append(f"  `# MCP v2: set_groove(swing={swing})`")
        lines.append("")

    lines.extend([
        "### Suggested Next Steps",
        "- Vary hi-hat velocities (80-127) for groove",
        "- Add ghost snares at lower velocity",
        "- Layer kick with a sub for weight",
        "- Sidechain other elements to the kick",
    ])

    return "\n".join(lines)


if __name__ == "__main__":
    # Test local generation (no API needed)
    print("=" * 60)
    print("Production Agent — Local Generation Test")
    print("=" * 60)
    print()

    # Test chord instructions
    test_progression = {
        "name": "Sad Lo-Fi",
        "key": "A minor",
        "tempo_suggestion": "75-85 BPM",
        "chords": [
            {"numeral": "i", "name": "Am", "note_names": ["A3", "C4", "E4"]},
            {"numeral": "VI", "name": "F", "note_names": ["F3", "A3", "C4"]},
            {"numeral": "iv", "name": "Dm", "note_names": ["D3", "F3", "A3"]},
            {"numeral": "VII", "name": "G", "note_names": ["G3", "B3", "D4"]},
        ],
    }

    print("### Chord Progression Instructions")
    print()
    print(generate_chord_instructions_local(test_progression))
    print()

    # Test drum instructions
    test_pattern = {
        "name": "Lo-Fi Basic",
        "description": "Mellow lo-fi beat with rim and soft hats",
        "tempo_range": (70, 90),
        "swing": 60,
        "grid": {
            "kick": [0, 10],
            "rim": [4, 12],
            "closed_hat": [0, 2, 4, 6, 8, 10, 12, 14],
        },
    }

    print()
    print("### Drum Pattern Instructions")
    print()
    print(generate_drum_instructions_local(test_pattern))
