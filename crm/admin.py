from django.contrib import admin

from .models import Conversation, Lead, Message

admin.site.site_header = "IWP Concierge · Admin"
admin.site.site_title = "IWP Concierge"


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    fields = ("created_at", "role", "author", "text")


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("ticket", "customer", "department", "status", "priority", "assigned_to", "updated_at")
    list_filter = ("department", "status", "priority")
    search_fields = ("ticket", "customer", "summary", "messages__text")
    inlines = [MessageInline]


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("name", "destination", "guests", "budget", "stage", "score", "created_at")
    list_filter = ("stage", "destination")
    list_editable = ("stage",)
    search_fields = ("name", "contact", "destination")
