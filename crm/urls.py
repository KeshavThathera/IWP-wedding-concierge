from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "crm"

urlpatterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", views.overview, name="overview"),
    path("inbox/", views.inbox, name="inbox"),
    path("inbox/<int:pk>/", views.conversation_action, name="conversation-action"),
    path("inbox/<int:pk>/updates/", views.thread_updates, name="thread-updates"),
    path("inbox/<int:pk>/typing/", views.staff_typing, name="staff-typing"),
    path("leads/", views.leads, name="leads"),
    path("leads/<int:pk>/move/", views.move_lead, name="move-lead"),
    path("analytics/", views.analytics_view, name="analytics"),
    path("demo/", views.demo, name="demo"),
    path("reset/", views.reset_demo, name="reset"),
]
