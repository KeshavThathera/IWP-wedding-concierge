"""Staff workspace. Every view requires a signed-in user.

Interactive actions (inbox updates, moving leads) are plain POSTs that also
work without JavaScript; when sent by HTMX they return just the changed panel.
"""

from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from concierge.ai import draft_staff_reply

from . import analytics
from .models import Conversation, Lead, Message
from .seed import DEMO_PASSWORD, DEMO_USERNAME, seed_demo
from .services import assign, is_typing, post_staff_reply, release, set_status, set_typing


def is_htmx(request: HttpRequest) -> bool:
    return request.headers.get("HX-Request") == "true"


class LoginView(auth_views.LoginView):
    template_name = "crm/login.html"
    redirect_authenticated_user = True
    extra_context = {"demo_username": DEMO_USERNAME, "demo_password": DEMO_PASSWORD}


def _greeting() -> str:
    hour = timezone.localtime().hour
    return "morning" if hour < 12 else "afternoon" if hour < 17 else "evening"


@login_required
def overview(request: HttpRequest):
    conversations = Conversation.objects.prefetch_related("messages")
    segments, total = analytics.department_mix()
    leads = Lead.objects.all()
    lead_count = leads.count()
    qualified = leads.exclude(stage=Lead.Stage.NEW).count()
    cards = [
        ("Conversations", conversations.count(), f"{conversations.filter(status=Conversation.Status.OPEN).count()} open right now"),
        ("Qualified leads", qualified, f"{round(qualified / max(lead_count, 1) * 100)}% of all leads"),
        (
            "Needs attention",
            conversations.filter(priority=Conversation.Priority.HIGH).exclude(status=Conversation.Status.RESOLVED).count(),
            "High-priority, unresolved",
        ),
        ("Celebrations won", leads.filter(stage=Lead.Stage.CONVERTED).count(), f"{lead_count} in the pipeline"),
    ]
    return render(
        request,
        "crm/overview.html",
        {
            "nav": "overview",
            "today": timezone.localdate(),
            "greeting": _greeting(),
            "cards": cards,
            "recent": conversations[:6],
            "segments": segments,
            "segment_total": total,
            "top_leads": leads.exclude(stage=Lead.Stage.CONVERTED).order_by("-score")[:3],
        },
    )


def _inbox_context(request: HttpRequest, selected_id=None) -> dict:
    department = request.GET.get("department", "") or request.POST.get("department", "")
    status = request.GET.get("status", "") or request.POST.get("status_filter", "")
    conversations = Conversation.objects.select_related("assigned_to").prefetch_related(
        Prefetch("messages", queryset=Message.objects.select_related("author"))
    )
    filtered = conversations
    if department:
        filtered = filtered.filter(department=department)
    if status:
        filtered = filtered.filter(status=status)
    filtered = list(filtered)
    selected_id = selected_id or request.GET.get("c")
    selected = next((c for c in filtered if str(c.pk) == str(selected_id)), filtered[0] if filtered else None)
    return {
        "nav": "inbox",
        "conversations": filtered,
        "selected": selected,
        "department": department,
        "status": status,
        "departments": sorted(set(Conversation.objects.values_list("department", flat=True))),
        "statuses": Conversation.Status.choices,
    }


@login_required
def inbox(request: HttpRequest):
    context = _inbox_context(request)
    if request.GET.get("partial") == "list":  # polled every few seconds to surface new activity
        return render(request, "crm/_inbox_list.html", context)
    template = "crm/_inbox_panel.html" if is_htmx(request) else "crm/inbox.html"
    return render(request, template, context)


