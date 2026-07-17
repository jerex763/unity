from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.constants import ACTIVE_CHURCH_SESSION_KEY
from accounts.models import ChurchMembership, User
from audit.models import AuditEvent
from people.models import ConsentRecord, Person
from tenancy.models import Church

pytestmark = pytest.mark.django_db

NOTICE_VERSION = "2026-07-draft"


def authenticated_client(
    user: User,
    church: Church,
) -> APIClient:
    client = APIClient()
    client.force_login(user)
    session = client.session
    session[ACTIVE_CHURCH_SESSION_KEY] = church.id
    session.save()
    return client


def make_worker(church: Church, role: str, username: str) -> User:
    user = User.objects.create_user(username=username)
    ChurchMembership.objects.create(user=user, church=church, role=role)
    return user


def consent_url(person: Person) -> str:
    return reverse("people:person-consent", args=(person.id,))


def test_missing_consent_is_unknown_and_person_creation_invents_nothing() -> None:
    church = Church.objects.create(name="Fictional Community Church")
    pastor = make_worker(
        church,
        ChurchMembership.Role.PASTOR,
        "fictional.consent.pastor",
    )
    person = Person.objects.create(church=church, full_name="Fictional Person")
    client = authenticated_client(pastor, church)

    response = client.get(consent_url(person))

    assert response.status_code == 200
    assert response.json() == {
        "id": None,
        "status": "unknown",
        "notice_version": None,
        "consented_at": None,
        "method": None,
        "recorded_by": None,
        "supersedes_id": None,
        "recorded_at": None,
    }
    assert not ConsentRecord.objects.exists()


def test_authorized_worker_records_and_corrects_consent_without_overwriting() -> None:
    church = Church.objects.create(name="Fictional Community Church")
    pastor = make_worker(
        church,
        ChurchMembership.Role.PASTOR,
        "fictional.consent.pastor",
    )
    person = Person.objects.create(church=church, full_name="Fictional Person")
    client = authenticated_client(pastor, church)
    first_decision_at = timezone.now() - timedelta(days=2)
    corrected_decision_at = timezone.now() - timedelta(days=1)

    first = client.post(
        consent_url(person),
        {
            "status": ConsentRecord.Status.GRANTED,
            "notice_version": NOTICE_VERSION,
            "consented_at": first_decision_at.isoformat(),
            "method": ConsentRecord.Method.PAPER_FORM,
        },
        format="json",
    )
    correction = client.post(
        consent_url(person),
        {
            "status": ConsentRecord.Status.DECLINED,
            "notice_version": NOTICE_VERSION,
            "consented_at": corrected_decision_at.isoformat(),
            "method": ConsentRecord.Method.STAFF_RECORDED,
        },
        format="json",
    )
    latest = client.get(consent_url(person))

    assert first.status_code == 201
    assert correction.status_code == 201
    assert latest.status_code == 200
    assert latest.json()["status"] == ConsentRecord.Status.DECLINED
    assert latest.json()["notice_version"] == NOTICE_VERSION
    assert latest.json()["recorded_by"] == pastor.username
    assert latest.json()["supersedes_id"] == first.json()["id"]
    assert latest.json()["consented_at"] == correction.json()["consented_at"]
    assert ConsentRecord.objects.filter(person=person).count() == 2
    assert ConsentRecord.objects.get(pk=first.json()["id"]).status == (
        ConsentRecord.Status.GRANTED
    )
    consent_events = AuditEvent.objects.filter(
        action=AuditEvent.Action.CONSENT_RECORDED
    )
    assert consent_events.count() == 2
    assert not consent_events.exclude(actor=pastor, church=church).exists()


def test_leader_cannot_read_or_record_consent() -> None:
    church = Church.objects.create(name="Fictional Community Church")
    leader = make_worker(
        church,
        ChurchMembership.Role.LEADER,
        "fictional.consent.leader",
    )
    person = Person.objects.create(church=church, full_name="Fictional Person")
    client = authenticated_client(leader, church)

    get_response = client.get(consent_url(person))
    post_response = client.post(
        consent_url(person),
        {
            "status": ConsentRecord.Status.GRANTED,
            "notice_version": NOTICE_VERSION,
            "consented_at": timezone.now().isoformat(),
            "method": ConsentRecord.Method.STAFF_RECORDED,
        },
        format="json",
    )

    assert get_response.status_code == 403
    assert post_response.status_code == 403
    assert not ConsentRecord.objects.exists()


def test_consent_lookup_cannot_cross_church() -> None:
    current_church = Church.objects.create(name="Fictional Community Church")
    other_church = Church.objects.create(name="Other Fictional Church")
    pastor = make_worker(
        current_church,
        ChurchMembership.Role.PASTOR,
        "fictional.scoped.pastor",
    )
    other_person = Person.objects.create(
        church=other_church,
        full_name="Other Fictional Person",
    )
    client = authenticated_client(pastor, current_church)

    response = client.get(consent_url(other_person))

    assert response.status_code == 404


def test_future_decision_time_is_rejected() -> None:
    church = Church.objects.create(name="Fictional Community Church")
    admin = make_worker(
        church,
        ChurchMembership.Role.ADMIN,
        "fictional.consent.admin",
    )
    person = Person.objects.create(church=church, full_name="Fictional Person")
    client = authenticated_client(admin, church)

    response = client.post(
        consent_url(person),
        {
            "status": ConsentRecord.Status.GRANTED,
            "notice_version": NOTICE_VERSION,
            "consented_at": (timezone.now() + timedelta(days=1)).isoformat(),
            "method": ConsentRecord.Method.SELF_SERVICE,
        },
        format="json",
    )

    assert response.status_code == 400
    assert "consented_at" in response.json()
    assert not ConsentRecord.objects.exists()


def test_consent_history_is_append_only() -> None:
    church = Church.objects.create(name="Fictional Community Church")
    recorder = make_worker(
        church,
        ChurchMembership.Role.PASTOR,
        "fictional.consent.recorder",
    )
    person = Person.objects.create(church=church, full_name="Fictional Person")
    record = ConsentRecord.objects.create(
        church=church,
        person=person,
        status=ConsentRecord.Status.GRANTED,
        notice_version=NOTICE_VERSION,
        consented_at=timezone.now(),
        method=ConsentRecord.Method.PAPER_FORM,
        recorded_by=recorder,
    )
    record.status = ConsentRecord.Status.DECLINED

    with pytest.raises(ValidationError, match="append-only"):
        record.save()
    with pytest.raises(ValidationError, match="cannot be deleted"):
        record.delete()
    with pytest.raises(ValidationError, match="append-only"):
        ConsentRecord.objects.filter(pk=record.pk).update(
            status=ConsentRecord.Status.DECLINED
        )
    with pytest.raises(ValidationError, match="cannot be deleted"):
        ConsentRecord.objects.filter(pk=record.pk).delete()
