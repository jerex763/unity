from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from people.models import Person
from tenancy.models import ChurchScopedModel


class Group(ChurchScopedModel):
    class Kind(models.TextChoices):
        SMALL_GROUP = "small_group", "Small group"
        MINISTRY = "ministry", "Ministry"
        ACTIVITY = "activity", "Activity"
        SERVICE_TEAM = "service_team", "Service team"

    class Health(models.TextChoices):
        HEALTHY = "healthy", "Healthy"
        NEEDS_ATTENTION = "needs_attention", "Needs attention"
        CRITICAL = "critical", "Critical"

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    kind = models.CharField(choices=Kind.choices, max_length=20)
    schedule_note = models.CharField(blank=True, max_length=200)
    location = models.CharField(blank=True, max_length=200)
    is_active = models.BooleanField(default=True)
    health = models.CharField(
        blank=True,
        choices=Health.choices,
        max_length=20,
        null=True,
    )

    class Meta:
        db_table = "group"
        indexes = [models.Index(fields=("church", "kind", "is_active"))]

    def __str__(self) -> str:
        return self.name


class GroupMembership(ChurchScopedModel):
    class Role(models.TextChoices):
        LEADER = "leader", "Leader"
        CO_LEADER = "co_leader", "Co-leader"
        MEMBER = "member", "Member"

    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="group_memberships",
    )
    role = models.CharField(choices=Role.choices, max_length=20)
    joined_at = models.DateField()
    left_at = models.DateField(blank=True, null=True)

    class Meta:
        db_table = "group_membership"
        constraints = [
            models.UniqueConstraint(
                condition=Q(left_at__isnull=True),
                fields=("group", "person"),
                name="uniq_active_group_membership",
            )
        ]
        indexes = [models.Index(fields=("church", "group", "left_at"))]

    def __str__(self) -> str:
        return f"{self.person} — {self.group} ({self.role})"

    def clean(self) -> None:
        super().clean()
        if (
            self.group.church_id != self.church_id
            or self.person.church_id != self.church_id
        ):
            raise ValidationError("Group, person and membership must share a church.")
        if self.left_at and self.left_at < self.joined_at:
            raise ValidationError({"left_at": "Leave date cannot precede join date."})
