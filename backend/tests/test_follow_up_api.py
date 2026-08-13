from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.constants import ACTIVE_CHURCH_SESSION_KEY
from accounts.models import ChurchMembership, User
from care.models import FollowUp, FollowUpDueDateChange, Interaction
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
        wechat_id="fictional_followup",
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
    assert list_response.json()[0]["person"]["wechat_id"] == "fictional_followup"
    assert list_response.json()[0]["person"]["has_whatsapp"] is True
    assert update.status_code == 200
    assert update.json()["assigned_to"] == leader.user_id
    assert update.json()["closed_at"] is not None
    assert update.json()["engagement"] == FollowUp.Engagement.LIKELY
    assert update.json()["outcome"] == "Fictional connected outcome"
    assert pastor.user_id != leader.user_id


@pytest.mark.parametrize(
    ("payload", "error_field"),
    [
        ({"assigned_to": "worker"}, "due_at"),
        ({"status": FollowUp.Status.ASSIGNED, "due_at": None}, "due_at"),
        ({"status": FollowUp.Status.IN_PROGRESS, "due_at": None}, "due_at"),
        ({"status": FollowUp.Status.CONNECTED, "due_at": None}, "due_at"),
        (
            {
                "status": FollowUp.Status.CLOSED,
                "due_at": None,
                "outcome": "   ",
            },
            "outcome",
        ),
    ],
)
def test_working_transitions_require_a_next_action_or_outcome(
    payload: dict[str, object],
    error_field: str,
) -> None:
    church = Church.objects.create(name=f"Fictional Validation {error_field}")
    client, _ = member(
        church, ChurchMembership.Role.PASTOR, f"validation.{error_field}"
    )
    _, worker = member(church, ChurchMembership.Role.LEADER, f"worker.{error_field}")
    item = follow_up(church, suffix=f"Validation {error_field}")
    item.due_at = None
    item.save(update_fields=("due_at", "updated_at"))
    if payload.get("assigned_to") == "worker":
        payload["assigned_to"] = worker.user_id

    response = client.patch(
        reverse("care:follow-up-detail", args=(item.id,)),
        payload,
        format="json",
    )

    assert response.status_code == 400
    assert error_field in response.json()


def test_connected_still_requires_due_and_closed_outcome_does_not() -> None:
    church = Church.objects.create(name="Fictional Follow-up Outcomes")
    client, _ = member(church, ChurchMembership.Role.PASTOR, "outcomes")
    connected_item = follow_up(church, suffix="Connected Outcome")
    closed_item = follow_up(church, suffix="Closed Outcome")
    detail_name = "care:follow-up-detail"

    connected = client.patch(
        reverse(detail_name, args=(connected_item.id,)),
        {
            "status": FollowUp.Status.CONNECTED,
            "due_at": None,
            "outcome": "  Connected with a fictional community group.  ",
        },
        format="json",
    )
    closed = client.patch(
        reverse(detail_name, args=(closed_item.id,)),
        {
            "status": FollowUp.Status.CLOSED,
            "due_at": None,
            "outcome": "Fictional follow-up completed.",
        },
        format="json",
    )

    assert connected.status_code == 400
    assert "due_at" in connected.json()
    assert closed.status_code == 200
    assert closed.json()["closed_at"] is not None


def test_reopening_closed_follow_up_clears_closed_at() -> None:
    church = Church.objects.create(name="Fictional Follow-up Reopening")
    client, _ = member(church, ChurchMembership.Role.PASTOR, "reopening")
    item = follow_up(church, suffix="Reopening")
    detail_url = reverse("care:follow-up-detail", args=(item.id,))

    closed = client.patch(
        detail_url,
        {
            "status": FollowUp.Status.CLOSED,
            "outcome": "Fictional follow-up completed.",
        },
        format="json",
    )
    item.refresh_from_db()

    assert closed.status_code == 200
    assert closed.json()["closed_at"] is not None
    assert item.closed_at is not None

    reopened = client.patch(
        detail_url,
        {"status": FollowUp.Status.IN_PROGRESS},
        format="json",
    )
    item.refresh_from_db()

    assert reopened.status_code == 200
    assert reopened.json()["closed_at"] is None
    assert item.closed_at is None


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


