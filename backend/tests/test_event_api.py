from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.constants import ACTIVE_CHURCH_SESSION_KEY
from accounts.models import ChurchMembership, User
from events.models import Event, EventRegistration
from groups.models import Group, GroupMembership
from people.models import Person
from tenancy.models import Church

pytestmark = pytest.mark.django_db


def make_membership(
    church: Church,
    *,
    role: str,
    suffix: str,
    person: Person | None = None,
) -> ChurchMembership:
    user = User.objects.create_user(username=f"fictional.event.api.{suffix}")
    return ChurchMembership.objects.create(
        user=user,
        church=church,
        person=person,
        role=role,
    )


def authenticated_client(membership: ChurchMembership) -> APIClient:
    client = APIClient()
    client.force_login(membership.user)
    session = client.session
    session[ACTIVE_CHURCH_SESSION_KEY] = membership.church_id
    session.save()
    return client


def event_payload(**overrides: object) -> dict[str, object]:
    starts_at = timezone.now() + timedelta(days=7)
    payload: dict[str, object] = {
        "title": "Fictional Community Lunch",
        "description": "A fictional event for API tests.",
        "starts_at": starts_at.isoformat(),
        "ends_at": (starts_at + timedelta(hours=2)).isoformat(),
        "location": "Fictional Hall",
        "capacity": 2,
        "signup_opens": True,
        "signup_closes_at": (starts_at - timedelta(hours=1)).isoformat(),
    }
    payload.update(overrides)
    return payload


def test_ministry_worker_can_create_read_update_and_delete_event() -> None:
    church = Church.objects.create(name="Fictional Event CRUD")
    pastor = make_membership(
        church,
        role=ChurchMembership.Role.PASTOR,
        suffix="crud",
    )
    group = Group.objects.create(
        church=church,
        name="Fictional Event Group",
        kind=Group.Kind.ACTIVITY,
    )
    client = authenticated_client(pastor)

    create_response = client.post(
        reverse("events:event-list"),
        event_payload(group=group.id),
        format="json",
    )
    event_id = create_response.json()["id"]
    detail_url = reverse("events:event-detail", args=(event_id,))
    patch_response = client.patch(
        detail_url,
        {"title": "Updated Fictional Lunch", "capacity": 3},
        format="json",
    )
    list_response = client.get(reverse("events:event-list"))

    assert create_response.status_code == 201
    assert create_response.json()["created_by"] == pastor.user.username
    assert create_response.json()["group_name"] == group.name
    assert create_response.json()["registration_open"] is True
    assert patch_response.status_code == 200
    assert patch_response.json()["title"] == "Updated Fictional Lunch"
    assert [item["id"] for item in list_response.json()] == [event_id]
    assert client.delete(detail_url).status_code == 204
    assert not Event.objects.filter(pk=event_id).exists()


def test_event_counts_capacity_and_signup_window_are_exposed() -> None:
    church = Church.objects.create(name="Fictional Event Availability")
    admin = make_membership(
        church,
        role=ChurchMembership.Role.ADMIN,
        suffix="availability",
    )
    starts_at = timezone.now() + timedelta(days=1)
    event = Event.objects.create(
        church=church,
        title="Fictional Full Event",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=1),
        capacity=1,
        created_by=admin.user,
    )
    registered = Person.objects.create(church=church, full_name="Registered Person")
    waitlisted = Person.objects.create(church=church, full_name="Waitlisted Person")
    EventRegistration.objects.create(
        church=church,
        event=event,
        person=registered,
    )
    EventRegistration.objects.create(
        church=church,
        event=event,
        person=waitlisted,
        status=EventRegistration.Status.WAITLISTED,
    )
    client = authenticated_client(admin)

    response = client.get(reverse("events:event-detail", args=(event.id,)))

    assert response.status_code == 200
    assert response.json()["registered_count"] == 1
    assert response.json()["waitlisted_count"] == 1
    assert response.json()["registration_open"] is True
    assert response.json()["places_available"] is False


