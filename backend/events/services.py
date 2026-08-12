import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from people.models import ConsentRecord, Person
from people.normalization import normalize_email, normalize_phone

from .models import (
    Event,
    EventRegistration,
    PublicRegistrationIdentityLock,
    PublicRegistrationLink,
    PublicRegistrationRateLimit,
)


class PublicRegistrationError(Exception):
    pass


class PublicRegistrationRateLimited(PublicRegistrationError):
    pass


@dataclass(frozen=True)
class PublicRegistrationOutcome:
    registration: EventRegistration | None
    cancellation_token: str

    @property
    def created(self) -> bool:
        return self.registration is not None


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _new_token() -> str:
    return secrets.token_urlsafe(32)


def registration_is_open(event: Event, *, now=None) -> bool:
    current_time = now or timezone.now()
    if not event.signup_opens or event.starts_at <= current_time:
        return False
    if event.signup_closes_at and event.signup_closes_at <= current_time:
        return False
    return True


@transaction.atomic
def rotate_public_registration_link(
    *, event: Event, created_by
) -> tuple[PublicRegistrationLink, str]:
    locked_event = Event.objects.select_for_update().get(pk=event.pk)
    if not registration_is_open(locked_event):
        raise ValidationError("Public registration is only available for open events.")
    raw_token = _new_token()
    link, _ = PublicRegistrationLink.objects.update_or_create(
        event=locked_event,
        defaults={
            "church": locked_event.church,
            "token_digest": token_digest(raw_token),
            "created_by": created_by,
            "revoked_at": None,
        },
    )
    return link, raw_token


@transaction.atomic
def revoke_public_registration_link(link: PublicRegistrationLink) -> None:
    locked = PublicRegistrationLink.objects.select_for_update().get(pk=link.pk)
    if locked.revoked_at is None:
        locked.revoked_at = timezone.now()
        locked.save(update_fields=("revoked_at", "updated_at"))


def public_event_for_token(token: str) -> Event | None:
    if len(token) > 200:
        return None
    link = (
        PublicRegistrationLink.objects.filter(
            token_digest=token_digest(token),
            revoked_at__isnull=True,
        )
        .select_related("event", "church")
        .first()
    )
    return link.event if link else None


def _matching_person(
    *, church, normalized_email: str | None, normalized_phone: str | None
) -> Person | None:
    people = Person.objects.for_church(church)
    email_person = (
        people.filter(normalized_email=normalized_email).first()
        if normalized_email
        else None
    )
    if email_person:
        phone_belongs_to_email_person = (
            not normalized_phone
            or people.filter(
                normalized_phone=normalized_phone,
                pk=email_person.pk,
            ).exists()
        )
        if (
            not phone_belongs_to_email_person
            and people.filter(normalized_phone=normalized_phone).exists()
        ):
            raise PublicRegistrationError("Unable to process registration.")
        return email_person
    phone_people = (
        list(people.filter(normalized_phone=normalized_phone).order_by("id")[:2])
        if normalized_phone
        else []
    )
    if len(phone_people) > 1:
        raise PublicRegistrationError("Unable to process registration.")
    return phone_people[0] if phone_people else None


def _identity_lock_digest(kind: str, value: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        f"public-registration:{kind}:{value}".encode(),
        hashlib.sha256,
    ).hexdigest()


def _acquire_identity_locks(
    *, church, normalized_email: str | None, normalized_phone: str | None
) -> None:
    digests = sorted(
        digest
        for digest in (
            (
                _identity_lock_digest("email", normalized_email)
                if normalized_email
                else None
            ),
            (
                _identity_lock_digest("phone", normalized_phone)
                if normalized_phone
                else None
            ),
        )
        if digest
    )
    for digest in digests:
        lock, _ = PublicRegistrationIdentityLock.objects.get_or_create(
            church=church,
            identity_digest=digest,
        )
        locked = PublicRegistrationIdentityLock.objects.select_for_update().get(
            pk=lock.pk
        )
        PublicRegistrationIdentityLock.objects.filter(pk=locked.pk).update(
            updated_at=timezone.now()
        )


def _find_or_create_public_person(
    *, church, full_name: str, email: str | None, phone: str | None
) -> tuple[Person, bool]:
    normalized_email = normalize_email(email)
    normalized_phone = normalize_phone(phone)
    _acquire_identity_locks(
        church=church,
        normalized_email=normalized_email,
        normalized_phone=normalized_phone,
    )
    person = _matching_person(
        church=church,
        normalized_email=normalized_email,
        normalized_phone=normalized_phone,
    )
    if person:
        return person, False

    candidate = Person(
        church=church,
        full_name=full_name,
        email=email or None,
        phone=phone or None,
        membership_status=Person.MembershipStatus.VISITOR,
    )
    try:
        # The savepoint keeps the surrounding transaction usable if a concurrent
        # request wins one of the normalized contact uniqueness constraints.
        with transaction.atomic():
            candidate.full_clean(exclude={"interests"})
            candidate.save()
        return candidate, True
    except (IntegrityError, ValidationError):
        person = _matching_person(
            church=church,
            normalized_email=normalized_email,
            normalized_phone=normalized_phone,
        )
        if person:
            return person, False
        raise PublicRegistrationError("Unable to process registration.") from None