def test_my_follow_ups_only_returns_open_assignments_in_due_date_order() -> None:
    church = Church.objects.create(name="Fictional My Follow-ups")
    client, pastor = member(church, ChurchMembership.Role.PASTOR, "mine")
    _, other = member(church, ChurchMembership.Role.LEADER, "mine.other")
    later = follow_up(church, assigned_to=pastor.user, suffix="Later")
    earlier = follow_up(church, assigned_to=pastor.user, suffix="Earlier")
    no_due_date = follow_up(church, assigned_to=pastor.user, suffix="No Due Date")
    closed = follow_up(church, assigned_to=pastor.user, suffix="Closed")
    follow_up(church, assigned_to=other.user, suffix="Other Worker")
    later.due_at = timezone.localdate() + timedelta(days=4)
    earlier.due_at = timezone.localdate() - timedelta(days=1)
    no_due_date.due_at = None
    closed.status = FollowUp.Status.CLOSED
    FollowUp.objects.bulk_update(
        [later, earlier, no_due_date, closed],
        ["due_at", "status"],
    )

    response = client.get(reverse("care:my-follow-up-list"))

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [
        earlier.id,
        later.id,
        no_due_date.id,
    ]


def test_member_is_denied_and_cross_church_follow_up_is_hidden() -> None:
    church = Church.objects.create(name="Fictional Follow-up Access")
    other_church = Church.objects.create(name="Fictional Follow-up Other")
    member_client, _ = member(church, ChurchMembership.Role.MEMBER, "member")
    pastor_client, _ = member(church, ChurchMembership.Role.PASTOR, "cross")
    hidden = follow_up(other_church, suffix="Other")

    assert member_client.get(reverse("care:follow-up-list")).status_code == 403
    assert member_client.get(reverse("care:my-follow-up-list")).status_code == 403
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


def test_attention_flags_use_church_date_and_exact_thresholds() -> None:
    church = Church.objects.create(
        name="Fictional Attention Boundaries",
        timezone="Pacific/Auckland",
    )
    client, pastor = member(church, ChurchMembership.Role.PASTOR, "attention")
    item = follow_up(church, assigned_to=pastor.user, suffix="Attention")
    local_today = timezone.localtime(
        timezone.now(), timezone.get_fixed_timezone(720)
    ).date()
    item.status = FollowUp.Status.IN_PROGRESS
    item.due_at = local_today - timedelta(days=3)
    item.status_changed_at = timezone.now() - timedelta(days=3)
    item.save(update_fields=("status", "due_at", "status_changed_at", "updated_at"))

    response = client.get(reverse("care:follow-up-detail", args=(item.id,)))

    assert response.status_code == 200
    attention = response.json()["attention"]
    assert attention["overdue"] is True
    assert attention["due_today"] is False
    assert attention["stale"] is True
    assert attention["escalated"] is True

    Interaction.objects.create(
        church=church,
        person=item.person,
        author=pastor.user,
        kind=Interaction.Kind.MESSAGE,
        summary="Fictional recent contact",
        follow_up=item,
    )
    refreshed = client.get(reverse("care:follow-up-detail", args=(item.id,)))
    assert refreshed.json()["attention"]["stale"] is False


def test_attention_uses_church_date_around_utc_midnight() -> None:
    church = Church.objects.create(
        name="Fictional Midnight Church", timezone="Australia/Sydney"
    )
    client, pastor = member(church, ChurchMembership.Role.PASTOR, "midnight")
    item = follow_up(church, assigned_to=pastor.user, suffix="Midnight")
    item.due_at = timezone.datetime(2026, 8, 13).date()
    item.save(update_fields=("due_at", "updated_at"))
    fixed_now = datetime(2026, 8, 13, 14, 5, tzinfo=UTC)

    with patch("care.attention.timezone.now", return_value=fixed_now):
        response = client.get(reverse("care:follow-up-detail", args=(item.id,)))

    assert response.json()["attention"]["overdue"] is True
    assert response.json()["attention"]["due_today"] is False


