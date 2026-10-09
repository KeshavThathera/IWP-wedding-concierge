import io
import json
import urllib.error

import pytest
from django.core.cache import cache
from django.urls import reverse

from concierge import llm
from concierge.ai import enhance_reply
from concierge.engine import ConciergeState, take_turn
from crm.models import Conversation, Message
from crm.seed import DEMO_PASSWORD, DEMO_USERNAME, seed_demo


class FakeLLM:
    model = "fake-model"

    def __init__(self, reply="December to February is ideal in Udaipur: pleasant days and cool evenings.", error=None):
        self.reply, self.error, self.calls = reply, error, []

    def generate(self, system, turns, *, temperature=0.6, max_tokens=400, json_schema=None, deadline=None):
        if json_schema:
            raise llm.LLMError("no routing opinion")
        self.calls.append({"system": system, "turns": turns})
        if self.error:
            raise self.error
        return self.reply


@pytest.fixture
def fake_llm():
    client = FakeLLM()
    llm.set_client(client)
    cache.clear()
    yield client
    llm.set_client(None)


def say(client, text):
    return client.post(reverse("concierge:chat-message"), data=json.dumps({"text": text}), content_type="application/json").json()


def test_question_mid_qualification_gets_answer_plus_next_question(fake_llm):
    state = ConciergeState()
    take_turn(state, "Plan my wedding")
    text = "What is the best month for Udaipur?"
    turn = take_turn(state, text)

    assert enhance_reply(state, turn, text, "visitor-1")
    reply = state.messages[-1]
    assert reply.ai
    assert reply.text.startswith("December to February is ideal")
    assert reply.text.endswith("Approximately how many guests are you hoping to welcome?")
    assert "Do not ask any question yourself" in fake_llm.calls[0]["system"]


def test_question_is_not_recorded_as_an_answer():
    state = ConciergeState()
    take_turn(state, "I'm planning a wedding in Goa")
    turn = take_turn(state, "Is the monsoon a bad idea?")
    assert "guests" not in turn.flow.answers


def test_generic_fallback_is_replaced_by_free_reply(fake_llm):
    state = ConciergeState()
    turn = take_turn(state, "Hello! What do you do?")
    assert turn.is_fallback
    assert enhance_reply(state, turn, "Hello! What do you do?", "visitor-2")
    assert state.messages[-1].text == fake_llm.reply
    assert "You may end with at most one short, relevant question" in fake_llm.calls[0]["system"]


def test_plain_answers_do_not_call_the_model(fake_llm):
    state = ConciergeState()
    take_turn(state, "Plan my wedding")
    turn = take_turn(state, "Jaipur")
    assert not enhance_reply(state, turn, "Jaipur", "visitor-3")
    assert fake_llm.calls == []


def test_model_failure_keeps_the_rule_based_reply(fake_llm):
    fake_llm.error = llm.LLMError("quota exceeded")
    state = ConciergeState()
    take_turn(state, "Plan my wedding")
    turn = take_turn(state, "What is the best month for Udaipur?")
    rule_reply = state.messages[-1].text
    assert not enhance_reply(state, turn, "What is the best month for Udaipur?", "visitor-4")
    assert state.messages[-1].text == rule_reply
    assert not state.messages[-1].ai


def test_no_api_key_means_rules_only(settings):
    settings.GEMINI_API_KEY = ""
    llm.set_client(None)
    assert llm.get_client() is None
    state = ConciergeState()
    turn = take_turn(state, "What do you do?")
    assert not enhance_reply(state, turn, "What do you do?", "visitor-5")


def test_history_ends_with_the_question_and_excludes_the_replaced_reply(fake_llm):
    state = ConciergeState()
    take_turn(state, "Plan my wedding")
    turn = take_turn(state, "Which is better, Jaipur or Udaipur?")
    rule_reply = state.messages[-1].text
    enhance_reply(state, turn, "Which is better, Jaipur or Udaipur?", "visitor-6")
    turns = fake_llm.calls[0]["turns"]
    assert turns[-1] == llm.Turn("user", "Which is better, Jaipur or Udaipur?")
    assert rule_reply not in [t.text for t in turns]


