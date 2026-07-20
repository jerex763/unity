from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.constants import ACTIVE_CHURCH_SESSION_KEY
from accounts.models import ChurchMembership, User
from audit.models import AuditEvent
from care.models import FollowUp
from events.models import Event, EventRegistration
from groups.models import Group, GroupMembership
from people.models import Household, Person, Relationship
from tenancy.models import Church

pytestmark = pytest.mark.django_db


def make_membership(
    church: Church,
    *,
    role: str,
    suffix: str,
    person: Person | None = None,
) -> ChurchMembership:
    user = User.objects.create_user(username=f"fictional.person.api.{suffix}")
    return ChurchMembership.objects.create(
        user=user,
        church=church,
        person=person,
        role=role,
    )


def authenticated_client(membership: ChurchMembership) -> APIClient:
    client = APIClient()
    client.force_login(membership.user)
    session = client.session
    session[ACTIVE_CHURCH_SESSION_KEY] = membership.church_id
    session.save()
    return client


def test_leader_can_list_create_and_update_without_sensitive_fields() -> None:
    church = Church.objects.create(name="Fictional Leader Directory")
    existing = Person.objects.create(
        church=church,
        full_name="Existing Person",
        faith_background="Must not be exposed",
        discipleship_stage=Person.DiscipleshipStage.MATURITY,
    )
    leader_person = Person.objects.create(
        church=church,
        full_name="Fictional Group Leader",
    )
    membership = make_membership(
        church,
        role=ChurchMembership.Role.LEADER,
        suffix="leader",
        person=leader_person,
    )
    group = Group.objects.create(
        church=church,
        name="Fictional Led Group",
        kind=Group.Kind.SMALL_GROUP,
    )
    GroupMembership.objects.create(
        church=church,
        group=group,
        person=leader_person,
        role=GroupMembership.Role.LEADER,
        joined_at=timezone.localdate(),
    )
    GroupMembership.objects.create(
        church=church,
        group=group,
        person=existing,
        role=GroupMembership.Role.MEMBER,
        joined_at=timezone.localdate(),
    )
    client = authenticated_client(membership)

    list_response = client.get(reverse("people:person-list"))
    create_response = client.post(
        reverse("people:person-list"),
        {
            "full_name": "  New   Fictional Person  ",
            "email": "NEW.PERSON@EXAMPLE.TEST",
            "phone": "  +61000000000 ",
            "wechat_id": "  fictional_wechat  ",
            "home_country": "au",
            "interests": ["Community", "Music"],
        },
        format="json",
    )
    detail_url = reverse("people:person-detail", args=(existing.id,))
    update_response = client.patch(
        detail_url,
        {"preferred_name": "New"},
        format="json",
    )

    assert list_response.status_code == 200
    assert len(list_response.json()) == 2
    assert list_response.json()[0]["id"] == existing.id
    assert list_response.json()[0]["groups"] == [
        {
            "id": group.id,
            "name": "Fictional Led Group",
            "role": GroupMembership.Role.MEMBER,
            "joined_at": timezone.localdate().isoformat(),
        }
    ]
    assert "faith_background" not in list_response.json()[0]
    assert "discipleship_stage" not in list_response.json()[0]
    assert create_response.status_code == 201
    assert create_response.json()["full_name"] == "New Fictional Person"
    assert create_response.json()["email"] == "new.person@example.test"
    assert create_response.json()["phone"] == "+61000000000"
    assert create_response.json()["wechat_id"] == "fictional_wechat"
    assert create_response.json()["home_country"] == "AU"
    assert update_response.status_code == 200
    assert update_response.json()["preferred_name"] == "New"
    assert "faith_background" not in update_response.json()
    created = Person.objects.get(pk=create_response.json()["id"])
    assert created.church == church
    assert AuditEvent.objects.filter(
        action=AuditEvent.Action.PERSON_CREATED,
        actor=membership.user,
        target_id=str(created.id),
    ).exists()


