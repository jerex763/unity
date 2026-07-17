from django.urls import path

from .views import (
    EventDetailView,
    EventGroupChoicesView,
    EventListCreateView,
    EventRegistrationCancelView,
    EventRegistrationListCreateView,
)

app_name = "events"

urlpatterns = [
    path("", EventListCreateView.as_view(), name="event-list"),
    path("groups/", EventGroupChoicesView.as_view(), name="event-group-choices"),
    path(
        "<int:event_id>/registrations/",
        EventRegistrationListCreateView.as_view(),
        name="event-registration-list",
    ),
    path(
        "<int:event_id>/registrations/<int:registration_id>/cancel/",
        EventRegistrationCancelView.as_view(),
        name="event-registration-cancel",
    ),
    path("<int:pk>/", EventDetailView.as_view(), name="event-detail"),
]
