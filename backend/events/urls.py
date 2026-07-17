from django.urls import path

from .views import EventDetailView, EventGroupChoicesView, EventListCreateView

app_name = "events"

urlpatterns = [
    path("", EventListCreateView.as_view(), name="event-list"),
    path("groups/", EventGroupChoicesView.as_view(), name="event-group-choices"),
    path("<int:pk>/", EventDetailView.as_view(), name="event-detail"),
]