def test_pastor_can_read_and_set_sensitive_fields() -> None:
    church = Church.objects.create(name="Fictional Pastor Directory")
    membership = make_membership(
        church,
        role=ChurchMembership.Role.PASTOR,
        suffix="pastor",
    )
    client = authenticated_client(membership)

    response = client.post(
        reverse("people:person-list"),
        {
            "full_name": "Fictional Sensitive Person",
            "faith_background": "Fictional background",
            "discipleship_stage": Person.DiscipleshipStage.EVANGELISM,
        },
        format="json",
    )
    detail = client.get(reverse("people:person-detail", args=(response.json()["id"],)))

    assert response.status_code == 201
    assert response.json()["faith_background"] == "Fictional background"
    assert response.json()["discipleship_stage"] == Person.DiscipleshipStage.EVANGELISM
    assert detail.json()["faith_background"] == "Fictional background"


@pytest.mark.parametrize(
    "role",
    (ChurchMembership.Role.LEADER, ChurchMembership.Role.MEMBER),
)
def test_unauthorized_roles_cannot_write_sensitive_fields(role: str) -> None:
    church = Church.objects.create(name=f"Fictional Sensitive Denial {role}")
    person = Person.objects.create(church=church, full_name="Fictional Subject")
    membership = make_membership(
        church,
        role=role,
        suffix=f"sensitive.{role}",
        person=person,
    )
    if role == ChurchMembership.Role.LEADER:
        group = Group.objects.create(
            church=church,
            name="Fictional Sensitive Group",
            kind=Group.Kind.SMALL_GROUP,
        )
        GroupMembership.objects.create(
            church=church,
            group=group,
            person=person,
            role=GroupMembership.Role.LEADER,
            joined_at=timezone.localdate(),
        )
    client = authenticated_client(membership)

    response = client.patch(
        reverse("people:person-detail", args=(person.id,)),
        {
            "faith_background": "Must be rejected",
            "discipleship_stage": Person.DiscipleshipStage.LEADERSHIP,
        },
        format="json",
    )

    expected_status = 403 if role == ChurchMembership.Role.MEMBER else 400
    assert response.status_code == expected_status
    if role == ChurchMembership.Role.LEADER:
        assert set(response.json()) == {"faith_background", "discipleship_stage"}
    person.refresh_from_db()
    assert person.faith_background is None
    assert person.discipleship_stage is None


def test_member_can_read_only_their_linked_person_and_cannot_write() -> None:
    church = Church.objects.create(name="Fictional Member Directory")
    own_person = Person.objects.create(
        church=church,
        full_name="Own Person",
        notes="Internal staff note",
    )
    unrelated = Person.objects.create(church=church, full_name="Unrelated Person")
    membership = make_membership(
        church,
        role=ChurchMembership.Role.MEMBER,
        suffix="member",
        person=own_person,
    )
    client = authenticated_client(membership)

    list_response = client.get(reverse("people:person-list"))
    own_response = client.get(reverse("people:person-detail", args=(own_person.id,)))
    unrelated_response = client.get(
        reverse("people:person-detail", args=(unrelated.id,))
    )
    create_response = client.post(
        reverse("people:person-list"),
        {"full_name": "Forbidden Person"},
        format="json",
    )
    update_response = client.patch(
        reverse("people:person-detail", args=(own_person.id,)),
        {"preferred_name": "Forbidden"},
        format="json",
    )

    assert [row["id"] for row in list_response.json()] == [own_person.id]
    assert own_response.status_code == 200
    assert "notes" not in own_response.json()
    assert unrelated_response.status_code == 404
    assert create_response.status_code == 403
    assert update_response.status_code == 403


