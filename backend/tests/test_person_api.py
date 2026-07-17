from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.constants import ACTIVE_CHURCH_SESSION_KEY
from accounts.models import ChurchMembership, User
from audit.models import AuditEvent
from groups.models import Group, GroupMembership
from people.models import Household, Person
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
    assert "faith_background" not in list_response.json()[0]
    assert "discipleship_stage" not in list_response.json()[0]
    assert create_response.status_code == 201
    assert create_response.json()["full_name"] == "New Fictional Person"
    assert create_response.json()["email"] == "new.person@example.test"
    assert create_response.json()["phone"] == "+61000000000"
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
