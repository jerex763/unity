from collections.abc import Mapping
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from django.db.models import Model

from .context import get_audit_context
from .models import AuditEvent

if TYPE_CHECKING:
    from django.http import HttpRequest

    from accounts.models import User
    from tenancy.models import Church


SAFE_METADATA_KEYS = frozenset(
    {
        "format",
        "delete_reason",
        "new_active",
        "new_role",
        "previous_active",
        "previous_role",
        "reason",
        "record_count",
    }
)
SAFE_FAILURE_REASONS = frozenset(
    {"InvalidCredentials", "PermissionDenied", "ValidationError"}
)
SAFE_DELETE_REASONS = frozenset(
    {"created_in_error", "duplicate", "legal_request", "test_data"}
)


def _request_id(request: "HttpRequest | None") -> UUID:
    raw_request = getattr(request, "_request", request)
    value = getattr(raw_request, "audit_request_id", None)
    if isinstance(value, UUID):
        return value
    context = get_audit_context()
    return context.request_id if context else uuid4()


def _actor_id(actor: "User | None") -> int | None:
    if actor is not None:
        return actor.pk
    context = get_audit_context()
    return context.actor_id if context else None


def _safe_metadata(metadata: Mapping[str, object] | None) -> dict[str, object]:
    values = dict(metadata or {})
    unexpected = values.keys() - SAFE_METADATA_KEYS
    if unexpected:
        names = ", ".join(sorted(unexpected))
        raise ValueError(f"Audit metadata keys are not approved: {names}")
    if "reason" in values and values["reason"] not in SAFE_FAILURE_REASONS:
        raise ValueError("Audit failure reasons must use an approved code.")
    if "delete_reason" in values and values["delete_reason"] not in SAFE_DELETE_REASONS:
        raise ValueError("Audit deletion reasons must use an approved code.")
    return values


def record_audit_event(
    *,
    action: str,
    actor: "User | None" = None,
    church: "Church | None" = None,
    target: Model | None = None,
    target_type: str = "",
    target_id: str = "",
    request: "HttpRequest | None" = None,
    metadata: Mapping[str, object] | None = None,
) -> AuditEvent:
    """Persist a deliberately minimal event without copying changed field values."""
    if target is not None:
        target_type = target._meta.label_lower
        target_id = str(target.pk or "")

    return AuditEvent.objects.create(
        action=action,
        actor_id=_actor_id(actor),
        church_id=church.pk if church is not None else None,
        target_type=target_type,
        target_id=target_id,
        request_id=_request_id(request),
        metadata=_safe_metadata(metadata),
    )


def record_csv_export(
    *,
    actor: "User",
    church: "Church",
    target_type: str,
    record_count: int,
    request: "HttpRequest | None" = None,
) -> AuditEvent:
    return record_audit_event(
        action=AuditEvent.Action.CSV_EXPORTED,
        actor=actor,
        church=church,
        target_type=target_type,
        request=request,
        metadata={"format": "csv", "record_count": record_count},
    )
