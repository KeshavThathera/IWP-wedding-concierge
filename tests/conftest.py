import pytest
from django.core.cache import cache

from concierge import llm


@pytest.fixture(autouse=True)
def offline_rules_only(settings):
    settings.GEMINI_API_KEY = ""
    settings.AI_SUMMARY_IN_BACKGROUND = False
    llm.set_client(None)
    cache.clear()
    yield
    llm.set_client(None)
