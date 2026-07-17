from django.urls import path

from .views import (
    CareCaseInteractionListCreateView,
    FollowUpDetailView,
    FollowUpInteractionListCreateView,
    FollowUpListView,
    FollowUpWorkerChoicesView,
)

app_name = "care"

urlpatterns = [
    path("", FollowUpListView.as_view(), name="follow-up-list"),
    path("workers/", FollowUpWorkerChoicesView.as_view(), name="worker-choices"),
    path(
        "<int:parent_id>/interactions/",
        FollowUpInteractionListCreateView.as_view(),
        name="follow-up-interactions",
    ),
    path(
        "care-cases/<int:parent_id>/interactions/",
        CareCaseInteractionListCreateView.as_view(),
        name="care-case-interactions",
    ),
    path("<int:pk>/", FollowUpDetailView.as_view(), name="follow-up-detail"),
]
