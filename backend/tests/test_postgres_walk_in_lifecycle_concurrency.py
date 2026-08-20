from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event as ThreadEvent

import pytest
from django.db import close_old_connections, connection, transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.constants import ACTIVE_CHURCH_SESSION_KEY
from accounts.models import ChurchMembership, User
from care.models import FollowUp
from events.models import Event, EventRegistration
from people.lifecycle import deactivate_person
from people.models import Person, PersonQuerySet
from tenancy.models import Church

pytestmark = [
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(
        connection.vendor != "postgresql",
        reason="SQLite cannot exercise PostgreSQL row-lock lifecycle serialization.",
    ),
]


def test_walk_in_contact_match_serializes_with_person_deactivation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    church = Church.objects.create(name="Fictional Concurrent Walk-in Church")
    worker = User.objects.create_user(username="fictional.concurrent.walkin")
    ChurchMembership.objects.create(
        church=church,
        user=worker,
        role=ChurchMembership.Role.LEADER,
    )
    person = Person.objects.create(
        church=church,
        full_name="Concurrent Existing Visitor",
        email="concurrent.walkin@example.test",
    )
    now = timezone.now()
    event = Event.objects.create(
        church=church,
        title="Fictional Concurrent Walk-in Event",
        starts_at=now,
        ends_at=now + timedelta(hours=1),
        created_by=worker,
    )
    client = APIClient()
    client.force_login(worker)
    session = client.session
    session[ACTIVE_CHURCH_SESSION_KEY] = church.id
    session.save()

    lifecycle_lock_acquired = ThreadEvent()
    walk_in_lock_attempted = ThreadEvent()

    from events import views

    original_candidates = views._locked_contact_candidates

    def signaled_candidates(
        people: PersonQuerySet,
        contact_predicate: Q,
    ) -> list[Person]:
        walk_in_lock_attempted.set()
        return original_candidates(people, contact_predicate)

    monkeypatch.setattr(views, "_locked_contact_candidates", signaled_candidates)

    def deactivate() -> None:
        close_old_connections()
        try:
            with transaction.atomic():
                locked = Person.objects.select_for_update().get(pk=person.pk)
                lifecycle_lock_acquired.set()
                assert walk_in_lock_attempted.wait(timeout=10)
                deactivate_person(locked)
        finally:
            close_old_connections()

    def submit_walk_in() -> tuple[int, dict[str, object]]:
        close_old_connections()
        try:
            assert lifecycle_lock_acquired.wait(timeout=10)
            response = client.post(
                reverse("events:event-walk-in-create", args=(event.id,)),
                {
                    "full_name": "Concurrent Submitted Visitor",
                    "email": "CONCURRENT.WALKIN@example.test",
                },
                format="json",
            )
            return response.status_code, response.json()
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        deactivation = executor.submit(deactivate)
        walk_in = executor.submit(submit_walk_in)
        deactivation.result(timeout=20)
        status_code, payload = walk_in.result(timeout=20)

    assert status_code == 400
    assert payload["detail"] == (
        "This contact needs Pastor or Admin review before check-in."
    )
    person.refresh_from_db()
    assert person.deactivated_at is not None
    assert Person.objects.for_church(church).count() == 1
    assert not EventRegistration.objects.filter(event=event).exists()
    assert not FollowUp.objects.filter(church=church).exists()