def test_elapsed_attention_thresholds_are_exact_across_dst_boundary() -> None:
    church = Church.objects.create(
        name="Fictional DST Church", timezone="Australia/Sydney"
    )
    client, pastor = member(church, ChurchMembership.Role.PASTOR, "dst")
    unassigned = follow_up(church, suffix="DST Unassigned")
    stale = follow_up(church, assigned_to=pastor.user, suffix="DST Stale")
    stale.status = FollowUp.Status.IN_PROGRESS
    fixed_now = datetime(2026, 10, 4, 16, 0, tzinfo=UTC)
    session = client.session
    session.set_expiry(fixed_now + timedelta(days=30))
    session.save()
    FollowUp.objects.filter(pk=unassigned.pk).update(
        created_at=fixed_now - timedelta(hours=24) + timedelta(seconds=1)
    )
    FollowUp.objects.filter(pk=stale.pk).update(
        status=FollowUp.Status.IN_PROGRESS,
        status_changed_at=fixed_now - timedelta(days=3) + timedelta(seconds=1),
    )

    with patch("care.attention.timezone.now", return_value=fixed_now):
        unassigned_before = client.get(
            reverse("care:follow-up-detail", args=(unassigned.id,))
        )
        stale_before = client.get(reverse("care:follow-up-detail", args=(stale.id,)))

    assert unassigned_before.json()["attention"]["unassigned_too_long"] is False
    assert stale_before.json()["attention"]["stale"] is False

    FollowUp.objects.filter(pk=unassigned.pk).update(
        created_at=fixed_now - timedelta(hours=24)
    )
    FollowUp.objects.filter(pk=stale.pk).update(
        status_changed_at=fixed_now - timedelta(days=3)
    )
    with patch("care.attention.timezone.now", return_value=fixed_now):
        unassigned_at = client.get(
            reverse("care:follow-up-detail", args=(unassigned.id,))
        )
        stale_at = client.get(reverse("care:follow-up-detail", args=(stale.id,)))

    assert unassigned_at.json()["attention"]["unassigned_too_long"] is True
    assert stale_at.json()["attention"]["stale"] is True


def test_status_transition_resets_stale_anchor() -> None:
    church = Church.objects.create(name="Fictional Status Anchor")
    client, pastor = member(church, ChurchMembership.Role.PASTOR, "status.anchor")
    item = follow_up(church, assigned_to=pastor.user, suffix="Status Anchor")
    old_anchor = timezone.now() - timedelta(days=5)
    FollowUp.objects.filter(pk=item.pk).update(
        status=FollowUp.Status.ASSIGNED,
        status_changed_at=old_anchor,
    )

    response = client.patch(
        reverse("care:follow-up-detail", args=(item.id,)),
        {"status": FollowUp.Status.IN_PROGRESS},
        format="json",
    )
    item.refresh_from_db()

    assert response.status_code == 200
    assert item.status_changed_at > old_anchor
    assert response.json()["attention"]["stale"] is False


def test_unassigned_and_no_action_attention_thresholds() -> None:
    church = Church.objects.create(name="Fictional Attention States")
    client, pastor = member(church, ChurchMembership.Role.PASTOR, "states")
    unassigned = follow_up(church, suffix="Unassigned")
    assigned = follow_up(church, assigned_to=pastor.user, suffix="No Action")
    FollowUp.objects.filter(pk=unassigned.pk).update(
        created_at=timezone.now() - timedelta(hours=24)
    )
    assigned.status = FollowUp.Status.ASSIGNED
    assigned.due_at = timezone.localdate()
    assigned.save(update_fields=("status", "due_at", "updated_at"))

    response = client.get(reverse("care:follow-up-list"))
    by_id = {row["id"]: row["attention"] for row in response.json()}

    assert by_id[unassigned.id]["unassigned_too_long"] is True
    assert by_id[assigned.id]["no_action"] is True
    assert by_id[assigned.id]["due_today"] is True


def test_postponement_is_audited_and_conditional_reason_is_enforced() -> None:
    church = Church.objects.create(name="Fictional Postponement")
    client, pastor = member(church, ChurchMembership.Role.PASTOR, "postpone")
    item = follow_up(church, assigned_to=pastor.user, suffix="Postpone")
    detail_url = reverse("care:follow-up-detail", args=(item.id,))

    first = client.patch(
        detail_url,
        {"due_at": (item.due_at + timedelta(days=1)).isoformat()},
        format="json",
    )
    second_without_reason = client.patch(
        detail_url,
        {"due_at": (item.due_at + timedelta(days=2)).isoformat()},
        format="json",
    )
    second = client.patch(
        detail_url,
        {
            "due_at": (item.due_at + timedelta(days=2)).isoformat(),
            "postpone_reason": FollowUpDueDateChange.Reason.AWAITING_RESPONSE,
        },
        format="json",
    )

    assert first.status_code == 200
    assert second_without_reason.status_code == 400
    assert "postpone_reason" in second_without_reason.json()
    assert second.status_code == 200
    assert second.json()["attention"]["postponement_count"] == 2
    assert second.json()["attention"]["escalated"] is True
    changes = list(item.due_date_changes.all())
    assert len(changes) == 2
    assert changes[0].actor_id == pastor.user_id
    assert changes[1].reason == FollowUpDueDateChange.Reason.AWAITING_RESPONSE