def test_per_visitor_budget_is_enforced(fake_llm, settings):
    settings.GEMINI_MAX_PER_VISITOR_HOUR = 2
    results = []
    for _ in range(3):
        state = ConciergeState()
        turn = take_turn(state, "What do you do?")
        results.append(enhance_reply(state, turn, "What do you do?", "same-visitor"))
    assert results == [True, True, False]


def test_long_or_markdown_replies_are_cleaned(fake_llm):
    fake_llm.reply = "**Udaipur** is " + "lovely " * 200
    state = ConciergeState()
    turn = take_turn(state, "Tell me about Udaipur")
    enhance_reply(state, turn, "Tell me about Udaipur", "visitor-7")
    text = state.messages[-1].text
    assert "**" not in text
    assert len(text.split("\n\n")[0]) <= 701


@pytest.mark.django_db
def test_chat_endpoint_marks_ai_messages(client, fake_llm):
    say(client, "Plan my wedding")
    data = say(client, "What is the best month for Udaipur?")
    assert data["aiEnabled"] is True
    assert data["messages"][-1]["ai"] is True


@pytest.mark.django_db
def test_handoff_uses_ai_summary_and_persists_ai_flags(client, fake_llm):
    say(client, "Plan my wedding")
    say(client, "What is the best month for Udaipur?")
    fake_llm.reply = "Visitor plans an Udaipur wedding and asked about the best season."
    data = say(client, "I want to speak to a person")

    conversation = Conversation.objects.get(ticket=data["ticket"])
    assert conversation.summary_ai
    assert conversation.summary == "Visitor plans an Udaipur wedding and asked about the best season."
    assert conversation.messages.filter(ai_generated=True).count() == 1


@pytest.mark.django_db
def test_handoff_summary_falls_back_to_rules(client, fake_llm):
    fake_llm.error = llm.LLMError("timeout")
    data = say(client, "I'm planning a Jaipur wedding for 250 guests. Can I speak to someone?")
    conversation = Conversation.objects.get(ticket=data["ticket"])
    assert not conversation.summary_ai
    assert "Jaipur · 250 guests" in conversation.summary


@pytest.mark.django_db
def test_staff_ai_draft_prefills_the_reply_box(client, fake_llm):
    seed_demo()
    client.login(username=DEMO_USERNAME, password=DEMO_PASSWORD)
    conversation = Conversation.objects.get(ticket="IWP-1036")
    url = reverse("crm:conversation-action", args=[conversation.pk])
    client.post(url, {"action": "take_over"})
    fake_llm.reply = "Namaste Rohan and Mira! I would love to share a few Goa beach options on a quick call."

    response = client.post(url, {"action": "draft"}, HTTP_HX_REQUEST="true")
    assert fake_llm.reply in response.content.decode()
    assert "Review and edit before sending" in response.content.decode()
    assert "Rohan & Mira" in fake_llm.calls[0]["turns"][0].text
    assert not conversation.messages.filter(role=Message.Role.AGENT).exists()


