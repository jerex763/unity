from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.constants import ACTIVE_CHURCH_SESSION_KEY
from accounts.models import ChurchMembership, User
from care.models import FollowUp
from events.models import Event, EventRegistration
from people.models import Person
from tenancy.models import Church

pytestmark = pytest.mark.django_db


def client_with_role(church: Church, role: str) -> tuple[APIClient, User]:
    user = User.objects.create_user(username=f"fictional.walkin.{role}")
    ChurchMembership.objects.create(user=user, church=church, role=role)
    client = APIClient()
    client.force_login(user)
    session = client.session
    session[ACTIVE_CHURCH_SESSION_KEY] = church.id
    session.save()
    return client, user


def test_worker_quick_adds_checked_in_walk_in_atomically() -> None:
    church = Church.objects.create(name="Fictional Walk-in Church")
    client, worker = client_with_role(church, ChurchMembership.Role.LEADER)
    now = timezone.now()
    event = Event.objects.create(
        church=church,
        title="Fictional Door Event",
        starts_at=now + timedelta(minutes=30),
        ends_at=now + timedelta(hours=2),
        capacity=1,
        created_by=worker,
    )

    response = client.post(
        reverse("events:event-walk-in-create", args=(event.id,)),
        {
            "full_name": "  Fictional   Walk In ",
            "preferred_name": "Walk",
            "email": "WALK.IN@example.test",
            "phone": " +61000000999 ",
            "note": "Fictional late pickup",
        },
        format="json",
    )

    assert response.status_code == 201
    person = Person.objects.get(email="walk.in@example.test")
    registration = EventRegistration.objects.get(person=person, event=event)
    assert person.full_name == "Fictional Walk In"
    assert person.membership_status == Person.MembershipStatus.VISITOR
    assert registration.status == EventRegistration.Status.WALK_IN
    assert registration.checked_in_at is not None
    assert registration.checkin_method == EventRegistration.CheckinMethod.MANUAL
    assert "needs_transport" not in response.json()
    assert (
        FollowUp.objects.filter(
            church=church,
            person=person,
            source=FollowUp.Source.EVENT_VISIT,
        ).count()
        == 1
    )


