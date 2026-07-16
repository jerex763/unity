from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from groups.models import Group
from people.models import Person
from tenancy.models import ChurchScopedModel


class Event(ChurchScopedModel):
    group = models.ForeignKey(
        Group,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="events",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    location = models.CharField(blank=True, max_length=200)
    capacity = models.PositiveIntegerField(blank=True, null=True)
    signup_opens = models.BooleanField(default=True)
    signup_closes_at = models.DateTimeField(blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="events_created",
    )

    class Meta:
        db_table = "event"
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_at__gt=models.F("starts_at")),
                name="event_ends_after_start",
            ),
            models.CheckConstraint(
                condition=Q(capacity__isnull=True) | Q(capacity__gt=0),
                name="event_positive_capacity",
            ),
        ]
        indexes = [models.Index(fields=("church", "starts_at"))]

    def __str__(self) -> str:
        return self.title

    def clean(self) -> None:
        super().clean()
        if self.group_id and self.group.church_id != self.church_id:
            raise ValidationError(
                {"group": "Event and group must belong to the same church."}
            )


class EventRegistration(ChurchScopedModel):
    class Status(models.TextChoices):
        REGISTERED = "registered", "Registered"
        WAITLISTED = "waitlisted", "Waitlisted"
        CANCELLED = "cancelled", "Cancelled"
        WALK_IN = "walk_in", "Walk-in"

    class CheckinMethod(models.TextChoices):
        QR = "qr", "QR"
        MANUAL = "manual", "Manual"

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="registrations",
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="event_registrations",
    )
    status = models.CharField(
        choices=Status.choices,
        default=Status.REGISTERED,
        max_length=20,
    )
    needs_transport = models.BooleanField(default=False)
    note = models.CharField(blank=True, max_length=200)
    registered_at = models.DateTimeField(default=timezone.now)
    checked_in_at = models.DateTimeField(blank=True, null=True)
    checkin_method = models.CharField(
        blank=True,
        choices=CheckinMethod.choices,
        max_length=20,
        null=True,
    )

    class Meta:
        db_table = "event_registration"
        constraints = [
            models.UniqueConstraint(
                fields=("event", "person"),
                name="uniq_event_registration_person",
            )
        ]
        indexes = [models.Index(fields=("church", "event", "status"))]

    def __str__(self) -> str:
        return f"{self.person} — {self.event} ({self.status})"

    def clean(self) -> None:
        super().clean()
        if (
            self.event.church_id != self.church_id
            or self.person.church_id != self.church_id
        ):
            raise ValidationError("Event, person and registration must share a church.")
