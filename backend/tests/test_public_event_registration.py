from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from django.core.management import call_command
from django.db import close_old_connections, connection
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.constants import ACTIVE_CHURCH_SESSION_KEY
from accounts.models import ChurchMembership, User
from audit.models import AuditEvent
from events.models import (
    Event,
    EventRegistration,
    PublicRegistrationIdentityLock,
    PublicRegistrationLink,
    PublicRegistrationRateLimit,
)
from events.services import register_public_visitor, token_digest
from people.models import ConsentRecord, Person
from tenancy.models import Church

pytestmark = pytest.mark.django_db


def organizer(church: Church, suffix: str = "organizer") -> tuple[User, APIClient]:
    user = User.objects.create_user(username=f"fictional.public.{suffix}")
    ChurchMembership.objects.create(
        user=user, church=church, role=ChurchMembership.Role.LEADER
    )
    client = APIClient()
    client.force_login(user)
    session = client.session
    session[ACTIVE_CHURCH_SESSION_KEY] = church.pk
    session.save()
    return user, client


def future_event(church: Church, user: User, capacity: int | None = None) -> Event:
    starts_at = timezone.now() + timedelta(days=3)
    return Event.objects.create(
        church=church,
        title="Fictional Public Picnic",
        description="Bring a fictional picnic lunch.",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=2),
        location="Fictional Park",
        capacity=capacity,
        signup_closes_at=starts_at - timedelta(hours=1),
        created_by=user,
    )


def create_link(client: APIClient, event: Event) -> tuple[str, str]:
    response = client.post(reverse("events:event-public-link", args=(event.pk,)))
    assert response.status_code == 201
    url = response.json()["url"]
    token = url.rstrip("/").rsplit("/", 1)[-1]
    return url, token


def registration_payload(**overrides: object) -> dict[str, object]:
    return {
        "full_name": "Fictional Visitor",
        "email": "visitor@example.test",
        "phone": "",
        "needs_transport": True,
        "consent": True,
        "notice_version": "2026-07-draft",
        **overrides,
    }


def test_link_is_hashed_rotatable_revocable_and_tenant_scoped() -> None:
    church = Church.objects.create(name="Fictional Public Church")
    other = Church.objects.create(name="Other Fictional Church")
    user, client = organizer(church)
    _, other_client = organizer(other, "other")
    event = future_event(church, user)

    first_url, first_token = create_link(client, event)
    link = PublicRegistrationLink.objects.get(event=event)
    assert first_token not in link.token_digest
    assert len(link.token_digest) == 64

    second_url, second_token = create_link(client, event)
    assert second_url != first_url
    assert (
        APIClient()
        .get(reverse("public-event-registration", args=(first_token,)))
        .status_code
        == 404
    )
    assert (
        other_client.delete(
            reverse("events:event-public-link", args=(event.pk,))
        ).status_code
        == 404
    )
    assert (
        client.delete(reverse("events:event-public-link", args=(event.pk,))).status_code
        == 204
    )
    assert (
        APIClient()
        .get(reverse("public-event-registration", args=(second_token,)))
        .status_code
        == 404
    )
    assert (
        AuditEvent.objects.filter(
            church=church, action=AuditEvent.Action.PUBLIC_EVENT_LINK_CREATED
        ).count()
        == 2
    )


def test_public_payload_is_minimal_and_registration_records_explicit_consent() -> None:
    church = Church.objects.create(name="Fictional Minimal Church")
    user, client = organizer(church)
    event = future_event(church, user)
    _, token = create_link(client, event)
    public_client = APIClient()

    detail = public_client.get(reverse("public-event-registration", args=(token,)))
    response = public_client.post(
        reverse("public-event-registration", args=(token,)),
        registration_payload(),
        format="json",
    )

    assert detail.status_code == 200
    assert set(detail.json()) == {
        "title",
        "description",
        "starts_at",
        "ends_at",
        "location",
        "registration_open",
        "privacy_notice",
    }
    assert response.status_code == 201
    assert set(response.json()) == {"accepted", "event_title", "cancellation_url"}
    assert response.json()["accepted"] is True
    person = Person.objects.get(church=church)
    assert person.membership_status == Person.MembershipStatus.VISITOR
    consent = ConsentRecord.objects.get(person=person)
    assert consent.status == ConsentRecord.Status.GRANTED
    assert consent.method == ConsentRecord.Method.SELF_SERVICE
    assert consent.recorded_by is None
    assert consent.notice_version == "2026-07-draft"
    assert EventRegistration.objects.get(person=person).needs_transport is True


