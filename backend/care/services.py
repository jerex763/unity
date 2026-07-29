from django.db import IntegrityError, transaction
from django.db.models import Q

from events.models import EventRegistration
from people.models import Person

from .models import FollowUp


@transaction.atomic
def ensure_first_event_follow_up(
    registration: EventRegistration,
) -> FollowUp | None:
    """Create one follow-up for a visitor's first actual event check-in."""
    if (
        registration.status == EventRegistration.Status.CANCELLED
        or registration.checked_in_at is None
        or registration.person.membership_status != Person.MembershipStatus.VISITOR
    ):
        return None
    prior_visit = (
        EventRegistration.objects.filter(
            church=registration.church,
            person=registration.person,
            checked_in_at__isnull=False,
        )
        .exclude(pk=registration.pk)
        .exists()
    )
    if prior_visit:
        return None
    historical_event_follow_up = (
        FollowUp.objects.filter(
            church=registration.church,
            person=registration.person,
            source=FollowUp.Source.EVENT_VISIT,
        )
        .order_by("created_at", "pk")
        .first()
    )
    if historical_event_follow_up is not None:
        return historical_event_follow_up
    existing = (
        FollowUp.objects.filter(
            church=registration.church,
            person=registration.person,
        )
        .exclude(status=FollowUp.Status.CLOSED)
        .first()
    )
    if existing is not None:
        return existing
    try:
        with transaction.atomic():
            return FollowUp.objects.create(
                church=registration.church,
                person=registration.person,
                source=FollowUp.Source.EVENT_VISIT,
                status=FollowUp.Status.NEW,
            )
    except IntegrityError:
        return (
            FollowUp.objects.filter(
                church=registration.church,
                person=registration.person,
            )
            .filter(
                Q(source=FollowUp.Source.EVENT_VISIT)
                | ~Q(status=FollowUp.Status.CLOSED)
            )
            .order_by("created_at", "pk")
            .first()
        )
