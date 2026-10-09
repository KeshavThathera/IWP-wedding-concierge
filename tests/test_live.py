"""Live chat between the visitor's widget and the staff inbox after a handoff."""

import json

import pytest
from django.test import Client
from django.urls import reverse

from crm.models import Conversation, Message
from crm.seed import DEMO_PASSWORD, DEMO_USERNAME, ensure_demo_user
from crm.services import WAITING_ACK

pytestmark = pytest.mark.django_db


def say(client, text):
    return client.post(reverse("concierge:chat-message"), data=json.dumps({"text": text}), content_type="application/json")


def poll(client, after=0):
    return client.get(reverse("concierge:chat-live"), {"after": after}).json()


@pytest.fixture
def handed_off(client):
    """A visitor who has just been handed off; returns (visitor client, conversation)."""
    data = say(client, "I’m planning a Jaipur wedding for 250 guests. Can I speak to someone?").json()
    return client, Conversation.objects.get(ticket=data["ticket"])


@pytest.fixture
def staff():
    ensure_demo_user()
    staff = Client()
    assert staff.login(username=DEMO_USERNAME, password=DEMO_PASSWORD)
    return staff


def act(staff, conversation, **data):
    return staff.post(reverse("crm:conversation-action", args=[conversation.pk]), data)


def test_handoff_switches_the_widget_to_live_mode(handed_off):
    client, conversation = handed_off
    data = client.get(reverse("concierge:chat-state")).json()
    assert data["live"]["status"] == "waiting"
    assert data["live"]["agent"] is None
    assert all("id" in m for m in data["messages"])  # transcript now comes from the database
    assert data["messages"][-1] == {**data["messages"][-1], "role": "system", "text": "Waiting for the Wedding Sales team to join"}
    assert data["live"]["cursor"] == conversation.messages.last().pk


def test_visitor_messages_reach_the_conversation_with_a_single_ack(handed_off):
    client, conversation = handed_off
    first = say(client, "Also, we love lakeside views").json()
    second = say(client, "And we need 40 rooms").json()
    assert [m["role"] for m in first["new"]] == ["visitor", "assistant"]
    assert first["new"][1]["text"] == WAITING_ACK
    assert [m["role"] for m in second["new"]] == ["visitor"]  # the ack is not repeated
    conversation.refresh_from_db()
    assert conversation.status == Conversation.Status.OPEN
    assert conversation.awaiting_reply


def test_full_round_trip_between_visitor_and_staff(handed_off, staff):
    client, conversation = handed_off
    cursor = poll(client)["live"]["cursor"]

    act(staff, conversation, action="take_over")
    joined = poll(client, cursor)
    assert joined["live"]["status"] == "connected"
    assert joined["live"]["agent"] == {"name": "Demo Manager", "initials": "DM"}
    assert joined["new"][-1]["text"] == "Demo Manager from Wedding Sales joined the chat"

    act(staff, conversation, action="reply", text="Namaste! Happy to help with Jaipur.")
    reply = poll(client, joined["live"]["cursor"])["new"]
    assert reply == [{**reply[0], "role": "agent", "author": "Demo Manager", "text": "Namaste! Happy to help with Jaipur."}]

    staff_cursor = conversation.messages.last().pk
    say(client, "Wonderful, thank you!")
    update = staff.get(reverse("crm:thread-updates", args=[conversation.pk]), {"after": staff_cursor}).json()
    assert "Wonderful, thank you!" in update["html"]
    assert update["cursor"] > staff_cursor


def test_typing_indicators_flow_both_ways(handed_off, staff):
    client, conversation = handed_off
    act(staff, conversation, action="take_over")
    assert poll(client)["live"]["agentTyping"] is False

    staff.post(reverse("crm:staff-typing", args=[conversation.pk]))
    assert poll(client)["live"]["agentTyping"] is True

    client.post(reverse("concierge:chat-typing"))
    update = staff.get(reverse("crm:thread-updates", args=[conversation.pk]), {"after": 0}).json()
    assert update["visitorTyping"] is True

    say(client, "Here is my message")  # sending clears the visitor's typing flag
    assert staff.get(reverse("crm:thread-updates", args=[conversation.pk])).json()["visitorTyping"] is False


def test_closing_the_conversation_ends_the_live_chat(handed_off, staff):
    client, conversation = handed_off
    act(staff, conversation, action="take_over")
    act(staff, conversation, action="status", value="resolved")
    data = poll(client)
    assert data["live"]["status"] == "closed"
    assert data["new"][-1]["text"] == "Demo Manager closed this conversation"
    assert say(client, "Hello?").status_code == 409

    act(staff, conversation, action="status", value="open")
    assert poll(client)["live"]["status"] == "connected"
    assert say(client, "Hello again").status_code == 200


def test_releasing_posts_a_leave_message(handed_off, staff):
    client, conversation = handed_off
    act(staff, conversation, action="toggle_owner")
    act(staff, conversation, action="toggle_owner")
    texts = list(conversation.messages.filter(role=Message.Role.SYSTEM).values_list("text", flat=True))
    assert texts[-2:] == ["Demo Manager from Wedding Sales joined the chat", "Demo Manager left the chat"]
    assert poll(client)["live"]["status"] == "waiting"


def test_visitors_can_only_reach_their_own_conversation(handed_off):
    _, conversation = handed_off
    stranger = Client()
    assert stranger.get(reverse("concierge:chat-live")).status_code == 404
    assert stranger.post(reverse("concierge:chat-typing")).status_code == 404
    # Even guessing an id in the query string reveals nothing: the conversation comes from the session.
    assert stranger.get(reverse("concierge:chat-live"), {"conversation": conversation.pk}).status_code == 404


def test_staff_live_endpoints_require_login(handed_off):
    _, conversation = handed_off
    anonymous = Client()
    for url in [reverse("crm:thread-updates", args=[conversation.pk]), reverse("crm:inbox") + "?partial=list"]:
        assert anonymous.get(url).status_code == 302


def test_inbox_list_partial_marks_conversations_awaiting_reply(handed_off, staff):
    client, _ = handed_off
    say(client, "Is anyone there?")
    html = staff.get(reverse("crm:inbox"), {"partial": "list"}).content.decode()
    assert "Awaiting reply" in html
    assert 'hx-swap-oob="true"' in html  # conversation count refreshes too


def test_live_demo_page_frames_site_and_compact_inbox(staff):
    html = staff.get(reverse("crm:demo")).content.decode()
    assert '?chat=open"' in html and "/dashboard/inbox/?embed=1" in html

    embedded = staff.get(reverse("crm:inbox"), {"embed": "1"})
    page = embedded.content.decode()
    assert 'class="bg-ivory embed' in page  # compact layout
    assert "data-sidebar" not in page  # no staff sidebar inside the frame
    assert embedded["X-Frame-Options"] == "SAMEORIGIN"


def test_live_demo_requires_login():
    assert Client().get(reverse("crm:demo")).status_code == 302