def test_person_api_never_crosses_active_church() -> None:
    current_church = Church.objects.create(name="Fictional Current Directory")
    other_church = Church.objects.create(name="Fictional Other Directory")
    current_person = Person.objects.create(
        church=current_church,
        full_name="Current Person",
    )
    other_person = Person.objects.create(
        church=other_church,
        full_name="Other Person",
    )
    membership = make_membership(
        current_church,
        role=ChurchMembership.Role.ADMIN,
        suffix="cross",
    )
    client = authenticated_client(membership)

    list_response = client.get(reverse("people:person-list"))
    get_response = client.get(reverse("people:person-detail", args=(other_person.id,)))
    patch_response = client.patch(
        reverse("people:person-detail", args=(other_person.id,)),
        {"full_name": "Crossed Boundary"},
        format="json",
    )

    assert [row["id"] for row in list_response.json()] == [current_person.id]
    assert get_response.status_code == 404
    assert patch_response.status_code == 404
    other_person.refresh_from_db()
    assert other_person.full_name == "Other Person"


def test_person_validation_rejects_duplicates_future_dates_and_cross_church_links() -> (
    None
):
    church = Church.objects.create(name="Fictional Validation Directory")
    other_church = Church.objects.create(name="Fictional Validation Other")
    Person.objects.create(
        church=church,
        full_name="Existing Person",
        email="duplicate@example.test",
    )
    other_household = Household.objects.create(
        church=other_church,
        name="Other Household",
    )
    other_inviter = Person.objects.create(
        church=other_church,
        full_name="Other Inviter",
    )
    membership = make_membership(
        church,
        role=ChurchMembership.Role.ADMIN,
        suffix="validation",
    )
    client = authenticated_client(membership)

    duplicate = client.post(
        reverse("people:person-list"),
        {
            "full_name": "Duplicate Person",
            "email": "DUPLICATE@example.test",
        },
        format="json",
    )
    invalid = client.post(
        reverse("people:person-list"),
        {
            "full_name": "Invalid Linked Person",
            "date_of_birth": (timezone.localdate() + timedelta(days=1)).isoformat(),
            "household": other_household.id,
            "invited_by": other_inviter.id,
            "interests": ["Music", "Music"],
        },
        format="json",
    )

    assert duplicate.status_code == 400
    assert "email" in duplicate.json()
    assert invalid.status_code == 400
    assert set(invalid.json()) == {
        "date_of_birth",
        "household",
        "interests",
        "invited_by",
    }


def test_routine_delete_is_not_an_api_method() -> None:
    church = Church.objects.create(name="Fictional No Delete Directory")
    person = Person.objects.create(church=church, full_name="Preserved Person")
    membership = make_membership(
        church,
        role=ChurchMembership.Role.ADMIN,
        suffix="no.delete",
    )
    client = authenticated_client(membership)

    response = client.delete(reverse("people:person-detail", args=(person.id,)))

    assert response.status_code == 405
    assert Person.objects.filter(pk=person.pk).exists()


def test_admin_can_manage_canonical_relationships_and_inviter_links() -> None:
    church = Church.objects.create(name="Fictional Relationship Directory")
    inviter = Person.objects.create(church=church, full_name="Fictional Inviter")
    person = Person.objects.create(
        church=church,
        full_name="Fictional Relationship Subject",
        invited_by=inviter,
    )
    friend = Person.objects.create(church=church, full_name="Fictional Friend")
    admin = make_membership(
        church,
        role=ChurchMembership.Role.ADMIN,
        suffix="relationships.admin",
    )
    client = authenticated_client(admin)
    list_url = reverse("people:person-relationship-list", args=(person.id,))

    create_response = client.post(
        list_url,
        {"person": friend.id, "kind": Relationship.Kind.FRIEND},
        format="json",
    )
    detail_response = client.get(reverse("people:person-detail", args=(person.id,)))

    assert create_response.status_code == 201
    relationship = Relationship.objects.get(pk=create_response.json()["id"])
    assert relationship.from_person_id == min(person.id, friend.id)
    assert relationship.to_person_id == max(person.id, friend.id)
    assert create_response.json()["person"]["id"] == friend.id
    assert detail_response.json()["inviter"]["id"] == inviter.id
    assert detail_response.json()["relationships"] == [create_response.json()]
    assert client.get(reverse("people:person-detail", args=(inviter.id,))).json()[
        "invitees"
    ] == [
        {
            "id": person.id,
            "full_name": person.full_name,
            "preferred_name": None,
            "photo_url": None,
        }
    ]

    delete_response = client.delete(
        reverse(
            "people:person-relationship-detail",
            args=(person.id, relationship.id),
        )
    )

    assert delete_response.status_code == 204
    assert not Relationship.objects.filter(pk=relationship.pk).exists()


