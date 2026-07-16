from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from tenancy.models import ChurchScopedModel


class Household(ChurchScopedModel):
    name = models.CharField(max_length=200)

    class Meta:
        db_table = "household"
        indexes = [models.Index(fields=("church", "name"))]

    def __str__(self) -> str:
        return self.name


class Person(ChurchScopedModel):
    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        UNSPECIFIED = "unspecified", "Unspecified"

    class MembershipStatus(models.TextChoices):
        VISITOR = "visitor", "Visitor"
        NEWCOMER = "newcomer", "Newcomer"
        REGULAR = "regular", "Regular"
        MEMBER = "member", "Member"
        INACTIVE = "inactive", "Inactive"

    class DiscipleshipStage(models.TextChoices):
        PRE_EVANGELISM = "pre_evangelism", "Pre-evangelism"
        EVANGELISM = "evangelism", "Evangelism"
        CONVERSION = "conversion", "Conversion"
        MATURITY = "maturity", "Maturity"
        LEADERSHIP = "leadership", "Leadership"

    full_name = models.CharField(max_length=200)
    preferred_name = models.CharField(blank=True, max_length=100, null=True)
    gender = models.CharField(
        choices=Gender.choices,
        default=Gender.UNSPECIFIED,
        max_length=20,
    )
    date_of_birth = models.DateField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)  # noqa: DJ001
    phone = models.CharField(blank=True, max_length=30, null=True)
    has_whatsapp = models.BooleanField(default=True)
    photo_url = models.URLField(blank=True, max_length=500, null=True)
    home_country = models.CharField(blank=True, max_length=2, null=True)
    suburb = models.CharField(blank=True, max_length=100, null=True)
    occupation = models.CharField(blank=True, max_length=200, null=True)
    university = models.CharField(blank=True, max_length=200, null=True)
    course = models.CharField(blank=True, max_length=200, null=True)
    interests = models.JSONField(default=list)
    household = models.ForeignKey(
        Household,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="people",
    )
    membership_status = models.CharField(
        choices=MembershipStatus.choices,
        default=MembershipStatus.VISITOR,
        max_length=20,
    )
    discipleship_stage = models.CharField(
        blank=True,
        choices=DiscipleshipStage.choices,
        max_length=20,
        null=True,
    )
    faith_background = models.CharField(blank=True, max_length=100, null=True)
    invited_by = models.ForeignKey(
        "self",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="invitees",
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "person"
        constraints = [
            models.UniqueConstraint(
                condition=Q(email__isnull=False) & ~Q(email=""),
                fields=("church", "email"),
                name="uniq_person_email_per_church",
            )
        ]
        indexes = [
            models.Index(fields=("church", "full_name")),
            models.Index(fields=("church", "membership_status")),
        ]

    def __str__(self) -> str:
        return self.full_name

    def clean(self) -> None:
        super().clean()
        errors: dict[str, str] = {}
        if self.household_id and self.household.church_id != self.church_id:
            errors["household"] = "Household and person must belong to the same church."
        if self.invited_by_id and self.invited_by.church_id != self.church_id:
            errors["invited_by"] = "Inviter and person must belong to the same church."
        if errors:
            raise ValidationError(errors)


class Relationship(ChurchScopedModel):
    class Kind(models.TextChoices):
        FRIEND = "friend", "Friend"
        FAMILY = "family", "Family"
        SPOUSE = "spouse", "Spouse"
        GUARDIAN = "guardian", "Guardian"

    from_person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="relationships_from",
    )
    to_person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="relationships_to",
    )
    kind = models.CharField(choices=Kind.choices, max_length=20)

    class Meta:
        db_table = "relationship"
        constraints = [
            models.UniqueConstraint(
                fields=("from_person", "to_person", "kind"),
                name="uniq_relationship_pair_kind",
            ),
            models.CheckConstraint(
                condition=Q(from_person_id__lt=models.F("to_person_id")),
                name="relationship_canonical_order",
            ),
        ]
        indexes = [
            models.Index(fields=("church", "from_person")),
            models.Index(fields=("church", "to_person")),
        ]

    def __str__(self) -> str:
        return f"{self.from_person} — {self.to_person} ({self.kind})"

    def clean(self) -> None:
        super().clean()
        if (
            self.from_person.church_id != self.church_id
            or self.to_person.church_id != self.church_id
        ):
            raise ValidationError(
                "Both people and the relationship must share a church."
            )

    def save(self, *args: object, **kwargs: object) -> None:
        if self.from_person_id and self.to_person_id:
            if self.from_person_id > self.to_person_id:
                self.from_person_id, self.to_person_id = (
                    self.to_person_id,
                    self.from_person_id,
                )
        super().save(*args, **kwargs)
