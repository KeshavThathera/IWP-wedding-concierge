import pytest
from django.core.cache import cache

from concierge import llm


@pytest.fixture(autouse=True)
def offline_rules_only(settings):
    """Tests never call the real Gemini API, even when a key is present in .env."""
    settings.GEMINI_API_KEY = ""
    settings.AI_SUMMARY_IN_BACKGROUND = False  # deterministic: summaries finish before assertions
    llm.set_client(None)
    cache.clear()
    yield
    llm.set_client(None)
