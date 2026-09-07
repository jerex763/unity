import json
from concurrent.futures import ThreadPoolExecutor
from threading import Event as ThreadEvent

import pytest
from cryptography.fernet import Fernet
from django.db import close_old_connections, connection, transaction
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import ChurchMembership
from audit.models import AuditEvent
from events.link_encryption import LinkRecoveryError
from events.models import Event, PublicRegistrationLink
from events.services import (
    public_event_for_token,
    recover_public_registration_link,
    revoke_public_registration_link,
    rotate_public_registration_link,
)
from tenancy.models import Church
from tests.test_public_event_registration import create_link, future_event, organizer

pytestmark = pytest.mark.django_db
NEW_KEY = "MTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTE="


@pytest.fixture
def setup_link():
    church = Church.objects.create(name="Fictional Recovery Church")
    user, client = organizer(church)
    event = future_event(church, user)
    url, token = create_link(client, event)
    return (
        church,
        user,
        client,
        event,
        url,
        token,
        reverse("events:event-public-link", args=(event.pk,)),
    )


@pytest.mark.parametrize("role", ["admin", "pastor", "leader"])
def test_new_session_same_url_no_list_or_audit_secrets(setup_link, role):
    church, user, _, event, url, token, endpoint = setup_link
    ChurchMembership.objects.filter(user=user).update(role=role)
    client = APIClient()
    client.force_login(user)
    session = client.session
    session["active_church_id"] = church.pk
    session.save()
    response = client.get(endpoint)
    assert response.status_code == 200
    assert response.json() == {"url": url}
    assert response["Cache-Control"] == "no-store"
    link = PublicRegistrationLink.objects.get(event=event)
    assert token not in link.encrypted_token
    content = client.get("/api/events/").content.decode()
    assert token not in content
    assert link.encrypted_token not in content
    audit = AuditEvent.objects.get(action=AuditEvent.Action.PUBLIC_EVENT_LINK_RECOVERED)
    assert audit.actor == user
    assert audit.target_type == "events.event"
    assert audit.target_id == str(event.pk)
    assert audit.metadata == {}
    assert token not in str(list(AuditEvent.objects.values()))


@pytest.mark.parametrize("method", ["get", "post", "delete", "head", "options"])
def test_member_denied(setup_link, method):
    _, user, client, _, _, _, endpoint = setup_link
    ChurchMembership.objects.filter(user=user).update(role="member")
    response = getattr(client, method)(endpoint)
    assert response.status_code == 403
    assert response["Cache-Control"] == "no-store"


def test_anonymous_inactive_other_tenant(setup_link):
    _, user, client, _, _, _, endpoint = setup_link
    assert APIClient().get(endpoint).status_code == 403
    _, other_client = organizer(Church.objects.create(name="Fictional Other"), "other")
    for method in ("get", "post", "delete"):
        response = getattr(other_client, method)(endpoint)
        assert response.status_code == 404
        assert response["Cache-Control"] == "no-store"
    ChurchMembership.objects.filter(user=user).update(is_active=False)
    assert client.get(endpoint).status_code == 403


@pytest.mark.parametrize("keys", [[], ["malformed"], [NEW_KEY], "not-list"])
def test_bad_key_recovery_fails_public_validation_survives(setup_link, keys):
    _, _, client, _, _, token, endpoint = setup_link
    with override_settings(PUBLIC_LINK_ENCRYPTION_KEYS=keys):
        response = client.get(endpoint)
        assert response.status_code == 503
        assert response.json()["code"] == "recovery_unavailable"
        assert response["Cache-Control"] == "no-store"
        assert public_event_for_token(token) is not None


@pytest.mark.parametrize("keys", [[], ["malformed"], [NEW_KEY, "malformed"]])
def test_creation_failure_preserves_link(setup_link, keys):
    _, _, client, event, _, token, endpoint = setup_link
    with override_settings(PUBLIC_LINK_ENCRYPTION_KEYS=keys):
        response = client.post(endpoint)
    assert response.status_code == 503
    assert response["Cache-Control"] == "no-store"
    assert public_event_for_token(token) == event


def test_legacy_closed_revoked_missing_replaced(setup_link):
    _, _, client, event, _, old_token, endpoint = setup_link
    PublicRegistrationLink.objects.filter(event=event).update(encrypted_token=None)
    assert client.get(endpoint).json()["code"] == "legacy_link"
    assert public_event_for_token(old_token) == event
    _, new_token = create_link(client, event)
    assert public_event_for_token(old_token) is None
    Event.objects.filter(pk=event.pk).update(signup_opens=False)
    assert client.get(endpoint).json()["code"] == "registration_closed"
    assert client.delete(endpoint).status_code == 204
    link = PublicRegistrationLink.objects.get(event=event)
    assert link.encrypted_token is None
    assert public_event_for_token(new_token) is None
    assert client.get(endpoint).status_code == 404
    link.delete()
    assert client.get(endpoint).status_code == 404