def test_postponement_evidence_misuse_reports_the_supplied_field() -> None:
    church = Church.objects.create(name="Fictional Evidence Errors")
    client, pastor = member(church, ChurchMembership.Role.PASTOR, "evidence.errors")
    item = follow_up(church, assigned_to=pastor.user, suffix="Evidence Errors")
    interaction = Interaction.objects.create(
        church=church,
        person=item.person,
        author=pastor.user,
        kind=Interaction.Kind.CALL,
        summary="Fictional evidence",
        follow_up=item,
    )
    url = reverse("care:follow-up-detail", args=(item.id,))

    reason_response = client.patch(
        url,
        {
            "due_at": (item.due_at - timedelta(days=1)).isoformat(),
            "postpone_reason": FollowUpDueDateChange.Reason.PERSON_REQUESTED,
        },
        format="json",
    )
    interaction_response = client.patch(
        url,
        {
            "due_at": (item.due_at - timedelta(days=1)).isoformat(),
            "postpone_interaction": interaction.id,
        },
        format="json",
    )

    assert reason_response.status_code == 400
    assert set(reason_response.json()) == {"postpone_reason"}
    assert interaction_response.status_code == 400
    assert set(interaction_response.json()) == {"postpone_interaction"}


def test_overdue_postponement_accepts_only_a_qualifying_linked_interaction() -> None:
    church = Church.objects.create(name="Fictional Interaction Postponement")
    client, pastor = member(church, ChurchMembership.Role.PASTOR, "interaction")
    item = follow_up(church, assigned_to=pastor.user, suffix="Interaction")
    other = follow_up(church, assigned_to=pastor.user, suffix="Other Interaction")
    item.due_at = timezone.localdate() - timedelta(days=1)
    item.save(update_fields=("due_at", "updated_at"))
    interaction = Interaction.objects.create(
        church=church,
        person=item.person,
        author=pastor.user,
        kind=Interaction.Kind.CALL,
        summary="Fictional safe schedule context",
        follow_up=item,
    )
    item.due_schedule_changed_at = timezone.now()
    item.save(update_fields=("due_schedule_changed_at", "updated_at"))
    Interaction.objects.filter(pk=interaction.pk).update(
        created_at=item.due_schedule_changed_at - timedelta(seconds=1)
    )
    interaction.refresh_from_db()
    wrong = Interaction.objects.create(
        church=church,
        person=other.person,
        author=pastor.user,
        kind=Interaction.Kind.CALL,
        summary="Fictional unrelated context",
        follow_up=other,
    )
    other_church = Church.objects.create(name="Fictional Other Schedule Church")
    cross_person = Person.objects.create(
        church=other_church,
        full_name="Fictional Cross Tenant Interaction",
    )
    cross_follow_up = FollowUp.objects.create(
        church=other_church,
        person=cross_person,
        source=FollowUp.Source.OTHER,
    )
    cross = Interaction.objects.create(
        church=other_church,
        person=cross_person,
        author=pastor.user,
        kind=Interaction.Kind.MESSAGE,
        summary="Fictional cross tenant context",
        follow_up=cross_follow_up,
    )
    detail_url = reverse("care:follow-up-detail", args=(item.id,))
    new_due = timezone.localdate() + timedelta(days=1)

    rejected = client.patch(
        detail_url,
        {"due_at": new_due.isoformat(), "postpone_interaction": wrong.id},
        format="json",
    )
    cross_rejected = client.patch(
        detail_url,
        {"due_at": new_due.isoformat(), "postpone_interaction": cross.id},
        format="json",
    )
    legacy_rejected = client.patch(
        detail_url,
        {"due_at": new_due.isoformat(), "postpone_interaction": interaction.id},
        format="json",
    )
    qualifying = Interaction.objects.create(
        church=church,
        person=item.person,
        author=pastor.user,
        kind=Interaction.Kind.MESSAGE,
        summary="Fictional new schedule context",
        follow_up=item,
    )
    accepted = client.patch(
        detail_url,
        {"due_at": new_due.isoformat(), "postpone_interaction": qualifying.id},
        format="json",
    )

    assert rejected.status_code == 400
    assert "postpone_interaction" in rejected.json()
    assert cross_rejected.status_code == 400
    assert "postpone_interaction" in cross_rejected.json()
    assert legacy_rejected.status_code == 400
    assert "postpone_interaction" in legacy_rejected.json()
    assert accepted.status_code == 200
    assert item.due_date_changes.get().interaction_id == qualifying.id


