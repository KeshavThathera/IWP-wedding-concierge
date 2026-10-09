import json

import pytest
from django.urls import reverse

from crm.models import Conversation, Lead, Message
from crm.seed import DEMO_PASSWORD, DEMO_USERNAME, seed_demo

pytestmark = pytest.mark.django_db


@pytest.fixture
def demo():
    seed_demo()


@pytest.fixture
def staff(client, demo):
    assert client.login(username=DEMO_USERNAME, password=DEMO_PASSWORD)
    return client


def say(client, text):
    return client.post(reverse("concierge:chat-message"), data=json.dumps({"text": text}), content_type="application/json")


def test_home_renders_with_csrf_cookie(client):
    response = client.get(reverse("concierge:home"))
    assert response.status_code == 200
    assert b"Every grand celebration begins" in response.content
    assert "csrftoken" in response.cookies


def test_chat_state_starts_with_greeting(client):
    data = client.get(reverse("concierge:chat-state")).json()
    assert data["messages"][0]["role"] == "assistant"
    assert data["department"] == "General Support"
    assert len(data["quickActions"]) == 7


def test_full_wedding_chat_creates_ticket_and_qualified_lead(client):
    for text in [
        "I'm planning a Jaipur wedding for 250 guests.",
        "December 2027",
        "Around ₹1.5-2 Cr",
        "Heritage palace",
        "WhatsApp on +91 90000 12345",
    ]:
        assert say(client, text).status_code == 200
    data = say(client, "Yes please").json()

    assert data["handoff"]["department"] == "Wedding Sales"
    conversation = Conversation.objects.get(ticket=data["ticket"])
    assert conversation.messages.filter(role=Message.Role.VISITOR).count() == 6
    assert "Jaipur · 250 guests" in conversation.summary
    lead = Lead.objects.get(conversation=conversation)
    assert (lead.destination, lead.guests, lead.stage) == ("Jaipur", 250, Lead.Stage.QUALIFIED)
    assert data["handoff"]["inboxUrl"].endswith(f"?c={conversation.pk}")


def test_reset_starts_a_fresh_conversation_after_handoff(client):
    say(client, "I want to speak to a person")
    data = client.post(reverse("concierge:chat-reset")).json()
    assert data["live"] is None and data["ticket"] is None
    assert say(client, "Hello again").status_code == 200


def test_client_servicing_handoff_is_high_priority(client):
    say(client, "I'm already a client and need urgent help.")
    ticket = say(client, "yes").json()["ticket"]
    assert Conversation.objects.get(ticket=ticket).priority == Conversation.Priority.HIGH


@pytest.mark.parametrize("body", [b"not json", json.dumps({"text": ""}).encode(), json.dumps({"text": "x" * 1001}).encode()])
def test_chat_rejects_bad_input(client, body):
    response = client.post(reverse("concierge:chat-message"), data=body, content_type="application/json")
    assert response.status_code == 400


def test_chat_requires_csrf_token():
    from django.test import Client

    strict = Client(enforce_csrf_checks=True)
    assert strict.post(reverse("concierge:chat-message"), data="{}", content_type="application/json").status_code == 403


@pytest.mark.parametrize("name", ["crm:overview", "crm:inbox", "crm:leads", "crm:analytics"])
def test_workspace_requires_login(client, name):
    response = client.get(reverse(name))
    assert response.status_code == 302
    assert reverse("crm:login") in response["Location"]


@pytest.mark.parametrize("name", ["crm:overview", "crm:inbox", "crm:leads", "crm:analytics"])
def test_workspace_pages_render(staff, name):
    response = staff.get(reverse(name))
    assert response.status_code == 200
    assert b"Demo Manager" in response.content


def test_inbox_filters_by_department(staff):
    response = staff.get(reverse("crm:inbox"), {"department": "Finance"})
    assert [c.customer for c in response.context["conversations"]] == ["Vivan Malhotra"]


def test_take_over_reply_and_note(staff):
    conversation = Conversation.objects.get(ticket="IWP-1036")
    url = reverse("crm:conversation-action", args=[conversation.pk])
    staff.post(url, {"action": "reply", "text": "Ignored until assigned"})
    assert not conversation.messages.filter(role=Message.Role.AGENT).exists()

    staff.post(url, {"action": "take_over"})
    staff.post(url, {"action": "reply", "text": "Namaste! Sharing Goa ideas shortly."})
    response = staff.post(url, {"action": "note", "note": "Prefers evenings."}, HTTP_HX_REQUEST="true")

    conversation.refresh_from_db()
    assert conversation.assigned_to.username == DEMO_USERNAME
    assert conversation.note == "Prefers evenings."
    assert conversation.status == Conversation.Status.WAITING
    assert conversation.messages.last().role == Message.Role.AGENT
    assert response.templates[0].name == "crm/_inbox_panel.html"


def test_status_change_ignores_unknown_values(staff):
    conversation = Conversation.objects.get(ticket="IWP-1037")
    url = reverse("crm:conversation-action", args=[conversation.pk])
    staff.post(url, {"action": "status", "value": "resolved"})
    staff.post(url, {"action": "status", "value": "bogus"})
    conversation.refresh_from_db()
    assert conversation.status == Conversation.Status.RESOLVED


def test_move_lead(staff):
    lead = Lead.objects.get(name="Rohan & Mira")
    response = staff.post(reverse("crm:move-lead", args=[lead.pk]), {"stage": "contacted"}, HTTP_HX_REQUEST="true")
    lead.refresh_from_db()
    assert lead.stage == Lead.Stage.CONTACTED
    assert response.templates[0].name == "crm/_board.html"


def test_reset_restores_seed_data(staff):
    Lead.objects.all().delete()
    staff.post(reverse("crm:reset"))
    assert Lead.objects.count() == 6
    assert Conversation.objects.count() == 8


def test_api_requires_authentication(client, demo):
    assert client.get("/api/leads/").status_code == 403


def test_api_lists_and_filters_conversations(staff):
    data = staff.get("/api/conversations/", {"department": "HR and Careers"}).json()
    assert data["count"] == 2
    assert {"ticket", "messages", "status"} <= set(data["results"][0])


def test_api_updates_lead_stage(staff):
    lead = Lead.objects.get(name="Tara Anand")
    response = staff.patch(f"/api/leads/{lead.pk}/", data={"stage": "proposal"}, content_type="application/json")
    assert response.status_code == 200
    lead.refresh_from_db()
    assert lead.stage == Lead.Stage.PROPOSAL


def test_api_funnel(staff):
    funnel = staff.get("/api/leads/funnel/").json()
    assert funnel[0]["name"] == "New"
    assert funnel[0]["value"] == 6
