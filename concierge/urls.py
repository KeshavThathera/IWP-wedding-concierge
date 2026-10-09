from django.urls import path

from . import views

app_name = "concierge"

urlpatterns = [
    path("", views.home, name="home"),
    path("concierge/state/", views.chat_state, name="chat-state"),
    path("concierge/messages/", views.chat_message, name="chat-message"),
    path("concierge/reset/", views.chat_reset, name="chat-reset"),
    path("concierge/live/", views.chat_live, name="chat-live"),
    path("concierge/typing/", views.chat_typing, name="chat-typing"),
]
