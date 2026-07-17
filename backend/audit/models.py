from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class AppendOnlyAuditQuerySet(models.QuerySet["AuditEvent"]):
    def update(self, **kwargs: object) -> int:
        raise ValidationError("Audit events are append-only and cannot be changed.")

    def delete(self) -> tuple[int, dict[str, int]]:
        raise ValidationError(
            "Audit events cannot be deleted through application code."
        )

    def bulk_update(
        self,
        objs: list["AuditEvent"],
        fields: list[str],
        batch_size: int | None = None,
    ) -> int:
        raise ValidationError("Audit events are append-only and cannot be changed.")


class AuditEvent(models.Model):
    """Append-only record of access and changes worth security review."""

    class Action(models.TextChoices):
        LOGIN_SUCCEEDED = "auth.login_succeeded", "Login succeeded"
        LOGIN_FAILED = "auth.login_failed", "Login failed"
        CONFIDENTIAL_CARE_VIEWED = (
            "care.confidential_viewed",
            "Confidential care viewed",
        )
        PERSON_CREATED = "person.created", "Person created"
        PERSON_UPDATED = "person.updated", "Person updated"
        PERSON_DEACTIVATED = "person.deactivated", "Person deactivated"
        MEMBERSHIP_ROLE_CHANGED = (
            "membership.role_changed",
            "Membership role changed",
        )
        MEMBERSHIP_ACCESS_CHANGED = (
            "membership.access_changed",
            "Membership access changed",
        )
        CSV_EXPORTED = "data.csv_exported", "CSV exported"
        CONSENT_RECORDED = "consent.recorded", "Consent recorded"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="audit_events",
    )
    church = models.ForeignKey(
        "tenancy.Church",
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name="audit_events",
    )
    action = models.CharField(choices=Action.choices, max_length=40)
    target_type = models.CharField(blank=True, max_length=100)
    target_id = models.CharField(blank=True, max_length=100)
    request_id = models.UUIDField(db_index=True)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = AppendOnlyAuditQuerySet.as_manager()

    class Meta:
        db_table = "audit_event"
        ordering = ("-created_at", "-id")
        indexes = [
            models.Index(fields=("church", "action", "created_at")),
            models.Index(fields=("actor", "created_at")),
            models.Index(fields=("target_type", "target_id")),
        ]

    def __str__(self) -> str:
        return f"{self.action} at {self.created_at}"

    def save(self, *args: object, **kwargs: object) -> None:
        if self.pk is not None:
            raise ValidationError("Audit events are append-only and cannot be changed.")
        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        raise ValidationError(
            "Audit events cannot be deleted through application code."
        )