def test_event_api_validates_times_capacity_and_group_scope() -> None:
    church = Church.objects.create(name="Fictional Event Validation")
    other_church = Church.objects.create(name="Fictional Event Other")
    admin = make_membership(
        church,
        role=ChurchMembership.Role.ADMIN,
        suffix="validation",
    )
    other_group = Group.objects.create(
        church=other_church,
        name="Other Church Group",
        kind=Group.Kind.MINISTRY,
    )
    starts_at = timezone.now() + timedelta(days=2)
    client = authenticated_client(admin)

    field_response = client.post(
        reverse("events:event-list"),
        event_payload(
            group=other_group.id,
            capacity=0,
        ),
        format="json",
    )
    time_response = client.post(
        reverse("events:event-list"),
        event_payload(
            ends_at=(starts_at - timedelta(hours=1)).isoformat(),
            starts_at=starts_at.isoformat(),
            signup_closes_at=(starts_at + timedelta(minutes=1)).isoformat(),
        ),
        format="json",
    )
    past_start = timezone.now() - timedelta(days=1)
    past_response = client.post(
        reverse("events:event-list"),
        event_payload(
            starts_at=past_start.isoformat(),
            ends_at=(past_start + timedelta(hours=1)).isoformat(),
            signup_closes_at=None,
        ),
        format="json",
    )

    assert field_response.status_code == 400
    assert set(field_response.json()) == {"capacity", "group"}
    assert time_response.status_code == 400
    assert set(time_response.json()) == {"ends_at", "signup_closes_at"}
    assert past_response.status_code == 400
    assert past_response.json() == {
        "starts_at": ["Start time cannot be in the past."]
    }


def test_member_can_read_events_but_cannot_mutate() -> None:
    church = Church.objects.create(name="Fictional Member Events")
    person = Person.objects.create(church=church, full_name="Fictional Member")
    member = make_membership(
        church,
        role=ChurchMembership.Role.MEMBER,
        suffix="member",
        person=person,
    )
    starts_at = timezone.now() + timedelta(days=1)
    event = Event.objects.create(
        church=church,
        title="Visible Fictional Event",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=1),
        created_by=member.user,
    )
    client = authenticated_client(member)

    list_response = client.get(reverse("events:event-list"))
    create_response = client.post(
        reverse("events:event-list"),
        event_payload(),
        format="json",
    )
    delete_response = client.delete(reverse("events:event-detail", args=(event.id,)))

    assert [item["id"] for item in list_response.json()] == [event.id]
    assert create_response.status_code == 403
    assert delete_response.status_code == 403


def test_event_detail_never_crosses_active_church() -> None:
    church = Church.objects.create(name="Fictional Current Event Church")
    other_church = Church.objects.create(name="Fictional Other Event Church")
    admin = make_membership(
        church,
        role=ChurchMembership.Role.ADMIN,
        suffix="cross",
    )
    starts_at = timezone.now() + timedelta(days=1)
    event = Event.objects.create(
        church=other_church,
        title="Hidden Other Event",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=1),
        created_by=admin.user,
    )
    client = authenticated_client(admin)
    url = reverse("events:event-detail", args=(event.id,))

    assert client.get(url).status_code == 404
    assert client.patch(url, {"title": "Crossed"}, format="json").status_code == 404


def test_event_group_choices_follow_group_visibility() -> None:
    church = Church.objects.create(name="Fictional Event Group Choices")
    leader_person = Person.objects.create(church=church, full_name="Group Leader")
    leader = make_membership(
        church,
        role=ChurchMembership.Role.LEADER,
        suffix="group.choices",
        person=leader_person,
    )
    joined = Group.objects.create(
        church=church,
        name="Joined Group",
        kind=Group.Kind.ACTIVITY,
    )
    hidden = Group.objects.create(
        church=church,
        name="Hidden Group",
        kind=Group.Kind.ACTIVITY,
    )
    GroupMembership.objects.create(
        church=church,
        group=joined,
        person=leader_person,
        role=GroupMembership.Role.LEADER,
        joined_at=timezone.localdate(),
    )
    client = authenticated_client(leader)

    response = client.get(reverse("events:event-group-choices"))

    assert response.json() == [{"id": joined.id, "name": joined.name}]
    assert hidden.id not in {item["id"] for item in response.json()}