@pytest.mark.parametrize(
    ("change", "field"),
    [
        ({"consent": False}, "consent"),
        ({"notice_version": "stale-version"}, "detail"),
        ({"email": "", "phone": ""}, "contact"),
    ],
)
def test_public_registration_requires_contact_and_current_explicit_consent(
    change: dict[str, object], field: str
) -> None:
    church = Church.objects.create(name="Fictional Consent Church")
    user, client = organizer(church)
    event = future_event(church, user)
    _, token = create_link(client, event)

    response = APIClient().post(
        reverse("public-event-registration", args=(token,)),
        registration_payload(**change),
        format="json",
    )

    assert response.status_code == 400
    assert field in response.json()
    assert not EventRegistration.objects.exists()


def test_contact_matching_is_normalized_same_church_only_and_duplicate_safe() -> None:
    church = Church.objects.create(name="Fictional Match Church")
    other = Church.objects.create(name="Other Fictional Match Church")
    user, client = organizer(church)
    existing = Person.objects.create(
        church=church,
        full_name="Existing Fictional Person",
        email="MATCH@EXAMPLE.TEST",
        phone="+61 400 000 001",
    )
    outsider = Person.objects.create(
        church=other,
        full_name="Other Tenant Person",
        email="match@example.test",
        phone="+61 400 000 001",
    )
    event = future_event(church, user)
    _, token = create_link(client, event)
    ConsentRecord.objects.create(
        church=church,
        person=existing,
        status=ConsentRecord.Status.GRANTED,
        notice_version="2026-07-draft",
        consented_at=timezone.now(),
        method=ConsentRecord.Method.SELF_SERVICE,
        recorded_by=None,
    )

    first = APIClient().post(
        reverse("public-event-registration", args=(token,)),
        registration_payload(email=" match@example.test ", phone=""),
        format="json",
    )
    second = APIClient().post(
        reverse("public-event-registration", args=(token,)),
        registration_payload(email="", phone="(+61) 400-000-001"),
        format="json",
    )

    assert first.status_code == second.status_code == 201
    assert Person.objects.filter(church=church).count() == 1
    assert EventRegistration.objects.get(event=event).person == existing
    assert Person.objects.filter(church=other).get() == outsider


def test_capacity_waitlist_duplicate_and_anonymous_cancellation_reuse_rules() -> None:
    church = Church.objects.create(name="Fictional Capacity Church")
    user, client = organizer(church)
    event = future_event(church, user, capacity=1)
    _, token = create_link(client, event)
    url = reverse("public-event-registration", args=(token,))

    first = APIClient().post(url, registration_payload(), format="json")
    duplicate = APIClient().post(url, registration_payload(), format="json")
    APIClient().post(
        url,
        registration_payload(
            full_name="Second Fictional Visitor", email="second@example.test"
        ),
        format="json",
    )

    assert first.json()["accepted"] == duplicate.json()["accepted"] is True
    assert EventRegistration.objects.filter(event=event).count() == 2
    assert (
        EventRegistration.objects.get(
            event=event, person__email="second@example.test"
        ).status
        == EventRegistration.Status.WAITLISTED
    )
    cancellation_token = first.json()["cancellation_url"].rsplit("/", 1)[-1]
    cancelled = APIClient().post(
        reverse("public-event-cancellation", args=(cancellation_token,))
    )
    replay = APIClient().post(
        reverse("public-event-cancellation", args=(cancellation_token,))
    )
    assert cancelled.status_code == 200
    assert replay.status_code == 200
    assert not any(
        key in duplicate.json()
        for key in ("person", "email", "phone", "registrations", "church")
    )


@override_settings(
    PUBLIC_REGISTRATION_RATE_LIMIT=2, PUBLIC_REGISTRATION_TOKEN_RATE_LIMIT=20
)
def test_public_endpoints_are_rate_limited_with_generic_errors() -> None:
    church = Church.objects.create(name="Fictional Rate Church")
    user, client = organizer(church)
    event = future_event(church, user)
    _, token = create_link(client, event)
    url = reverse("public-event-registration", args=(token,))
    public_client = APIClient(REMOTE_ADDR="203.0.113.10")

    assert public_client.get(url).status_code == 200
    assert public_client.get(url).status_code == 200
    limited = public_client.get(url)

    assert limited.status_code == 429
    assert "later" in limited.json()["detail"].lower()


