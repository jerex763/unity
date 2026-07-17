from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from people.models import Person

from .models import Event, EventRegistration


def registration_is_open(event: Event, *, now=None) -> bool:
    current_time = now or timezone.now()
    if not event.signup_opens or event.starts_at <= current_time:
        return False
    if event.signup_closes_at and event.signup_closes_at <= current_time:
        return False
    return True


@transaction.atomic
def register_for_event(
    *,
    event: Event,
    person: Person,
    needs_transport: bool = False,
    note: str = "",
) -> EventRegistration:
    locked_event = Event.objects.select_for_update().get(pk=event.pk)
    if person.church_id != locked_event.church_id:
        raise ValidationError("Event and person must belong to the same church.")
    now = timezone.now()
    if not locked_event.signup_opens or locked_event.starts_at <= now:
        raise ValidationError("Registration is closed for this event.")
    if locked_event.signup_closes_at and locked_event.signup_closes_at <= now:
        raise ValidationError("Registration is closed for this event.")

    existing = (
        EventRegistration.objects.select_for_update()
        .filter(event=locked_event, person=person)
        .first()
    )
    active_count = (
        EventRegistration.objects.filter(
            event=locked_event,
            status__in=(
                EventRegistration.Status.REGISTERED,
                EventRegistration.Status.WALK_IN,
            ),
        )
        .exclude(pk=getattr(existing, "pk", None))
        .count()
    )
    status = (
        EventRegistration.Status.WAITLISTED
        if locked_event.capacity is not None and active_count >= locked_event.capacity
        else EventRegistration.Status.REGISTERED
    )
    registration = existing or EventRegistration(
        church=locked_event.church,
        event=locked_event,
        person=person,
    )
    registration.status = status
    registration.needs_transport = needs_transport
    registration.note = note.strip()
    registration.registered_at = now
    registration.checked_in_at = None
    registration.checkin_method = None
    registration.full_clean()
    registration.save()
    return registration


@transaction.atomic
def cancel_registration(registration: EventRegistration) -> EventRegistration:
    locked = EventRegistration.objects.select_for_update().get(pk=registration.pk)
    if locked.status != EventRegistration.Status.CANCELLED:
        locked.status = EventRegistration.Status.CANCELLED
        locked.save(update_fields=("status", "updated_at"))
    return locked


@transaction.atomic
def set_manual_check_in(
    registration: EventRegistration,
    *,
    checked_in: bool,
) -> EventRegistration:
    locked = EventRegistration.objects.select_for_update().get(pk=registration.pk)
    if locked.status == EventRegistration.Status.CANCELLED and checked_in:
        raise ValidationError("A cancelled registration cannot be checked in.")
    if checked_in:
        if locked.checked_in_at is None:
            locked.checked_in_at = timezone.now()
            locked.checkin_method = EventRegistration.CheckinMethod.MANUAL
            locked.save(update_fields=("checked_in_at", "checkin_method", "updated_at"))
    elif locked.checked_in_at is not None or locked.checkin_method is not None:
        locked.checked_in_at = None
        locked.checkin_method = None
        locked.save(update_fields=("checked_in_at", "checkin_method", "updated_at"))
    return locked
