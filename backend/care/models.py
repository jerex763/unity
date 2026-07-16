from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from people.models import Person
from tenancy.models import ChurchScopedModel


class FollowUp(ChurchScopedModel):
    class Source(models.TextChoices):
        EVENT_VISIT = "event_visit", "Event visit"
        FRIEND_INVITE = "friend_invite", "Friend invite"
        WALK_IN = "walk_in", "Walk-in"
        OTHER = "other", "Other"

    class Engagement(models.TextChoices):
        POSSIBLE = "possible", "Possible"
        PROBABLE = "probable", "Probable"
        LIKELY = "likely", "Likely"

    class Status(models.TextChoices):
        NEW = "new", "New"
        ASSIGNED = "assigned", "Assigned"
        IN_PROGRESS = "in_progress", "In progress"
        CONNECTED = "connected", "Connected"
        CLOSED = "closed", "Closed"

    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="follow_ups",
    )
    source = models.CharField(choices=Source.choices, max_length=20)
    engagement = models.CharField(
        choices=Engagement.choices,
        default=Engagement.POSSIBLE,
        max_length=20,
    )
    status = models.CharField(
        choices=Status.choices,
        default=Status.NEW,
        max_length=20,
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="follow_ups_assigned",
    )
    due_at = models.DateField(blank=True, null=True)
    closed_at = models.DateTimeField(blank=True, null=True)
    outcome = models.CharField(blank=True, max_length=200, null=True)

    class Meta:
        db_table = "follow_up"
        constraints = [
            models.UniqueConstraint(
                condition=~Q(status="closed"),
                fields=("person",),
                name="follow_up_one_open_per_person",
            )
        ]
        indexes = [models.Index(fields=("church", "assigned_to", "status"))]

    def __str__(self) -> str:
        return f"{self.person} — {self.status}"

    def clean(self) -> None:
        super().clean()
        if self.person.church_id != self.church_id:
            raise ValidationError(
                "Person and follow-up must belong to the same church."
            )


class CareCase(ChurchScopedModel):
    class Kind(models.TextChoices):
        PASTORAL = "pastoral", "Pastoral"
        PRAYER = "prayer", "Prayer"
        PRACTICAL = "practical", "Practical"

    class Urgency(models.TextChoices):
        LOW = "low", "Low"
        NORMAL = "normal", "Normal"
        HIGH = "high", "High"
        CRISIS = "crisis", "Crisis"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In progress"
        WAITING = "waiting", "Waiting"
        CLOSED = "closed", "Closed"

    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="care_cases",
    )
    kind = models.CharField(choices=Kind.choices, max_length=20)
    title = models.CharField(max_length=200)
    details = models.TextField()
    urgency = models.CharField(
        choices=Urgency.choices,
        default=Urgency.NORMAL,
        max_length=20,
    )
    status = models.CharField(
        choices=Status.choices,
        default=Status.OPEN,
        max_length=20,
    )
    is_confidential = models.BooleanField(default=False)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="care_cases_assigned",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="care_cases_created",
    )
    closed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "care_case"
        indexes = [models.Index(fields=("church", "status", "urgency"))]

    def __str__(self) -> str:
        return self.title

    def clean(self) -> None:
        super().clean()
        if self.person.church_id != self.church_id:
            raise ValidationError(
                "Person and care case must belong to the same church."
            )


class Interaction(ChurchScopedModel):
    class Kind(models.TextChoices):
        CALL = "call", "Call"
        MESSAGE = "message", "Message"
        VISIT = "visit", "Visit"
        MEETING = "meeting", "Meeting"
        OTHER = "other", "Other"

    class Visibility(models.TextChoices):
        STAFF = "staff", "Staff"
        LEADERS = "leaders", "Leaders"
        PASTORS_ONLY = "pastors_only", "Pastors only"

    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="interactions",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="interactions_authored",
    )
    kind = models.CharField(choices=Kind.choices, max_length=20)
    occurred_at = models.DateTimeField(default=timezone.now)
    summary = models.TextField()
    visibility = models.CharField(
        choices=Visibility.choices,
        default=Visibility.STAFF,
        max_length=20,
    )
    follow_up = models.ForeignKey(
        FollowUp,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="interactions",
    )
    care_case = models.ForeignKey(
        CareCase,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="interactions",
    )

    class Meta:
        db_table = "interaction"
        constraints = [
            models.CheckConstraint(
                condition=Q(follow_up__isnull=True) | Q(care_case__isnull=True),
                name="interaction_one_context",
            )
        ]
        indexes = [models.Index(fields=("church", "person", "occurred_at"))]

    def __str__(self) -> str:
        return f"{self.person} — {self.kind}"

    def clean(self) -> None:
        super().clean()
        related = [self.person, self.follow_up, self.care_case]
        if any(item and item.church_id != self.church_id for item in related):
            raise ValidationError("Interaction and linked records must share a church.")
