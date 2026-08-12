from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from threading import Event as ThreadEvent

import pytest
from django.db import close_old_connections, connection
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.constants import ACTIVE_CHURCH_SESSION_KEY
from accounts.models import ChurchMembership, User
from care.models import FollowUp, FollowUpDueDateChange
from care.serializers import FollowUpSerializer
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


def test_concurrent_first_postponements_are_serialized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    church = Church.objects.create(name="Fictional Concurrent Scheduling")
    worker = User.objects.create_user(username="fictional.concurrent.schedule")
    ChurchMembership.objects.create(
        church=church,
        user=worker,
        role=ChurchMembership.Role.PASTOR,
    )
    person = Person.objects.create(church=church, full_name="Concurrent Schedule")
    original_due = timezone.localdate() + timedelta(days=2)
    item = FollowUp.objects.create(
        church=church,
        person=person,
        source=FollowUp.Source.OTHER,
        assigned_to=worker,
        due_at=original_due,
    )
    first_has_lock = ThreadEvent()
    second_started = ThreadEvent()
    original_validate = FollowUpSerializer.validate

    def synchronized_validate(serializer, attrs):
        requested_due = attrs.get("due_at")
        if requested_due == original_due + timedelta(days=1):
            first_has_lock.set()
            assert second_started.wait(timeout=10)
        return original_validate(serializer, attrs)

    monkeypatch.setattr(FollowUpSerializer, "validate", synchronized_validate)

    clients = []
    for _ in range(2):
        client = APIClient()
        client.force_login(worker)
        session = client.session
        session[ACTIVE_CHURCH_SESSION_KEY] = church.id
        session.save()
        clients.append(client)

    def postpone(client: APIClient, days: int) -> tuple[int, dict[str, object]]:
        close_old_connections()
        try:
            if days == 2:
                assert first_has_lock.wait(timeout=10)
                second_started.set()
            response = client.patch(
                reverse("care:follow-up-detail", args=(item.id,)),
                {"due_at": (original_due + timedelta(days=days)).isoformat()},
                format="json",
            )
            return response.status_code, response.json()
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(postpone, clients[0], 1),
            executor.submit(postpone, clients[1], 2),
        ]
        results = [future.result(timeout=20) for future in futures]
    monkeypatch.setattr(FollowUpSerializer, "validate", original_validate)

    assert sorted(status for status, _ in results) == [200, 400]
    rejected_payload = next(payload for status, payload in results if status == 400)
    assert "postpone_reason" in rejected_payload
    first_change = FollowUpDueDateChange.objects.get(follow_up=item)
    assert first_change.previous_due_at == original_due

    item.refresh_from_db()
    final_due = item.due_at + timedelta(days=1)
    retry = clients[0].patch(
        reverse("care:follow-up-detail", args=(item.id,)),
        {
            "due_at": final_due.isoformat(),
            "postpone_reason": FollowUpDueDateChange.Reason.OTHER_OPERATIONAL,
        },
        format="json",
    )

    assert retry.status_code == 200
    changes = list(item.due_date_changes.all())
    assert len(changes) == 2
    assert changes[1].previous_due_at == changes[0].new_due_at
    assert changes[1].new_due_at == final_due
