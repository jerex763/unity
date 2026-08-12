from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from people.models import Person
from tenancy.models import Church

pytestmark = pytest.mark.django_db(transaction=True)


def test_preflight_reports_only_church_and_person_ids_for_collisions() -> None:
    church = Church.objects.create(name="Fictional Preflight Church")
    first = Person.objects.create(
        church=church,
        full_name="Fictional First Person",
        email="first@example.test",
    )
    second = Person.objects.create(
        church=church,
        full_name="Fictional Second Person",
        email="second@example.test",
    )
    Person.objects.filter(pk=first.pk).update(email=" Collision@Example.Test ")
    Person.objects.filter(pk=second.pk).update(email="collision@example.test")

    output = StringIO()
    with pytest.raises(CommandError) as caught:
        call_command("preflight_person_contact_normalization", stdout=output)

    message = str(caught.value)
    assert f"church_id={church.pk}" in message
    assert f"person_ids=[{first.pk}, {second.pk}]" in message
    assert "collision@example.test" not in message.lower()


def test_normalization_migration_rolls_back_collision_then_succeeds_after_review() -> (
    None
):
    executor = MigrationExecutor(connection)
    old_target = [("people", "0004_person_wechat_id")]
    new_target = [
        (
            "people",
            "0005_person_normalized_email_person_normalized_phone_and_more",
        )
    ]
    executor.migrate(old_target)
    old_apps = executor.loader.project_state(old_target).apps
    OldChurch = old_apps.get_model("tenancy", "Church")
    OldPerson = old_apps.get_model("people", "Person")
    church = OldChurch.objects.create(name="Fictional Migration Church")
    first = OldPerson.objects.create(
        church=church,
        full_name="Fictional Migration First",
        email=" Migrate@Example.Test ",
    )
    second = OldPerson.objects.create(
        church=church,
        full_name="Fictional Migration Second",
        email="migrate@example.test",
    )

    executor = MigrationExecutor(connection)
    with pytest.raises(RuntimeError, match="require human review") as caught:
        executor.migrate(new_target)
    assert f"church_id={church.pk}" in str(caught.value)
    assert f"person_ids=[{first.pk}, {second.pk}]" in str(caught.value)
    assert "migrate@example.test" not in str(caught.value).lower()

    # The failed atomic migration leaves the old schema/data intact. A human
    # review changes the conflicting contact; it never auto-merges people.
    executor = MigrationExecutor(connection)
    old_apps = executor.loader.project_state(old_target).apps
    OldPerson = old_apps.get_model("people", "Person")
    OldPerson.objects.filter(pk=second.pk).update(email="reviewed@example.test")
    executor.migrate(new_target)
    new_apps = executor.loader.project_state(new_target).apps
    NewPerson = new_apps.get_model("people", "Person")
    assert NewPerson.objects.get(pk=first.pk).normalized_email == (
        "migrate@example.test"
    )
    assert NewPerson.objects.get(pk=second.pk).normalized_email == (
        "reviewed@example.test"
    )
