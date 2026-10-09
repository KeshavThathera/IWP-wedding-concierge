"""Public website and the concierge chat endpoints.

Chat state lives in the visitor's session; nothing is written to the database
until the conversation is handed off to a person.
"""

import json

from django.http import HttpRequest, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from crm.models import Conversation, Message
from crm.services import add_visitor_message, create_handoff, is_typing, live_status, set_typing

from .ai import enhance_reply
from .engine import QUICK_ACTIONS, TEAM_CHOICES, ConciergeState, ask_for_team, take_turn
from .llm import get_client
from .routing import accepted_offer, decide_team, visitor_choice

SESSION_KEY = "concierge"
MAX_MESSAGE_LENGTH = 1000

DESTINATIONS = [
    {
        "city": "Udaipur",
        "region": "Rajasthan",
        "note": "Lakeside palaces, sunset terraces and quiet, intimate grandeur.",
        "position": "15% 60%",
    },
    {
        "city": "Jaipur",
        "region": "Rajasthan",
        "note": "Pink-city courtyards, heritage havelis and celebrations at a royal scale.",
        "position": "62% 30%",
    },
    {
        "city": "Jodhpur",
        "region": "Rajasthan",
        "note": "Blue-city fort ramparts for dramatic, desert-edge evenings.",
        "position": "95% 45%",
    },
    {
        "city": "Goa",
        "region": "West coast",
        "note": "Barefoot ceremonies, sunlit coastlines and relaxed multi-day festivities.",
        "position": "40% 85%",
    },
]
PILLARS = [
    (
        "I",
        "Listens first",
        "Every enquiry—whether a wedding, a career or a partnership—is understood before it is routed. No forms, no menus.",
    ),
    (
        "II",
        "Asks with care",
        "One gentle question at a time captures destination, guest count, season and style, the way a senior planner would.",
    ),
    (
        "III",
        "Hands over gracefully",
        "The right specialist receives a summary, the full conversation and a reference—before they pick up the phone.",
    ),
]
JOURNEY = [
    ("Welcome", "A warm greeting in English, हिन्दी or Hinglish, available at any hour."),
    ("Understand", "Intent is recognised—wedding sales, client servicing, careers, vendors or finance."),
    ("Qualify", "Destination, guests, dates and budget are gathered conversationally."),
    ("Introduce", "A prepared handoff arrives in the team inbox and lead pipeline."),
]
SAMPLE_PROMPTS = [
    "I’m planning a Jaipur wedding for 250 guests.",
    "Main Udaipur mein shaadi plan kar raha hoon.",
    "I’m a photographer and would love to collaborate.",
    "I’m already a client and need urgent help.",
    "I need a copy of my invoice.",
    "I would like to speak to a person.",
]


@ensure_csrf_cookie
def home(request: HttpRequest):
    return render(
        request,
        "concierge/home.html",
        {
            "destinations": DESTINATIONS,
            "pillars": PILLARS,
            "journey": JOURNEY,
            "prompts": SAMPLE_PROMPTS,
        },
    )


def _load(request: HttpRequest) -> ConciergeState:
    return ConciergeState.from_dict(request.session.get(SESSION_KEY))


def _serialize(message: Message) -> dict:
    data = {"id": message.pk, "role": message.role, "text": message.text, "ai": message.ai_generated}
    if message.role == Message.Role.AGENT and message.author:
        data["author"] = message.author.get_full_name() or message.author.username
    return data


def _conversation(state: ConciergeState) -> Conversation | None:
    """The visitor's own handed-off conversation; the id only ever comes from their session."""
    if not state.conversation_id:
        return None
    return Conversation.objects.select_related("assigned_to").filter(pk=state.conversation_id).first()


def _live(conversation: Conversation) -> dict:
    agent = conversation.assigned_to
    name = (agent.get_full_name() or agent.username) if agent else None
    last = conversation.messages.order_by("-id").values_list("id", flat=True).first()
    return {
        "status": live_status(conversation),
        "agent": {"name": name, "initials": "".join(w[0] for w in name.split()[:2]).upper()} if name else None,
        "agentTyping": is_typing(conversation.pk, "agent"),
        "cursor": last or 0,
    }


