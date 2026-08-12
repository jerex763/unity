from datetime import timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.utils import timezone

from .models import FollowUp


def church_timezone(church) -> ZoneInfo:
    try:
        return ZoneInfo(church.timezone)
    except ZoneInfoNotFoundError:
        return ZoneInfo("Australia/Sydney")


def church_today(church):
    return timezone.localtime(timezone.now(), church_timezone(church)).date()


def attention_for(follow_up: FollowUp) -> dict[str, object]:
    now = timezone.now()
    today = church_today(follow_up.church)
    is_open = follow_up.status != FollowUp.Status.CLOSED
    overdue_days = (
        (today - follow_up.due_at).days
        if is_open and follow_up.due_at and follow_up.due_at < today
        else 0
    )
    last_interaction_at = None
    for interaction in follow_up.interactions.all():
        # created_at is the trustworthy evidence that contact was logged. A future
        # occurred_at value must not indefinitely suppress stale attention.
        candidate = interaction.created_at
        if last_interaction_at is None or candidate > last_interaction_at:
            last_interaction_at = candidate
    stale_anchor = last_interaction_at or follow_up.status_changed_at
    postponement_count = sum(
        1
        for change in follow_up.due_date_changes.all()
        if change.previous_due_at is not None
        and change.new_due_at is not None
        and change.new_due_at > change.previous_due_at
    )
    flags = {
        "overdue": bool(overdue_days),
        "due_today": bool(is_open and follow_up.due_at == today),
        "unassigned_too_long": bool(
            is_open
            and follow_up.status == FollowUp.Status.NEW
            and follow_up.assigned_to_id is None
            and now - follow_up.created_at >= timedelta(hours=24)
        ),
        "no_action": bool(
            is_open
            and follow_up.status == FollowUp.Status.ASSIGNED
            and follow_up.due_at is not None
            and follow_up.due_at <= today
        ),
        "stale": bool(
            is_open
            and follow_up.status == FollowUp.Status.IN_PROGRESS
            and now - stale_anchor >= timedelta(days=3)
        ),
        "escalated": bool(is_open and (postponement_count >= 2 or overdue_days >= 3)),
    }
    priorities = (
        ("escalated", "Escalate and agree the next action"),
        ("overdue", "Complete or reschedule the overdue action"),
        ("due_today", "Complete today's agreed action"),
        ("unassigned_too_long", "Assign an owner and due date"),
        ("stale", "Log contact or agree a new action"),
        ("no_action", "Record progress or agree a new due date"),
    )
    next_action = next(
        (message for flag, message in priorities if flags[flag]),
        "Continue the agreed follow-up",
    )
    return {
        **flags,
        "postponement_count": postponement_count,
        "next_action": next_action,
    }
