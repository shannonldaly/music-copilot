"""
E2E Test — Core User Journey

Tests the primary user flow through the browser:
  Welcome → Session Modal → Enter Prompt → Generate → Panels Render →
  Keep Confirmation → Stage Advance

Reusable template: the test structure (setup → action → verify) is
project-agnostic. To port to a new project, swap the data-testid
selectors and the assertion values.

Prerequisites:
  - Backend running on :8000
  - Frontend running on :5173
  - Playwright + chromium installed

Run with:
  pytest tests/e2e/ --headed   (watch the browser)
  pytest tests/e2e/            (headless, CI-friendly)

Selectors used (all data-testid attributes):

  CRITICAL PATH:
    welcome-start-button     WelcomeScreen.jsx
    session-modal            SessionStartModal.jsx
    session-mode-chords      SessionStartModal.jsx
    session-mode-drums       SessionStartModal.jsx
    session-modal-continue   SessionStartModal.jsx
    prompt-input             InputBar.jsx
    generate-button          InputBar.jsx
    keep-button              InputBar.jsx

  ASSERT TARGETS:
    chord-row                MainWorkspace.jsx
    validation-badge         MainWorkspace.jsx
    teaching-note-section    MainWorkspace.jsx
    ableton-steps-section    MainWorkspace.jsx
    also-try-section         MainWorkspace.jsx
    melody-direction-panel   MainWorkspace.jsx
    drum-grid-block          MainWorkspace.jsx
    sound-engineering-panel  App.jsx
    artist-blend-panel       App.jsx

  STAGE VERIFICATION:
    progress-sidebar         ProgressSidebar.jsx
"""

import pytest


# =============================================================================
# Helpers — reusable across projects
# =============================================================================

def tid(testid: str) -> str:
    """Build a data-testid selector string. Single place to change the pattern."""
    return f"[data-testid='{testid}']"


def wait_and_click(page, testid: str, timeout: int = 5000):
    """Wait for an element to appear, then click it."""
    page.locator(tid(testid)).wait_for(timeout=timeout)
    page.locator(tid(testid)).click()


def wait_for_visible(page, testid: str, timeout: int = 10000):
    """Assert an element becomes visible within timeout."""
    page.locator(tid(testid)).wait_for(state="visible", timeout=timeout)


def fill_and_submit(page, input_testid: str, text: str, submit_testid: str):
    """Fill an input field and click a submit button."""
    page.locator(tid(input_testid)).fill(text)
    page.locator(tid(submit_testid)).click()


def navigate_to_workspace(page, mode: str = "chords"):
    """Reusable setup: welcome → modal → select mode → continue → workspace.

    Args:
        page: Playwright page (from app_page fixture)
        mode: "chords", "drums", "mixing", or "full"
    """
    wait_and_click(page, "welcome-start-button")
    wait_for_visible(page, "session-modal")
    wait_and_click(page, f"session-mode-{mode}")
    wait_and_click(page, "session-modal-continue")
    wait_for_visible(page, "prompt-input")


# =============================================================================
# Test 1: Welcome → Modal → Session Created
# =============================================================================

@pytest.mark.e2e
def test_welcome_to_session_modal(app_page):
    """User lands on welcome screen and opens the session modal."""
    page = app_page

    # Welcome screen visible
    wait_for_visible(page, "welcome-start-button")

    # Click start → modal opens
    wait_and_click(page, "welcome-start-button")

    # Modal is visible with mode options
    wait_for_visible(page, "session-modal")


@pytest.mark.e2e
def test_select_mode_and_continue(app_page):
    """User selects a mode and clicks continue to start the session."""
    page = app_page

    # Navigate to modal
    wait_and_click(page, "welcome-start-button")
    wait_for_visible(page, "session-modal")

    # Select "Chords + Melody" mode
    wait_and_click(page, "session-mode-chords")

    # Click continue
    wait_and_click(page, "session-modal-continue")

    # Modal closes, workspace visible with prompt input
    wait_for_visible(page, "prompt-input")