def test_relationship_api_rejects_self_duplicates_and_invisible_people() -> None:
    church = Church.objects.create(name="Fictional Relationship Validation")
    other_church = Church.objects.create(name="Fictional Relationship Other")
    person = Person.objects.create(church=church, full_name="Fictional Subject")
    friend = Person.objects.create(church=church, full_name="Fictional Friend")
    outsider = Person.objects.create(
        church=other_church,
        full_name="Fictional Outsider",
    )
    admin = make_membership(
        church,
        role=ChurchMembership.Role.ADMIN,
        suffix="relationships.validation",
    )
    client = authenticated_client(admin)
    url = reverse("people:person-relationship-list", args=(person.id,))

    first = client.post(
        url,
        {"person": friend.id, "kind": Relationship.Kind.FAMILY},
        format="json",
    )
    duplicate = client.post(
        url,
        {"person": friend.id, "kind": Relationship.Kind.FAMILY},
        format="json",
    )
    self_link = client.post(
        url,
        {"person": person.id, "kind": Relationship.Kind.FRIEND},
        format="json",
    )
    cross_church = client.post(
        url,
        {"person": outsider.id, "kind": Relationship.Kind.FRIEND},
        format="json",
    )

    assert first.status_code == 201
    assert duplicate.status_code == 400
    assert self_link.status_code == 400
    assert cross_church.status_code == 400


def test_member_relationship_view_does_not_disclose_invisible_people() -> None:
    church = Church.objects.create(name="Fictional Relationship Privacy")
    friend = Person.objects.create(church=church, full_name="Fictional Hidden Friend")
    person = Person.objects.create(
        church=church,
        full_name="Fictional Own Person",
        invited_by=friend,
    )
    Relationship.objects.create(
        church=church,
        from_person=person,
        to_person=friend,
        kind=Relationship.Kind.FRIEND,
    )
    member = make_membership(
        church,
        role=ChurchMembership.Role.MEMBER,
        suffix="relationships.member",
        person=person,
    )
    client = authenticated_client(member)
    url = reverse("people:person-relationship-list", args=(person.id,))

    detail = client.get(reverse("people:person-detail", args=(person.id,)))
    list_response = client.get(url)
    create_response = client.post(
        url,
        {"person": friend.id, "kind": Relationship.Kind.FAMILY},
        format="json",
    )

    assert detail.status_code == 200
    assert detail.json()["invited_by"] is None
    assert detail.json()["inviter"] is None
    assert detail.json()["relationships"] == []
    assert list_response.json() == []
    assert create_response.status_code == 403


def add_profile_history(
    *,
    church: Church,
    person: Person,
    worker: User,
    assigned_worker: User,
) -> tuple[Event, Event, FollowUp, FollowUp]:
    now = timezone.now()
    attended_event = Event.objects.create(
        church=church,
        title="Fictional Attended Gathering",
        starts_at=now - timedelta(days=7),
        ends_at=now - timedelta(days=7) + timedelta(hours=2),
        location="Fictional Hall",
        created_by=worker,
    )
    registered_event = Event.objects.create(
        church=church,
        title="Fictional Future Gathering",
        starts_at=now + timedelta(days=7),
        ends_at=now + timedelta(days=7, hours=2),
        created_by=worker,
    )
    EventRegistration.objects.create(
        church=church,
        event=attended_event,
        person=person,
        checked_in_at=now - timedelta(days=7),
        checkin_method=EventRegistration.CheckinMethod.MANUAL,
    )
    EventRegistration.objects.create(
        church=church,
        event=registered_event,
        person=person,
    )
    assigned = FollowUp.objects.create(
        church=church,
        person=person,
        source=FollowUp.Source.EVENT_VISIT,
        status=FollowUp.Status.CLOSED,
        assigned_to=assigned_worker,
        closed_at=now,
        outcome="Fictional connected outcome",
    )
    historical = FollowUp.objects.create(
        church=church,
        person=person,
        source=FollowUp.Source.FRIEND_INVITE,
        status=FollowUp.Status.CLOSED,
        assigned_to=worker,
        closed_at=now - timedelta(days=30),
        outcome="Fictional historical outcome",
    )
    return attended_event, registered_event, assigned, historical


