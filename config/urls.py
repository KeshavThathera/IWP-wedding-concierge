from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from crm.api import ConversationViewSet, LeadViewSet

router = DefaultRouter()
router.register("conversations", ConversationViewSet, basename="conversation")
router.register("leads", LeadViewSet, basename="lead")

urlpatterns = [
    path("", include("concierge.urls")),
    path("dashboard/", include("crm.urls")),
    path("api/", include(router.urls)),
    path("admin/", admin.site.urls),
]
