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


def membership(
    church: Church,
    *,
    role: str,
    suffix: str,
    person: Person | None = None,
) -> ChurchMembership:
    user = User.objects.create_user(username=f"fictional.registration.{suffix}")
    return ChurchMembership.objects.create(
        user=user,
        church=church,
        role=role,
        person=person,
    )


def client_for(church_membership: ChurchMembership) -> APIClient:
    client = APIClient()
    client.force_login(church_membership.user)
    session = client.session
    session[ACTIVE_CHURCH_SESSION_KEY] = church_membership.church_id
    session.save()
    return client


def future_event(
    church: Church,
    creator: User,
    *,
    capacity: int | None = None,
) -> Event:
    starts_at = timezone.now() + timedelta(days=3)
    return Event.objects.create(
        church=church,
        title="Fictional Signup Event",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=2),
        capacity=capacity,
        signup_closes_at=starts_at - timedelta(hours=1),
        created_by=creator,
    )


def test_members_register_waitlist_reregister_and_cancel_themselves() -> None:
    church = Church.objects.create(name="Fictional Signup Church")
    first_person = Person.objects.create(church=church, full_name="First Signup")
    second_person = Person.objects.create(church=church, full_name="Second Signup")
    first = membership(
        church,
        role=ChurchMembership.Role.MEMBER,
        suffix="first",
        person=first_person,
    )
    second = membership(
        church,
        role=ChurchMembership.Role.MEMBER,
        suffix="second",
        person=second_person,
    )
    event = future_event(church, first.user, capacity=1)
    list_url = reverse("events:event-registration-list", args=(event.id,))

    first_response = client_for(first).post(
        list_url,
        {"needs_transport": True, "note": "Fictional pickup"},
        format="json",
    )
    second_response = client_for(second).post(list_url, {}, format="json")
    repeated = client_for(first).post(
        list_url,
        {"needs_transport": False, "note": "Updated note"},
        format="json",
    )
    cancel_url = reverse(
        "events:event-registration-cancel",
        args=(event.id, first_response.json()["id"]),
    )
    cancelled = client_for(first).post(cancel_url)

    assert first_response.status_code == 201
    assert first_response.json()["status"] == EventRegistration.Status.REGISTERED
    assert first_response.json()["needs_transport"] is True
    assert second_response.json()["status"] == EventRegistration.Status.WAITLISTED
    assert repeated.json()["id"] == first_response.json()["id"]
    assert repeated.json()["note"] == "Updated note"
    assert cancelled.json()["status"] == EventRegistration.Status.CANCELLED
    assert EventRegistration.objects.filter(event=event).count() == 2


def test_member_registration_list_and_cancel_are_self_scoped() -> None:
    church = Church.objects.create(name="Fictional Signup Privacy")
    first_person = Person.objects.create(church=church, full_name="First Member")
    second_person = Person.objects.create(church=church, full_name="Second Member")
    first = membership(
        church,
        role=ChurchMembership.Role.MEMBER,
        suffix="privacy.first",
        person=first_person,
    )
    membership(
        church,
        role=ChurchMembership.Role.MEMBER,
        suffix="privacy.second",
        person=second_person,
    )
    event = future_event(church, first.user)
    first_registration = EventRegistration.objects.create(
        church=church,
        event=event,
        person=first_person,
    )
    second_registration = EventRegistration.objects.create(
        church=church,
        event=event,
        person=second_person,
    )
    client = client_for(first)

    list_response = client.get(
        reverse("events:event-registration-list", args=(event.id,))
    )
    forbidden_cancel = client.post(
        reverse(
            "events:event-registration-cancel",
            args=(event.id, second_registration.id),
        )
    )

    assert [item["id"] for item in list_response.json()] == [first_registration.id]
    assert forbidden_cancel.status_code == 404


def test_leader_can_view_full_registration_list() -> None:
    church = Church.objects.create(name="Fictional Leader Roster")
    leader_person = Person.objects.create(church=church, full_name="Leader Person")
    leader = membership(
        church,
        role=ChurchMembership.Role.LEADER,
        suffix="leader",
        person=leader_person,
    )
    event = future_event(church, leader.user)
    people = [
        Person.objects.create(church=church, full_name=f"Roster Person {index}")
        for index in range(2)
    ]
    for person in people:
        EventRegistration.objects.create(
            church=church,
            event=event,
            person=person,
            needs_transport=True,
        )

    response = client_for(leader).get(
        reverse("events:event-registration-list", args=(event.id,))
    )

    assert response.status_code == 200
    assert {item["person"]["id"] for item in response.json()} == {
        person.id for person in people
    }
    assert all(item["needs_transport"] for item in response.json())


def test_registration_rejects_closed_events_and_invisible_people() -> None:
    church = Church.objects.create(name="Fictional Closed Signup")
    other_church = Church.objects.create(name="Fictional Signup Other")
    admin = membership(
        church,
        role=ChurchMembership.Role.ADMIN,
        suffix="closed",
    )
    event = future_event(church, admin.user)
    event.signup_opens = False
    event.save(update_fields=("signup_opens", "updated_at"))
    outsider = Person.objects.create(church=other_church, full_name="Outsider")
    client = client_for(admin)
    url = reverse("events:event-registration-list", args=(event.id,))

    invisible = client.post(url, {"person": outsider.id}, format="json")
    closed = client.post(
        url,
        {
            "person": Person.objects.create(
                church=church,
                full_name="Visible Person",
            ).id
        },
        format="json",
    )

    assert invisible.status_code == 400
    assert closed.status_code == 400
    assert closed.json()["detail"] == "Registration is closed for this event."


def test_event_payload_includes_current_members_registration() -> None:
    church = Church.objects.create(name="Fictional My Signup")
    person = Person.objects.create(church=church, full_name="Current Member")
    member = membership(
        church,
        role=ChurchMembership.Role.MEMBER,
        suffix="mine",
        person=person,
    )
    event = future_event(church, member.user)
    registration = EventRegistration.objects.create(
        church=church,
        event=event,
        person=person,
        status=EventRegistration.Status.WAITLISTED,
    )

    response = client_for(member).get(reverse("events:event-list"))

    assert response.json()[0]["my_registration"]["id"] == registration.id
    assert (
        response.json()[0]["my_registration"]["status"]
        == EventRegistration.Status.WAITLISTED
    )
