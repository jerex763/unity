from django.urls import path

from .views import (
    PersonAnonymizeView,
    PersonConsentView,
    PersonDeactivateView,
    PersonHardDeleteView,
)

app_name = "people"

urlpatterns = [
    path(
        "<int:person_id>/consent/",
        PersonConsentView.as_view(),
        name="person-consent",
    ),
    path(
        "<int:person_id>/deactivate/",
        PersonDeactivateView.as_view(),
        name="person-deactivate",
    ),
    path(
        "<int:person_id>/anonymize/",
        PersonAnonymizeView.as_view(),
        name="person-anonymize",
    ),
    path(
        "<int:person_id>/hard-delete/",
        PersonHardDeleteView.as_view(),
        name="person-hard-delete",
    ),
]
