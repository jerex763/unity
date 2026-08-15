from datetime import timedelta

import pytest
from django.db import connection, models
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone

pytestmark = pytest.mark.django_db(transaction=True)


def test_contact_preference_migration_resets_implicit_whatsapp_opt_ins() -> None:
    old_target = [
        ("people", "0005_person_normalized_email_person_normalized_phone_and_more")
    ]
    data_target = [("people", "0006_person_contact_preferences")]
    index_target = [("people", "0007_person_wechat_index")]
    executor = MigrationExecutor(connection)
    executor.migrate(old_target)
    old_apps = executor.loader.project_state(old_target).apps
    Church = old_apps.get_model("tenancy", "Church")
    Person = old_apps.get_model("people", "Person")
    church = Church.objects.create(name="Fictional WhatsApp Migration Church")
    opted_by_legacy_default = Person.objects.create(
        church=church,
        full_name="Fictional Legacy Default",
    )
    explicitly_false = Person.objects.create(
        church=church,
        full_name="Fictional Explicit False",
        has_whatsapp=False,
    )
    assert opted_by_legacy_default.has_whatsapp is True

    executor = MigrationExecutor(connection)
    executor.migrate(data_target)
    data_apps = executor.loader.project_state(data_target).apps
    DataPerson = data_apps.get_model("people", "Person")

    # 0006 commits its field and data changes before 0007 creates the index.
    # This transaction boundary avoids PostgreSQL's pending-trigger-events
    # failure while keeping each migration atomic and safely retryable.
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(
            cursor, DataPerson._meta.db_table
        )
    assert "person_church__9b7c6c_idx" not in constraints

    executor = MigrationExecutor(connection)
    executor.migrate(index_target)
    new_apps = executor.loader.project_state(index_target).apps
    NewPerson = new_apps.get_model("people", "Person")

    # Historical true values were indistinguishable from the old implicit
    # default, so the privacy-safe upgrade requires everyone to opt in again.
    assert NewPerson.objects.get(pk=opted_by_legacy_default.pk).has_whatsapp is False
    assert NewPerson.objects.get(pk=explicitly_false.pk).has_whatsapp is False
    assert NewPerson._meta.get_field("has_whatsapp").default is False
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(
            cursor, NewPerson._meta.db_table
        )
    assert constraints["person_church__9b7c6c_idx"]["index"] is True
    assert "person_church__9b7c6c_idx" in {
        index.name for index in NewPerson._meta.indexes
    }


def test_wechat_index_migration_accepts_legacy_index_and_reverses_safely() -> None:
    old_target = [
        ("people", "0005_person_normalized_email_person_normalized_phone_and_more")
    ]
    data_target = [("people", "0006_person_contact_preferences")]
    index_target = [("people", "0007_person_wechat_index")]
    executor = MigrationExecutor(connection)
    executor.migrate(old_target)
    executor = MigrationExecutor(connection)
    executor.migrate(data_target)
    data_apps = executor.loader.project_state(data_target).apps
    DataPerson = data_apps.get_model("people", "Person")

    # Simulate a database where the earlier published 0006 succeeded and
    # created the index before 0007 existed.
    legacy_index = models.Index(
        fields=["church", "normalized_wechat_id"],
        name="person_church__9b7c6c_idx",
    )
    with connection.schema_editor() as schema_editor:
        schema_editor.add_index(DataPerson, legacy_index)

    executor = MigrationExecutor(connection)
    executor.migrate(index_target)
    indexed_apps = executor.loader.project_state(index_target).apps
    IndexedPerson = indexed_apps.get_model("people", "Person")
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(
            cursor, IndexedPerson._meta.db_table
        )
    assert constraints["person_church__9b7c6c_idx"]["index"] is True
    assert "person_church__9b7c6c_idx" in {
        index.name for index in IndexedPerson._meta.indexes
    }

    executor = MigrationExecutor(connection)
    executor.migrate(data_target)
    reversed_apps = executor.loader.project_state(data_target).apps
    ReversedPerson = reversed_apps.get_model("people", "Person")
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(
            cursor, ReversedPerson._meta.db_table
        )
    assert "person_church__9b7c6c_idx" not in constraints

    # Leave the schema at the current leaf for subsequent tests.
    MigrationExecutor(connection).migrate(index_target)


def test_transport_removal_blocks_true_rows_until_manual_review() -> None:
    old_target = [("events", "0005_publicregistrationidentitylock")]
    new_target = [("events", "0006_remove_transport")]
    executor = MigrationExecutor(connection)
    executor.migrate(old_target)
    old_apps = executor.loader.project_state(old_target).apps
    Church = old_apps.get_model("tenancy", "Church")
    User = old_apps.get_model("accounts", "User")
    Person = old_apps.get_model("people", "Person")
    Event = old_apps.get_model("events", "Event")
    EventRegistration = old_apps.get_model("events", "EventRegistration")

    church = Church.objects.create(name="Fictional Transport Migration Church")
    user = User.objects.create(username="fictional.transport.migration")
    person_without_request = Person.objects.create(
        church=church,
        full_name="Fictional No Transport Request",
    )
    person_with_request = Person.objects.create(
        church=church,
        full_name="Fictional Transport Request",
    )
    starts_at = timezone.now() + timedelta(days=3)
    event = Event.objects.create(
        church=church,
        title="Fictional Migration Event",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=1),
        created_by=user,
    )
    EventRegistration.objects.create(
        church=church,
        event=event,
        person=person_without_request,
        needs_transport=False,
    )
    requested = EventRegistration.objects.create(
        church=church,
        event=event,
        person=person_with_request,
        needs_transport=True,
    )

    executor = MigrationExecutor(connection)
    with pytest.raises(RuntimeError, match="require manual review"):
        executor.migrate(new_target)

    # The failed atomic migration preserves the flag. A human must resolve and
    # explicitly confirm every true row; this test simulates that review only.
    executor = MigrationExecutor(connection)
    old_apps = executor.loader.project_state(old_target).apps
    OldRegistration = old_apps.get_model("events", "EventRegistration")
    assert OldRegistration.objects.get(pk=requested.pk).needs_transport is True
    OldRegistration.objects.filter(pk=requested.pk).update(needs_transport=False)

    executor.migrate(new_target)
    new_apps = executor.loader.project_state(new_target).apps
    NewRegistration = new_apps.get_model("events", "EventRegistration")
    assert "needs_transport" not in {
        field.name for field in NewRegistration._meta.get_fields()
    }
