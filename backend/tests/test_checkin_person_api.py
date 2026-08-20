from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.constants import ACTIVE_CHURCH_SESSION_KEY
from accounts.models import ChurchMembership, User
from care.models import FollowUp
from events.models import Event, EventRegistration
from people.models import Person
from tenancy.models import Church

pytestmark = pytest.mark.django_db


def client_for(church: Church, role: str, suffix: str) -> tuple[APIClient, User]:
    user = User.objects.create_user(username=f"fictional.selector.{suffix}")
    ChurchMembership.objects.create(user=user, church=church, role=role)
    client = APIClient()
    client.force_login(user)
    session = client.session
    session[ACTIVE_CHURCH_SESSION_KEY] = church.id
    session.save()
    return client, user


def active_event(church: Church, creator: User, suffix: str) -> Event:
    now = timezone.now()
    return Event.objects.create(
        church=church,
        title=f"Fictional Selector Event {suffix}",
        starts_at=now - timedelta(minutes=10),
        ends_at=now + timedelta(hours=2),
        created_by=creator,
    )


@pytest.mark.parametrize(
    ("role", "allowed"),
    (
        (ChurchMembership.Role.ADMIN, True),
        (ChurchMembership.Role.PASTOR, True),
        (ChurchMembership.Role.LEADER, True),
        (ChurchMembership.Role.MEMBER, False),
    ),
)
def test_check_in_capability_covers_search_walk_in_and_manual_check_in(
    role: str,
    allowed: bool,
) -> None:
    church = Church.objects.create(name=f"Fictional Check-in Matrix {role}")
    client, user = client_for(church, role, role)
    event = active_event(church, user, role)
    person = Person.objects.create(church=church, full_name="Matrix Person")
    registration = EventRegistration.objects.create(
        church=church,
        event=event,
        person=person,
    )

    search = client.get(
        reverse("events:event-check-in-person-search", args=(event.id,)),
        {"q": "Matrix"},
    )
    manual = client.post(
        reverse(
            "events:event-registration-check-in",
            args=(event.id, registration.id),
        ),
        {"checked_in": True},
        format="json",
    )
    walk_in = client.post(
        reverse("events:event-walk-in-create", args=(event.id,)),
        {"person": person.id},
        format="json",
    )

    expected = 200 if allowed else 403
    assert search.status_code == expected
    assert manual.status_code == expected
    assert walk_in.status_code == (201 if allowed else 403)


def test_check_in_search_is_minimal_masked_and_church_scoped() -> None:
    church = Church.objects.create(name="Fictional Private Selector")
    other_church = Church.objects.create(name="Fictional Other Selector")
    client, user = client_for(church, ChurchMembership.Role.LEADER, "privacy")
    event = active_event(church, user, "privacy")
    first = Person.objects.create(
        church=church,
        full_name="Duplicate Fictional Name",
        preferred_name="One",
        email="first.private@example.test",
        membership_status=Person.MembershipStatus.VISITOR,
    )
    second = Person.objects.create(
        church=church,
        full_name="Duplicate Fictional Name",
        preferred_name="Two",
        phone="+61 400 123 987",
        membership_status=Person.MembershipStatus.MEMBER,
    )
    deactivated = Person.objects.create(
        church=church,
        full_name="Duplicate Fictional Name Deactivated",
        deactivated_at=timezone.now(),
    )
    anonymized = Person.objects.create(
        church=church,
        full_name="Duplicate Fictional Name Anonymized",
        anonymized_at=timezone.now(),
    )
    status_only_inactive = Person.objects.create(
        church=church,
        full_name="Duplicate Fictional Name Status Inactive",
        membership_status=Person.MembershipStatus.INACTIVE,
    )
    outsider = Person.objects.create(
        church=other_church,
        full_name="Duplicate Fictional Name Outsider",
        email="outsider.private@example.test",
    )
    EventRegistration.objects.create(
        church=church,
        event=event,
        person=first,
        status=EventRegistration.Status.WAITLISTED,
    )
    url = reverse("events:event-check-in-person-search", args=(event.id,))

    assert client.get(url).json() == []
    assert client.get(url, {"q": "D"}).json() == []
    response = client.get(url, {"q": "Duplicate Fictional"})

    assert response.status_code == 200
    rows = response.json()
    assert [row["id"] for row in rows] == [first.id, second.id]
    assert all(
        set(row)
        == {
            "id",
            "full_name",
            "preferred_name",
            "membership_status",
            "current_registration_status",
            "contact_hint",
        }
        for row in rows
    )
    assert rows[0]["current_registration_status"] == "waitlisted"
    assert rows[1]["current_registration_status"] is None
    assert rows[0]["membership_status"] == "visitor"
    assert rows[1]["membership_status"] == "member"
    serialized = str(rows)
    for raw_contact in (
        first.email,
        second.phone,
        outsider.email,
    ):
        assert raw_contact not in serialized
    assert "f***@e***.test" in rows[0]["contact_hint"]
    assert "ending 3987" in rows[1]["contact_hint"]
    assert deactivated.id not in {row["id"] for row in rows}
    assert anonymized.id not in {row["id"] for row in rows}
    assert status_only_inactive.id not in {row["id"] for row in rows}
    assert outsider.id not in {row["id"] for row in rows}

    contact_match = client.get(url, {"q": "3987"})
    assert [row["id"] for row in contact_match.json()] == [second.id]
    walk_in_url = reverse("events:event-walk-in-create", args=(event.id,))
    assert (
        client.post(walk_in_url, {"person": deactivated.id}, format="json").status_code
        == 404
    )
    assert (
        client.post(walk_in_url, {"person": anonymized.id}, format="json").status_code
        == 404
    )
    assert (
        client.post(
            walk_in_url,
            {"person": status_only_inactive.id},
            format="json",
        ).status_code
        == 404
    )
    assert not EventRegistration.objects.filter(
        event=event,
        person=status_only_inactive,
    ).exists()
    assert not FollowUp.objects.filter(person=status_only_inactive).exists()


