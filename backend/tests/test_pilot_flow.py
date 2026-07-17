from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.constants import ACTIVE_CHURCH_SESSION_KEY
from accounts.models import ChurchMembership, User
from care.models import FollowUp, Interaction
from events.models import Event
from people.models import Person
from tenancy.models import Church

pytestmark = pytest.mark.django_db


def client_for(membership: ChurchMembership) -> APIClient:
    client = APIClient()
    client.force_login(membership.user)
    session = client.session
    session[ACTIVE_CHURCH_SESSION_KEY] = membership.church_id
    session.save()
    return client


def test_fictional_pilot_flow_from_signup_to_recorded_outcome() -> None:
    church = Church.objects.create(name="Fictional Pilot Church")
    worker = User.objects.create_user(
        username="fictional.pilot.worker",
        first_name="Fictional",
        last_name="Worker",
    )
    worker_membership = ChurchMembership.objects.create(
        user=worker,
        church=church,
        role=ChurchMembership.Role.ADMIN,
    )
    member_person = Person.objects.create(
        church=church,
        full_name="Fictional Registered Member",
        membership_status=Person.MembershipStatus.MEMBER,
    )
    member = User.objects.create_user(username="fictional.pilot.member")
    member_membership = ChurchMembership.objects.create(
        user=member,
        church=church,
        role=ChurchMembership.Role.MEMBER,
        person=member_person,
    )
    now = timezone.now()
    event = Event.objects.create(
        church=church,
        title="Fictional Pilot Welcome Lunch",
        starts_at=now + timedelta(minutes=30),
        ends_at=now + timedelta(hours=2),
        signup_closes_at=now + timedelta(minutes=20),
        created_by=worker,
    )

    signup = client_for(member_membership).post(
        reverse("events:event-registration-list", args=(event.id,)),
        {"needs_transport": True, "note": "Fictional pickup request"},
        format="json",
    )
    check_in = client_for(worker_membership).post(
        reverse(
            "events:event-registration-check-in",
            args=(event.id, signup.json()["id"]),
        ),
        {"checked_in": True},
        format="json",
    )
    walk_in = client_for(worker_membership).post(
        reverse("events:event-walk-in-create", args=(event.id,)),
        {
            "full_name": "Fictional Pilot Visitor",
            "phone": "+61000000077",
            "note": "Fictional first visit",
        },
        format="json",
    )
    follow_up = FollowUp.objects.get(
        church=church,
        person_id=walk_in.json()["person"]["id"],
    )
    assigned = client_for(worker_membership).patch(
        reverse("care:follow-up-detail", args=(follow_up.id,)),
        {
            "assigned_to": worker.id,
            "due_at": (timezone.localdate() + timedelta(days=2)).isoformat(),
            "status": FollowUp.Status.IN_PROGRESS,
        },
        format="json",
    )
    interaction = client_for(worker_membership).post(
        reverse("care:follow-up-interactions", args=(follow_up.id,)),
        {
            "kind": Interaction.Kind.CALL,
            "visibility": Interaction.Visibility.STAFF,
            "summary": "Fictional welcome call completed.",
        },
        format="json",
    )
    closed = client_for(worker_membership).patch(
        reverse("care:follow-up-detail", args=(follow_up.id,)),
        {
            "status": FollowUp.Status.CLOSED,
            "engagement": FollowUp.Engagement.LIKELY,
            "outcome": "Fictional visitor connected with a community group.",
        },
        format="json",
    )

    assert signup.status_code == 201
    assert signup.json()["needs_transport"] is True
    assert check_in.status_code == 200
    assert check_in.json()["checked_in_at"] is not None
    assert walk_in.status_code == 201
    assert walk_in.json()["checked_in_at"] is not None
    assert assigned.status_code == 200
    assert assigned.json()["assigned_to"] == worker.id
    assert interaction.status_code == 201
    assert interaction.json()["summary"] == "Fictional welcome call completed."
    assert closed.status_code == 200
    assert closed.json()["closed_at"] is not None
    assert closed.json()["outcome"] == (
        "Fictional visitor connected with a community group."
    )
    assert (
        client_for(worker_membership).get(reverse("care:my-follow-up-list")).json()
        == []
    )
