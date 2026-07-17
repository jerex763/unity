from typing import Any

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from accounts.models import ChurchMembership
from people.models import Person

from .models import AuditEvent
from .services import record_audit_event


@receiver(pre_save, sender=Person)
def capture_person_state(
    sender: type[Person],
    instance: Person,
    **kwargs: Any,
) -> None:
    instance._audit_previous = (
        sender.objects.filter(pk=instance.pk)
        .values("membership_status", "anonymized_at")
        .first()
        if instance.pk
        else None
    )


@receiver(post_save, sender=Person)
def audit_person_change(
    sender: type[Person],
    instance: Person,
    created: bool,
    **kwargs: Any,
) -> None:
    previous = getattr(instance, "_audit_previous", None)
    if created:
        action = AuditEvent.Action.PERSON_CREATED
    elif previous and previous["anonymized_at"] is None and instance.anonymized_at:
        action = AuditEvent.Action.PERSON_ANONYMIZED
    elif (
        previous
        and previous["membership_status"] != instance.membership_status
        and instance.membership_status == Person.MembershipStatus.INACTIVE
    ):
        action = AuditEvent.Action.PERSON_DEACTIVATED
    else:
        action = AuditEvent.Action.PERSON_UPDATED
    record_audit_event(action=action, church=instance.church, target=instance)


@receiver(pre_save, sender=ChurchMembership)
def capture_membership_state(
    sender: type[ChurchMembership],
    instance: ChurchMembership,
    **kwargs: Any,
) -> None:
    instance._audit_previous = (
        sender.objects.filter(pk=instance.pk).values("role", "is_active").first()
        if instance.pk
        else None
    )


@receiver(post_save, sender=ChurchMembership)
def audit_membership_change(
    sender: type[ChurchMembership],
    instance: ChurchMembership,
    created: bool,
    **kwargs: Any,
) -> None:
    previous = getattr(instance, "_audit_previous", None)
    previous_role = previous["role"] if previous else None
    previous_active = previous["is_active"] if previous else None

    if created or previous_role != instance.role:
        record_audit_event(
            action=AuditEvent.Action.MEMBERSHIP_ROLE_CHANGED,
            church=instance.church,
            target=instance,
            metadata={
                "previous_role": previous_role,
                "new_role": instance.role,
            },
        )
    if not created and previous_active != instance.is_active:
        record_audit_event(
            action=AuditEvent.Action.MEMBERSHIP_ACCESS_CHANGED,
            church=instance.church,
            target=instance,
            metadata={
                "previous_active": previous_active,
                "new_active": instance.is_active,
            },
        )
