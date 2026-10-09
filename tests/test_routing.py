import json

import pytest
from django.urls import reverse

from concierge import llm
from concierge.engine import TEAM_CHOICES, TEAM_QUESTION, ConciergeState, Department, route_by_rules, take_turn
from concierge.routing import decide_team
from crm.models import Conversation

D = Department

# "ASK" = not enough information to pick a team
SCENARIOS = [
    (
        D.CLIENT_SERVICING,
        ["Our wedding is next week and the decorator hasn't confirmed the mandap design", "Can I talk to someone please?"],
    ),
    (
        D.CLIENT_SERVICING,
        ["Hi, we booked our December wedding with you last month", "We need to change the guest count, can I speak to my planner?"],
    ),
    (D.CLIENT_SERVICING, ["meri shaadi ki booking hai aapke saath, urgent help chahiye", "kisi se baat karni hai"]),
    (D.FINANCE, ["Plan my wedding", "Actually I paid the advance but haven't received a receipt", "Connect me to someone"]),
    (D.FINANCE, ["I want to talk to someone in accounts about a refund"]),
    (D.VENDORS, ["We run a floral decor studio in Jaipur and would love to work on your weddings", "Who can I speak to?"]),
    (D.VENDORS, ["I'm a wedding photographer. Can I speak to someone about joining your vendor list?"]),
    (D.VENDORS, ["We own a heritage haveli in Jaipur that hosts weddings. Would IWP list us as a venue?", "can someone contact me"]),
    (D.HR_CAREERS, ["Are you hiring wedding planners in Delhi?", "I'd like to talk to a person"]),
    (D.HR_CAREERS, ["I have 5 years of experience in event production", "Is there an opening? Can I talk to someone"]),
    (D.MARKETING, ["I write for a bridal magazine and want to feature your Udaipur weddings", "Can I talk to someone?"]),
    (
        D.MARKETING,
        ["Hi, I'm a lifestyle creator with 200k followers", "Would love a collab on your next palace wedding, who do I talk to?"],
    ),
    (D.WEDDING_SALES, ["Hello!", "We're getting married next year and want something in Rajasthan", "Can a planner call me?"]),
    (D.WEDDING_SALES, ["What kind of events do you help with?", "Great, can I speak to someone about my sister's wedding?"]),
    (D.WEDDING_SALES, ["My fiance and I are looking at Udaipur for Nov 2027, around 150 guests", "Can a planner call me tomorrow?"]),
    (
        D.CLIENT_SERVICING,
        [
            "Plan my wedding",
            "Udaipur",
            "What's the best month for an Udaipur wedding?",
            "I booked with you already and need to change our guest count, can someone call me?",
        ],
    ),
    ("ASK", ["Speak to a person"]),
    ("ASK", ["Hi", "I want to talk to a human"]),
]


def converse(messages):
    state = ConciergeState()
    for text in messages:
        turn = take_turn(state, text)
        if turn.is_handoff:
            break
    return state, turn


@pytest.mark.parametrize(("expected", "messages"), SCENARIOS, ids=[m[-1][:40] for _, m in SCENARIOS])
def test_rules_route_every_scenario_correctly_or_ask(expected, messages):
    state, turn = converse(messages)
    assert turn.is_handoff, "the last message should be recognised as asking for a person"
    route = route_by_rules(state.visitor_texts)
    assert (route.department or "ASK") == expected


@pytest.mark.parametrize(
    ("text", "department"),
    [
        ("I need a photographer for my wedding", D.WEDDING_SALES),
        ("My partner and I are getting married", D.WEDDING_SALES),
        ("We would love to partner with IWP", D.VENDORS),
        ("What's the cost per person for a sangeet?", D.WEDDING_SALES),
    ],
)
def test_ambiguous_words_resolve_correctly(text, department):
    assert route_by_rules([text]).department == department


@pytest.mark.parametrize("text", ["What's the cost per person?", "Someone told me about you", "Can you speak Hindi?"])
def test_ordinary_questions_are_not_handoff_requests(text):
    _, turn = converse([text])
    assert not turn.is_handoff


class RoutingLLM:
    model = "fake"

    def __init__(self, department="Client Servicing", confidence=0.95, raw=None):
        self.raw = raw or json.dumps(
            {"department": department, "confidence": confidence, "reason": "Existing booking with an urgent issue"}
        )

    def generate(self, system, turns, *, temperature=0.6, max_tokens=400, json_schema=None, deadline=None):
        if json_schema:
            assert json_schema["properties"]["department"]["enum"] == [d.value for d in Department]
            return self.raw
        raise llm.LLMError("not used in these tests")


@pytest.fixture
def with_llm():
    def install(**kwargs):
        llm.set_client(RoutingLLM(**kwargs))

    yield install
    llm.set_client(None)


def test_confident_ai_decision_wins_and_notes_disagreement(with_llm):
    with_llm(department="Client Servicing", confidence=0.92)
    state, _ = converse(["Plan a wedding in Goa for 200 guests", "Can someone call me?"])
    decision = decide_team(state)
    assert (decision.department, decision.source) == (D.CLIENT_SERVICING, "ai")
    assert "keyword rules suggested Wedding Sales" in decision.reason


