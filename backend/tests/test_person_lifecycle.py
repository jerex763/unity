from datetime import timedelta

import pytest
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.constants import ACTIVE_CHURCH_SESSION_KEY
from accounts.models import ChurchMembership, User
from audit.models import AuditEvent
from care.models import CareCase, FollowUp, Interaction
from events.models import Event, EventRegistration
from groups.models import Group, GroupMembership
from people.admin import PersonAdmin
from people.models import ConsentRecord, Household, Person, Relationship
from tenancy.models import Church

pytestmark = pytest.mark.django_db


def make_worker(
    church: Church,
    *,
    role: str,
    username: str,
    person: Person | None = None,
) -> User:
    user = User.objects.create_user(username=username)
    ChurchMembership.objects.create(
        user=user,
        church=church,
        person=person,
        role=role,
    )
    return user


def authenticated_client(user: User, church: Church) -> APIClient:
    client = APIClient()
    client.force_login(user)
    session = client.session
    session[ACTIVE_CHURCH_SESSION_KEY] = church.id
    session.save()
    return client


def lifecycle_url(action: str, person: Person) -> str:
    return reverse(f"people:person-{action}", args=(person.id,))


def add_related_history(
    *,
    church: Church,
    person: Person,
    worker: User,
) -> dict[str, object]:
    now = timezone.now()
    group = Group.objects.create(
        church=church,
        name="Fictional Group",
        kind=Group.Kind.SMALL_GROUP,
    )
    group_membership = GroupMembership.objects.create(
        church=church,
        group=group,
        person=person,
        role=GroupMembership.Role.MEMBER,
        joined_at=now.date(),
    )
    event = Event.objects.create(
        church=church,
        title="Fictional Event",
        starts_at=now,
        ends_at=now + timedelta(hours=1),
        created_by=worker,
    )
    registration = EventRegistration.objects.create(
        church=church,
        event=event,
        person=person,
        note="Fictional transport note",
    )
    follow_up = FollowUp.objects.create(
        church=church,
        person=person,
        source=FollowUp.Source.WALK_IN,
        outcome="Fictional follow-up outcome",
    )
    care_case = CareCase.objects.create(
        church=church,
        person=person,
        kind=CareCase.Kind.PASTORAL,
        title="Fictional pastoral title",
        details="Fictional confidential details",
        is_confidential=True,
        created_by=worker,
    )
    interaction = Interaction.objects.create(
        church=church,
        person=person,
        author=worker,
        kind=Interaction.Kind.MEETING,
        summary="Fictional interaction summary",
        care_case=care_case,
    )
    return {
        "group_membership": group_membership,
        "registration": registration,
        "follow_up": follow_up,
        "care_case": care_case,
        "interaction": interaction,
    }


def test_leader_deactivates_person_and_history_is_preserved() -> None:
    church = Church.objects.create(name="Fictional Community Church")
    person = Person.objects.create(church=church, full_name="Fictional Person")
    leader = make_worker(
        church,
        role=ChurchMembership.Role.LEADER,
        username="fictional.lifecycle.leader",
    )
    related = add_related_history(church=church, person=person, worker=leader)
    client = authenticated_client(leader, church)

    response = client.post(lifecycle_url("deactivate", person), format="json")

    person.refresh_from_db()
    assert response.status_code == 200
    assert person.membership_status == Person.MembershipStatus.INACTIVE
    assert person.deactivated_at is not None
    for record in related.values():
        assert type(record).objects.filter(pk=record.pk).exists()
    event = AuditEvent.objects.get(action=AuditEvent.Action.PERSON_DEACTIVATED)
    assert event.actor == leader
    assert event.church == church
    assert event.target_id == str(person.id)