@login_required
@require_POST
def conversation_action(request: HttpRequest, pk: int):
    """Assign, change status, save a note or reply. One endpoint keeps the panel re-render simple."""
    conversation = get_object_or_404(Conversation, pk=pk)
    action = request.POST.get("action")
    note_saved = False
    draft = draft_error = None
    if action == "toggle_owner" and conversation.assigned_to_id:
        release(conversation)
    elif action == "toggle_owner" or action == "take_over":
        assign(conversation, request.user)
    elif action == "status" and request.POST.get("value") in Conversation.Status.values:
        set_status(conversation, request.POST["value"], request.user)
    elif action == "note":
        conversation.note = request.POST.get("note", "").strip()[:2000]
        conversation.save(update_fields=["note"])
        note_saved = True
    elif action == "draft" and conversation.assigned_to_id:
        transcript = [(_speaker(m, conversation), m.text) for m in conversation.messages.select_related("author")]
        name = request.user.get_full_name() or request.user.username
        draft = draft_staff_reply(transcript, conversation.customer, conversation.department, name)
        draft_error = draft is None
    elif action == "reply" and conversation.assigned_to_id and (text := request.POST.get("text", "").strip()):
        post_staff_reply(conversation, request.user, text[:2000])

    if is_htmx(request):
        return render(
            request,
            "crm/_inbox_panel.html",
            {**_inbox_context(request, selected_id=pk), "note_saved": note_saved, "draft": draft, "draft_error": draft_error},
        )
    return redirect(f"{reverse('crm:inbox')}?c={pk}")


@login_required
@require_GET
def thread_updates(request: HttpRequest, pk: int):
    """Polled by the open inbox thread: rendered new messages since ``after``, plus visitor typing."""
    conversation = get_object_or_404(Conversation, pk=pk)
    try:
        after = int(request.GET.get("after", 0))
    except ValueError:
        after = 0
    new = list(conversation.messages.filter(id__gt=after).select_related("author"))
    html = render_to_string("crm/_messages.html", {"messages_list": new, "selected": conversation}, request=request) if new else ""
    return JsonResponse(
        {
            "html": html,
            "cursor": new[-1].pk if new else after,
            "visitorTyping": is_typing(conversation.pk, "visitor"),
            "status": conversation.status,
            "statusLabel": conversation.get_status_display(),
            "assigned": conversation.assigned_to_id is not None,
        }
    )


@login_required
@require_POST
def staff_typing(request: HttpRequest, pk: int):
    set_typing(get_object_or_404(Conversation, pk=pk).pk, "agent")
    return JsonResponse({"ok": True})


def _speaker(message: Message, conversation: Conversation) -> str:
    if message.role == Message.Role.VISITOR:
        return conversation.customer
    if message.role == Message.Role.AGENT:
        return message.author.get_full_name() if message.author else "Staff"
    return "Concierge"


@login_required
def leads(request: HttpRequest):
    return render(request, "crm/leads.html", {"nav": "leads", **_board_context()})


def _board_context() -> dict:
    all_leads = list(Lead.objects.all())
    return {"columns": [(stage, [lead for lead in all_leads if lead.stage == stage]) for stage in Lead.Stage], "stages": Lead.Stage.choices}


@login_required
@require_POST
def move_lead(request: HttpRequest, pk: int):
    lead = get_object_or_404(Lead, pk=pk)
    if (stage := request.POST.get("stage")) in Lead.Stage.values:
        lead.stage = stage
        lead.save(update_fields=["stage"])
    if is_htmx(request):
        return render(request, "crm/_board.html", _board_context())
    return redirect("crm:leads")


@login_required
def demo(request: HttpRequest):
    """Live handoff demo: the public site (in a phone frame) and the team inbox side by side."""
    return render(request, "crm/demo.html", {"nav": "demo"})


@login_required
def analytics_view(request: HttpRequest):
    segments, total = analytics.department_mix()
    return render(
        request,
        "crm/analytics.html",
        {
            "nav": "analytics",
            "segments": segments,
            "segment_total": total,
            "stats": analytics.pipeline_stats(),
            "funnel": analytics.lead_funnel(),
            "destinations": analytics.popular_destinations(),
            "topics": analytics.visitor_topics(),
        },
    )


@login_required
@require_POST
def reset_demo(request: HttpRequest):
    seed_demo()
    messages.success(request, "Demo data has been reset.")
    return redirect("crm:overview")
