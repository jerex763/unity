from django.urls import path

from .views import FollowUpDetailView, FollowUpListView, FollowUpWorkerChoicesView

app_name = "care"

urlpatterns = [
    path("", FollowUpListView.as_view(), name="follow-up-list"),
    path("workers/", FollowUpWorkerChoicesView.as_view(), name="worker-choices"),
    path("<int:pk>/", FollowUpDetailView.as_view(), name="follow-up-detail"),
]
