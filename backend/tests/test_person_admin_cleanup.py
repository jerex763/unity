from unittest.mock import patch
from uuid import uuid4

import pytest
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import ChurchMembership, User
from audit.models import AuditEvent
from people.admin import PersonAdmin
from people.lifecycle import hard_delete_person as lifecycle_hard_delete_person
from people.models import ConsentRecord, Person
from tenancy.models import Church

pytestmark = pytest.mark.django_db

ACTION = "hard_delete_fictional_test_people"
RUN_ID = "20260813-0303"
OTHER_RUN_ID = "20260813-0304"


@pytest.fixture
def church() -> Church:
    return Church.objects.create(name="Fictional Cleanup Church")


@pytest.fixture
def superuser_client() -> tuple[Client, User]:
    user = User.objects.create_superuser(
        username="fictional.cleanup.superuser",
        email="fictional.cleanup.superuser@example.test",
        password="test-password-only",
    )
    client = Client()
    client.force_login(user)
    return client, user


def make_person(
    church: Church,
    *,
    label: str,
    run_id: str = RUN_ID,
    email_domain: str = "example.test",
    membership_status: str = Person.MembershipStatus.VISITOR,
    full_name: str | None = None,
    email: str | None = None,
) -> Person:
    return Person.objects.create(
        church=church,
        full_name=full_name or f"Fictional {label} {run_id}",
        email=email or f"{label.lower()}.{run_id}@{email_domain}",
        membership_status=membership_status,
    )


def preview_action(
    client: Client,
    people: list[Person],
    *,
    select_across: str = "0",
):
    data: dict[str, object] = {
        "action": ACTION,
        ACTION_CHECKBOX_NAME: [person.pk for person in people],
        "select_across": select_across,
    }
    return client.post(reverse("admin:people_person_changelist"), data)


def selection_manifest(response) -> str:
    return response.context_data["selection_manifest"]


def confirm_action(
    client: Client,
    selected_ids: list[int],
    *,
    run_id: str,
    manifest: str,
):
    return client.post(
        reverse("admin:people_person_changelist"),
        {
            "action": ACTION,
            ACTION_CHECKBOX_NAME: selected_ids,
            "select_across": "0",
            "confirm_cleanup": "yes",
            "run_id": run_id,
            "selection_manifest": manifest,
        },
    )


def run_action(client: Client, people: list[Person], *, run_id: str):
    preview = preview_action(client, people)
    return confirm_action(
        client,
        [person.pk for person in people],
        run_id=run_id,
        manifest=selection_manifest(preview),
    )


def test_cleanup_confirmation_displays_only_selected_targets(
    church: Church,
    superuser_client: tuple[Client, User],
) -> None:
    client, _ = superuser_client
    selected = make_person(church, label="Selected")
    unselected = make_person(church, label="Unselected")

    response = preview_action(client, [selected])

    assert response.status_code == 200
    assert (
        response.template_name
        == "admin/people/person/confirm_fictional_test_cleanup.html"
    )
    content = response.content.decode()
    assert selected.full_name in content
    assert selected.email in content
    assert unselected.full_name not in content
    assert unselected.email not in content
    assert 'name="run_id"' in content
    assert 'name="selection_manifest"' in content
    assert Person.objects.filter(pk=selected.pk).exists()


