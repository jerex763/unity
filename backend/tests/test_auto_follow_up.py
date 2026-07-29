from datetime import timedelta

import pytest
from django.utils import timezone

from accounts.models import User
from care.models import FollowUp, Interaction
from care.services import ensure_first_event_follow_up
from events.models import Event, EventRegistration
from events.services import (
    cancel_registration,
    register_for_event,
    set_manual_check_in,
)
from people.models import Person
from tenancy.models import Church

pytestmark = pytest.mark.django_db


def event(church: Church, creator: User, suffix: str) -> Event:
    starts_at = timezone.now() + timedelta(days=2)
    return Event.objects.create(
        church=church,
        title=f"Fictional Follow-up Event {suffix}",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=1),
        created_by=creator,
    )


def test_registration_and_pre_check_in_cancel_create_no_follow_up() -> None:
    church = Church.objects.create(name="Fictional Registration Follow-up")
    worker = User.objects.create_user(username="fictional.registration.followup")
    person = Person.objects.create(church=church, full_name="Registered Visitor")
    first_event = event(church, worker, "Registration")

    registration = register_for_event(event=first_event, person=person)
    assert not FollowUp.objects.filter(person=person).exists()

    repeated = register_for_event(
        event=first_event,
        person=person,
        note="Fictional updated registration",
    )
    assert not FollowUp.objects.filter(person=person).exists()

    cancelled = cancel_registration(registration)

    assert repeated.pk == registration.pk
    assert cancelled.status == EventRegistration.Status.CANCELLED
    assert not FollowUp.objects.filter(person=person).exists()


def test_first_visitor_check_in_creates_exactly_one_event_follow_up() -> None:
    church = Church.objects.create(name="Fictional First Check-in")
    worker = User.objects.create_user(username="fictional.first.checkin")
    person = Person.objects.create(church=church, full_name="First Visitor")
    registration = register_for_event(
        event=event(church, worker, "First"),
        person=person,
    )

    set_manual_check_in(registration, checked_in=True)

    follow_up = FollowUp.objects.get(person=person)
    assert follow_up.church == church
    assert follow_up.source == FollowUp.Source.EVENT_VISIT
    assert follow_up.status == FollowUp.Status.NEW


def test_unattended_registration_does_not_block_first_actual_check_in() -> None:
    church = Church.objects.create(name="Fictional Unattended Registration")
    worker = User.objects.create_user(username="fictional.unattended.registration")
    person = Person.objects.create(church=church, full_name="Later Attending Visitor")
    register_for_event(event=event(church, worker, "Unattended"), person=person)
    attended = register_for_event(
        event=event(church, worker, "Attended"),
        person=person,
    )

    set_manual_check_in(attended, checked_in=True)

    assert (
        FollowUp.objects.filter(
            church=church,
            person=person,
            source=FollowUp.Source.EVENT_VISIT,
        ).count()
        == 1
    )


def test_repeat_undo_and_recheck_do_not_duplicate_or_delete_follow_up() -> None:
    church = Church.objects.create(name="Fictional Repeated Check-in")
    worker = User.objects.create_user(username="fictional.repeated.checkin")
    person = Person.objects.create(church=church, full_name="Repeated Visitor")
    registration = register_for_event(
        event=event(church, worker, "Repeated"),
        person=person,
    )

    first = set_manual_check_in(registration, checked_in=True)
    follow_up = FollowUp.objects.get(person=person)
    repeated = set_manual_check_in(first, checked_in=True)
    undone = set_manual_check_in(repeated, checked_in=False)
    set_manual_check_in(undone, checked_in=True)

    assert repeated.checked_in_at == first.checked_in_at
    assert FollowUp.objects.filter(person=person).count() == 1
    assert FollowUp.objects.get(person=person) == follow_up


def test_later_event_does_not_recreate_follow_up_after_first_is_closed() -> None:
    church = Church.objects.create(name="Fictional Later Follow-up")
    worker = User.objects.create_user(username="fictional.later.followup")
    person = Person.objects.create(church=church, full_name="Returning Visitor")
    first = register_for_event(
        event=event(church, worker, "First"),
        person=person,
    )
    set_manual_check_in(first, checked_in=True)
    follow_up = FollowUp.objects.get(person=person)
    follow_up.status = FollowUp.Status.CLOSED
    follow_up.closed_at = timezone.now()
    follow_up.save(update_fields=("status", "closed_at", "updated_at"))
    later = register_for_event(
        event=event(church, worker, "Second"),
        person=person,
    )

    set_manual_check_in(later, checked_in=True)
    ensure_first_event_follow_up(first)

    assert FollowUp.objects.filter(person=person).count() == 1


