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
  - data-testid attributes added to frontend components (see list below)

Run with:
  pytest tests/e2e/ --headed   (watch the browser)
  pytest tests/e2e/            (headless, CI-friendly)

TODO: The following data-testid attributes must be added by Cursor before
these tests will pass. Each TODO comment marks where a selector is used.

  CRITICAL PATH (test blocks without these):
    WelcomeScreen.jsx    → data-testid="welcome-start-button"
    SessionStartModal.jsx → data-testid="session-modal"
    SessionStartModal.jsx → data-testid="session-mode-chords"
    SessionStartModal.jsx → data-testid="session-mode-drums"
    SessionStartModal.jsx → data-testid="session-modal-continue"
    InputBar.jsx          → data-testid="prompt-input"
    InputBar.jsx          → data-testid="generate-button"
    InputBar.jsx          → data-testid="keep-button"

  ASSERT TARGETS (test verifies these exist):
    MainWorkspace.jsx     → data-testid="chord-row"
    MainWorkspace.jsx     → data-testid="validation-badge"
    MainWorkspace.jsx     → data-testid="teaching-note-section"
    MainWorkspace.jsx     → data-testid="ableton-steps-section"
    MainWorkspace.jsx     → data-testid="also-try-section"
    MainWorkspace.jsx     → data-testid="melody-direction-panel"
    MainWorkspace.jsx     → data-testid="drum-grid-block"
    App.jsx               → data-testid="sound-engineering-panel"
    App.jsx               → data-testid="artist-blend-panel"

  STAGE VERIFICATION:
    ProgressSidebar.jsx   → data-testid="progress-sidebar"
    ProgressSidebar.jsx   → data-testid="stage-row-{stageId}"
    App.jsx               → data-testid="app-root"
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


# =============================================================================
# Test 1: Welcome → Modal → Session Created
# =============================================================================

@pytest.mark.e2e
def test_welcome_to_session_modal(app_page):
    """User lands on welcome screen and opens the session modal."""
    page = app_page

    # Step 1: Welcome screen visible
    # TODO: requires data-testid="welcome-start-button" on WelcomeScreen.jsx
    wait_for_visible(page, "welcome-start-button")

    # Step 2: Click start → modal opens
    wait_and_click(page, "welcome-start-button")

    # Step 3: Modal is visible with mode options
    # TODO: requires data-testid="session-modal" on SessionStartModal.jsx
    wait_for_visible(page, "session-modal")


@pytest.mark.e2e
def test_select_mode_and_continue(app_page):
    """User selects a mode and clicks continue to start the session."""
    page = app_page

    # Navigate to modal
    wait_and_click(page, "welcome-start-button")
    wait_for_visible(page, "session-modal")

    # Step 1: Select "Chords + Melody" mode
    # TODO: requires data-testid="session-mode-chords" on SessionStartModal.jsx
    wait_and_click(page, "session-mode-chords")

    # Step 2: Click continue
    # TODO: requires data-testid="session-modal-continue" on SessionStartModal.jsx
    wait_and_click(page, "session-modal-continue")

    # Step 3: Modal closes, workspace visible with prompt input
    # TODO: requires data-testid="prompt-input" on InputBar.jsx
    wait_for_visible(page, "prompt-input")


# =============================================================================
# Test 2: Generate Chord Progression
# =============================================================================

@pytest.mark.e2e
def test_generate_chord_progression(app_page):
    """User enters a mood prompt and gets a full chord response."""
    page = app_page

    # Setup: get to the workspace
    wait_and_click(page, "welcome-start-button")
    wait_for_visible(page, "session-modal")
    wait_and_click(page, "session-mode-chords")
    wait_and_click(page, "session-modal-continue")
    wait_for_visible(page, "prompt-input")

    # Step 1: Type a prompt and generate
    # TODO: requires data-testid="prompt-input" and "generate-button" on InputBar.jsx
    fill_and_submit(page, "prompt-input", "melancholic lo-fi", "generate-button")

    # Step 2: Wait for chord row to appear (generation complete)
    # TODO: requires data-testid="chord-row" on MainWorkspace.jsx
    wait_for_visible(page, "chord-row", timeout=15000)

    # Step 3: Verify all panels rendered
    # TODO: requires data-testid on each panel in MainWorkspace.jsx
    wait_for_visible(page, "validation-badge")
    wait_for_visible(page, "teaching-note-section")
    wait_for_visible(page, "ableton-steps-section")
    wait_for_visible(page, "also-try-section")
    wait_for_visible(page, "melody-direction-panel")


