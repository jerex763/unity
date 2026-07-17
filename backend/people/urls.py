from django.urls import path

from .views import PersonConsentView

app_name = "people"

urlpatterns = [
    path(
        "<int:person_id>/consent/",
        PersonConsentView.as_view(),
        name="person-consent",
    ),
]