@transaction.atomic
def register_public_visitor(
    *,
    event: Event,
    full_name: str,
    email: str | None,
    phone: str | None,
    needs_transport: bool,
    notice_version: str,
) -> PublicRegistrationOutcome:
    locked_event = Event.objects.select_for_update().get(pk=event.pk)
    if not registration_is_open(locked_event):
        raise PublicRegistrationError("Unable to process registration.")
    if notice_version != settings.PRIVACY_NOTICE_VERSION:
        raise PublicRegistrationError("Unable to process registration.")

    person, person_created = _find_or_create_public_person(
        church=locked_event.church,
        full_name=full_name,
        email=email,
        phone=phone,
    )
    existing_registration = (
        EventRegistration.objects.select_for_update()
        .filter(event=locked_event, person=person)
        .first()
    )
    if existing_registration is not None:
        return PublicRegistrationOutcome(None, _new_token())

    previous_consent = (
        ConsentRecord.objects.select_for_update()
        .filter(person=person)
        .order_by("-created_at", "-id")
        .first()
    )
    if person_created:
        ConsentRecord.objects.create(
            church=locked_event.church,
            person=person,
            status=ConsentRecord.Status.GRANTED,
            notice_version=settings.PRIVACY_NOTICE_VERSION,
            consented_at=timezone.now(),
            method=ConsentRecord.Method.SELF_SERVICE,
            recorded_by=None,
            supersedes=None,
        )
    elif not (
        previous_consent is not None
        and previous_consent.status == ConsentRecord.Status.GRANTED
        and previous_consent.method == ConsentRecord.Method.SELF_SERVICE
        and previous_consent.notice_version == settings.PRIVACY_NOTICE_VERSION
    ):
        # Knowing contact details is not identity verification. Existing people
        # without current self-service consent require staff follow-up.
        return PublicRegistrationOutcome(None, _new_token())
    try:
        registration = register_for_event(
            event=locked_event,
            person=person,
            needs_transport=needs_transport,
        )
    except ValidationError as error:
        raise PublicRegistrationError("Unable to process registration.") from error
    cancellation_token = _new_token()
    registration.cancellation_token_digest = token_digest(cancellation_token)
    registration.save(update_fields=("cancellation_token_digest", "updated_at"))
    return PublicRegistrationOutcome(registration, cancellation_token)


@transaction.atomic
def cancel_public_registration(token: str) -> EventRegistration | None:
    if len(token) > 200:
        return None
    registration = (
        EventRegistration.objects.select_for_update()
        .filter(cancellation_token_digest=token_digest(token))
        .first()
    )
    if registration is None:
        return None
    cancelled = cancel_registration(registration)
    cancelled.cancellation_token_digest = None
    cancelled.save(update_fields=("cancellation_token_digest", "updated_at"))
    return cancelled


def _rate_window(now: datetime) -> datetime:
    seconds = settings.PUBLIC_REGISTRATION_RATE_WINDOW_SECONDS
    timestamp = int(now.timestamp())
    return datetime.fromtimestamp(timestamp - (timestamp % seconds), tz=UTC)


