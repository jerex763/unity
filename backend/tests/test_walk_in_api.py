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


def client_with_role(church: Church, role: str) -> tuple[APIClient, User]:
    user = User.objects.create_user(username=f"fictional.walkin.{role}")
    ChurchMembership.objects.create(user=user, church=church, role=role)
    client = APIClient()
    client.force_login(user)
    session = client.session
    session[ACTIVE_CHURCH_SESSION_KEY] = church.id
    session.save()
    return client, user


def test_worker_quick_adds_checked_in_walk_in_atomically() -> None:
    church = Church.objects.create(name="Fictional Walk-in Church")
    client, worker = client_with_role(church, ChurchMembership.Role.LEADER)
    now = timezone.now()
    event = Event.objects.create(
        church=church,
        title="Fictional Door Event",
        starts_at=now + timedelta(minutes=30),
        ends_at=now + timedelta(hours=2),
        capacity=1,
        created_by=worker,
    )

    response = client.post(
        reverse("events:event-walk-in-create", args=(event.id,)),
        {
            "full_name": "  Fictional   Walk In ",
            "preferred_name": "Walk",
            "email": "WALK.IN@example.test",
            "phone": " +61000000999 ",
            "needs_transport": True,
            "note": "Fictional late pickup",
        },
        format="json",
    )

    assert response.status_code == 201
    person = Person.objects.get(email="walk.in@example.test")
    registration = EventRegistration.objects.get(person=person, event=event)
    assert person.full_name == "Fictional Walk In"
    assert person.membership_status == Person.MembershipStatus.VISITOR
    assert registration.status == EventRegistration.Status.WALK_IN
    assert registration.checked_in_at is not None
    assert registration.checkin_method == EventRegistration.CheckinMethod.MANUAL
    assert response.json()["needs_transport"] is True


def test_walk_in_reuses_same_church_contact_without_duplicate_person() -> None:
    church = Church.objects.create(name="Fictional Existing Walk-in")
    client, worker = client_with_role(church, ChurchMembership.Role.PASTOR)
    person = Person.objects.create(
        church=church,
        full_name="Existing Contact",
        email="existing@example.test",
    )
    now = timezone.now()
    event = Event.objects.create(
        church=church,
        title="Fictional Existing Event",
        starts_at=now - timedelta(minutes=15),
        ends_at=now + timedelta(hours=1),
        created_by=worker,
    )

    response = client.post(
        reverse("events:event-walk-in-create", args=(event.id,)),
        {
            "full_name": "Different Submitted Name",
            "email": "EXISTING@example.test",
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["person"]["id"] == person.id
    assert Person.objects.for_church(church).count() == 1


def test_member_cannot_quick_add_walk_in_and_cross_church_event_is_hidden() -> None:
    church = Church.objects.create(name="Fictional Walk-in Access")
    other_church = Church.objects.create(name="Fictional Walk-in Other")
    member_client, member_user = client_with_role(
        church,
        ChurchMembership.Role.MEMBER,
    )
    leader_client, _ = client_with_role(church, ChurchMembership.Role.LEADER)
    now = timezone.now()
    other_event = Event.objects.create(
        church=other_church,
        title="Hidden Walk-in Event",
        starts_at=now,
        ends_at=now + timedelta(hours=1),
        created_by=member_user,
    )
    payload = {"full_name": "Forbidden Walk In"}
    url = reverse("events:event-walk-in-create", args=(other_event.id,))

    assert member_client.post(url, payload, format="json").status_code == 403
    assert leader_client.post(url, payload, format="json").status_code == 404
    assert not Person.objects.filter(full_name="Forbidden Walk In").exists()


def test_walk_in_rejects_ended_event_without_creating_person() -> None:
    church = Church.objects.create(name="Fictional Ended Walk-in")
    client, worker = client_with_role(church, ChurchMembership.Role.ADMIN)
    now = timezone.now()
    event = Event.objects.create(
        church=church,
        title="Ended Walk-in Event",
        starts_at=now - timedelta(hours=2),
        ends_at=now - timedelta(hours=1),
        created_by=worker,
    )

    response = client.post(
        reverse("events:event-walk-in-create", args=(event.id,)),
        {"full_name": "Too Late Person"},
        format="json",
    )

    assert response.status_code == 400
    assert not Person.objects.filter(full_name="Too Late Person").exists()