def test_admin_anonymizes_identifiers_and_sensitive_related_text() -> None:
    church = Church.objects.create(name="Fictional Community Church")
    household = Household.objects.create(church=church, name="Fictional Household")
    inviter = Person.objects.create(church=church, full_name="Fictional Inviter")
    person = Person.objects.create(
        church=church,
        full_name="Fictional Identifiable Person",
        preferred_name="Fictional Preferred",
        gender=Person.Gender.FEMALE,
        date_of_birth=timezone.now().date() - timedelta(days=10_000),
        email="fictional.person@example.test",
        phone="+61000000000",
        wechat_id="fictional_wechat",
        photo_url="https://example.test/fictional.jpg",
        home_country="AU",
        suburb="Fictional Suburb",
        occupation="Fictional Occupation",
        university="Fictional University",
        course="Fictional Course",
        interests=["fictional interest"],
        household=household,
        discipleship_stage=Person.DiscipleshipStage.MATURITY,
        faith_background="Fictional faith background",
        invited_by=inviter,
        notes="Fictional private note",
    )
    invitee = Person.objects.create(
        church=church,
        full_name="Fictional Invitee",
        invited_by=person,
    )
    Relationship.objects.create(
        church=church,
        from_person=inviter,
        to_person=person,
        kind=Relationship.Kind.FRIEND,
    )
    admin_user = make_worker(
        church,
        role=ChurchMembership.Role.ADMIN,
        username="fictional.lifecycle.admin",
    )
    subject_user = make_worker(
        church,
        role=ChurchMembership.Role.MEMBER,
        username="fictional.lifecycle.subject",
        person=person,
    )
    related = add_related_history(church=church, person=person, worker=admin_user)
    consent = ConsentRecord.objects.create(
        church=church,
        person=person,
        status=ConsentRecord.Status.GRANTED,
        notice_version="2026-07-draft",
        consented_at=timezone.now(),
        method=ConsentRecord.Method.PAPER_FORM,
        recorded_by=admin_user,
    )
    client = authenticated_client(admin_user, church)

    response = client.post(lifecycle_url("anonymize", person), format="json")

    person.refresh_from_db()
    invitee.refresh_from_db()
    subject_membership = ChurchMembership.objects.get(user=subject_user)
    registration = EventRegistration.objects.get(pk=related["registration"].pk)
    follow_up = FollowUp.objects.get(pk=related["follow_up"].pk)
    care_case = CareCase.objects.get(pk=related["care_case"].pk)
    interaction = Interaction.objects.get(pk=related["interaction"].pk)
    assert response.status_code == 200
    assert person.full_name == f"Anonymized person {person.id}"
    assert person.membership_status == Person.MembershipStatus.INACTIVE
    assert person.anonymized_at is not None
    assert person.deactivated_at is not None
    assert person.preferred_name is None
    assert person.date_of_birth is None
    assert person.email is None
    assert person.phone is None
    assert person.wechat_id is None
    assert person.photo_url is None
    assert person.home_country is None
    assert person.suburb is None
    assert person.occupation is None
    assert person.university is None
    assert person.course is None
    assert person.interests == []
    assert person.household is None
    assert person.discipleship_stage is None
    assert person.faith_background is None
    assert person.invited_by is None
    assert person.notes == ""
    assert invitee.invited_by is None
    assert not Relationship.objects.filter(from_person=person).exists()
    assert registration.note == ""
    assert follow_up.outcome is None
    assert care_case.title == "Anonymized care record"
    assert care_case.details == ""
    assert not care_case.is_confidential
    assert interaction.summary == ""
    assert GroupMembership.objects.filter(pk=related["group_membership"].pk).exists()
    assert ConsentRecord.objects.filter(pk=consent.pk).exists()
    assert not subject_membership.is_active
    assert subject_membership.person is None
    event = AuditEvent.objects.get(action=AuditEvent.Action.PERSON_ANONYMIZED)
    assert event.actor == admin_user
    assert event.metadata == {}
    assert "Fictional Identifiable Person" not in str(event)


def test_only_admin_can_anonymize_or_hard_delete_with_reason() -> None:
    church = Church.objects.create(name="Fictional Community Church")
    leader = make_worker(
        church,
        role=ChurchMembership.Role.LEADER,
        username="fictional.restricted.leader",
    )
    admin_user = make_worker(
        church,
        role=ChurchMembership.Role.ADMIN,
        username="fictional.destructive.admin",
    )
    person = Person.objects.create(church=church, full_name="Fictional Person")
    leader_client = authenticated_client(leader, church)
    admin_client = authenticated_client(admin_user, church)

    denied_anonymize = leader_client.post(
        lifecycle_url("anonymize", person),
        format="json",
    )
    denied_delete = leader_client.delete(
        lifecycle_url("hard-delete", person),
        {"reason": Person.HardDeleteReason.TEST_DATA},
        format="json",
    )
    missing_reason = admin_client.delete(
        lifecycle_url("hard-delete", person),
        {},
        format="json",
    )

    assert denied_anonymize.status_code == 403
    assert denied_delete.status_code == 403
    assert missing_reason.status_code == 400
    assert Person.objects.filter(pk=person.pk).exists()


