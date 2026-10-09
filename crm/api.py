"""REST API for the staff workspace (Django REST Framework).

Authenticated staff only. Browsable at /api/ when signed in.
"""

from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from . import analytics
from .models import Conversation, Lead, Message


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ["id", "role", "text", "created_at"]


class ConversationSerializer(serializers.ModelSerializer):
    assigned_to = serializers.CharField(source="assigned_to.get_full_name", default=None, read_only=True)
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = [
            "id",
            "ticket",
            "customer",
            "department",
            "status",
            "priority",
            "summary",
            "routed_by",
            "routing_confidence",
            "routing_reason",
            "assigned_to",
            "note",
            "created_at",
            "updated_at",
            "messages",
        ]
        read_only_fields = ["ticket", "customer", "department", "priority", "summary", "created_at", "updated_at"]


class LeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = [
            "id",
            "name",
            "contact",
            "destination",
            "guests",
            "budget",
            "event_date",
            "venue_style",
            "contact_method",
            "stage",
            "score",
            "conversation",
            "created_at",
        ]
        read_only_fields = ["conversation", "created_at"]


class ConversationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """List, read and update (status / note) conversations. Filter with ?department= and ?status=."""

    serializer_class = ConversationSerializer

    def get_queryset(self):
        qs = Conversation.objects.select_related("assigned_to").prefetch_related("messages")
        for field in ("department", "status"):
            if value := self.request.query_params.get(field):
                qs = qs.filter(**{field: value})
        return qs


class LeadViewSet(viewsets.ModelViewSet):
    """Full CRUD on leads. ``GET /api/leads/funnel/`` returns pipeline counts per stage."""

    serializer_class = LeadSerializer
    queryset = Lead.objects.all()

    @action(detail=False)
    def funnel(self, request):
        return Response(analytics.lead_funnel())
