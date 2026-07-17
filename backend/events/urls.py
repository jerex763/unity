from django.urls import path

from .views import (
    EventDetailView,
    EventGroupChoicesView,
    EventListCreateView,
    EventRegistrationCancelView,
    EventRegistrationCheckInView,
    EventRegistrationListCreateView,
    EventWalkInCreateView,
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
    path(
        "<int:event_id>/registrations/<int:registration_id>/check-in/",
        EventRegistrationCheckInView.as_view(),
        name="event-registration-check-in",
    ),
    path(
        "<int:event_id>/walk-ins/",
        EventWalkInCreateView.as_view(),
        name="event-walk-in-create",
    ),
    path("<int:pk>/", EventDetailView.as_view(), name="event-detail"),
]
