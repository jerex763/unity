from collections.abc import Iterable

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from tenancy.models import Church


class User(AbstractUser):
    """Minimal authentication identity, deliberately separate from Person."""

    class Meta(AbstractUser.Meta):
        db_table = "app_user"

    def has_church_access(
        self,
        church: Church,
        *,
        roles: Iterable[str] | None = None,
    ) -> bool:
        """Return whether this active user has an active membership in a church."""
        if not self.is_active:
            return False

        memberships = self.church_memberships.active().for_church(church)
        if roles is not None:
            memberships = memberships.filter(role__in=roles)
        return memberships.exists()


class ChurchMembershipQuerySet(models.QuerySet["ChurchMembership"]):
    def active(self) -> "ChurchMembershipQuerySet":
        return self.filter(is_active=True)

    def for_user(self, user: User) -> "ChurchMembershipQuerySet":
        return self.filter(user=user)

    def for_church(self, church: Church) -> "ChurchMembershipQuerySet":
        return self.filter(church=church)


class ChurchMembership(models.Model):
    """A user's role and access state within one church."""

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        PASTOR = "pastor", "Pastor"
        LEADER = "leader", "Leader"
        MEMBER = "member", "Member"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="church_memberships",
    )
    church = models.ForeignKey(
        Church,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    person = models.OneToOneField(
        "people.Person",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="auth_membership",
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ChurchMembershipQuerySet.as_manager()

    class Meta:
        db_table = "church_membership"
        constraints = [
            models.UniqueConstraint(
                fields=("user", "church"),
                condition=Q(is_active=True),
                name="uniq_active_church_membership",
            )
        ]
        indexes = [models.Index(fields=("church", "role", "is_active"))]

    def __str__(self) -> str:
        return f"{self.user} — {self.church} ({self.role})"

    def clean(self) -> None:
        super().clean()
        if self.person_id and self.person.church_id != self.church_id:
            raise ValidationError(
                {
                    "person": (
                        "Person and church membership must belong to the same church."
                    )
                }
            )
