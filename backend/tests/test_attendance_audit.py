from unittest.mock import patch
from uuid import UUID

import pytest
from django.urls import reverse

from accounts.models import ChurchMembership
from audit.models import AuditEvent
from care.models import FollowUp
from events.models import EventRegistration
from events.services import set_manual_check_in
from people.models import Person
from tenancy.models import Church
from tests.test_manual_checkin_api import client_for, registration_fixture

pytestmark = pytest.mark.django_db
ACTIONS = (
    AuditEvent.Action.EVENT_CHECKED_IN,
    AuditEvent.Action.EVENT_CHECK_IN_REVERSED,
)


@pytest.fixture
def attendance():
    church = Church.objects.create(name="Fictional Attendance Audit")
    client, actor = client_for(church, ChurchMembership.Role.LEADER, "audit")
    event, registration = registration_fixture(church, actor)
    return church, client, actor, event, registration


def events():
    return AuditEvent.objects.filter(action__in=ACTIONS).order_by("id")


def test_transitions_capture_actor_request_and_no_personal_values(attendance):
    church, client, actor, event, registration = attendance
    url = reverse(
        "events:event-registration-check-in", args=(event.id, registration.id)
    )
    first = client.post(url, {"checked_in": True}, format="json")
    assert first.status_code == 200
    assert client.post(url, {"checked_in": True}, format="json").status_code == 200
    undone = client.post(url, {"checked_in": False}, format="json")
    assert undone.status_code == 200
    assert client.post(url, {"checked_in": False}, format="json").status_code == 200
    rows = list(events())
    assert [row.action for row in rows] == list(ACTIONS)
    assert [row.request_id for row in rows] == [
        UUID(first["X-Request-ID"]),
        UUID(undone["X-Request-ID"]),
    ]
    for row in rows:
        assert row.actor_id == actor.id
        assert row.church_id == church.id
        assert row.target_type == "events.eventregistration"
        assert row.target_id == str(registration.id)
        assert row.metadata == {}


@pytest.mark.parametrize("existing", [True, False])
def test_walk_in_retries_emit_one_attendance_event(attendance, existing):
    church, client, actor, event, registration = attendance
    payload = (
        {"person": registration.person_id}
        if existing
        else {"full_name": "Fictional New Visitor", "email": "audit-only@example.test"}
    )
    url = reverse("events:event-walk-in-create", args=(event.id,))
    first = client.post(url, payload, format="json")
    second = client.post(url, payload, format="json")
    assert first.status_code == second.status_code == 201
    row = events().get()
    assert row.actor_id == actor.id
    assert row.church_id == church.id
    assert row.target_id == str(first.json()["id"])
    assert row.request_id == UUID(first["X-Request-ID"])
    assert row.metadata == {}


@pytest.mark.parametrize("path", ["manual", "existing", "new"])
def test_audit_failure_rolls_back_attendance_person_and_follow_up(attendance, path):
    church, client, _, event, registration = attendance
    registration.person.membership_status = Person.MembershipStatus.VISITOR
    registration.person.save()
    before = (
        Person.objects.count(),
        EventRegistration.objects.count(),
        FollowUp.objects.count(),
    )
    if path == "manual":
        url = reverse(
            "events:event-registration-check-in", args=(event.id, registration.id)
        )
        payload = {"checked_in": True}
    else:
        url = reverse("events:event-walk-in-create", args=(event.id,))
        payload = (
            {"person": registration.person_id}
            if path == "existing"
            else {"full_name": "Fictional Rollback", "email": "rollback@example.test"}
        )
    with patch(
        "events.services.record_audit_event",
        side_effect=RuntimeError("audit unavailable"),
    ):
        with pytest.raises(RuntimeError, match="audit unavailable"):
            client.post(url, payload, format="json")
    registration.refresh_from_db()
    assert registration.checked_in_at is None
    assert before == (
        Person.objects.count(),
        EventRegistration.objects.count(),
        FollowUp.objects.count(),
    )
    assert not events().exists()


def test_reversal_audit_failure_preserves_attendance(attendance):
    _, _, _, _, registration = attendance
    set_manual_check_in(registration, checked_in=True)
    registration.refresh_from_db()
    original = registration.checked_in_at
    with patch(
        "events.services.record_audit_event",
        side_effect=RuntimeError("audit unavailable"),
    ):
        with pytest.raises(RuntimeError):
            set_manual_check_in(registration, checked_in=False)
    registration.refresh_from_db()
    assert registration.checked_in_at == original
    assert events().count() == 1


def test_denied_cross_church_and_invalid_requests_emit_no_success(attendance):
    church, leader, _, event, registration = attendance
    member, _ = client_for(church, ChurchMembership.Role.MEMBER, "audit.member")
    other = Church.objects.create(name="Fictional Other Audit Church")
    outsider, _ = client_for(other, ChurchMembership.Role.LEADER, "audit.other")
    url = reverse(
        "events:event-registration-check-in", args=(event.id, registration.id)
    )
    for client, expected in [(member, 403), (outsider, 404)]:
        assert (
            client.post(url, {"checked_in": True}, format="json").status_code
            == expected
        )
        assert (
            client.post(
                reverse("events:event-walk-in-create", args=(event.id,)),
                {"person": registration.person_id},
                format="json",
            ).status_code
            == expected
        )
    registration.status = EventRegistration.Status.CANCELLED
    registration.save()
    assert leader.post(url, {"checked_in": True}, format="json").status_code == 400
    assert not events().exists()


def test_internal_call_has_null_actor_without_inventing_identity(attendance):
    _, _, _, _, registration = attendance
    set_manual_check_in(registration, checked_in=True)
    row = events().get()
    assert row.actor_id is None
    assert isinstance(row.request_id, UUID)


@pytest.mark.django_db(transaction=True)
def test_concurrent_check_ins_emit_one_transition(attendance):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import close_old_connections, connection

    if connection.vendor != "postgresql":
        pytest.skip("Requires PostgreSQL row locks")
    _, _, _, _, registration = attendance
    barrier = Barrier(2)

    def check_in():
        close_old_connections()
        try:
            target = EventRegistration.objects.get(pk=registration.pk)
            barrier.wait(timeout=10)
            set_manual_check_in(target, checked_in=True)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(check_in) for _ in range(2)]
        for future in futures:
            future.result(timeout=20)
    assert events().count() == 1
    assert events().get().action == AuditEvent.Action.EVENT_CHECKED_IN