# =============================================================================
# Test 2: Generate Chord Progression
# =============================================================================

@pytest.mark.e2e
def test_generate_chord_progression(app_page):
    """User enters a mood prompt and gets a full chord response."""
    page = app_page
    navigate_to_workspace(page, "chords")

    # Type a prompt and generate
    fill_and_submit(page, "prompt-input", "melancholic lo-fi", "generate-button")

    # Wait for chord row to appear (generation complete)
    wait_for_visible(page, "chord-row", timeout=15000)

    # Verify all panels rendered
    wait_for_visible(page, "validation-badge")
    wait_for_visible(page, "teaching-note-section")
    wait_for_visible(page, "ableton-steps-section")
    wait_for_visible(page, "also-try-section")
    wait_for_visible(page, "melody-direction-panel")


@pytest.mark.e2e
def test_generate_drum_pattern(app_page):
    """User enters a drum prompt and gets a drum grid response."""
    page = app_page
    navigate_to_workspace(page, "drums")

    # Generate
    fill_and_submit(page, "prompt-input", "trap beat", "generate-button")

    # Verify drum grid appears
    wait_for_visible(page, "drum-grid-block", timeout=15000)


@pytest.mark.e2e
def test_generate_sound_engineering(app_page):
    """User asks a sound engineering question and gets the SE panel."""
    page = app_page
    navigate_to_workspace(page, "chords")

    # Generate SE response
    fill_and_submit(page, "prompt-input", "how do I sidechain my bass", "generate-button")

    # Verify SE panel appears
    wait_for_visible(page, "sound-engineering-panel", timeout=15000)


# =============================================================================
# Test 3: Keep Confirmation + Stage Advance
# =============================================================================

@pytest.mark.e2e
def test_keep_advances_stage(app_page):
    """After generation, clicking Keep confirms the stage and advances."""
    page = app_page
    navigate_to_workspace(page, "chords")

    # Generate a progression
    fill_and_submit(page, "prompt-input", "melancholic lo-fi", "generate-button")
    wait_for_visible(page, "chord-row", timeout=15000)

    # Click Keep
    wait_and_click(page, "keep-button")

    # Verify stage advanced — sidebar visible, prompt input ready for next stage
    wait_for_visible(page, "progress-sidebar")
    wait_for_visible(page, "prompt-input")


# =============================================================================
# Test 4: Artist Blend
# =============================================================================

@pytest.mark.e2e
def test_artist_blend_shows_panel(app_page):
    """Artist blend prompt shows the blend attribution panel."""
    page = app_page
    navigate_to_workspace(page, "chords")

    # Generate blend
    fill_and_submit(
        page, "prompt-input",
        "Massive Attack meets Deadmau5",
        "generate-button",
    )

    # Verify blend panel appears
    wait_for_visible(page, "artist-blend-panel", timeout=15000)


# =============================================================================
# Test 5: Full Journey (integration)
# =============================================================================

@pytest.mark.e2e
def test_full_journey_welcome_to_keep(app_page):
    """Complete journey: welcome → modal → generate → verify → keep."""
    page = app_page

    # 1. Welcome
    wait_for_visible(page, "welcome-start-button")
    wait_and_click(page, "welcome-start-button")

    # 2. Modal — select chords mode
    wait_for_visible(page, "session-modal")
    wait_and_click(page, "session-mode-chords")
    wait_and_click(page, "session-modal-continue")

    # 3. Generate
    wait_for_visible(page, "prompt-input")
    fill_and_submit(page, "prompt-input", "dark epic in A minor", "generate-button")

    # 4. Verify all output panels
    wait_for_visible(page, "chord-row", timeout=15000)
    wait_for_visible(page, "validation-badge")
    wait_for_visible(page, "teaching-note-section")
    wait_for_visible(page, "ableton-steps-section")
    wait_for_visible(page, "also-try-section")
    wait_for_visible(page, "melody-direction-panel")

    # 5. Keep
    wait_and_click(page, "keep-button")

    # 6. Ready for next stage
    wait_for_visible(page, "prompt-input")