@pytest.mark.parametrize(
    ("initial_status", "expected_status"),
    (
        (None, EventRegistration.Status.WALK_IN),
        (EventRegistration.Status.CANCELLED, EventRegistration.Status.WALK_IN),
        (EventRegistration.Status.REGISTERED, EventRegistration.Status.REGISTERED),
        (EventRegistration.Status.WALK_IN, EventRegistration.Status.WALK_IN),
        (EventRegistration.Status.WAITLISTED, EventRegistration.Status.REGISTERED),
    ),
)
def test_selected_person_check_in_status_and_profile_nonmutation(
    initial_status: str | None,
    expected_status: str,
) -> None:
    suffix = initial_status or "none"
    church = Church.objects.create(name=f"Fictional Existing State {suffix}")
    client, user = client_for(church, ChurchMembership.Role.PASTOR, suffix)
    event = active_event(church, user, suffix)
    person = Person.objects.create(
        church=church,
        full_name="Original Profile Name",
        preferred_name="Original",
        email=f"original.{suffix}@example.test",
        phone="+61 400 000 111",
        wechat_id=f"original_{suffix}",
        membership_status=Person.MembershipStatus.REGULAR,
    )
    registration = None
    if initial_status is not None:
        registration = EventRegistration.objects.create(
            church=church,
            event=event,
            person=person,
            status=initial_status,
            note="Original registration note",
            cancellation_token_digest=(
                "a" * 64
                if initial_status == EventRegistration.Status.CANCELLED
                else None
            ),
        )
    original_registered_at = registration.registered_at if registration else None

    response = client.post(
        reverse("events:event-walk-in-create", args=(event.id,)),
        {
            "person": person.id,
            "full_name": "Must Not Replace Name",
            "preferred_name": "Must Not Replace Preferred",
            "email": "must-not-replace@example.test",
            "phone": "+61 499 999 999",
            "wechat_id": "must_not_replace",
            "note": "Arrival note",
        },
        format="json",
    )

    assert response.status_code == 201
    person.refresh_from_db()
    registration = EventRegistration.objects.get(event=event, person=person)
    assert registration.status == expected_status
    assert registration.checked_in_at is not None
    assert registration.checkin_method == EventRegistration.CheckinMethod.MANUAL
    assert person.full_name == "Original Profile Name"
    assert person.preferred_name == "Original"
    assert person.email == f"original.{suffix}@example.test"
    assert person.phone == "+61 400 000 111"
    assert person.wechat_id == f"original_{suffix}"
    assert person.membership_status == Person.MembershipStatus.REGULAR
    if initial_status in {
        EventRegistration.Status.REGISTERED,
        EventRegistration.Status.WALK_IN,
        EventRegistration.Status.WAITLISTED,
    }:
        assert registration.note == "Original registration note"
        assert registration.registered_at == original_registered_at
    else:
        assert registration.note == "Arrival note"
    if initial_status == EventRegistration.Status.CANCELLED:
        assert registration.cancellation_token_digest is None


def test_selected_person_cannot_cross_church() -> None:
    church = Church.objects.create(name="Fictional Existing Current")
    other_church = Church.objects.create(name="Fictional Existing Other")
    client, user = client_for(church, ChurchMembership.Role.ADMIN, "cross")
    event = active_event(church, user, "cross")
    outsider = Person.objects.create(
        church=other_church,
        full_name="Other Church Person",
    )

    response = client.post(
        reverse("events:event-walk-in-create", args=(event.id,)),
        {"person": outsider.id},
        format="json",
    )

    assert response.status_code == 404
    assert not EventRegistration.objects.filter(event=event).exists()


def test_selected_existing_person_preserves_visitor_only_first_visit_follow_up() -> (
    None
):
    church = Church.objects.create(name="Fictional Existing Follow-up")
    client, user = client_for(church, ChurchMembership.Role.LEADER, "followup")
    first_event = active_event(church, user, "first")
    second_event = active_event(church, user, "second")
    visitor = Person.objects.create(
        church=church,
        full_name="Existing Visitor",
        membership_status=Person.MembershipStatus.VISITOR,
    )
    member = Person.objects.create(
        church=church,
        full_name="Existing Member",
        membership_status=Person.MembershipStatus.MEMBER,
    )

    for event, person in (
        (first_event, visitor),
        (first_event, member),
        (second_event, visitor),
    ):
        response = client.post(
            reverse("events:event-walk-in-create", args=(event.id,)),
            {"person": person.id},
            format="json",
        )
        assert response.status_code == 201

    assert (
        FollowUp.objects.filter(
            church=church,
            person=visitor,
            source=FollowUp.Source.EVENT_VISIT,
        ).count()
        == 1
    )
    assert not FollowUp.objects.filter(church=church, person=member).exists()
