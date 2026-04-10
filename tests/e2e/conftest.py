"""
E2E test configuration for Playwright.

Reusable template: to adapt for a new project, change:
  - FRONTEND_URL: where the frontend dev server runs
  - BACKEND_URL: where the API server runs
  - The data-testid selectors in the test files

Prerequisites:
  1. Backend running:  uvicorn api.main:app --port 8000
  2. Frontend running: cd frontend && npm run dev  (port 5173)
  3. Playwright installed: pip install playwright && python -m playwright install chromium
"""

import pytest
from playwright.sync_api import sync_playwright

# --- Project-specific URLs (change per project) ---
FRONTEND_URL = "http://localhost:5173"
BACKEND_URL = "http://localhost:8000"


@pytest.fixture(scope="session")
def browser():
    """Launch a single browser instance for the entire test session."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    """Create a fresh browser page (tab) for each test."""
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    yield page
    context.close()


@pytest.fixture
def app_page(page):
    """Navigate to the frontend and wait for initial load."""
    page.goto(FRONTEND_URL)
    # Wait for the React app to mount — look for the root container
    # TODO: requires data-testid="app-root" on the root div in App.jsx
    page.wait_for_selector("[data-testid='app-root']", timeout=10000)
    return page
