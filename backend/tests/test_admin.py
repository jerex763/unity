import pytest
from django.contrib import admin
from django.test import Client, RequestFactory
from django.urls import reverse

from accounts.models import ChurchMembership, User
from care.models import CareCase, FollowUp, Interaction
from events.models import Event, EventRegistration
from groups.models import Group, GroupMembership
from people.admin import PersonAdmin
from people.models import Household, Person, Relationship
from tenancy.models import Church

pytestmark = pytest.mark.django_db

PROJECT_MODELS = {
    User,
    ChurchMembership,
    Church,
    Household,
    Person,
    Relationship,
    Group,
    GroupMembership,
    Event,
    EventRegistration,
    FollowUp,
    CareCase,
    Interaction,
}

ADMIN_CHANGELISTS = (
    "admin:accounts_user_changelist",
    "admin:accounts_churchmembership_changelist",
    "admin:tenancy_church_changelist",
    "admin:people_household_changelist",
    "admin:people_person_changelist",
    "admin:people_relationship_changelist",
    "admin:groups_group_changelist",
    "admin:groups_groupmembership_changelist",
    "admin:events_event_changelist",
    "admin:events_eventregistration_changelist",
    "admin:care_followup_changelist",
    "admin:care_carecase_changelist",
    "admin:care_interaction_changelist",
)


def test_all_project_models_are_registered() -> None:
    assert PROJECT_MODELS <= set(admin.site._registry)


@pytest.mark.parametrize("url_name", ADMIN_CHANGELISTS)
def test_superuser_can_open_every_admin_changelist(url_name: str) -> None:
    user = User.objects.create_superuser(
        username="fictional.admin",
        email="fictional.admin@example.test",
        password="test-password-only",
    )
    client = Client()
    client.force_login(user)

    response = client.get(reverse(url_name))

    assert response.status_code == 200


def test_non_superuser_person_form_excludes_sensitive_fields() -> None:
    staff_user = User.objects.create_user(
        username="fictional.staff",
        is_staff=True,
    )
    request = RequestFactory().get("/admin/people/person/")
    request.user = staff_user
    model_admin = PersonAdmin(Person, admin.site)

    excluded = model_admin.get_exclude(request)

    assert excluded is not None
    assert "faith_background" in excluded
    assert "discipleship_stage" in excluded


def test_superuser_person_form_keeps_sensitive_fields() -> None:
    superuser = User.objects.create_superuser(
        username="fictional.superuser",
        password="test-password-only",
    )
    request = RequestFactory().get("/admin/people/person/")
    request.user = superuser
    model_admin = PersonAdmin(Person, admin.site)

    assert model_admin.get_exclude(request) is None


def test_project_admin_models_are_superuser_only() -> None:
    staff_user = User.objects.create_user(
        username="fictional.restricted.staff",
        is_staff=True,
    )
    request = RequestFactory().get("/admin/")
    request.user = staff_user

    for model in PROJECT_MODELS:
        model_admin = admin.site._registry[model]
        assert not model_admin.has_module_permission(request)
        assert not model_admin.has_view_permission(request)
        assert not model_admin.has_add_permission(request)
        assert not model_admin.has_change_permission(request)
        assert not model_admin.has_delete_permission(request)
