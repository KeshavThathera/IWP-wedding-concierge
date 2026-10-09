import pytest

from concierge.engine import (
    ConciergeState,
    Department,
    Flow,
    classify_topics,
    detect_department,
    detect_lang,
    extract_lead,
    take_turn,
)


def converse(*messages: str) -> tuple[ConciergeState, list]:
    state = ConciergeState()
    turns = [take_turn(state, m) for m in messages]
    return state, turns


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("I'm planning a Jaipur wedding for 250 guests.", Department.WEDDING_SALES),
        ("I'm a photographer and would love to collaborate on a wedding.", Department.VENDORS),
        ("Do you have any internships?", Department.HR_CAREERS),
        ("I need a copy of my invoice.", Department.FINANCE),
        ("I'm already a client and need urgent help.", Department.CLIENT_SERVICING),
        ("Can we feature you in our magazine? I work in media.", Department.MARKETING),
        ("Hello there", Department.GENERAL),
        ("Main Udaipur mein shaadi plan kar raha hoon.", Department.WEDDING_SALES),
    ],
)
def test_detect_department(text, expected):
    assert detect_department(text) == expected


def test_specific_routes_win_over_wedding_terms():
    assert detect_department("Wedding photographer here, keen to partner") == Department.VENDORS


def test_unrecognised_text_keeps_current_department():
    assert detect_department("250", current=Department.WEDDING_SALES) == Department.WEDDING_SALES


@pytest.mark.parametrize(("text", "lang"), [("Plan my wedding", "en"), ("Main shaadi plan kar raha hoon", "hi"), ("मुझे मदद चाहिए", "hi")])
def test_detect_lang(text, lang):
    assert detect_lang(text) == lang


def test_wedding_qualification_never_repeats_a_question():
    state, turns = converse(
        "I'm planning a Jaipur wedding for 250 guests.",
        "December 2027",
        "Around ₹1.5-2 Cr",
        "A heritage palace",
        "WhatsApp on +91 90000 12345",
    )
    replies = [t.reply for t in turns]
    assert "Jaipur is extraordinary" in replies[0] and "month or season" in replies[0]
    assert "budget" in replies[1]
    assert "palace, a fort" in replies[2]
    assert "phone, WhatsApp or email" in replies[3]
    assert "introduce you to our Wedding Sales team" in replies[4]
    assert len(set(replies)) == len(replies)
    assert not any("how many guests" in r for r in replies)
    assert state.flow.offered


def test_accepting_the_offer_requests_a_handoff():
    state, turns = converse("I'm planning a Jaipur wedding for 250 guests.", "December", "₹50 lakh", "Palace", "Email", "Yes please")
    assert turns[-1].is_handoff
    assert state.messages[-1].role == "visitor"


def test_declining_the_offer_keeps_the_conversation_open():
    _, turns = converse("I'm planning a Jaipur wedding for 250 guests.", "December", "₹50 lakh", "Palace", "Email", "No, not now")
    assert not turns[-1].is_handoff
    assert "no rush" in turns[-1].reply


def test_hinglish_is_sticky_for_the_whole_conversation():
    _, turns = converse("Main Udaipur mein shaadi plan kar raha hoon.", "150 log", "Agle saal February")
    assert turns[0].reply.startswith("Udaipur ek behtareen choice hai!")
    assert turns[1].lang == "hi" and "mahina" in turns[1].reply
    assert turns[2].lang == "hi" and "budget range" in turns[2].reply


def test_budget_question_starts_with_guest_count():
    _, turns = converse("Understand budgets", "200")
    assert "how many guests" in turns[0].reply
    assert turns[1].flow.answers == {"guests": "200"}
    assert "destination" in turns[1].reply


def test_asking_for_a_person_hands_off_immediately():
    state, turns = converse("I would like to speak to a person.")
    assert turns[0].is_handoff
    assert state.department == Department.GENERAL


def test_client_servicing_offers_urgent_handoff_then_accepts_yes():
    _, turns = converse("I'm already a client and need urgent help.", "Yes")
    assert "Shall I connect you" in turns[0].reply
    assert turns[1].is_handoff


def test_other_departments_collect_contact_then_offer_handoff():
    _, turns = converse("Do you have any jobs?", "nisha@example.com", "ok")
    assert "email address" in turns[0].reply
    assert "pass this conversation to our HR and Careers team" in turns[1].reply
    assert turns[2].is_handoff


def test_extract_lead_from_a_full_conversation():
    state, _ = converse(
        "I'm planning a Jaipur wedding for 250 guests.",
        "December 2027",
        "Around ₹1.5-2 Cr",
        "A heritage palace",
        "WhatsApp on +91 90000 12345",
    )
    lead = extract_lead(state)
    assert lead.destination == "Jaipur"
    assert lead.guests == 250
    assert lead.budget == "₹1.5-2 Cr"
    assert lead.month == "December"
    assert lead.style == "Heritage"
    assert lead.contact == "+91 90000 12345"
    assert lead.contact_method == "Whatsapp"
    assert lead.is_qualified


def test_state_round_trips_through_a_dict():
    state, _ = converse("Plan my wedding", "Goa")
    restored = ConciergeState.from_dict(state.to_dict())
    assert restored == state
    assert ConciergeState.from_dict(None).messages[0].role == "assistant"


def test_flow_defaults_are_independent():
    a, b = Flow(), Flow()
    a.asked.append("guests")
    assert b.asked == []


def test_classify_topics():
    assert classify_topics("What would a palace venue in Udaipur cost, budget wise?") == ["Destination & venue", "Budget guidance"]
    assert classify_topics("Hello") == []


def test_hypothetical_details_in_questions_are_not_recorded():
    _, turns = converse("Plan my wedding", "Can we host 300 guests in Goa?", "How much does a palace wedding cost in December?")
    answers = turns[-1].flow.answers
    assert "300 guests" in answers["guests"] and "Goa" in answers["destination"]
    assert "style" not in answers and "budget" not in answers and "date" not in answers