def _payload(state: ConciergeState, handoff=None) -> dict:
    conversation = _conversation(state)
    if conversation:
        messages = [_serialize(m) for m in conversation.messages.select_related("author")]
    else:
        messages = [{"role": m.role, "text": m.text, "ai": m.ai} for m in state.messages]
    return {
        "messages": messages,
        "aiEnabled": get_client() is not None,
        "department": str(state.department),
        "ticket": state.ticket,
        "quickActions": _quick_actions(state, conversation),
        "handoff": handoff,
        "live": _live(conversation) if conversation else None,
    }


def _quick_actions(state: ConciergeState, conversation: Conversation | None) -> list[str]:
    if conversation:
        return []
    if state.flow.choosing_team:
        return list(TEAM_CHOICES)
    return list(QUICK_ACTIONS) if len(state.messages) == 1 else []


def _read_text(request: HttpRequest) -> tuple[str | None, JsonResponse | None]:
    try:
        text = str(json.loads(request.body or b"{}").get("text", "")).strip()
    except (ValueError, AttributeError):
        return None, JsonResponse({"error": "Invalid JSON."}, status=400)
    if not text or len(text) > MAX_MESSAGE_LENGTH:
        return None, JsonResponse({"error": f"Message must be 1–{MAX_MESSAGE_LENGTH} characters."}, status=400)
    return text, None


@require_GET
def chat_state(request: HttpRequest):
    return JsonResponse(_payload(_load(request)))


@require_POST
def chat_message(request: HttpRequest):
    text, error = _read_text(request)
    if error:
        return error
    state = _load(request)

    if state.ticket:  # Handed off: the visitor is now talking to the team, not the concierge.
        conversation = _conversation(state)
        if conversation is None or live_status(conversation) == "closed":
            return JsonResponse({"error": "This conversation has been closed. Start a new one."}, status=409)
        new = add_visitor_message(conversation, text)
        return JsonResponse({"new": [_serialize(m) for m in new], "live": _live(conversation)})

    turn = take_turn(state, text)
    if not request.session.session_key:
        request.session.save()
    enhance_reply(state, turn, text, budget_scope=request.session.session_key)
    handoff = None
    if turn.is_handoff:
        # The visitor wants a person: pick the right team (their own choice, Gemini, or rules), or ask them.
        if turn.team_chosen:
            routing = visitor_choice(state.department, text)
        elif turn.accepted_offer:
            routing = accepted_offer(state.department)
        else:
            routing = decide_team(state, request.session.session_key)
        if routing.department is None:
            ask_for_team(state, turn.lang)
            request.session[SESSION_KEY] = state.to_dict()
            return JsonResponse(_payload(state))
        conversation = create_handoff(state, routing)
        handoff = {
            "ticket": conversation.ticket,
            "department": conversation.department,
            "inboxUrl": f"{reverse('crm:inbox')}?c={conversation.pk}",
        }
    request.session[SESSION_KEY] = state.to_dict()
    return JsonResponse(_payload(state, handoff))


@require_GET
def chat_live(request: HttpRequest):
    """Polled by the widget after handoff: new messages since ``after``, plus status and typing."""
    conversation = _conversation(_load(request))
    if conversation is None:
        return JsonResponse({"error": "No live conversation."}, status=404)
    try:
        after = int(request.GET.get("after", 0))
    except ValueError:
        after = 0
    new = conversation.messages.filter(id__gt=after).select_related("author")
    return JsonResponse({"new": [_serialize(m) for m in new], "live": _live(conversation)})


@require_POST
def chat_typing(request: HttpRequest):
    conversation = _conversation(_load(request))
    if conversation is None:
        return JsonResponse({"error": "No live conversation."}, status=404)
    set_typing(conversation.pk, "visitor")
    return JsonResponse({"ok": True})


@require_POST
def chat_reset(request: HttpRequest):
    request.session.pop(SESSION_KEY, None)
    return JsonResponse(_payload(ConciergeState()))
