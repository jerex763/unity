from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.constants import ACTIVE_CHURCH_SESSION_KEY
from accounts.models import ChurchMembership, User
from care.models import FollowUp
from people.models import Person
from tenancy.models import Church

pytestmark = pytest.mark.django_db


def member(
    church: Church,
    role: str,
    suffix: str,
) -> tuple[APIClient, ChurchMembership]:
    user = User.objects.create_user(
        username=f"fictional.followup.{suffix}",
        first_name="Fictional",
        last_name=suffix.title(),
    )
    membership = ChurchMembership.objects.create(
        user=user,
        church=church,
        role=role,
    )
    client = APIClient()
    client.force_login(user)
    session = client.session
    session[ACTIVE_CHURCH_SESSION_KEY] = church.id
    session.save()
    return client, membership


def follow_up(
    church: Church,
    *,
    assigned_to: User | None = None,
    suffix: str,
) -> FollowUp:
    person = Person.objects.create(
        church=church,
        full_name=f"Follow-up Person {suffix}",
        phone="+61000000000",
    )
    return FollowUp.objects.create(
        church=church,
        person=person,
        source=FollowUp.Source.EVENT_VISIT,
        assigned_to=assigned_to,
        due_at=timezone.localdate() + timedelta(days=2),
    )


def test_pastor_can_view_pipeline_assign_and_close_follow_up() -> None:
    church = Church.objects.create(name="Fictional Follow-up Queue")
    client, pastor = member(church, ChurchMembership.Role.PASTOR, "pastor")
    _, leader = member(church, ChurchMembership.Role.LEADER, "leader")
    item = follow_up(church, suffix="Queue")

    list_response = client.get(reverse("care:follow-up-list"))
    update = client.patch(
        reverse("care:follow-up-detail", args=(item.id,)),
        {
            "status": FollowUp.Status.CLOSED,
            "engagement": FollowUp.Engagement.LIKELY,
            "assigned_to": leader.user_id,
            "outcome": "Fictional connected outcome",
        },
        format="json",
    )

    assert list_response.status_code == 200
    assert list_response.json()[0]["person"]["full_name"] == item.person.full_name
    assert update.status_code == 200
    assert update.json()["assigned_to"] == leader.user_id
    assert update.json()["closed_at"] is not None
    assert update.json()["engagement"] == FollowUp.Engagement.LIKELY
    assert update.json()["outcome"] == "Fictional connected outcome"
    assert pastor.user_id != leader.user_id


def test_leader_only_sees_and_updates_items_assigned_to_self() -> None:
    church = Church.objects.create(name="Fictional Leader Follow-ups")
    client, leader = member(church, ChurchMembership.Role.LEADER, "self")
    _, other = member(church, ChurchMembership.Role.LEADER, "other")
    own = follow_up(church, assigned_to=leader.user, suffix="Own")
    hidden = follow_up(church, assigned_to=other.user, suffix="Hidden")

    list_response = client.get(reverse("care:follow-up-list"))
    update = client.patch(
        reverse("care:follow-up-detail", args=(own.id,)),
        {
            "status": FollowUp.Status.IN_PROGRESS,
            "assigned_to": other.user_id,
        },
        format="json",
    )
    hidden_response = client.get(reverse("care:follow-up-detail", args=(hidden.id,)))

    assert [item["id"] for item in list_response.json()] == [own.id]
    assert update.status_code == 200
    assert update.json()["status"] == FollowUp.Status.IN_PROGRESS
    assert update.json()["assigned_to"] == leader.user_id
    assert hidden_response.status_code == 404


def test_member_is_denied_and_cross_church_follow_up_is_hidden() -> None:
    church = Church.objects.create(name="Fictional Follow-up Access")
    other_church = Church.objects.create(name="Fictional Follow-up Other")
    member_client, _ = member(church, ChurchMembership.Role.MEMBER, "member")
    pastor_client, _ = member(church, ChurchMembership.Role.PASTOR, "cross")
    hidden = follow_up(other_church, suffix="Other")

    assert member_client.get(reverse("care:follow-up-list")).status_code == 403
    assert (
        pastor_client.get(
            reverse("care:follow-up-detail", args=(hidden.id,))
        ).status_code
        == 404
    )


def test_worker_choices_are_church_scoped_and_leader_gets_self_only() -> None:
    church = Church.objects.create(name="Fictional Worker Choices")
    other_church = Church.objects.create(name="Fictional Worker Other")
    pastor_client, pastor = member(
        church,
        ChurchMembership.Role.PASTOR,
        "choices.pastor",
    )
    leader_client, leader = member(
        church,
        ChurchMembership.Role.LEADER,
        "choices.leader",
    )
    _, outsider = member(
        other_church,
        ChurchMembership.Role.LEADER,
        "choices.outsider",
    )

    pastor_response = pastor_client.get(reverse("care:worker-choices"))
    leader_response = leader_client.get(reverse("care:worker-choices"))

    assert {item["id"] for item in pastor_response.json()} == {
        pastor.user_id,
        leader.user_id,
    }
    assert leader_response.json()[0]["id"] == leader.user_id
    assert outsider.user_id not in {item["id"] for item in pastor_response.json()}