def test_cleanup_happy_path_is_case_insensitive_and_keeps_audit_rows(
    church: Church,
    superuser_client: tuple[Client, User],
) -> None:
    client, user = superuser_client
    person = make_person(church, label="Eligible", email_domain="Example.Test")
    person_id = person.pk
    consent = ConsentRecord.objects.create(
        church=church,
        person=person,
        status=ConsentRecord.Status.GRANTED,
        notice_version="2026-07-draft",
        consented_at=timezone.now(),
        method=ConsentRecord.Method.SELF_SERVICE,
        recorded_by=None,
    )
    existing_audit = AuditEvent.objects.create(
        actor=user,
        church=church,
        action=AuditEvent.Action.PERSON_CREATED,
        target_type="people.person",
        target_id=str(person_id),
        request_id=uuid4(),
    )

    response = run_action(client, [person], run_id=RUN_ID)

    assert response.status_code == 302
    assert not Person.objects.filter(pk=person_id).exists()
    assert not ConsentRecord.objects.filter(pk=consent.pk).exists()
    assert AuditEvent.objects.filter(pk=existing_audit.pk).exists()
    deletion = AuditEvent.objects.get(
        action=AuditEvent.Action.PERSON_HARD_DELETED,
        target_id=str(person_id),
    )
    assert deletion.actor == user
    assert deletion.metadata == {"delete_reason": Person.HardDeleteReason.TEST_DATA}


def test_cleanup_rejects_people_with_mismatched_run_ids(
    church: Church,
    superuser_client: tuple[Client, User],
) -> None:
    client, _ = superuser_client
    first = make_person(church, label="First")
    second = make_person(church, label="Second", run_id=OTHER_RUN_ID)

    response = run_action(client, [first, second], run_id=RUN_ID)

    assert response.status_code == 200
    assert b"Nothing was deleted" in response.content
    assert Person.objects.filter(pk__in=(first.pk, second.pk)).count() == 2
    assert not AuditEvent.objects.filter(
        action=AuditEvent.Action.PERSON_HARD_DELETED
    ).exists()


def test_cleanup_rejects_non_example_test_email(
    church: Church,
    superuser_client: tuple[Client, User],
) -> None:
    client, _ = superuser_client
    person = make_person(
        church, label="WrongDomain", email_domain="example.test.invalid"
    )

    response = run_action(client, [person], run_id=RUN_ID)

    assert response.status_code == 200
    assert b"Nothing was deleted" in response.content
    assert Person.objects.filter(pk=person.pk).exists()


def test_cleanup_rejects_non_visitor(
    church: Church,
    superuser_client: tuple[Client, User],
) -> None:
    client, _ = superuser_client
    person = make_person(
        church,
        label="Member",
        membership_status=Person.MembershipStatus.MEMBER,
    )

    response = run_action(client, [person], run_id=RUN_ID)

    assert response.status_code == 200
    assert b"Nothing was deleted" in response.content
    assert Person.objects.filter(pk=person.pk).exists()


def test_cleanup_rejects_person_linked_to_a_user(
    church: Church,
    superuser_client: tuple[Client, User],
) -> None:
    client, _ = superuser_client
    person = make_person(church, label="Linked")
    linked_user = User.objects.create_user(username="fictional.cleanup.linked")
    ChurchMembership.objects.create(
        user=linked_user,
        church=church,
        person=person,
        role=ChurchMembership.Role.MEMBER,
        is_active=False,
    )

    response = run_action(client, [person], run_id=RUN_ID)

    assert response.status_code == 200
    assert b"Nothing was deleted" in response.content
    assert Person.objects.filter(pk=person.pk).exists()


def test_cleanup_rejects_invalid_run_id_format(
    church: Church,
    superuser_client: tuple[Client, User],
) -> None:
    client, _ = superuser_client
    person = make_person(church, label="InvalidInput")

    response = run_action(client, [person], run_id="2026-08-13")

    assert response.status_code == 200
    assert b"Enter a RUN_ID in YYYYMMDD-HHMM format" in response.content
    assert Person.objects.filter(pk=person.pk).exists()


def test_cleanup_rejects_entire_batch_when_one_person_is_ineligible(
    church: Church,
    superuser_client: tuple[Client, User],
) -> None:
    client, _ = superuser_client
    eligible = make_person(church, label="AtomicEligible")
    ineligible = make_person(
        church,
        label="AtomicIneligible",
        email_domain="invalid.example",
    )

    response = run_action(client, [eligible, ineligible], run_id=RUN_ID)

    assert response.status_code == 200
    assert b"Nothing was deleted" in response.content
    assert Person.objects.filter(pk__in=(eligible.pk, ineligible.pk)).count() == 2
    assert not AuditEvent.objects.filter(
        action=AuditEvent.Action.PERSON_HARD_DELETED
    ).exists()