def test_existing_active_registration_cannot_be_taken_over() -> None:
    church = Church.objects.create(name="Fictional Takeover Church")
    user, client = organizer(church)
    event = future_event(church, user)
    person = Person.objects.create(
        church=church,
        full_name="Existing Fictional Visitor",
        email="existing@example.test",
    )
    declined = ConsentRecord.objects.create(
        church=church,
        person=person,
        status=ConsentRecord.Status.DECLINED,
        notice_version="2026-07-draft",
        consented_at=timezone.now(),
        method=ConsentRecord.Method.SELF_SERVICE,
        recorded_by=None,
    )
    original_token = "fictional-original-cancellation-secret"
    registration = EventRegistration.objects.create(
        church=church,
        event=event,
        person=person,
        status=EventRegistration.Status.REGISTERED,
        needs_transport=False,
        note="Private fictional staff note",
        cancellation_token_digest=token_digest(original_token),
    )
    original_registered_at = registration.registered_at
    _, public_token = create_link(client, event)

    attack = APIClient().post(
        reverse("public-event-registration", args=(public_token,)),
        registration_payload(
            full_name="Attacker Supplied Name",
            email="EXISTING@example.test",
            needs_transport=True,
        ),
        format="json",
    )
    decoy_token = attack.json()["cancellation_url"].rsplit("/", 1)[-1]
    decoy_cancel = APIClient().post(
        reverse("public-event-cancellation", args=(decoy_token,))
    )

    registration.refresh_from_db()
    assert attack.status_code == 201
    assert attack.json()["accepted"] is True
    assert decoy_cancel.status_code == 200
    assert registration.status == EventRegistration.Status.REGISTERED
    assert registration.needs_transport is False
    assert registration.note == "Private fictional staff note"
    assert registration.registered_at == original_registered_at
    assert registration.cancellation_token_digest == token_digest(original_token)
    assert list(ConsentRecord.objects.filter(person=person)) == [declined]

    original_cancel = APIClient().post(
        reverse("public-event-cancellation", args=(original_token,))
    )
    registration.refresh_from_db()
    assert original_cancel.status_code == 200
    assert registration.status == EventRegistration.Status.CANCELLED


def test_existing_cancelled_registration_and_consent_are_unchanged() -> None:
    church = Church.objects.create(name="Fictional Cancelled Takeover Church")
    user, client = organizer(church)
    event = future_event(church, user)
    person = Person.objects.create(
        church=church,
        full_name="Cancelled Fictional Visitor",
        phone="+61 400 000 077",
    )
    declined = ConsentRecord.objects.create(
        church=church,
        person=person,
        status=ConsentRecord.Status.DECLINED,
        notice_version="2026-07-draft",
        consented_at=timezone.now(),
        method=ConsentRecord.Method.SELF_SERVICE,
        recorded_by=None,
    )
    registration = EventRegistration.objects.create(
        church=church,
        event=event,
        person=person,
        status=EventRegistration.Status.CANCELLED,
        needs_transport=False,
        cancellation_token_digest=token_digest("preserved-cancelled-secret"),
    )
    _, public_token = create_link(client, event)

    response = APIClient().post(
        reverse("public-event-registration", args=(public_token,)),
        registration_payload(email="", phone="(+61) 400-000-077"),
        format="json",
    )

    registration.refresh_from_db()
    assert response.status_code == 201
    assert registration.status == EventRegistration.Status.CANCELLED
    assert registration.needs_transport is False
    assert registration.cancellation_token_digest == token_digest(
        "preserved-cancelled-secret"
    )
    assert list(ConsentRecord.objects.filter(person=person)) == [declined]