def test_gemini_client_builds_the_documented_request(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured.update(url=request.full_url, headers=dict(request.header_items()), body=json.loads(request.data), timeout=timeout)
        payload = {"candidates": [{"content": {"parts": [{"text": "thinking…", "thought": True}, {"text": "Namaste!"}]}}]}
        return io.BytesIO(json.dumps(payload).encode())

    monkeypatch.setattr(llm.urllib.request, "urlopen", fake_urlopen)
    client = llm.GeminiClient("test-key", "gemini-test", timeout=5)
    turns = [llm.Turn("model", "Welcome"), llm.Turn("user", "Hi"), llm.Turn("user", "Anyone there?")]
    assert client.generate("Be kind", turns, temperature=0.3, max_tokens=100) == "Namaste!"

    assert captured["url"].endswith("/models/gemini-test:generateContent")
    assert captured["headers"]["X-goog-api-key"] == "test-key"
    assert captured["timeout"] == pytest.approx(5, abs=0.05)
    body = captured["body"]
    assert body["systemInstruction"]["parts"][0]["text"] == "Be kind"
    assert body["contents"] == [{"role": "user", "parts": [{"text": "Hi\n\nAnyone there?"}]}]
    assert body["generationConfig"] == {"temperature": 0.3, "maxOutputTokens": 100, "thinkingConfig": {"thinkingLevel": "minimal"}}


@pytest.mark.parametrize(
    "failure",
    [
        urllib.error.HTTPError("u", 429, "Too Many Requests", {}, io.BytesIO(b'{"error": "quota"}')),
        urllib.error.URLError("offline"),
        TimeoutError("slow"),
    ],
)
def test_gemini_client_wraps_failures(monkeypatch, failure):
    def boom(request, timeout):
        raise failure

    monkeypatch.setattr(llm.urllib.request, "urlopen", boom)
    with pytest.raises(llm.LLMError):
        llm.GeminiClient("k", "m").generate("s", [llm.Turn("user", "hi")])


def test_gemini_client_rejects_empty_or_blocked_answers(monkeypatch):
    payload = {"candidates": [{"finishReason": "SAFETY", "content": {"parts": []}}]}
    monkeypatch.setattr(llm.urllib.request, "urlopen", lambda request, timeout: io.BytesIO(json.dumps(payload).encode()))
    with pytest.raises(llm.LLMError, match="SAFETY"):
        llm.GeminiClient("k", "m").generate("s", [llm.Turn("user", "hi")])


def _http_error(code):
    return urllib.error.HTTPError("u", code, "error", {}, io.BytesIO(b'{"error": "x"}'))


@pytest.mark.parametrize(
    ("first_failure", "tries_fallback"),
    [
        (_http_error(503), True),
        (_http_error(429), True),
        (TimeoutError("slow"), True),
        (_http_error(400), False),
        (_http_error(403), False),
    ],
)
def test_gemini_fails_over_to_the_next_model_only_when_unavailable(monkeypatch, first_failure, tries_fallback):
    called = []
    ok = {"candidates": [{"content": {"parts": [{"text": "Namaste!"}]}}]}

    def urlopen(request, timeout):
        model = request.full_url.split("/models/")[1].split(":")[0]
        called.append(model)
        if model == "primary":
            raise first_failure
        return io.BytesIO(json.dumps(ok).encode())

    monkeypatch.setattr(llm.urllib.request, "urlopen", urlopen)
    client = llm.GeminiClient("k", ["primary", "fallback"])
    if tries_fallback:
        assert client.generate("s", [llm.Turn("user", "hi")]) == "Namaste!"
        assert called == ["primary", "fallback"]
    else:
        with pytest.raises(llm.LLMError):
            client.generate("s", [llm.Turn("user", "hi")])
        assert called == ["primary"]


def test_gemini_reports_when_every_model_is_unavailable(monkeypatch):
    def overloaded(request, timeout):
        raise _http_error(503)

    monkeypatch.setattr(llm.urllib.request, "urlopen", overloaded)
    with pytest.raises(llm.LLMError, match="No Gemini model available"):
        llm.GeminiClient("k", ["a", "b"]).generate("s", [llm.Turn("user", "hi")])


def test_get_client_builds_the_configured_model_chain(settings):
    settings.GEMINI_API_KEY = "k"
    settings.GEMINI_MODEL = "gemini-3.5-flash"
    settings.GEMINI_FALLBACK_MODELS = ["gemini-3.1-flash-lite", "gemini-3.5-flash"]
    assert llm.get_client().models == ["gemini-3.5-flash", "gemini-3.1-flash-lite"]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Haan, February accha hai. Mausam suhana rehta hai aur shaadi ke", "Haan, February accha hai."),
        ("Winters are lovely! Evenings are cool and", "Winters are lovely!"),
        ("फ़रवरी अच्छा है। शाम को", "फ़रवरी अच्छा है।"),
    ],
)
def test_truncated_replies_are_cut_to_a_full_sentence(monkeypatch, text, expected):
    payload = {"candidates": [{"finishReason": "MAX_TOKENS", "content": {"parts": [{"text": text}]}}]}
    monkeypatch.setattr(llm.urllib.request, "urlopen", lambda request, timeout: io.BytesIO(json.dumps(payload).encode()))
    assert llm.GeminiClient("k", "m").generate("s", [llm.Turn("user", "hi")]) == expected