@pytest.mark.parametrize(
    ("full_name", "email"),
    (
        (
            f"Fictional x{RUN_ID}y",
            f"valid.{RUN_ID}@example.test",
        ),
        (
            f"Fictional Valid {RUN_ID}",
            f"x{RUN_ID}y@example.test",
        ),
    ),
)
def test_cleanup_rejects_run_id_substring_false_positives(
    church: Church,
    superuser_client: tuple[Client, User],
    full_name: str,
    email: str,
) -> None:
    client, _ = superuser_client
    person = make_person(
        church,
        label="FalsePositive",
        full_name=full_name,
        email=email,
    )

    response = run_action(client, [person], run_id=RUN_ID)

    assert response.status_code == 200
    assert b"Nothing was deleted" in response.content
    assert Person.objects.filter(pk=person.pk).exists()


def test_cleanup_manifest_rejects_added_target(
    church: Church,
    superuser_client: tuple[Client, User],
) -> None:
    client, _ = superuser_client
    signed = make_person(church, label="Signed")
    added = make_person(church, label="Added")
    preview = preview_action(client, [signed])

    response = confirm_action(
        client,
        [signed.pk, added.pk],
        run_id=RUN_ID,
        manifest=selection_manifest(preview),
    )

    assert response.status_code == 200
    assert b"differ from the confirmed selection" in response.content
    assert Person.objects.filter(pk__in=(signed.pk, added.pk)).count() == 2


def test_cleanup_manifest_rejects_swapped_target(
    church: Church,
    superuser_client: tuple[Client, User],
) -> None:
    client, _ = superuser_client
    signed = make_person(church, label="SignedSwap")
    swapped = make_person(church, label="Swapped")
    preview = preview_action(client, [signed])

    response = confirm_action(
        client,
        [swapped.pk],
        run_id=RUN_ID,
        manifest=selection_manifest(preview),
    )

    assert response.status_code == 200
    assert b"differ from the confirmed selection" in response.content
    assert Person.objects.filter(pk__in=(signed.pk, swapped.pk)).count() == 2


def test_cleanup_manifest_rejects_removed_target(
    church: Church,
    superuser_client: tuple[Client, User],
) -> None:
    client, _ = superuser_client
    retained = make_person(church, label="Retained")
    removed = make_person(church, label="Removed")
    preview = preview_action(client, [retained, removed])

    response = confirm_action(
        client,
        [retained.pk],
        run_id=RUN_ID,
        manifest=selection_manifest(preview),
    )

    assert response.status_code == 200
    assert b"differ from the confirmed selection" in response.content
    assert Person.objects.filter(pk__in=(retained.pk, removed.pk)).count() == 2


def test_cleanup_manifest_rejects_duplicate_submitted_id(
    church: Church,
    superuser_client: tuple[Client, User],
) -> None:
    client, _ = superuser_client
    person = make_person(church, label="Duplicate")
    preview = preview_action(client, [person])

    response = confirm_action(
        client,
        [person.pk, person.pk],
        run_id=RUN_ID,
        manifest=selection_manifest(preview),
    )

    assert response.status_code == 200
    assert b"differ from the confirmed selection" in response.content
    assert Person.objects.filter(pk=person.pk).exists()


def test_cleanup_manifest_rejects_stale_deleted_target(
    church: Church,
    superuser_client: tuple[Client, User],
) -> None:
    client, _ = superuser_client
    stale = make_person(church, label="Stale")
    current = make_person(church, label="Current")
    stale_id = stale.pk
    preview = preview_action(client, [stale, current])
    stale.delete(hard_delete_reason=Person.HardDeleteReason.TEST_DATA)

    response = confirm_action(
        client,
        [stale_id, current.pk],
        run_id=RUN_ID,
        manifest=selection_manifest(preview),
    )

    assert response.status_code == 200
    assert b"Nothing was deleted" in response.content
    assert Person.objects.filter(pk=current.pk).exists()


