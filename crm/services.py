"""Business operations shared by views, the API and tests."""

import copy
import logging
import secrets
import threading

from django.conf import settings
from django.core.cache import cache
from django.db import close_old_connections, transaction
from django.utils import timezone

from concierge.ai import summarise_handoff
from concierge.engine import TEAM_BLURBS, ChatMessage, ConciergeState, Department, extract_lead
from concierge.routing import RoutingDecision

from .models import Conversation, Lead, Message

HANDOFF_CONFIRMATION = (
    "Thank you. I’m connecting you with our {department} team, {blurb}. Someone will join this chat shortly. Your reference is {ticket}."
)
logger = logging.getLogger(__name__)
WAITING_ACK = "Thank you, I’ve added that to your conversation. The team will reply right here as soon as someone joins."
TYPING_TTL = 5  # seconds a typing signal stays fresh


def new_ticket() -> str:
    while True:
        ticket = f"IWP-{secrets.randbelow(9000) + 1000}"
        if not Conversation.objects.filter(ticket=ticket).exists():
            return ticket


# Handoff --------------------------------------------------------------------------


def create_handoff(state: ConciergeState, routing: RoutingDecision | None = None) -> Conversation:
    """Persist a finished concierge conversation as a live ticket (and a lead for wedding enquiries)."""
    if routing and routing.department:
        state.department = routing.department
    department = state.department
    details = extract_lead(state) if department == Department.WEDDING_SALES else None
    if details and details.summary_line():
        summary = f"Wedding enquiry from the website concierge: {details.summary_line()}. Visitor asked to be introduced to a planner."
    else:
        summary = f"New {department.lower()} enquiry from the website concierge. Visitor requested a human handoff."
    snapshot = copy.deepcopy(state)  # the transcript as it stood at handoff, for the AI summary
    with transaction.atomic():
        conversation = _persist_handoff(state, details, summary, summary_ai=False, routing=routing)

    # The visitor is connected now; the AI summary (a slow network call) replaces the rule-based one when ready.
    if settings.AI_SUMMARY_IN_BACKGROUND:
        threading.Thread(target=_write_ai_summary, args=(conversation.pk, snapshot, department), daemon=True).start()
    else:
        _write_ai_summary(conversation.pk, snapshot, department)
        conversation.refresh_from_db()
    return conversation


def _write_ai_summary(conversation_id: int, state: ConciergeState, department: str) -> None:
    try:
        if ai_summary := summarise_handoff(state, department):
            Conversation.objects.filter(pk=conversation_id).update(summary=ai_summary, summary_ai=True)
    except Exception:  # never let a background summary failure surface anywhere
        logger.exception("AI summary failed for conversation %s", conversation_id)
    finally:
        if settings.AI_SUMMARY_IN_BACKGROUND:
            close_old_connections()  # this thread opened its own database connection


def _persist_handoff(state: ConciergeState, details, summary: str, *, summary_ai: bool, routing: RoutingDecision | None) -> Conversation:
    now = timezone.now()
    department = state.department
    ticket = new_ticket()
    state.messages.append(
        ChatMessage("assistant", HANDOFF_CONFIRMATION.format(department=department, blurb=TEAM_BLURBS[department], ticket=ticket))
    )

    conversation = Conversation.objects.create(
        ticket=ticket,
        department=department,
        priority=Conversation.Priority.HIGH if department == Department.CLIENT_SERVICING else Conversation.Priority.MEDIUM,
        summary=summary,
        summary_ai=summary_ai,
        routed_by=routing.source if routing else "rules",
        routing_confidence=routing.confidence if routing else None,
        routing_reason=routing.reason[:400] if routing else "",
        created_at=now,
        updated_at=now,
    )
    Message.objects.bulk_create(
        [Message(conversation=conversation, role=m.role, text=m.text, ai_generated=m.ai, created_at=now) for m in state.messages]
        + [Message(conversation=conversation, role=Message.Role.SYSTEM, text=f"Waiting for the {department} team to join", created_at=now)]
    )
    state.ticket, state.conversation_id = ticket, conversation.pk
    if details and details.has_signal:
        Lead.objects.create(
            name="Website visitor",
            contact=details.contact or "To be collected",
            destination=details.destination or "To be decided",
            guests=details.guests or 0,
            budget=details.budget or "To be discussed",
            event_date=f"{details.month} (year TBD)" if details.month else "Flexible",
            venue_style=details.style or "To be discussed",
            contact_method=details.contact_method or "To be collected",
            stage=Lead.Stage.QUALIFIED if details.is_qualified else Lead.Stage.NEW,
            score=86 if details.is_qualified else 62,
            conversation=conversation,
            created_at=now,
        )
    return conversation


