from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.constants import ACTIVE_CHURCH_SESSION_KEY
from accounts.models import ChurchMembership, User
from events.models import Event, EventRegistration
from people.models import Person
from tenancy.models import Church

pytestmark = pytest.mark.django_db


def client_for(
    church: Church,
    role: str,
    suffix: str,
) -> tuple[APIClient, User]:
    user = User.objects.create_user(username=f"fictional.checkin.{suffix}")
    ChurchMembership.objects.create(user=user, church=church, role=role)
    client = APIClient()
    client.force_login(user)
    session = client.session
    session[ACTIVE_CHURCH_SESSION_KEY] = church.id
    session.save()
    return client, user


def registration_fixture(
    church: Church,
    creator: User,
) -> tuple[Event, EventRegistration]:
    now = timezone.now()
    event = Event.objects.create(
        church=church,
        title="Fictional Check-in Event",
        starts_at=now - timedelta(minutes=15),
        ends_at=now + timedelta(hours=1),
        created_by=creator,
    )
    person = Person.objects.create(church=church, full_name="Check-in Person")
    registration = EventRegistration.objects.create(
        church=church,
        event=event,
        person=person,
    )
    return event, registration


def test_leader_can_idempotently_check_in_and_correct_attendance() -> None:
    church = Church.objects.create(name="Fictional Manual Check-in")
    client, leader = client_for(church, ChurchMembership.Role.LEADER, "leader")
    event, registration = registration_fixture(church, leader)
    url = reverse(
        "events:event-registration-check-in",
        args=(event.id, registration.id),
    )

    first = client.post(url, {"checked_in": True}, format="json")
    first_timestamp = first.json()["checked_in_at"]
    repeated = client.post(url, {"checked_in": True}, format="json")
    undone = client.post(url, {"checked_in": False}, format="json")
    repeated_undo = client.post(url, {"checked_in": False}, format="json")

    assert first.status_code == 200
    assert first.json()["checkin_method"] == EventRegistration.CheckinMethod.MANUAL
    assert repeated.json()["checked_in_at"] == first_timestamp
    assert undone.json()["checked_in_at"] is None
    assert undone.json()["checkin_method"] is None
    assert repeated_undo.status_code == 200


def test_member_cannot_check_in_and_cross_church_ids_are_hidden() -> None:
    church = Church.objects.create(name="Fictional Check-in Access")
    other_church = Church.objects.create(name="Fictional Check-in Other")
    member_client, member = client_for(
        church,
        ChurchMembership.Role.MEMBER,
        "member",
    )
    leader_client, _ = client_for(
        church,
        ChurchMembership.Role.LEADER,
        "leader.cross",
    )
    event, registration = registration_fixture(other_church, member)
    url = reverse(
        "events:event-registration-check-in",
        args=(event.id, registration.id),
    )

    assert (
        member_client.post(url, {"checked_in": True}, format="json").status_code == 403
    )
    assert (
        leader_client.post(url, {"checked_in": True}, format="json").status_code == 404
    )
    registration.refresh_from_db()
    assert registration.checked_in_at is None


def test_cancelled_registration_cannot_be_checked_in() -> None:
    church = Church.objects.create(name="Fictional Cancelled Check-in")
    client, pastor = client_for(church, ChurchMembership.Role.PASTOR, "pastor")
    event, registration = registration_fixture(church, pastor)
    registration.status = EventRegistration.Status.CANCELLED
    registration.save(update_fields=("status", "updated_at"))

    response = client.post(
        reverse(
            "events:event-registration-check-in",
            args=(event.id, registration.id),
        ),
        {"checked_in": True},
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "A cancelled registration cannot be checked in."
    )
