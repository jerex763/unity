from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from tenancy.models import ChurchScopedModel, ChurchScopedQuerySet

from .normalization import normalize_email, normalize_phone, normalize_wechat_id


class Household(ChurchScopedModel):
    name = models.CharField(max_length=200)

    class Meta:
        db_table = "household"
        indexes = [models.Index(fields=("church", "name"))]

    def __str__(self) -> str:
        return self.name


class PersonQuerySet(ChurchScopedQuerySet):
    def delete(self) -> tuple[int, dict[str, int]]:
        raise ValidationError(
            "Routine person deletion is disabled; use the authorized lifecycle service."
        )


class Person(ChurchScopedModel):
    class PreferredContact(models.TextChoices):
        PHONE = "phone", "Phone"
        WHATSAPP = "whatsapp", "WhatsApp"
        WECHAT = "wechat", "WeChat"
        EMAIL = "email", "Email"

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

    class HardDeleteReason(models.TextChoices):
        CREATED_IN_ERROR = "created_in_error", "Created in error"
        DUPLICATE = "duplicate", "Confirmed duplicate"
        LEGAL_REQUEST = "legal_request", "Approved legal/privacy request"
        TEST_DATA = "test_data", "Fictional test data cleanup"

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
    normalized_email = models.CharField(blank=True, max_length=254, null=True)
    normalized_phone = models.CharField(blank=True, max_length=30, null=True)
    wechat_id = models.CharField(blank=True, max_length=100, null=True)
    normalized_wechat_id = models.CharField(blank=True, max_length=100, null=True)
    has_whatsapp = models.BooleanField(default=False)
    preferred_contact = models.CharField(
        blank=True,
        choices=PreferredContact.choices,
        max_length=20,
        null=True,
    )
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
    deactivated_at = models.DateTimeField(blank=True, null=True)
    anonymized_at = models.DateTimeField(blank=True, null=True)

    objects = PersonQuerySet.as_manager()

    class Meta:
        db_table = "person"
        constraints = [
            models.UniqueConstraint(
                condition=Q(email__isnull=False) & ~Q(email=""),
                fields=("church", "email"),
                name="uniq_person_email_per_church",
            ),
            models.UniqueConstraint(
                condition=Q(normalized_email__isnull=False),
                fields=("church", "normalized_email"),
                name="uniq_person_normalized_email_per_church",
            ),
        ]
        indexes = [
            models.Index(fields=("church", "full_name")),
            models.Index(fields=("church", "membership_status")),
            models.Index(fields=("church", "normalized_phone")),
            models.Index(fields=("church", "normalized_wechat_id")),
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
        if self.has_whatsapp and not self.phone:
            errors["has_whatsapp"] = "WhatsApp requires a phone number."
        contact_available = {
            self.PreferredContact.PHONE: bool(self.phone),
            self.PreferredContact.WHATSAPP: bool(self.phone and self.has_whatsapp),
            self.PreferredContact.WECHAT: bool(self.wechat_id),
            self.PreferredContact.EMAIL: bool(self.email),
        }
        if self.preferred_contact and not contact_available[self.preferred_contact]:
            errors["preferred_contact"] = (
                "Preferred contact must identify an available contact method."
            )
        if errors:
            raise ValidationError(errors)

    def save(self, *args: object, **kwargs: object) -> None:
        self.normalized_email = normalize_email(self.email)
        self.normalized_phone = normalize_phone(self.phone)
        self.normalized_wechat_id = normalize_wechat_id(self.wechat_id)
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            fields = set(update_fields)
            if "email" in fields:
                fields.add("normalized_email")
            if "phone" in fields:
                fields.add("normalized_phone")
            if "wechat_id" in fields:
                fields.add("normalized_wechat_id")
            kwargs["update_fields"] = fields
        super().save(*args, **kwargs)

    def delete(
        self,
        using: str | None = None,
        keep_parents: bool = False,
        *,
        hard_delete_reason: str | None = None,
    ) -> tuple[int, dict[str, int]]:
        if hard_delete_reason not in self.HardDeleteReason.values:
            raise ValidationError("Hard deletion requires an approved explicit reason.")
        return super().delete(using=using, keep_parents=keep_parents)


class AppendOnlyConsentQuerySet(ChurchScopedQuerySet):
    def update(self, **kwargs: object) -> int:
        raise ValidationError(
            "Consent records are append-only; record a correction instead."
        )

    def delete(self) -> tuple[int, dict[str, int]]:
        raise ValidationError(
            "Consent records cannot be deleted through application code."
        )

    def bulk_update(
        self,
        objs: list["ConsentRecord"],
        fields: list[str],
        batch_size: int | None = None,
    ) -> int:
        raise ValidationError(
            "Consent records are append-only; record a correction instead."
        )


class ConsentRecord(ChurchScopedModel):
    """One immutable consent decision; later records supersede earlier ones."""

    class Status(models.TextChoices):
        GRANTED = "granted", "Granted"
        DECLINED = "declined", "Declined"

    class Method(models.TextChoices):
        SELF_SERVICE = "self_service", "Self-service"
        PAPER_FORM = "paper_form", "Paper form"
        STAFF_RECORDED = "staff_recorded", "Staff-recorded"

    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="consent_records",
    )
    status = models.CharField(choices=Status.choices, max_length=20)
    notice_version = models.CharField(max_length=50)
    consented_at = models.DateTimeField()
    method = models.CharField(choices=Method.choices, max_length=20)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name="consent_records_recorded",
    )
    supersedes = models.ForeignKey(
        "self",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="corrections",
    )

    objects = AppendOnlyConsentQuerySet.as_manager()

    class Meta:
        db_table = "person_consent_record"
        ordering = ("-created_at", "-id")
        indexes = [
            models.Index(fields=("church", "person", "created_at")),
            models.Index(fields=("church", "status", "created_at")),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(method="self_service", recorded_by__isnull=True)
                    | (~Q(method="self_service") & Q(recorded_by__isnull=False))
                ),
                name="consent_recorder_matches_method",
            )
        ]

    def __str__(self) -> str:
        return f"{self.person} — {self.status} ({self.notice_version})"

    def clean(self) -> None:
        super().clean()
        errors: dict[str, str] = {}
        if self.person_id and self.person.church_id != self.church_id:
            errors["person"] = "Person and consent record must share a church."
        if self.supersedes_id and (
            self.supersedes.person_id != self.person_id
            or self.supersedes.church_id != self.church_id
        ):
            errors["supersedes"] = (
                "A correction must supersede a consent record for the same person."
            )
        if self.method == self.Method.SELF_SERVICE and self.recorded_by_id is not None:
            errors["recorded_by"] = (
                "Self-service consent must not name a staff recorder."
            )
        if self.method != self.Method.SELF_SERVICE and self.recorded_by_id is None:
            errors["recorded_by"] = "Staff and paper consent require a recorder."
        if errors:
            raise ValidationError(errors)

    def save(self, *args: object, **kwargs: object) -> None:
        if self.pk is not None:
            raise ValidationError(
                "Consent records are append-only; record a correction instead."
            )
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        raise ValidationError(
            "Consent records cannot be deleted through application code."
        )


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
