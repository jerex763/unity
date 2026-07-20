from typing import TYPE_CHECKING

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from accounts.models import ChurchMembership
from audit.models import AuditEvent
from audit.services import record_audit_event
from care.models import CareCase, FollowUp, Interaction
from events.models import EventRegistration

from .models import Person, Relationship

if TYPE_CHECKING:
    from django.http import HttpRequest

    from accounts.models import User


@transaction.atomic
def deactivate_person(person: Person) -> Person:
    """Deactivate access to routine workflows while preserving history."""
    if person.membership_status == Person.MembershipStatus.INACTIVE:
        return person
    person.membership_status = Person.MembershipStatus.INACTIVE
    person.deactivated_at = timezone.now()
    person.save(update_fields=("membership_status", "deactivated_at", "updated_at"))
    return person


@transaction.atomic
def anonymize_person(person: Person) -> Person:
    """Remove identifying and free-text data while retaining operational history."""
    if person.anonymized_at is not None:
        return person

    now = timezone.now()
    person.full_name = f"Anonymized person {person.pk}"
    person.preferred_name = None
    person.gender = Person.Gender.UNSPECIFIED
    person.date_of_birth = None
    person.email = None
    person.phone = None
    person.wechat_id = None
    person.has_whatsapp = False
    person.photo_url = None
    person.home_country = None
    person.suburb = None
    person.occupation = None
    person.university = None
    person.course = None
    person.interests = []
    person.household = None
    person.membership_status = Person.MembershipStatus.INACTIVE
    person.discipleship_stage = None
    person.faith_background = None
    person.invited_by = None
    person.notes = ""
    person.deactivated_at = person.deactivated_at or now
    person.anonymized_at = now
    person.save()

    Person.objects.filter(invited_by=person).update(invited_by=None)
    Relationship.objects.filter(Q(from_person=person) | Q(to_person=person)).delete()
    EventRegistration.objects.filter(person=person).update(note="")
    FollowUp.objects.filter(person=person).update(outcome=None)
    CareCase.objects.filter(person=person).update(
        title="Anonymized care record",
        details="",
        is_confidential=False,
    )
    Interaction.objects.filter(person=person).update(summary="")

    for membership in ChurchMembership.objects.filter(person=person):
        membership.person = None
        membership.is_active = False
        membership.save(update_fields=("person", "is_active", "updated_at"))

    return person


@transaction.atomic
def hard_delete_person(
    *,
    person: Person,
    actor: "User",
    reason: str,
    request: "HttpRequest | None" = None,
) -> None:
    """Delete a person and cascading domain rows after recording a safe reason."""
    if reason not in Person.HardDeleteReason.values:
        raise ValueError("Hard deletion requires an approved explicit reason.")

    person_id = str(person.pk)
    record_audit_event(
        action=AuditEvent.Action.PERSON_HARD_DELETED,
        actor=actor,
        church=person.church,
        target_type="people.person",
        target_id=person_id,
        request=request,
        metadata={"delete_reason": reason},
    )
    person.delete(hard_delete_reason=reason)