# Live chat ------------------------------------------------------------------------


def _touch(conversation: Conversation, status: str | None = None) -> None:
    conversation.updated_at = timezone.now()
    fields = ["updated_at"]
    if status:
        conversation.status = status
        fields.append("status")
    conversation.save(update_fields=fields)


def add_system_message(conversation: Conversation, text: str) -> Message:
    return Message.objects.create(conversation=conversation, role=Message.Role.SYSTEM, text=text, created_at=timezone.now())


def add_visitor_message(conversation: Conversation, text: str) -> list[Message]:
    """A visitor writes after handoff. Returns the new messages (theirs, plus a one-off ack while nobody has joined)."""
    created = [Message.objects.create(conversation=conversation, role=Message.Role.VISITOR, text=text, created_at=timezone.now())]
    if conversation.assigned_to_id is None and not conversation.messages.filter(role=Message.Role.ASSISTANT, text=WAITING_ACK).exists():
        created.append(
            Message.objects.create(conversation=conversation, role=Message.Role.ASSISTANT, text=WAITING_ACK, created_at=timezone.now())
        )
    clear_typing(conversation.pk, "visitor")
    _touch(conversation, Conversation.Status.OPEN)  # the ball is in the team's court
    return created


def post_staff_reply(conversation: Conversation, user, text: str) -> Message:
    message = Message.objects.create(conversation=conversation, role=Message.Role.AGENT, author=user, text=text, created_at=timezone.now())
    clear_typing(conversation.pk, "agent")
    _touch(conversation, Conversation.Status.WAITING)  # now waiting on the customer
    return message


def assign(conversation: Conversation, user) -> None:
    """Give the conversation to ``user`` and tell the visitor someone has joined."""
    if conversation.assigned_to_id == user.pk:
        return
    conversation.assigned_to = user
    conversation.save(update_fields=["assigned_to"])
    add_system_message(conversation, f"{_name(user)} from {conversation.department} joined the chat")
    _touch(conversation, Conversation.Status.OPEN)


def release(conversation: Conversation) -> None:
    if conversation.assigned_to is None:
        return
    add_system_message(conversation, f"{_name(conversation.assigned_to)} left the chat")
    conversation.assigned_to = None
    conversation.save(update_fields=["assigned_to"])
    _touch(conversation)


def set_status(conversation: Conversation, status: str, user) -> None:
    previous = conversation.status
    if status == previous:
        return
    if status == Conversation.Status.RESOLVED:
        add_system_message(conversation, f"{_name(user)} closed this conversation")
    elif previous == Conversation.Status.RESOLVED:
        add_system_message(conversation, f"{_name(user)} reopened this conversation")
    _touch(conversation, status)


def live_status(conversation: Conversation) -> str:
    if conversation.status == Conversation.Status.RESOLVED:
        return "closed"
    return "connected" if conversation.assigned_to_id else "waiting"


def _name(user) -> str:
    return user.get_full_name() or user.username


# Typing indicators (short-lived cache flags; no database writes) --------------------


def set_typing(conversation_id: int, who: str) -> None:
    cache.set(f"typing:{conversation_id}:{who}", True, TYPING_TTL)


def clear_typing(conversation_id: int, who: str) -> None:
    cache.delete(f"typing:{conversation_id}:{who}")


def is_typing(conversation_id: int, who: str) -> bool:
    return bool(cache.get(f"typing:{conversation_id}:{who}"))