def test_cleanup_manifest_rejects_tampering(
    church: Church,
    superuser_client: tuple[Client, User],
) -> None:
    client, _ = superuser_client
    person = make_person(church, label="Tampered")
    preview = preview_action(client, [person])
    manifest = selection_manifest(preview)
    tampered_manifest = manifest[:-1] + ("a" if manifest[-1] != "a" else "b")

    response = confirm_action(
        client,
        [person.pk],
        run_id=RUN_ID,
        manifest=tampered_manifest,
    )

    assert response.status_code == 200
    assert b"could not be verified" in response.content
    assert Person.objects.filter(pk=person.pk).exists()


def test_cleanup_manifest_rejects_expired_confirmation(
    church: Church,
    superuser_client: tuple[Client, User],
) -> None:
    client, _ = superuser_client
    person = make_person(church, label="Expired")
    with patch("django.core.signing.time.time", return_value=1_000_000):
        preview = preview_action(client, [person])
    with patch(
        "django.core.signing.time.time",
        return_value=1_000_000 + PersonAdmin.fictional_cleanup_manifest_max_age + 1,
    ):
        response = confirm_action(
            client,
            [person.pk],
            run_id=RUN_ID,
            manifest=selection_manifest(preview),
        )

    assert response.status_code == 200
    assert b"confirmation expired" in response.content
    assert Person.objects.filter(pk=person.pk).exists()


def test_cleanup_disables_select_across(
    church: Church,
    superuser_client: tuple[Client, User],
) -> None:
    client, _ = superuser_client
    person = make_person(church, label="SelectAcross")

    response = preview_action(client, [person], select_across="1")

    assert response.status_code == 302
    assert Person.objects.filter(pk=person.pk).exists()


def test_cleanup_admin_denies_anonymous_and_non_superuser_users(
    church: Church,
) -> None:
    person = make_person(church, label="Restricted")
    url = reverse("admin:people_person_changelist")

    anonymous_response = Client().get(url)
    staff = User.objects.create_user(
        username="fictional.cleanup.staff",
        is_active=True,
        is_staff=True,
    )
    staff_client = Client()
    staff_client.force_login(staff)
    staff_get_response = staff_client.get(url)
    staff_post_response = preview_action(staff_client, [person])

    assert anonymous_response.status_code == 302
    assert reverse("admin:login") in anonymous_response.url
    assert staff_get_response.status_code == 403
    assert staff_post_response.status_code == 403
    assert Person.objects.filter(pk=person.pk).exists()


def test_cleanup_admin_post_requires_csrf(
    church: Church,
    superuser_client: tuple[Client, User],
) -> None:
    _, user = superuser_client
    person = make_person(church, label="Csrf")
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)

    response = preview_action(client, [person])

    assert response.status_code == 403
    assert Person.objects.filter(pk=person.pk).exists()


def test_cleanup_rolls_back_everything_if_later_hard_delete_fails(
    church: Church,
    superuser_client: tuple[Client, User],
) -> None:
    client, _ = superuser_client
    first = make_person(church, label="RollbackFirst")
    second = make_person(church, label="RollbackSecond")
    preview = preview_action(client, [first, second])
    call_count = 0

    def fail_second_delete(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise RuntimeError("fictional second-delete failure")
        return lifecycle_hard_delete_person(**kwargs)

    with patch("people.admin.hard_delete_person", side_effect=fail_second_delete):
        with pytest.raises(RuntimeError, match="second-delete failure"):
            confirm_action(
                client,
                [first.pk, second.pk],
                run_id=RUN_ID,
                manifest=selection_manifest(preview),
            )

    assert Person.objects.filter(pk__in=(first.pk, second.pk)).count() == 2
    assert not AuditEvent.objects.filter(
        action=AuditEvent.Action.PERSON_HARD_DELETED
    ).exists()