def test_closed_legacy_event_follow_up_suppresses_first_actual_check_in() -> None:
    church = Church.objects.create(name="Fictional Legacy Follow-up")
    worker = User.objects.create_user(username="fictional.legacy.followup")
    person = Person.objects.create(church=church, full_name="Legacy Visitor")
    historical = FollowUp.objects.create(
        church=church,
        person=person,
        source=FollowUp.Source.EVENT_VISIT,
        status=FollowUp.Status.CLOSED,
        closed_at=timezone.now(),
        outcome="Fictional legacy registration follow-up",
    )
    registration = register_for_event(
        event=event(church, worker, "First Actual Check-in"),
        person=person,
    )

    set_manual_check_in(registration, checked_in=True)

    assert FollowUp.objects.filter(person=person).count() == 1
    assert FollowUp.objects.get(person=person) == historical
    assert not (
        FollowUp.objects.filter(person=person)
        .exclude(status=FollowUp.Status.CLOSED)
        .exists()
    )


def test_existing_open_same_church_follow_up_is_reused() -> None:
    church = Church.objects.create(name="Fictional Existing Follow-up")
    worker = User.objects.create_user(username="fictional.existing.followup")
    visitor = Person.objects.create(church=church, full_name="Visitor With Follow-up")
    existing = FollowUp.objects.create(
        church=church,
        person=visitor,
        source=FollowUp.Source.FRIEND_INVITE,
        status=FollowUp.Status.IN_PROGRESS,
        assigned_to=worker,
    )
    interaction = Interaction.objects.create(
        church=church,
        person=visitor,
        author=worker,
        follow_up=existing,
        kind=Interaction.Kind.MESSAGE,
        summary="Fictional existing follow-up history",
    )
    registration = EventRegistration.objects.create(
        church=church,
        event=event(church, worker, "Visitor"),
        person=visitor,
        checked_in_at=timezone.now(),
        checkin_method=EventRegistration.CheckinMethod.MANUAL,
    )

    assert ensure_first_event_follow_up(registration) == existing
    existing.refresh_from_db()
    interaction.refresh_from_db()
    assert FollowUp.objects.filter(person=visitor).count() == 1
    assert existing.source == FollowUp.Source.FRIEND_INVITE
    assert existing.status == FollowUp.Status.IN_PROGRESS
    assert existing.assigned_to == worker
    assert interaction.follow_up == existing


@pytest.mark.parametrize(
    "membership_status",
    (
        Person.MembershipStatus.NEWCOMER,
        Person.MembershipStatus.REGULAR,
        Person.MembershipStatus.MEMBER,
        Person.MembershipStatus.INACTIVE,
    ),
)
def test_non_visitor_check_in_does_not_create_follow_up(
    membership_status: str,
) -> None:
    church = Church.objects.create(name=f"Fictional Excluded {membership_status}")
    worker = User.objects.create_user(
        username=f"fictional.excluded.{membership_status}"
    )
    person = Person.objects.create(
        church=church,
        full_name=f"Excluded {membership_status}",
        membership_status=membership_status,
    )
    registration = EventRegistration.objects.create(
        church=church,
        event=event(church, worker, membership_status),
        person=person,
    )

    set_manual_check_in(registration, checked_in=True)

    assert not FollowUp.objects.filter(person=person).exists()


def test_cancellation_and_status_change_preserve_follow_up_and_interaction() -> None:
    church = Church.objects.create(name="Fictional Preserved History")
    worker = User.objects.create_user(username="fictional.preserved.history")
    person = Person.objects.create(church=church, full_name="History Visitor")
    registration = register_for_event(
        event=event(church, worker, "History"),
        person=person,
    )
    set_manual_check_in(registration, checked_in=True)
    follow_up = FollowUp.objects.get(person=person)
    interaction = Interaction.objects.create(
        church=church,
        person=person,
        author=worker,
        follow_up=follow_up,
        kind=Interaction.Kind.CALL,
        summary="Fictional welcome call",
    )

    cancel_registration(registration)
    person.membership_status = Person.MembershipStatus.MEMBER
    person.save(update_fields=("membership_status", "updated_at"))

    follow_up.refresh_from_db()
    interaction.refresh_from_db()
    assert follow_up.person == person
    assert interaction.follow_up == follow_up
    assert FollowUp.objects.filter(person=person).count() == 1
