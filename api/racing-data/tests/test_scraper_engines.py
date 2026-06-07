"""
Tests for scraper engines (Webclaw, Scrapling).

Run: PYTHONPATH=/home/evo/evo_01/01_evolution/api python3 -m pytest api/racing-data/tests/test_scraper_engines.py -v

Note: Integration tests require API keys / venv and are skipped by default.
"""

import pytest
import os
import sys

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engines.webclaw import WebclawEngine
from engines.scrapling import ScraplingEngine


# ── Unit Tests (no external deps) ───────────────────────────────────

def test_webclaw_engine_init_without_key():
    """WebclawEngine should initialize but raise on fetch without API key."""
    # Clear any env var for this test
    old_key = os.environ.get("WEBCLAW_API_KEY")
    if old_key:
        del os.environ["WEBCLAW_API_KEY"]

    try:
        engine = WebclawEngine()
        assert engine.api_key == ""
        assert engine.api_url == "https://api.webclaw.io/v1/extract"

        # fetch should raise without key
        with pytest.raises(RuntimeError, match="WEBCLAW_API_KEY not configured"):
            engine.fetch("https://example.com/")
    finally:
        if old_key:
            os.environ["WEBCLAW_API_KEY"] = old_key


def test_webclaw_engine_init_with_key(monkeypatch):
    """WebclawEngine should use provided API key."""
    monkeypatch.setenv("WEBCLAW_API_KEY", "test-key-123")
    engine = WebclawEngine()
    assert engine.api_key == "test-key-123"


def test_scrapling_engine_init():
    """ScraplingEngine should initialize (may raise if not installed)."""
    engine = ScraplingEngine()
    assert engine._fetcher is None


def test_scrapling_engine_get_fetcher_missing(monkeypatch):
    """_get_fetcher should raise RuntimeError if scrapling not installed."""
    # Mock the import to fail
    import engines.scrapling as scrapling_module
    original_fetcher = scrapling_module.StealthyFetcher
    scrapling_module.StealthyFetcher = None

    try:
        engine = ScraplingEngine()
        with pytest.raises(RuntimeError, match="Scrapling not installed"):
            engine._get_fetcher()
    finally:
        scrapling_module.StealthyFetcher = original_fetcher


# ── Integration Tests (require external services) ───────────────────

# These are skipped by default. Run with:
#   WEBCLAW_API_KEY=xxx pytest api/racing-data/tests/test_scraper_engines.py::test_webclaw_engine_fetch -v -s

@pytest.mark.skipif(
    not os.getenv("WEBCLAW_API_KEY"),
    reason="WEBCLAW_API_KEY not configured"
)
def test_webclaw_engine_fetch():
    """Test WebclawEngine.fetch against a real URL."""
    engine = WebclawEngine()
    html = engine.fetch("https://example.com/")
    assert isinstance(html, str)
    assert len(html) > 100
    assert "Example Domain" in html


@pytest.mark.skipif(
    not os.getenv("WEBCLAW_API_KEY"),
    reason="WEBCLAW_API_KEY not configured"
)
def test_webclaw_engine_extract():
    """Test WebclawEngine.extract with a prompt."""
    engine = WebclawEngine()
    result = engine.extract(
        "https://example.com/",
        "Extract the page title and main heading as JSON"
    )
    assert isinstance(result, dict)


@pytest.mark.skip(
    reason="Scrapling requires specific venv activation"
)
def test_scrapling_engine_fetch():
    """Test ScraplingEngine.fetch against a real URL (requires venv)."""
    engine = ScraplingEngine()
    html = engine.fetch("https://example.com/")
    assert isinstance(html, str)
    assert len(html) > 100


# ── Fallback Chain Logic Tests ──────────────────────────────────────

def test_adapter_fallback_order():
    """Verify the fallback chain order in adapter: Webclaw → Scrapling."""
    from adapters import loveracing as adapter

    # Check fetch_html function exists
    assert hasattr(adapter, 'fetch_html')
    assert callable(adapter.fetch_html)

    # Verify the function uses Webclaw first, then Scrapling
    import inspect
    source = inspect.getsource(adapter.fetch_html)
    assert "WebclawEngine" in source
    assert "ScraplingEngine" in source
    # Webclaw should appear before Scrapling in the source
    webclaw_pos = source.find("WebclawEngine")
    scrapling_pos = source.find("ScraplingEngine")
    assert webclaw_pos < scrapling_pos


if __name__ == "__main__":
    pytest.main([__file__, "-v"])