@pytest.mark.parametrize(
    "kwargs",
    [
        {"confidence": 0.4},
        {"department": "General Support", "confidence": 0.99},
        {"raw": "not json"},
        {"raw": '{"department": "Astrology"}'},
    ],
)
def test_unsure_or_invalid_ai_falls_back_to_rules(with_llm, kwargs):
    with_llm(**kwargs)
    state, _ = converse(["I need a copy of my invoice", "Can I talk to someone?"])
    decision = decide_team(state)
    assert (decision.department, decision.source) == (D.FINANCE, "rules")


def test_nobody_sure_means_ask_the_visitor(with_llm):
    with_llm(department="General Support", confidence=0.5)
    state, _ = converse(["Hi", "I want to talk to a human"])
    assert decide_team(state).department is None


def say(client, text):
    return client.post(reverse("concierge:chat-message"), data=json.dumps({"text": text}), content_type="application/json").json()


@pytest.mark.django_db
def test_unclear_request_asks_which_team_then_hands_off_to_the_choice(client):
    data = say(client, "I want to talk to a human")
    assert data["ticket"] is None
    assert data["messages"][-1]["text"] == TEAM_QUESTION["en"]
    assert data["quickActions"] == list(TEAM_CHOICES)

    data = say(client, "An existing booking")
    conversation = Conversation.objects.get(ticket=data["ticket"])
    assert conversation.department == D.CLIENT_SERVICING
    assert conversation.routed_by == "visitor"
    assert "who look after confirmed bookings" in conversation.messages.filter(role="assistant").last().text
    assert data["live"]["status"] == "waiting"


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("answer", "department"), [("it's about my invoice", D.FINANCE), ("hmm not sure", D.GENERAL), ("Something else", D.GENERAL)]
)
def test_any_answer_to_the_team_question_completes_the_handoff(client, answer, department):
    say(client, "Speak to a person")
    data = say(client, answer)
    assert Conversation.objects.get(ticket=data["ticket"]).department == department


@pytest.mark.django_db
def test_hinglish_visitors_are_asked_in_hinglish(client):
    data = say(client, "mujhe kisi se baat karni hai")
    assert data["messages"][-1]["text"] == TEAM_QUESTION["hi"]


@pytest.mark.django_db
def test_clear_request_hands_off_directly_with_routing_metadata(client):
    data = say(client, "I paid the advance but have no receipt. Can I talk to someone?")
    conversation = Conversation.objects.get(ticket=data["ticket"])
    assert (conversation.department, conversation.routed_by) == (D.FINANCE, "rules")
    assert conversation.routing_confidence == 1.0
    assert "who handle invoices, payments and refunds" in conversation.messages.filter(role="assistant").last().text


@pytest.mark.django_db
def test_ai_routing_is_stored_for_staff(client, with_llm):
    with_llm(department="Client Servicing", confidence=0.95)
    data = say(client, "Our mehendi is on Saturday and the band still isn't confirmed, please get someone")
    conversation = Conversation.objects.get(ticket=data["ticket"])
    assert (conversation.department, conversation.routed_by, conversation.routing_confidence) == (D.CLIENT_SERVICING, "ai", 0.95)
    assert conversation.routing_reason == "Existing booking with an urgent issue"


def test_ai_guess_without_any_evidence_is_not_trusted(with_llm):
    with_llm(department="Wedding Sales", confidence=0.85)
    state, _ = converse(["Hello", "I want to talk to a human"])
    assert decide_team(state).department is None


def test_ai_with_supporting_evidence_needs_less_certainty(with_llm):
    with_llm(department="Client Servicing", confidence=0.85)
    state, _ = converse(["We booked our wedding with you", "Can someone call me?"])
    assert decide_team(state).department == D.CLIENT_SERVICING


@pytest.mark.parametrize("text", ["who can help?", "Who do I contact about this?", "please get someone", "I need a person"])
def test_more_ways_of_asking_for_a_person(text):
    _, turn = converse([text])
    assert turn.is_handoff


def test_vague_request_continues_the_conversations_topic():
    state, _ = converse(["Plan my wedding", "Jaipur", "December 2027", "Around 2 crore", "Palace", "Can someone call me?"])
    decision = decide_team(state)
    assert decision.department == D.WEDDING_SALES


@pytest.mark.django_db
def test_accepting_the_concierges_offer_goes_straight_to_that_team(client):
    for text in ["I'm planning a Jaipur wedding for 250 guests.", "December 2027", "Around ₹1.5-2 Cr", "Palace", "WhatsApp"]:
        say(client, text)
    data = say(client, "Yes please")
    conversation = Conversation.objects.get(ticket=data["ticket"])
    assert (conversation.department, conversation.routed_by) == (D.WEDDING_SALES, "visitor")
    assert "accepted the concierge" in conversation.routing_reason
