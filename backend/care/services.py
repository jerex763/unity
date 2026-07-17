from django.db import IntegrityError, transaction

from events.models import EventRegistration
from people.models import Person

from .models import FollowUp


@transaction.atomic
def ensure_first_event_follow_up(
    registration: EventRegistration,
) -> FollowUp | None:
    """Create one follow-up for a visitor's first non-cancelled event."""
    if (
        registration.status == EventRegistration.Status.CANCELLED
        or registration.person.membership_status != Person.MembershipStatus.VISITOR
    ):
        return None
    prior_visit = (
        EventRegistration.objects.filter(person=registration.person)
        .exclude(pk=registration.pk)
        .exclude(status=EventRegistration.Status.CANCELLED)
        .exists()
    )
    if prior_visit:
        return None
    existing = (
        FollowUp.objects.filter(person=registration.person)
        .exclude(status=FollowUp.Status.CLOSED)
        .first()
    )
    if existing is not None:
        return existing
    try:
        return FollowUp.objects.create(
            church=registration.church,
            person=registration.person,
            source=FollowUp.Source.EVENT_VISIT,
            status=FollowUp.Status.NEW,
        )
    except IntegrityError:
        return (
            FollowUp.objects.filter(person=registration.person)
            .exclude(status=FollowUp.Status.CLOSED)
            .first()
        )
