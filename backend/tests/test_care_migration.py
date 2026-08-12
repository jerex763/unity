from datetime import timedelta
from importlib import import_module

import pytest
from django.apps import apps
from django.utils import timezone

from care.attention import attention_for
from care.models import FollowUp
from people.models import Person
from tenancy.models import Church

pytestmark = pytest.mark.django_db


def test_schedule_anchor_backfill_uses_existing_updated_at() -> None:
    church = Church.objects.create(name="Fictional Legacy Anchor")
    person = Person.objects.create(church=church, full_name="Fictional Legacy Person")
    item = FollowUp.objects.create(
        church=church,
        person=person,
        source=FollowUp.Source.OTHER,
        status=FollowUp.Status.IN_PROGRESS,
        due_at=timezone.localdate() - timedelta(days=5),
    )
    legacy_updated_at = timezone.now() - timedelta(days=7)
    FollowUp.objects.filter(pk=item.pk).update(
        updated_at=legacy_updated_at,
        status_changed_at=timezone.now(),
        due_schedule_changed_at=timezone.now(),
    )
    migration = import_module(
        "care.migrations.0003_followup_status_changed_at_followupduedatechange"
    )

    migration.backfill_schedule_anchors(apps, None)
    item.refresh_from_db()

    assert item.status_changed_at == legacy_updated_at
    assert item.due_schedule_changed_at == legacy_updated_at
    assert attention_for(item)["stale"] is True
