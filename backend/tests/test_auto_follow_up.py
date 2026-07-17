from datetime import timedelta

import pytest
from django.utils import timezone

from accounts.models import User
from care.models import FollowUp
from care.services import ensure_first_event_follow_up
from events.models import Event, EventRegistration
from events.services import register_for_event, set_manual_check_in
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


def test_first_visitor_registration_creates_one_event_follow_up() -> None:
    church = Church.objects.create(name="Fictional Auto Follow-up")
    worker = User.objects.create_user(username="fictional.auto.followup")
    person = Person.objects.create(church=church, full_name="First Visitor")
    first_event = event(church, worker, "First")

    registration = register_for_event(event=first_event, person=person)
    repeated = register_for_event(event=first_event, person=person)

    assert repeated.pk == registration.pk
    follow_up = FollowUp.objects.get(person=person)
    assert follow_up.source == FollowUp.Source.EVENT_VISIT
    assert follow_up.status == FollowUp.Status.NEW


def test_later_event_does_not_recreate_follow_up_after_first_is_closed() -> None:
    church = Church.objects.create(name="Fictional Later Follow-up")
    worker = User.objects.create_user(username="fictional.later.followup")
    person = Person.objects.create(church=church, full_name="Returning Visitor")
    first = register_for_event(event=event(church, worker, "First"), person=person)
    follow_up = FollowUp.objects.get(person=person)
    follow_up.status = FollowUp.Status.CLOSED
    follow_up.closed_at = timezone.now()
    follow_up.save(update_fields=("status", "closed_at", "updated_at"))

    register_for_event(event=event(church, worker, "Second"), person=person)
    ensure_first_event_follow_up(first)

    assert FollowUp.objects.filter(person=person).count() == 1


def test_existing_open_follow_up_is_reused_and_members_are_ignored() -> None:
    church = Church.objects.create(name="Fictional Existing Follow-up")
    worker = User.objects.create_user(username="fictional.existing.followup")
    visitor = Person.objects.create(church=church, full_name="Visitor With Follow-up")
    existing = FollowUp.objects.create(
        church=church,
        person=visitor,
        source=FollowUp.Source.FRIEND_INVITE,
    )
    visitor_registration = EventRegistration.objects.create(
        church=church,
        event=event(church, worker, "Visitor"),
        person=visitor,
    )
    member = Person.objects.create(
        church=church,
        full_name="Established Member",
        membership_status=Person.MembershipStatus.MEMBER,
    )
    member_registration = EventRegistration.objects.create(
        church=church,
        event=event(church, worker, "Member"),
        person=member,
    )

    assert ensure_first_event_follow_up(visitor_registration) == existing
    assert ensure_first_event_follow_up(member_registration) is None
    assert FollowUp.objects.filter(person=member).count() == 0


def test_manual_check_in_backfills_follow_up_for_historical_registration() -> None:
    church = Church.objects.create(name="Fictional Check-in Follow-up")
    worker = User.objects.create_user(username="fictional.checkin.followup")
    person = Person.objects.create(church=church, full_name="Historical Visitor")
    registration = EventRegistration.objects.create(
        church=church,
        event=event(church, worker, "Historical"),
        person=person,
    )

    set_manual_check_in(registration, checked_in=True)

    assert FollowUp.objects.filter(
        person=person,
        source=FollowUp.Source.EVENT_VISIT,
        status=FollowUp.Status.NEW,
    ).exists()
