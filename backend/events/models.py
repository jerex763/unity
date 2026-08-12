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
    cancellation_token_digest = models.CharField(
        blank=True,
        max_length=64,
        null=True,
        unique=True,
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


class PublicRegistrationLink(ChurchScopedModel):
    event = models.OneToOneField(
        Event,
        on_delete=models.CASCADE,
        related_name="public_registration_link",
    )
    token_digest = models.CharField(max_length=64, unique=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="public_registration_links_created",
    )
    revoked_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "event_public_registration_link"
        indexes = [models.Index(fields=("church", "event", "revoked_at"))]

    def clean(self) -> None:
        super().clean()
        if self.event_id and self.event.church_id != self.church_id:
            raise ValidationError("Event and public link must share a church.")


class PublicRegistrationRateLimit(models.Model):
    """Cross-process fixed-window abuse counter containing no raw client data."""

    token_digest = models.CharField(max_length=64)
    client_digest = models.CharField(max_length=64)
    window_started_at = models.DateTimeField()
    request_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "event_public_registration_rate_limit"
        constraints = [
            models.UniqueConstraint(
                fields=("token_digest", "client_digest", "window_started_at"),
                name="uniq_public_registration_rate_window",
            )
        ]
        indexes = [models.Index(fields=("window_started_at",))]

    def __str__(self) -> str:
        return f"Public registration rate window {self.window_started_at}"


class PublicRegistrationIdentityLock(ChurchScopedModel):
    """Serializes public matching without retaining raw contact details."""

    identity_digest = models.CharField(max_length=64)

    class Meta:
        db_table = "event_public_registration_identity_lock"
        constraints = [
            models.UniqueConstraint(
                fields=("church", "identity_digest"),
                name="uniq_public_registration_identity_lock",
            )
        ]

    def __str__(self) -> str:
        return f"Public registration identity lock {self.pk}"