@pytest.mark.parametrize("damage", ["corrupt", "digest", "event", "church", "shape"])
def test_ciphertext_or_context_corruption(setup_link, damage, settings):
    church, _, client, event, _, token, endpoint = setup_link
    link = PublicRegistrationLink.objects.get(event=event)
    if damage == "corrupt":
        link.encrypted_token = "corrupt"
    elif damage == "digest":
        link.token_digest = "0" * 64
    else:
        payload = {"token": token, "event_id": event.pk, "church_id": church.pk}
        if damage == "event":
            payload["event_id"] += 100
        elif damage == "church":
            payload["church_id"] += 100
        else:
            payload = []
        link.encrypted_token = (
            Fernet(settings.PUBLIC_LINK_ENCRYPTION_KEYS[0])
            .encrypt(json.dumps(payload).encode())
            .decode()
        )
    link.save()
    response = client.get(endpoint)
    assert response.status_code == 503
    assert response.json()["code"] == "recovery_unavailable"
    assert token not in response.content.decode()


def test_key_rollover(setup_link, settings):
    _, _, client, event, old_url, _, endpoint = setup_link
    original = PublicRegistrationLink.objects.get(event=event).encrypted_token
    old_key = settings.PUBLIC_LINK_ENCRYPTION_KEYS[0]
    with override_settings(PUBLIC_LINK_ENCRYPTION_KEYS=[NEW_KEY, old_key]):
        assert client.get(endpoint).json()["url"] == old_url
        assert (
            PublicRegistrationLink.objects.get(event=event).encrypted_token == original
        )
        new_url, _ = create_link(client, event)
    with override_settings(PUBLIC_LINK_ENCRYPTION_KEYS=[NEW_KEY]):
        assert client.get(endpoint).json()["url"] == new_url
    with override_settings(PUBLIC_LINK_ENCRYPTION_KEYS=[old_key]):
        assert client.get(endpoint).status_code == 503


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("mutation", ["revoke", "rotate"])
def test_recovery_waits_for_event_lock_then_observes_mutation(mutation):
    if connection.vendor != "postgresql":
        pytest.skip("Requires PostgreSQL row locks")
    church = Church.objects.create(name="Fictional Concurrent Recovery")
    user, _ = organizer(church)
    event = future_event(church, user)
    link, old_token = rotate_public_registration_link(event=event, created_by=user)
    started = ThreadEvent()

    def recover():
        close_old_connections()
        try:
            started.set()
            try:
                return recover_public_registration_link(event=event)
            except LinkRecoveryError as error:
                return error.code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=1) as pool:
        with transaction.atomic():
            Event.objects.select_for_update().get(pk=event.pk)
            future = pool.submit(recover)
            assert started.wait(5)
            if mutation == "revoke":
                revoke_public_registration_link(link)
                expected = "not_found"
            else:
                _, expected = rotate_public_registration_link(
                    event=event, created_by=user
                )
        assert future.result(timeout=10) == expected
    assert public_event_for_token(old_token) is None


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("mutation", ["revoke", "rotate"])
def test_mutation_waits_until_recovery_releases_lock(mutation):
    from concurrent.futures import TimeoutError
    from unittest.mock import patch

    from events.link_encryption import decrypt_link_token

    if connection.vendor != "postgresql":
        pytest.skip("Requires PostgreSQL row locks")
    church = Church.objects.create(name="Fictional Recovery Lock")
    user, _ = organizer(church)
    event = future_event(church, user)
    link, original = rotate_public_registration_link(event=event, created_by=user)
    decrypting, release, mutating = ThreadEvent(), ThreadEvent(), ThreadEvent()

    def delayed_decrypt(value):
        decrypting.set()
        assert release.wait(5)
        return decrypt_link_token(value)

    def recover():
        close_old_connections()
        try:
            return recover_public_registration_link(event=event)
        finally:
            close_old_connections()

    def mutate():
        close_old_connections()
        try:
            mutating.set()
            if mutation == "revoke":
                revoke_public_registration_link(link)
                return None
            return rotate_public_registration_link(event=event, created_by=user)[1]
        finally:
            close_old_connections()

    with patch("events.services.decrypt_link_token", delayed_decrypt):
        with ThreadPoolExecutor(max_workers=2) as pool:
            recovering = pool.submit(recover)
            assert decrypting.wait(5)
            changing = pool.submit(mutate)
            assert mutating.wait(5)
            try:
                with pytest.raises(TimeoutError):
                    changing.result(timeout=0.2)
            finally:
                release.set()
            assert recovering.result(timeout=5) == original
            new_token = changing.result(timeout=5)
    assert public_event_for_token(original) is None
    if mutation == "revoke":
        assert PublicRegistrationLink.objects.get(event=event).encrypted_token is None
    else:
        assert recover_public_registration_link(event=event) == new_token


def test_revocation_uses_current_link_even_with_stale_caller(setup_link):
    _, user, _, event, _, _, _ = setup_link
    stale = PublicRegistrationLink.objects.get(event=event)
    _, latest = rotate_public_registration_link(event=event, created_by=user)
    revoke_public_registration_link(stale)
    assert public_event_for_token(latest) is None
    with pytest.raises(LinkRecoveryError) as error:
        recover_public_registration_link(event=event)
    assert error.value.status_code == 404