def test_existing_person_requires_current_self_service_consent() -> None:
    church = Church.objects.create(name="Fictional Existing Consent Church")
    user, client = organizer(church)
    event = future_event(church, user)
    person = Person.objects.create(
        church=church,
        full_name="Existing Fictional Person",
        email="known@example.test",
    )
    declined = ConsentRecord.objects.create(
        church=church,
        person=person,
        status=ConsentRecord.Status.DECLINED,
        notice_version="2026-07-draft",
        consented_at=timezone.now(),
        method=ConsentRecord.Method.SELF_SERVICE,
        recorded_by=None,
    )
    _, public_token = create_link(client, event)

    response = APIClient().post(
        reverse("public-event-registration", args=(public_token,)),
        registration_payload(email="known@example.test"),
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["accepted"] is True
    assert not EventRegistration.objects.filter(event=event, person=person).exists()
    assert list(ConsentRecord.objects.filter(person=person)) == [declined]
    assert Person.objects.filter(church=church).count() == 1


def test_existing_current_self_service_consent_allows_first_registration() -> None:
    church = Church.objects.create(name="Fictional Existing Granted Church")
    user, client = organizer(church)
    event = future_event(church, user)
    person = Person.objects.create(
        church=church,
        full_name="Granted Fictional Person",
        email="granted@example.test",
    )
    granted = ConsentRecord.objects.create(
        church=church,
        person=person,
        status=ConsentRecord.Status.GRANTED,
        notice_version="2026-07-draft",
        consented_at=timezone.now(),
        method=ConsentRecord.Method.SELF_SERVICE,
        recorded_by=None,
    )
    _, public_token = create_link(client, event)

    response = APIClient().post(
        reverse("public-event-registration", args=(public_token,)),
        registration_payload(email="granted@example.test"),
        format="json",
    )

    assert response.status_code == 201
    assert EventRegistration.objects.get(event=event, person=person)
    assert list(ConsentRecord.objects.filter(person=person)) == [granted]


def test_unique_email_wins_when_its_person_shares_the_supplied_phone() -> None:
    church = Church.objects.create(name="Fictional Shared Phone Church")
    user, client = organizer(church)
    Person.objects.create(
        church=church,
        full_name="First Shared Phone Fictional Person",
        phone="+61 400 000 066",
    )
    Person.objects.create(
        church=church,
        full_name="Second Shared Phone Fictional Person",
        phone="(+61) 400-000-066",
    )
    email_person = Person.objects.create(
        church=church,
        full_name="Third Email Fictional Person",
        email="unique@example.test",
        phone="0061 400 000 066",
    )
    ConsentRecord.objects.create(
        church=church,
        person=email_person,
        status=ConsentRecord.Status.GRANTED,
        notice_version="2026-07-draft",
        consented_at=timezone.now(),
        method=ConsentRecord.Method.SELF_SERVICE,
        recorded_by=None,
    )
    event = future_event(church, user)
    _, public_token = create_link(client, event)

    by_email = APIClient().post(
        reverse("public-event-registration", args=(public_token,)),
        registration_payload(email="unique@example.test", phone="+61 400 000 066"),
        format="json",
    )

    assert by_email.status_code == 201
    assert EventRegistration.objects.get(event=event).person == email_person


def test_phone_only_shared_match_is_ambiguous_and_creates_nothing() -> None:
    church = Church.objects.create(name="Fictional Ambiguous Phone Church")
    user, client = organizer(church)
    for suffix in ("First", "Second", "Third"):
        Person.objects.create(
            church=church,
            full_name=f"{suffix} Ambiguous Fictional Person",
            phone="+61 400 000 055",
        )
    event = future_event(church, user)
    _, public_token = create_link(client, event)

    response = APIClient().post(
        reverse("public-event-registration", args=(public_token,)),
        registration_payload(email="", phone="(+61) 400-000-055"),
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unable to process registration."
    assert not EventRegistration.objects.filter(event=event).exists()
    assert Person.objects.filter(church=church).count() == 3


def test_email_and_phone_pointing_to_different_people_is_rejected() -> None:
    church = Church.objects.create(name="Fictional Contact Conflict Church")
    user, client = organizer(church)
    email_person = Person.objects.create(
        church=church,
        full_name="Email Owner Fictional Person",
        email="owner@example.test",
    )
    phone_person = Person.objects.create(
        church=church,
        full_name="Phone Owner Fictional Person",
        phone="+61 400 000 044",
    )
    event = future_event(church, user)
    _, public_token = create_link(client, event)

    response = APIClient().post(
        reverse("public-event-registration", args=(public_token,)),
        registration_payload(email="owner@example.test", phone="(+61) 400-000-044"),
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unable to process registration."
    assert not EventRegistration.objects.filter(event=event).exists()
    assert Person.objects.filter(pk__in=(email_person.pk, phone_person.pk)).count() == 2


@override_settings(
    PUBLIC_REGISTRATION_RATE_LIMIT=50,
    PUBLIC_REGISTRATION_TOKEN_RATE_LIMIT=100,
    PUBLIC_REGISTRATION_TRUSTED_PROXY_HOPS=0,
)
def test_invalid_token_flood_and_spoofed_xff_keep_rate_storage_bounded() -> None:
    public_client = APIClient(REMOTE_ADDR="203.0.113.44")
    for index in range(20):
        response = public_client.get(
            reverse("public-event-registration", args=(f"invalid-{index}",)),
            HTTP_X_FORWARDED_FOR=f"198.51.100.{index}",
        )
        assert response.status_code == 404

    rows = list(PublicRegistrationRateLimit.objects.all())
    assert len(rows) == 1
    assert rows[0].token_digest == "global-client"


@override_settings(
    PUBLIC_REGISTRATION_RATE_LIMIT=2,
    PUBLIC_REGISTRATION_TOKEN_RATE_LIMIT=20,
    PUBLIC_REGISTRATION_TRUSTED_PROXY_HOPS=0,
)
def test_spoofed_xff_does_not_bypass_default_remote_address_limit() -> None:
    church = Church.objects.create(name="Fictional XFF Church")
    user, client = organizer(church)
    event = future_event(church, user)
    _, token = create_link(client, event)
    url = reverse("public-event-registration", args=(token,))
    public_client = APIClient(REMOTE_ADDR="203.0.113.55")

    assert (
        public_client.get(url, HTTP_X_FORWARDED_FOR="198.51.100.1").status_code == 200
    )
    assert (
        public_client.get(url, HTTP_X_FORWARDED_FOR="198.51.100.2").status_code == 200
    )
    assert (
        public_client.get(url, HTTP_X_FORWARDED_FOR="198.51.100.3").status_code == 429
    )


def test_security_state_housekeeping_removes_only_expired_rows() -> None:
    church = Church.objects.create(name="Fictional Housekeeping Church")
    old = timezone.now() - timedelta(days=40)
    current = timezone.now()
    PublicRegistrationRateLimit.objects.create(
        token_digest="old",
        client_digest="old",
        window_started_at=old,
    )
    current_rate = PublicRegistrationRateLimit.objects.create(
        token_digest="current",
        client_digest="current",
        window_started_at=current,
    )
    old_lock = PublicRegistrationIdentityLock.objects.create(
        church=church, identity_digest="old-lock"
    )
    current_lock = PublicRegistrationIdentityLock.objects.create(
        church=church, identity_digest="current-lock"
    )
    PublicRegistrationIdentityLock.objects.filter(pk=old_lock.pk).update(updated_at=old)

    call_command("cleanup_public_registration_security_state", identity_days=30)

    assert PublicRegistrationRateLimit.objects.filter(pk=current_rate.pk).exists()
    assert not PublicRegistrationRateLimit.objects.filter(token_digest="old").exists()
    assert PublicRegistrationIdentityLock.objects.filter(pk=current_lock.pk).exists()
    assert not PublicRegistrationIdentityLock.objects.filter(pk=old_lock.pk).exists()


@pytest.mark.skipif(
    connection.vendor != "postgresql",
    reason="SQLite does not reproduce PostgreSQL identity-lock concurrency.",
)
@pytest.mark.django_db(transaction=True)
def test_concurrent_public_submissions_share_one_same_church_person(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    church = Church.objects.create(name="Fictional Concurrent Public Church")
    user, _ = organizer(church)
    events = [future_event(church, user), future_event(church, user)]
    barrier = Barrier(2)

    from events import services

    original_acquire = services._acquire_identity_locks

    def synchronized_acquire(**kwargs):
        barrier.wait(timeout=10)
        return original_acquire(**kwargs)

    monkeypatch.setattr(services, "_acquire_identity_locks", synchronized_acquire)

    def submit(event_id: int) -> int:
        close_old_connections()
        try:
            outcome = register_public_visitor(
                event=Event.objects.get(pk=event_id),
                full_name="Fictional Concurrent Visitor",
                email=None,
                phone="+61 400 000 088",
                needs_transport=False,
                notice_version="2026-07-draft",
            )
            assert outcome.registration is not None
            return outcome.registration.person_id
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        person_ids = list(executor.map(submit, [event.pk for event in events]))

    assert person_ids[0] == person_ids[1]
    assert Person.objects.filter(church=church).count() == 1
    assert EventRegistration.objects.filter(person_id=person_ids[0]).count() == 2