def test_future_occurred_at_does_not_hide_a_stale_contact_log() -> None:
    church = Church.objects.create(name="Fictional Future Interaction")
    client, pastor = member(church, ChurchMembership.Role.PASTOR, "future.interaction")
    item = follow_up(church, assigned_to=pastor.user, suffix="Future Interaction")
    item.status = FollowUp.Status.IN_PROGRESS
    item.status_changed_at = timezone.now() - timedelta(days=5)
    item.save(update_fields=("status", "status_changed_at", "updated_at"))
    interaction = Interaction.objects.create(
        church=church,
        person=item.person,
        author=pastor.user,
        kind=Interaction.Kind.CALL,
        occurred_at=timezone.now() + timedelta(days=30),
        summary="Fictional future occurred time",
        follow_up=item,
    )
    Interaction.objects.filter(pk=interaction.pk).update(
        created_at=timezone.now() - timedelta(days=4)
    )

    response = client.get(reverse("care:follow-up-detail", args=(item.id,)))

    assert response.json()["attention"]["stale"] is True


def test_senior_attention_dashboard_and_leader_scope() -> None:
    church = Church.objects.create(name="Fictional Attention Dashboard")
    pastor_client, pastor = member(
        church, ChurchMembership.Role.PASTOR, "dashboard.pastor"
    )
    leader_client, leader = member(
        church, ChurchMembership.Role.LEADER, "dashboard.leader"
    )
    _, other = member(church, ChurchMembership.Role.LEADER, "dashboard.other")
    own = follow_up(church, assigned_to=pastor.user, suffix="Pastor Own")
    leader_own = follow_up(church, assigned_to=leader.user, suffix="Leader Own")
    escalated = follow_up(church, assigned_to=other.user, suffix="Escalated")
    unassigned = follow_up(church, suffix="Old Unassigned")
    escalated.due_at = timezone.localdate() - timedelta(days=3)
    escalated.save(update_fields=("due_at", "updated_at"))
    FollowUp.objects.filter(pk=unassigned.pk).update(
        created_at=timezone.now() - timedelta(hours=24)
    )

    pastor_response = pastor_client.get(reverse("care:my-follow-up-list"))
    leader_response = leader_client.get(reverse("care:my-follow-up-list"))

    assert {row["id"] for row in pastor_response.json()} == {
        own.id,
        escalated.id,
        unassigned.id,
    }
    assert [row["id"] for row in leader_response.json()] == [leader_own.id]


def test_pipeline_orders_overdue_before_today_future_and_no_date() -> None:
    church = Church.objects.create(name="Fictional Due Priority")
    client, _ = member(church, ChurchMembership.Role.PASTOR, "priority")
    future = follow_up(church, suffix="Future")
    no_date = follow_up(church, suffix="No Date Priority")
    today = follow_up(church, suffix="Today")
    overdue = follow_up(church, suffix="Overdue")
    future.status = FollowUp.Status.NEW
    future.due_at = timezone.localdate() + timedelta(days=1)
    no_date.status = FollowUp.Status.ASSIGNED
    no_date.due_at = None
    today.status = FollowUp.Status.CONNECTED
    today.due_at = timezone.localdate()
    overdue.status = FollowUp.Status.NEW
    overdue.due_at = timezone.localdate() - timedelta(days=1)
    FollowUp.objects.bulk_update(
        [future, no_date, today, overdue], ["status", "due_at"]
    )

    response = client.get(reverse("care:follow-up-list"))

    assert [row["id"] for row in response.json()] == [
        overdue.id,
        today.id,
        future.id,
        no_date.id,
    ]