def test_pastor_profile_includes_attendance_and_full_follow_up_history() -> None:
    church = Church.objects.create(name="Fictional Pastor Profile")
    pastor = make_membership(
        church,
        role=ChurchMembership.Role.PASTOR,
        suffix="profile.pastor",
    )
    other_worker = make_membership(
        church,
        role=ChurchMembership.Role.LEADER,
        suffix="profile.other",
    )
    person = Person.objects.create(church=church, full_name="Profile Person")
    attended, registered, assigned, historical = add_profile_history(
        church=church,
        person=person,
        worker=pastor.user,
        assigned_worker=other_worker.user,
    )
    client = authenticated_client(pastor)

    response = client.get(reverse("people:person-detail", args=(person.id,)))

    assert response.status_code == 200
    assert [event["id"] for event in response.json()["events_attended"]] == [
        attended.id
    ]
    assert registered.id not in {
        event["id"] for event in response.json()["events_attended"]
    }
    assert {item["id"] for item in response.json()["follow_up_history"]} == {
        assigned.id,
        historical.id,
    }


def test_leader_profile_only_includes_follow_ups_assigned_to_self() -> None:
    church = Church.objects.create(name="Fictional Leader Profile")
    person = Person.objects.create(church=church, full_name="Profile Person")
    leader_person = Person.objects.create(church=church, full_name="Leader Person")
    leader = make_membership(
        church,
        role=ChurchMembership.Role.LEADER,
        suffix="profile.leader",
        person=leader_person,
    )
    other_worker = make_membership(
        church,
        role=ChurchMembership.Role.PASTOR,
        suffix="profile.pastor.other",
    )
    group = Group.objects.create(
        church=church,
        name="Fictional Profile Group",
        kind=Group.Kind.SMALL_GROUP,
    )
    for group_person, role in (
        (leader_person, GroupMembership.Role.LEADER),
        (person, GroupMembership.Role.MEMBER),
    ):
        GroupMembership.objects.create(
            church=church,
            group=group,
            person=group_person,
            role=role,
            joined_at=timezone.localdate(),
        )
    _, _, assigned, historical = add_profile_history(
        church=church,
        person=person,
        worker=other_worker.user,
        assigned_worker=leader.user,
    )
    client = authenticated_client(leader)

    response = client.get(reverse("people:person-detail", args=(person.id,)))

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["follow_up_history"]] == [
        assigned.id
    ]
    assert historical.id not in {
        item["id"] for item in response.json()["follow_up_history"]
    }


def test_member_profile_omits_follow_up_history_and_staff_fields() -> None:
    church = Church.objects.create(name="Fictional Member Profile")
    person = Person.objects.create(
        church=church,
        full_name="Own Profile Person",
        notes="Internal staff note",
    )
    member = make_membership(
        church,
        role=ChurchMembership.Role.MEMBER,
        suffix="profile.member",
        person=person,
    )
    add_profile_history(
        church=church,
        person=person,
        worker=member.user,
        assigned_worker=member.user,
    )
    client = authenticated_client(member)

    response = client.get(reverse("people:person-detail", args=(person.id,)))

    assert response.status_code == 200
    assert len(response.json()["events_attended"]) == 1
    assert "follow_up_history" not in response.json()
    assert "notes" not in response.json()