def test_admin_hard_delete_cascades_history_but_keeps_safe_audit() -> None:
    church = Church.objects.create(name="Fictional Community Church")
    admin_user = make_worker(
        church,
        role=ChurchMembership.Role.ADMIN,
        username="fictional.delete.admin",
    )
    person = Person.objects.create(church=church, full_name="Fictional Delete Person")
    related = add_related_history(church=church, person=person, worker=admin_user)
    first_consent = ConsentRecord.objects.create(
        church=church,
        person=person,
        status=ConsentRecord.Status.GRANTED,
        notice_version="2026-07-draft",
        consented_at=timezone.now() - timedelta(days=1),
        method=ConsentRecord.Method.PAPER_FORM,
        recorded_by=admin_user,
    )
    ConsentRecord.objects.create(
        church=church,
        person=person,
        status=ConsentRecord.Status.DECLINED,
        notice_version="2026-07-draft",
        consented_at=timezone.now(),
        method=ConsentRecord.Method.STAFF_RECORDED,
        recorded_by=admin_user,
        supersedes=first_consent,
    )
    person_id = person.id
    client = authenticated_client(admin_user, church)

    response = client.delete(
        lifecycle_url("hard-delete", person),
        {"reason": Person.HardDeleteReason.TEST_DATA},
        format="json",
    )

    assert response.status_code == 204
    assert not Person.objects.filter(pk=person_id).exists()
    for record in related.values():
        assert not type(record).objects.filter(pk=record.pk).exists()
    assert not ConsentRecord.objects.filter(person_id=person_id).exists()
    event = AuditEvent.objects.get(action=AuditEvent.Action.PERSON_HARD_DELETED)
    assert event.actor == admin_user
    assert event.church == church
    assert event.target_type == "people.person"
    assert event.target_id == str(person_id)
    assert event.metadata == {"delete_reason": Person.HardDeleteReason.TEST_DATA}


def test_direct_hard_delete_and_bulk_delete_are_blocked() -> None:
    church = Church.objects.create(name="Fictional Community Church")
    person = Person.objects.create(church=church, full_name="Fictional Person")

    with pytest.raises(ValidationError, match="explicit reason"):
        person.delete()
    with pytest.raises(ValidationError, match="Routine person deletion"):
        Person.objects.filter(pk=person.pk).delete()


def test_lifecycle_endpoints_cannot_cross_church() -> None:
    current_church = Church.objects.create(name="Fictional Community Church")
    other_church = Church.objects.create(name="Other Fictional Church")
    admin_user = make_worker(
        current_church,
        role=ChurchMembership.Role.ADMIN,
        username="fictional.scoped.admin",
    )
    other_person = Person.objects.create(
        church=other_church,
        full_name="Other Fictional Person",
    )
    client = authenticated_client(admin_user, current_church)

    deactivate = client.post(
        lifecycle_url("deactivate", other_person),
        format="json",
    )
    anonymize = client.post(
        lifecycle_url("anonymize", other_person),
        format="json",
    )
    hard_delete = client.delete(
        lifecycle_url("hard-delete", other_person),
        {"reason": Person.HardDeleteReason.TEST_DATA},
        format="json",
    )

    assert deactivate.status_code == 404
    assert anonymize.status_code == 404
    assert hard_delete.status_code == 404
    assert Person.objects.filter(pk=other_person.pk).exists()


def test_person_admin_defaults_to_deactivation_and_hides_delete() -> None:
    superuser = User.objects.create_superuser(
        username="fictional.lifecycle.superuser",
        password="test-password-only",
    )
    request = RequestFactory().get("/admin/people/person/")
    request.user = superuser
    model_admin = PersonAdmin(Person, admin.site)

    actions = model_admin.get_actions(request)

    assert "deactivate_selected_people" in actions
    assert "delete_selected" not in actions
    assert not model_admin.has_delete_permission(request)