def _client_digest(client_identifier: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        client_identifier.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _increment_rate_bucket(
    *, token_hash: str, client_hash: str, limit: int, now: datetime
) -> None:
    window = _rate_window(now)
    with transaction.atomic():
        updated = PublicRegistrationRateLimit.objects.filter(
            token_digest=token_hash,
            client_digest=client_hash,
            window_started_at=window,
            request_count__lt=limit,
        ).update(request_count=F("request_count") + 1)
        if updated:
            return
        existing = PublicRegistrationRateLimit.objects.filter(
            token_digest=token_hash,
            client_digest=client_hash,
            window_started_at=window,
        ).first()
        if existing is not None:
            raise PublicRegistrationRateLimited
        try:
            with transaction.atomic():
                PublicRegistrationRateLimit.objects.create(
                    token_digest=token_hash,
                    client_digest=client_hash,
                    window_started_at=window,
                    request_count=1,
                )
        except IntegrityError:
            updated = PublicRegistrationRateLimit.objects.filter(
                token_digest=token_hash,
                client_digest=client_hash,
                window_started_at=window,
                request_count__lt=limit,
            ).update(request_count=F("request_count") + 1)
            if not updated:
                raise PublicRegistrationRateLimited from None


def cleanup_expired_rate_limits(*, now: datetime | None = None) -> int:
    current = now or timezone.now()
    cutoff = current - timedelta(
        seconds=settings.PUBLIC_REGISTRATION_RATE_WINDOW_SECONDS * 2
    )
    deleted, _ = PublicRegistrationRateLimit.objects.filter(
        window_started_at__lt=cutoff
    ).delete()
    return deleted


def enforce_public_client_rate_limit(*, client_identifier: str) -> None:
    """Bound invalid-token traffic to one shared row per client and window."""
    client_hash = _client_digest(client_identifier)
    try:
        cleanup_expired_rate_limits()
        _increment_rate_bucket(
            token_hash="global-client",
            client_hash=client_hash,
            limit=settings.PUBLIC_REGISTRATION_RATE_LIMIT,
            now=timezone.now(),
        )
    except PublicRegistrationRateLimited:
        raise
    except DatabaseError as error:
        raise PublicRegistrationRateLimited from error


def enforce_valid_public_token_rate_limit(
    *, token: str, client_identifier: str
) -> None:
    """Add token buckets only after the caller's token was resolved as valid."""
    token_hash = token_digest(token)
    client_hash = _client_digest(client_identifier)
    try:
        _increment_rate_bucket(
            token_hash=token_hash,
            client_hash=client_hash,
            limit=settings.PUBLIC_REGISTRATION_RATE_LIMIT,
            now=timezone.now(),
        )
        _increment_rate_bucket(
            token_hash=token_hash,
            client_hash="token-total",
            limit=settings.PUBLIC_REGISTRATION_TOKEN_RATE_LIMIT,
            now=timezone.now(),
        )
    except PublicRegistrationRateLimited:
        raise
    except DatabaseError as error:
        raise PublicRegistrationRateLimited from error


def public_cancellation_token_is_valid(token: str) -> bool:
    if len(token) > 200:
        return False
    return EventRegistration.objects.filter(
        cancellation_token_digest=token_digest(token)
    ).exists()


@transaction.atomic
def register_for_event(
    *,
    event: Event,
    person: Person,
    needs_transport: bool = False,
    note: str = "",
) -> EventRegistration:
    locked_event = Event.objects.select_for_update().get(pk=event.pk)
    if person.church_id != locked_event.church_id:
        raise ValidationError("Event and person must belong to the same church.")
    now = timezone.now()
    if not locked_event.signup_opens or locked_event.starts_at <= now:
        raise ValidationError("Registration is closed for this event.")
    if locked_event.signup_closes_at and locked_event.signup_closes_at <= now:
        raise ValidationError("Registration is closed for this event.")

    existing = (
        EventRegistration.objects.select_for_update()
        .filter(event=locked_event, person=person)
        .first()
    )
    active_count = (
        EventRegistration.objects.filter(
            event=locked_event,
            status__in=(
                EventRegistration.Status.REGISTERED,
                EventRegistration.Status.WALK_IN,
            ),
        )
        .exclude(pk=getattr(existing, "pk", None))
        .count()
    )
    status = (
        EventRegistration.Status.WAITLISTED
        if locked_event.capacity is not None and active_count >= locked_event.capacity
        else EventRegistration.Status.REGISTERED
    )
    registration = existing or EventRegistration(
        church=locked_event.church,
        event=locked_event,
        person=person,
    )
    registration.status = status
    registration.needs_transport = needs_transport
    registration.note = note.strip()
    registration.registered_at = now
    registration.checked_in_at = None
    registration.checkin_method = None
    registration.full_clean()
    registration.save()
    return registration


@transaction.atomic
def cancel_registration(registration: EventRegistration) -> EventRegistration:
    locked = EventRegistration.objects.select_for_update().get(pk=registration.pk)
    if locked.status != EventRegistration.Status.CANCELLED:
        locked.status = EventRegistration.Status.CANCELLED
        locked.save(update_fields=("status", "updated_at"))
    return locked


@transaction.atomic
def set_manual_check_in(
    registration: EventRegistration,
    *,
    checked_in: bool,
) -> EventRegistration:
    locked = EventRegistration.objects.select_for_update().get(pk=registration.pk)
    if locked.status == EventRegistration.Status.CANCELLED and checked_in:
        raise ValidationError("A cancelled registration cannot be checked in.")
    if checked_in:
        if locked.checked_in_at is None:
            locked.checked_in_at = timezone.now()
            locked.checkin_method = EventRegistration.CheckinMethod.MANUAL
            locked.save(update_fields=("checked_in_at", "checkin_method", "updated_at"))
        from care.services import ensure_first_event_follow_up

        ensure_first_event_follow_up(locked)
    elif locked.checked_in_at is not None or locked.checkin_method is not None:
        locked.checked_in_at = None
        locked.checkin_method = None
        locked.save(update_fields=("checked_in_at", "checkin_method", "updated_at"))
    return locked
