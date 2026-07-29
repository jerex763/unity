from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from django.db import close_old_connections, connection
from django.utils import timezone

from accounts.models import User
from care.models import FollowUp
from events.models import Event, EventRegistration
from events.services import set_manual_check_in
from people.models import Person
from tenancy.models import Church

pytestmark = [
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(
        connection.vendor != "postgresql",
        reason=(
            "SQLite cannot exercise PostgreSQL's concurrent partial-unique "
            "constraint and IntegrityError recovery path."
        ),
    ),
]


def test_concurrent_first_check_ins_create_one_open_follow_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    church = Church.objects.create(name="Fictional Concurrent Follow-up")
    worker = User.objects.create_user(username="fictional.concurrent.followup")
    person = Person.objects.create(church=church, full_name="Concurrent Visitor")
    starts_at = timezone.now() + timedelta(days=1)
    registrations = []
    for suffix in ("A", "B"):
        event = Event.objects.create(
            church=church,
            title=f"Fictional Concurrent Event {suffix}",
            starts_at=starts_at,
            ends_at=starts_at + timedelta(hours=1),
            created_by=worker,
        )
        registrations.append(
            EventRegistration.objects.create(
                church=church,
                event=event,
                person=person,
            )
        )

    create_barrier = Barrier(2)
    original_create = FollowUp.objects.create

    def synchronized_create(**kwargs):
        create_barrier.wait(timeout=10)
        return original_create(**kwargs)

    monkeypatch.setattr(FollowUp.objects, "create", synchronized_create)

    def check_in(registration_id: int) -> None:
        close_old_connections()
        try:
            registration = EventRegistration.objects.get(pk=registration_id)
            set_manual_check_in(registration, checked_in=True)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(check_in, registration.pk) for registration in registrations
        ]
        for future in futures:
            future.result(timeout=20)

    assert (
        EventRegistration.objects.filter(
            pk__in=[registration.pk for registration in registrations],
            checked_in_at__isnull=False,
        ).count()
        == 2
    )
    assert (
        FollowUp.objects.filter(
            church=church,
            person=person,
            status=FollowUp.Status.NEW,
            source=FollowUp.Source.EVENT_VISIT,
        ).count()
        == 1
    )
