from concierge.llm import get_client

from .models import Conversation

WORKSPACE_LINKS = [
    ("overview", "Overview", "crm:overview", "layout-dashboard"),
    ("inbox", "Team inbox", "crm:inbox", "inbox"),
    ("leads", "Lead pipeline", "crm:leads", "users-round"),
    ("analytics", "Analytics", "crm:analytics", "bar-chart"),
]
PAGE_TITLES = {key: label for key, label, *_ in WORKSPACE_LINKS} | {"demo": "Live demo"}


def workspace(request):
    if not request.path.startswith("/dashboard/") or not request.user.is_authenticated:
        return {}
    url_name = request.resolver_match.url_name if request.resolver_match else ""
    return {
        "workspace_links": WORKSPACE_LINKS,
        "embed": request.GET.get("embed") == "1" or "embed=1" in request.headers.get("HX-Current-URL", ""),
        "page_title": PAGE_TITLES.get(url_name, "Workspace"),
        "ai_enabled": get_client() is not None,
        "open_count": Conversation.objects.filter(status=Conversation.Status.OPEN).count(),
    }