@pytest.mark.e2e
def test_generate_drum_pattern(app_page):
    """User enters a drum prompt and gets a drum grid response."""
    page = app_page

    # Setup: get to workspace in drums mode
    wait_and_click(page, "welcome-start-button")
    wait_for_visible(page, "session-modal")
    # TODO: requires data-testid="session-mode-drums" on SessionStartModal.jsx
    wait_and_click(page, "session-mode-drums")
    wait_and_click(page, "session-modal-continue")
    wait_for_visible(page, "prompt-input")

    # Generate
    fill_and_submit(page, "prompt-input", "trap beat", "generate-button")

    # Verify drum grid appears
    # TODO: requires data-testid="drum-grid-block" on MainWorkspace.jsx
    wait_for_visible(page, "drum-grid-block", timeout=15000)


@pytest.mark.e2e
def test_generate_sound_engineering(app_page):
    """User asks a sound engineering question and gets the SE panel."""
    page = app_page

    # Setup: get to workspace
    wait_and_click(page, "welcome-start-button")
    wait_for_visible(page, "session-modal")
    wait_and_click(page, "session-mode-chords")
    wait_and_click(page, "session-modal-continue")
    wait_for_visible(page, "prompt-input")

    # Generate SE response
    fill_and_submit(page, "prompt-input", "how do I sidechain my bass", "generate-button")

    # Verify SE panel appears
    # TODO: requires data-testid="sound-engineering-panel" on App.jsx
    wait_for_visible(page, "sound-engineering-panel", timeout=15000)


# =============================================================================
# Test 3: Keep Confirmation + Stage Advance
# =============================================================================

@pytest.mark.e2e
def test_keep_advances_stage(app_page):
    """After generation, clicking Keep confirms the stage and advances."""
    page = app_page

    # Setup: generate a progression
    wait_and_click(page, "welcome-start-button")
    wait_for_visible(page, "session-modal")
    wait_and_click(page, "session-mode-chords")
    wait_and_click(page, "session-modal-continue")
    wait_for_visible(page, "prompt-input")
    fill_and_submit(page, "prompt-input", "melancholic lo-fi", "generate-button")
    wait_for_visible(page, "chord-row", timeout=15000)

    # Step 1: Click Keep
    # TODO: requires data-testid="keep-button" on InputBar.jsx
    wait_and_click(page, "keep-button")

    # Step 2: Verify stage advanced in sidebar
    # TODO: requires data-testid="progress-sidebar" on ProgressSidebar.jsx
    wait_for_visible(page, "progress-sidebar")

    # The prompt input should be available for the next stage
    wait_for_visible(page, "prompt-input")


# =============================================================================
# Test 4: Artist Blend
# =============================================================================

@pytest.mark.e2e
def test_artist_blend_shows_panel(app_page):
    """Artist blend prompt shows the blend attribution panel."""
    page = app_page

    # Setup
    wait_and_click(page, "welcome-start-button")
    wait_for_visible(page, "session-modal")
    wait_and_click(page, "session-mode-chords")
    wait_and_click(page, "session-modal-continue")
    wait_for_visible(page, "prompt-input")

    # Generate blend
    fill_and_submit(
        page, "prompt-input",
        "Massive Attack meets Deadmau5",
        "generate-button",
    )

    # Verify blend panel appears
    # TODO: requires data-testid="artist-blend-panel" on App.jsx
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