def test_walk_in_reuses_same_church_contact_without_duplicate_person() -> None:
    church = Church.objects.create(name="Fictional Existing Walk-in")
    client, worker = client_with_role(church, ChurchMembership.Role.PASTOR)
    person = Person.objects.create(
        church=church,
        full_name="Existing Contact",
        email="existing@example.test",
    )
    now = timezone.now()
    event = Event.objects.create(
        church=church,
        title="Fictional Existing Event",
        starts_at=now - timedelta(minutes=15),
        ends_at=now + timedelta(hours=1),
        created_by=worker,
    )

    response = client.post(
        reverse("events:event-walk-in-create", args=(event.id,)),
        {
            "full_name": "Different Submitted Name",
            "email": "EXISTING@example.test",
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["person"]["id"] == person.id
    assert Person.objects.for_church(church).count() == 1


def test_new_visitor_path_never_matches_by_name() -> None:
    church = Church.objects.create(name="Fictional No Name Matching")
    client, worker = client_with_role(church, ChurchMembership.Role.LEADER)
    existing = Person.objects.create(
        church=church,
        full_name="Duplicate Display Name",
        email="existing.name@example.test",
    )
    now = timezone.now()
    event = Event.objects.create(
        church=church,
        title="Fictional Duplicate Name Event",
        starts_at=now,
        ends_at=now + timedelta(hours=1),
        created_by=worker,
    )

    response = client.post(
        reverse("events:event-walk-in-create", args=(event.id,)),
        {
            "full_name": "Duplicate Display Name",
            "email": "new.name@example.test",
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["person"]["id"] != existing.id
    assert (
        Person.objects.for_church(church)
        .filter(full_name="Duplicate Display Name")
        .count()
        == 2
    )


def test_walk_in_requires_a_contact_method_without_creating_records() -> None:
    church = Church.objects.create(name="Fictional Contact Required")
    client, worker = client_with_role(church, ChurchMembership.Role.LEADER)
    now = timezone.now()
    event = Event.objects.create(
        church=church,
        title="Fictional Contact Event",
        starts_at=now,
        ends_at=now + timedelta(hours=1),
        created_by=worker,
    )

    response = client.post(
        reverse("events:event-walk-in-create", args=(event.id,)),
        {
            "full_name": "Contactless Walk In",
            "email": " ",
            "phone": " ",
            "wechat_id": " ",
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["contact"] == [
        "Provide at least one contact method: email, phone, or WeChat ID."
    ]
    assert not Person.objects.for_church(church).exists()
    assert not EventRegistration.objects.filter(event=event).exists()


@pytest.mark.parametrize(
    ("contact_field", "contact_value", "model_value"),
    (
        ("phone", " +61000000123 ", "+61000000123"),
        ("wechat_id", " fictional_wechat ", "fictional_wechat"),
    ),
)
def test_walk_in_accepts_each_non_email_contact_method(
    contact_field: str,
    contact_value: str,
    model_value: str,
) -> None:
    church = Church.objects.create(name=f"Fictional Contact {contact_field}")
    client, worker = client_with_role(church, ChurchMembership.Role.LEADER)
    now = timezone.now()
    event = Event.objects.create(
        church=church,
        title=f"Fictional {contact_field} Event",
        starts_at=now,
        ends_at=now + timedelta(hours=1),
        created_by=worker,
    )

    response = client.post(
        reverse("events:event-walk-in-create", args=(event.id,)),
        {
            "full_name": f"Fictional {contact_field} Person",
            contact_field: contact_value,
        },
        format="json",
    )

    assert response.status_code == 201
    person = Person.objects.get(pk=response.json()["person"]["id"])
    assert getattr(person, contact_field) == model_value
    assert EventRegistration.objects.filter(
        event=event,
        person=person,
        status=EventRegistration.Status.WALK_IN,
    ).exists()


def test_walk_in_reuses_wechat_id_only_within_active_church() -> None:
    church = Church.objects.create(name="Fictional WeChat Church")
    other_church = Church.objects.create(name="Fictional Other WeChat Church")
    client, worker = client_with_role(church, ChurchMembership.Role.PASTOR)
    current_person = Person.objects.create(
        church=church,
        full_name="Current WeChat Contact",
        wechat_id="shared_wechat",
    )
    other_person = Person.objects.create(
        church=other_church,
        full_name="Other WeChat Contact",
        wechat_id="shared_wechat",
    )
    now = timezone.now()
    event = Event.objects.create(
        church=church,
        title="Fictional WeChat Event",
        starts_at=now,
        ends_at=now + timedelta(hours=1),
        created_by=worker,
    )

    response = client.post(
        reverse("events:event-walk-in-create", args=(event.id,)),
        {
            "full_name": "Submitted WeChat Name",
            "wechat_id": " shared_wechat ",
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["person"]["id"] == current_person.id
    assert Person.objects.for_church(church).count() == 1
    assert Person.objects.for_church(other_church).get() == other_person
    current_person.refresh_from_db()
    assert current_person.full_name == "Current WeChat Contact"


def test_walk_in_rejects_contacts_that_match_different_people() -> None:
    church = Church.objects.create(name="Fictional Contact Priority")
    client, worker = client_with_role(church, ChurchMembership.Role.PASTOR)
    email_person = Person.objects.create(
        church=church,
        full_name="Email Match",
        email="priority@example.test",
    )
    phone_person = Person.objects.create(
        church=church,
        full_name="Phone Match",
        phone="+61000000456",
    )
    Person.objects.create(
        church=church,
        full_name="WeChat Match",
        wechat_id="priority_wechat",
    )
    now = timezone.now()
    email_event = Event.objects.create(
        church=church,
        title="Fictional Email Priority",
        starts_at=now,
        ends_at=now + timedelta(hours=1),
        created_by=worker,
    )
    phone_event = Event.objects.create(
        church=church,
        title="Fictional Phone Priority",
        starts_at=now,
        ends_at=now + timedelta(hours=1),
        created_by=worker,
    )

    email_response = client.post(
        reverse("events:event-walk-in-create", args=(email_event.id,)),
        {
            "full_name": "Submitted Priority",
            "email": "PRIORITY@example.test",
            "phone": "+61000000456",
            "wechat_id": "priority_wechat",
        },
        format="json",
    )
    phone_response = client.post(
        reverse("events:event-walk-in-create", args=(phone_event.id,)),
        {
            "full_name": "Submitted Priority",
            "phone": "+61000000456",
            "wechat_id": "priority_wechat",
        },
        format="json",
    )

    assert email_response.status_code == 400
    assert phone_response.status_code == 400
    assert (
        EventRegistration.objects.filter(event__in=(email_event, phone_event)).count()
        == 0
    )
    assert Person.objects.filter(pk__in=(email_person.pk, phone_person.pk)).count() == 2


@pytest.mark.parametrize(
    ("contact_field", "contact_value", "lifecycle_field"),
    (
        ("email", "inactive.email@example.test", "deactivated_at"),
        ("phone", "+61 400 777 111", "anonymized_at"),
        ("wechat_id", "inactive_wechat", "deactivated_at"),
    ),
)
def test_new_visitor_contact_cannot_reuse_inactive_lifecycle_person(
    contact_field: str,
    contact_value: str,
    lifecycle_field: str,
) -> None:
    church = Church.objects.create(name=f"Fictional Inactive {contact_field}")
    client, worker = client_with_role(church, ChurchMembership.Role.LEADER)
    person = Person.objects.create(
        church=church,
        full_name="Inactive Contact Person",
        **{contact_field: contact_value, lifecycle_field: timezone.now()},
    )
    original_profile = (
        person.full_name,
        person.email,
        person.phone,
        person.wechat_id,
        person.deactivated_at,
        person.anonymized_at,
    )
    now = timezone.now()
    event = Event.objects.create(
        church=church,
        title=f"Fictional Inactive {contact_field} Event",
        starts_at=now,
        ends_at=now + timedelta(hours=1),
        created_by=worker,
    )

    response = client.post(
        reverse("events:event-walk-in-create", args=(event.id,)),
        {"full_name": "Submitted New Visitor", contact_field: contact_value},
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "This contact needs Pastor or Admin review before check-in."
    )
    assert Person.objects.for_church(church).count() == 1
    assert not EventRegistration.objects.filter(event=event).exists()
    assert not FollowUp.objects.filter(church=church).exists()
    person.refresh_from_db()
    assert (
        person.full_name,
        person.email,
        person.phone,
        person.wechat_id,
        person.deactivated_at,
        person.anonymized_at,
    ) == original_profile


def test_new_visitor_mixed_active_and_inactive_contact_match_requires_review() -> None:
    church = Church.objects.create(name="Fictional Mixed Lifecycle Contact")
    client, worker = client_with_role(church, ChurchMembership.Role.PASTOR)
    active_person = Person.objects.create(
        church=church,
        full_name="Active Email Person",
        email="active.mixed@example.test",
    )
    inactive_person = Person.objects.create(
        church=church,
        full_name="Inactive Phone Person",
        phone="+61 400 888 222",
        deactivated_at=timezone.now(),
    )
    now = timezone.now()
    event = Event.objects.create(
        church=church,
        title="Fictional Mixed Contact Event",
        starts_at=now,
        ends_at=now + timedelta(hours=1),
        created_by=worker,
    )

    response = client.post(
        reverse("events:event-walk-in-create", args=(event.id,)),
        {
            "full_name": "Submitted Mixed Person",
            "email": "ACTIVE.MIXED@example.test",
            "phone": "+61 400 888 222",
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "This contact needs Pastor or Admin review before check-in."
    )
    assert Person.objects.for_church(church).count() == 2
    assert not EventRegistration.objects.filter(event=event).exists()
    active_person.refresh_from_db()
    inactive_person.refresh_from_db()
    assert active_person.full_name == "Active Email Person"
    assert active_person.phone is None
    assert inactive_person.full_name == "Inactive Phone Person"
    assert inactive_person.email is None


def test_member_cannot_quick_add_walk_in_and_cross_church_event_is_hidden() -> None:
    church = Church.objects.create(name="Fictional Walk-in Access")
    other_church = Church.objects.create(name="Fictional Walk-in Other")
    member_client, member_user = client_with_role(
        church,
        ChurchMembership.Role.MEMBER,
    )
    leader_client, _ = client_with_role(church, ChurchMembership.Role.LEADER)
    now = timezone.now()
    other_event = Event.objects.create(
        church=other_church,
        title="Hidden Walk-in Event",
        starts_at=now,
        ends_at=now + timedelta(hours=1),
        created_by=member_user,
    )
    payload = {"full_name": "Forbidden Walk In"}
    url = reverse("events:event-walk-in-create", args=(other_event.id,))

    assert member_client.post(url, payload, format="json").status_code == 403
    assert leader_client.post(url, payload, format="json").status_code == 404
    assert not Person.objects.filter(full_name="Forbidden Walk In").exists()


def test_walk_in_rejects_ended_event_without_creating_person() -> None:
    church = Church.objects.create(name="Fictional Ended Walk-in")
    client, worker = client_with_role(church, ChurchMembership.Role.ADMIN)
    now = timezone.now()
    event = Event.objects.create(
        church=church,
        title="Ended Walk-in Event",
        starts_at=now - timedelta(hours=2),
        ends_at=now - timedelta(hours=1),
        created_by=worker,
    )

    response = client.post(
        reverse("events:event-walk-in-create", args=(event.id,)),
        {"full_name": "Too Late Person"},
        format="json",
    )

    assert response.status_code == 400
    assert not Person.objects.filter(full_name="Too Late Person").exists()