def test_thinking_config_can_be_disabled(monkeypatch):
    bodies = []

    def urlopen(request, timeout):
        bodies.append(json.loads(request.data))
        return io.BytesIO(json.dumps({"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}).encode())

    monkeypatch.setattr(llm.urllib.request, "urlopen", urlopen)
    llm.GeminiClient("k", "m", thinking_level="").generate("s", [llm.Turn("user", "hi")])
    assert "thinkingConfig" not in bodies[0]["generationConfig"]


def test_a_failing_model_is_skipped_during_its_cooldown(monkeypatch):
    called = []
    ok = {"candidates": [{"content": {"parts": [{"text": "Namaste!"}]}}]}

    def urlopen(request, timeout):
        model = request.full_url.split("/models/")[1].split(":")[0]
        called.append(model)
        if model == "primary":
            raise _http_error(429)
        return io.BytesIO(json.dumps(ok).encode())

    monkeypatch.setattr(llm.urllib.request, "urlopen", urlopen)
    client = llm.GeminiClient("k", ["primary", "fallback"])
    client.generate("s", [llm.Turn("user", "hi")])
    client.generate("s", [llm.Turn("user", "hi again")])
    assert called == ["primary", "fallback", "fallback"]


def test_one_deadline_covers_every_model(monkeypatch):
    timeouts = []

    def slow(request, timeout):
        timeouts.append(timeout)
        raise TimeoutError("slow")

    monkeypatch.setattr(llm.urllib.request, "urlopen", slow)
    client = llm.GeminiClient("k", ["a", "b", "c"], timeout=6)
    with pytest.raises(llm.LLMError):
        client.generate("s", [llm.Turn("user", "hi")], deadline=2)
    assert timeouts and all(t <= 2 for t in timeouts)


@pytest.mark.django_db
def test_handoff_does_not_wait_for_the_ai_summary(client, fake_llm, settings, monkeypatch):
    settings.AI_SUMMARY_IN_BACKGROUND = True
    started = []
    monkeypatch.setattr(
        "crm.services.threading.Thread", lambda target, args, daemon: type("T", (), {"start": lambda self: started.append(args)})()
    )
    data = say(client, "I'm planning a Jaipur wedding for 250 guests. Can I speak to someone?")
    conversation = Conversation.objects.get(ticket=data["ticket"])
    assert not conversation.summary_ai
    assert started and started[0][0] == conversation.pk


def test_the_fallback_model_keeps_part_of_the_budget(monkeypatch):
    timeouts = {}
    ok = {"candidates": [{"content": {"parts": [{"text": "Namaste!"}]}}]}

    def urlopen(request, timeout):
        model = request.full_url.split("/models/")[1].split(":")[0]
        timeouts[model] = timeout
        if model == "primary":
            raise TimeoutError("slow")
        return io.BytesIO(json.dumps(ok).encode())

    monkeypatch.setattr(llm.urllib.request, "urlopen", urlopen)
    assert llm.GeminiClient("k", ["primary", "fallback"], timeout=6).generate("s", [llm.Turn("user", "hi")], deadline=4) == "Namaste!"
    assert timeouts["primary"] == pytest.approx(2.4, abs=0.1)
