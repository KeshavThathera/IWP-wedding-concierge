from django.conf import settings
from django.db import models

from concierge.engine import Department


class Conversation(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        WAITING = "waiting", "Waiting"
        RESOLVED = "resolved", "Resolved"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    ticket = models.CharField(max_length=20, unique=True)
    customer = models.CharField(max_length=120, default="Website visitor")
    department = models.CharField(max_length=40, choices=[(d.value, d.value) for d in Department], default=Department.GENERAL)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    summary = models.TextField(blank=True)
    summary_ai = models.BooleanField(default=False, help_text="Summary written by the language model.")
    routed_by = models.CharField(max_length=10, choices=[("ai", "Gemini"), ("rules", "Rules"), ("visitor", "Visitor")], default="rules")
    routing_confidence = models.FloatField(null=True, blank=True)
    routing_reason = models.CharField(max_length=400, blank=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="conversations"
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"{self.ticket} · {self.customer}"

    @property
    def latest_visitor_text(self) -> str:
        message = next((m for m in reversed(self.messages.all()) if m.role == Message.Role.VISITOR), None)
        return message.text if message else ""

    @property
    def awaiting_reply(self) -> bool:
        """No one on the team has answered since the visitor last wrote (automated replies don't count)."""
        if self.status == self.Status.RESOLVED:
            return False
        human = (Message.Role.VISITOR, Message.Role.AGENT)
        last = next((m for m in reversed(self.messages.all()) if m.role in human), None)
        return bool(last and last.role == Message.Role.VISITOR)

    @property
    def needs_attention(self) -> bool:
        return self.priority == self.Priority.HIGH and self.status != self.Status.RESOLVED


class Message(models.Model):
    class Role(models.TextChoices):
        VISITOR = "visitor", "Visitor"
        ASSISTANT = "assistant", "Concierge"
        AGENT = "agent", "Staff"
        SYSTEM = "system", "System"  # join / leave / close events shown to both sides

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=10, choices=Role.choices)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    text = models.TextField()
    ai_generated = models.BooleanField(default=False)
    created_at = models.DateTimeField()

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self) -> str:
        return f"{self.get_role_display()}: {self.text[:40]}"


class Lead(models.Model):
    class Stage(models.TextChoices):
        NEW = "new", "New"
        QUALIFIED = "qualified", "Qualified"
        CONTACTED = "contacted", "Contacted"
        CONSULTATION = "consultation", "Consultation booked"
        PROPOSAL = "proposal", "Proposal sent"
        CONVERTED = "converted", "Converted"

    name = models.CharField(max_length=120)
    contact = models.CharField(max_length=120, default="To be collected")
    destination = models.CharField(max_length=60, default="To be decided")
    guests = models.PositiveIntegerField(default=0)
    budget = models.CharField(max_length=60, default="To be discussed")
    event_date = models.CharField(max_length=60, default="Flexible")
    venue_style = models.CharField(max_length=60, default="To be discussed")
    contact_method = models.CharField(max_length=30, default="To be collected")
    stage = models.CharField(max_length=20, choices=Stage.choices, default=Stage.NEW)
    score = models.PositiveSmallIntegerField(default=60)
    conversation = models.ForeignKey(Conversation, null=True, blank=True, on_delete=models.SET_NULL, related_name="leads")
    created_at = models.DateTimeField()

    class Meta:
        ordering = ["-score", "-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_stage_display()})"
