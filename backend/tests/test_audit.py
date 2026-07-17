from uuid import UUID, uuid4

import pytest
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.test import Client, RequestFactory
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import ChurchMembership, User
from audit.admin import AuditEventAdmin
from audit.context import AuditContext, bind_audit_context
from audit.models import AuditEvent
from audit.services import record_audit_event, record_csv_export
from care.models import CareCase
from people.models import Person
from tenancy.models import Church

pytestmark = pytest.mark.django_db


def make_user(
    username: str,
    *,
    is_staff: bool = False,
    is_superuser: bool = False,
) -> User:
    return User.objects.create_user(
        username=username,
        password="test-password-only",
        is_staff=is_staff,
        is_superuser=is_superuser,
    )


def test_login_success_and_failure_are_audited_without_credentials() -> None:
    church = Church.objects.create(name="Fictional Community Church")
    user = make_user("fictional.audit.login")
    ChurchMembership.objects.create(
        user=user,
        church=church,
        role=ChurchMembership.Role.LEADER,
    )
    client = APIClient()

    failure = client.post(
        reverse("accounts:login"),
        {"username": user.username, "password": "not-the-password"},
        format="json",
    )
    success = client.post(
        reverse("accounts:login"),
        {"username": user.username, "password": "test-password-only"},
        format="json",
    )

    failed_event = AuditEvent.objects.get(action=AuditEvent.Action.LOGIN_FAILED)
    success_event = AuditEvent.objects.get(action=AuditEvent.Action.LOGIN_SUCCEEDED)
    assert failure.status_code == 401
    assert success.status_code == 200
    assert failed_event.actor is None
    assert failed_event.church is None
    assert failed_event.metadata == {"reason": "InvalidCredentials"}
    assert success_event.actor == user
    assert success_event.church == church
    assert success_event.target_type == "accounts.user"
    assert str(failed_event.request_id) == failure["X-Request-ID"]
    assert str(success_event.request_id) == success["X-Request-ID"]
    assert "password" not in str(failed_event.metadata).lower()
    assert "test-password-only" not in str(failed_event.metadata)


def test_person_and_membership_changes_capture_actor_and_request_id() -> None:
    church = Church.objects.create(name="Fictional Community Church")
    actor = make_user("fictional.auditor")
    request_id = uuid4()

    with bind_audit_context(AuditContext(actor_id=actor.id, request_id=request_id)):
        person = Person.objects.create(church=church, full_name="Fictional Person")
        person.preferred_name = "Example"
        person.save()
        person.membership_status = Person.MembershipStatus.INACTIVE
        person.save()

        membership = ChurchMembership.objects.create(
            user=actor,
            church=church,
            role=ChurchMembership.Role.LEADER,
        )
        membership.role = ChurchMembership.Role.ADMIN
        membership.is_active = False
        membership.save()

    person_actions = list(
        AuditEvent.objects.filter(target_type="people.person").values_list(
            "action", flat=True
        )
    )
    membership_actions = set(
        AuditEvent.objects.filter(target_type="accounts.churchmembership").values_list(
            "action", flat=True
        )
    )
    assert AuditEvent.Action.PERSON_CREATED in person_actions
    assert AuditEvent.Action.PERSON_UPDATED in person_actions
    assert AuditEvent.Action.PERSON_DEACTIVATED in person_actions
    assert AuditEvent.Action.MEMBERSHIP_ROLE_CHANGED in membership_actions
    assert AuditEvent.Action.MEMBERSHIP_ACCESS_CHANGED in membership_actions
    assert not AuditEvent.objects.exclude(actor=actor).exists()
    assert not AuditEvent.objects.exclude(request_id=request_id).exists()
    assert (
        not AuditEvent.objects.exclude(metadata={})
        .filter(target_type="people.person")
        .exists()
    )


def test_confidential_care_admin_view_is_audited() -> None:
    church = Church.objects.create(name="Fictional Community Church")
    superuser = make_user(
        "fictional.superuser",
        is_staff=True,
        is_superuser=True,
    )
    person = Person.objects.create(church=church, full_name="Fictional Person")
    care_case = CareCase.objects.create(
        church=church,
        person=person,
        kind=CareCase.Kind.PASTORAL,
        title="Fictional confidential case",
        details="Fictional details only.",
        is_confidential=True,
        created_by=superuser,
    )
    client = Client()
    client.force_login(superuser)

    response = client.get(reverse("admin:care_carecase_change", args=(care_case.id,)))

    event = AuditEvent.objects.get(action=AuditEvent.Action.CONFIDENTIAL_CARE_VIEWED)
    assert response.status_code == 200
    assert event.actor == superuser
    assert event.church == church
    assert event.target_id == str(care_case.id)
    assert event.metadata == {}


def test_audit_entries_are_append_only_and_metadata_is_allow_listed() -> None:
    event = record_audit_event(action=AuditEvent.Action.LOGIN_FAILED)
    event.metadata = {"reason": "InvalidCredentials"}

    with pytest.raises(ValidationError, match="append-only"):
        event.save()
    with pytest.raises(ValidationError, match="cannot be deleted"):
        event.delete()
    with pytest.raises(ValidationError, match="append-only"):
        AuditEvent.objects.filter(pk=event.pk).update(action="changed")
    with pytest.raises(ValidationError, match="cannot be deleted"):
        AuditEvent.objects.filter(pk=event.pk).delete()
    with pytest.raises(ValueError, match="not approved"):
        record_audit_event(
            action=AuditEvent.Action.LOGIN_FAILED,
            metadata={"password": "must-never-be-stored"},
        )


def test_csv_export_records_counts_but_not_exported_values() -> None:
    church = Church.objects.create(name="Fictional Community Church")
    actor = make_user("fictional.exporter")

    event = record_csv_export(
        actor=actor,
        church=church,
        target_type="people.person",
        record_count=12,
    )

    assert event.action == AuditEvent.Action.CSV_EXPORTED
    assert event.metadata == {"format": "csv", "record_count": 12}
    assert event.target_type == "people.person"


def test_ordinary_leader_cannot_read_audit_admin() -> None:
    church = Church.objects.create(name="Fictional Community Church")
    leader = make_user("fictional.leader", is_staff=True)
    ChurchMembership.objects.create(
        user=leader,
        church=church,
        role=ChurchMembership.Role.LEADER,
    )
    request = RequestFactory().get("/admin/audit/auditevent/")
    request.user = leader
    model_admin = AuditEventAdmin(AuditEvent, admin.site)
    client = Client()
    client.force_login(leader)

    response = client.get(reverse("admin:audit_auditevent_changelist"))

    assert response.status_code == 403
    assert not model_admin.has_module_permission(request)
    assert not model_admin.has_view_permission(request)
    assert not model_admin.has_add_permission(request)
    assert not model_admin.has_change_permission(request)
    assert not model_admin.has_delete_permission(request)


def test_request_id_is_a_server_generated_uuid() -> None:
    client = APIClient()
    response = client.get(reverse("health-check"), HTTP_X_REQUEST_ID="untrusted")

    assert response.status_code == 200
    assert response["X-Request-ID"] != "untrusted"
    UUID(response["X-Request-ID"])
