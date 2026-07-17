from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.access import (
    can_export_person_data,
    care_cases_visible_to,
    follow_ups_visible_to,
    groups_visible_to,
    people_visible_to,
)
from accounts.constants import ACTIVE_CHURCH_SESSION_KEY
from accounts.models import ChurchMembership, User
from care.models import CareCase, FollowUp
from events.models import Event, EventRegistration
from groups.models import Group, GroupMembership
from people.models import ConsentRecord, Person
from tenancy.models import Church

pytestmark = [pytest.mark.django_db, pytest.mark.permission_matrix]


def make_membership(
    church: Church,
    *,
    role: str,
    suffix: str,
    person: Person | None = None,
) -> ChurchMembership:
    user = User.objects.create_user(username=f"fictional.matrix.{suffix}")
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


@pytest.mark.parametrize(
    ("endpoint", "method", "allowed_roles"),
    (
        (
            "person-consent",
            "get",
            {ChurchMembership.Role.ADMIN, ChurchMembership.Role.PASTOR},
        ),
        (
            "person-deactivate",
            "post",
            {
                ChurchMembership.Role.ADMIN,
                ChurchMembership.Role.PASTOR,
                ChurchMembership.Role.LEADER,
            },
        ),
        ("person-anonymize", "post", {ChurchMembership.Role.ADMIN}),
        ("person-hard-delete", "delete", {ChurchMembership.Role.ADMIN}),
    ),
)
@pytest.mark.parametrize("role", ChurchMembership.Role.values)
def test_every_sensitive_person_endpoint_has_allow_and_deny_coverage(
    endpoint: str,
    method: str,
    allowed_roles: set[str],
    role: str,
) -> None:
    church = Church.objects.create(name=f"Fictional Matrix Church {role} {endpoint}")
    person = Person.objects.create(church=church, full_name="Fictional Subject")
    membership = make_membership(
        church,
        role=role,
        suffix=f"{role}.{endpoint}",
    )
    client = authenticated_client(membership)
    url = reverse(f"people:{endpoint}", args=(person.id,))

    if method == "delete":
        response = client.delete(url, {"reason": "test_data"}, format="json")
    else:
        response = getattr(client, method)(url, format="json")

    if role in allowed_roles:
        assert response.status_code in {200, 204}
    else:
        assert response.status_code == 403


@pytest.mark.parametrize(
    ("endpoint", "method"),
    (
        ("person-consent", "get"),
        ("person-deactivate", "post"),
        ("person-anonymize", "post"),
        ("person-hard-delete", "delete"),
    ),
)
def test_sensitive_object_ids_cannot_cross_church(
    endpoint: str,
    method: str,
) -> None:
    current_church = Church.objects.create(name=f"Current {endpoint}")
    other_church = Church.objects.create(name=f"Other {endpoint}")
    other_person = Person.objects.create(
        church=other_church,
        full_name="Other Church Person",
    )
    admin_membership = make_membership(
        current_church,
        role=ChurchMembership.Role.ADMIN,
        suffix=f"cross.{endpoint}",
    )
    client = authenticated_client(admin_membership)
    url = reverse(f"people:{endpoint}", args=(other_person.id,))

    if method == "delete":
        response = client.delete(url, {"reason": "test_data"}, format="json")
    else:
        response = getattr(client, method)(url, format="json")

    assert response.status_code == 404
    assert Person.objects.filter(pk=other_person.pk).exists()


@pytest.mark.parametrize(
    ("role", "expected_names"),
    (
        (
            ChurchMembership.Role.ADMIN,
            {"Own Person", "Other Person", "Unrelated Person"},
        ),
        (
            ChurchMembership.Role.PASTOR,
            {"Own Person", "Other Person", "Unrelated Person"},
        ),
        (ChurchMembership.Role.LEADER, {"Own Person", "Other Person"}),
        (ChurchMembership.Role.MEMBER, {"Own Person"}),
    ),
)
def test_people_api_policy_is_distinct_from_csv_export(
    role: str,
    expected_names: set[str],
) -> None:
    church = Church.objects.create(name=f"Fictional People Policy {role}")
    own_person = Person.objects.create(church=church, full_name="Own Person")
    other_person = Person.objects.create(church=church, full_name="Other Person")
    Person.objects.create(church=church, full_name="Unrelated Person")
    other_church = Church.objects.create(name=f"Other People Policy {role}")
    Person.objects.create(church=other_church, full_name="Cross Church Person")
    membership = make_membership(
        church,
        role=role,
        suffix=f"people.{role}",
        person=own_person,
    )
    if role == ChurchMembership.Role.LEADER:
        led_group = Group.objects.create(
            church=church,
            name="Led Group",
            kind=Group.Kind.SMALL_GROUP,
        )
        GroupMembership.objects.create(
            church=church,
            group=led_group,
            person=own_person,
            role=GroupMembership.Role.LEADER,
            joined_at=timezone.localdate(),
        )
        GroupMembership.objects.create(
            church=church,
            group=led_group,
            person=other_person,
            role=GroupMembership.Role.MEMBER,
            joined_at=timezone.localdate(),
        )

    visible_names = set(
        people_visible_to(Person.objects.all(), membership).values_list(
            "full_name",
            flat=True,
        )
    )

    assert visible_names == expected_names
    assert can_export_person_data(membership) is (role == ChurchMembership.Role.ADMIN)


@pytest.mark.parametrize(
    ("role", "expected_groups"),
    (
        (ChurchMembership.Role.ADMIN, {"Own Group", "Unrelated Group"}),
        (ChurchMembership.Role.PASTOR, {"Own Group", "Unrelated Group"}),
        (ChurchMembership.Role.LEADER, {"Own Group"}),
        (ChurchMembership.Role.MEMBER, {"Own Group"}),
    ),
)
def test_own_group_and_unrelated_group_matrix(
    role: str,
    expected_groups: set[str],
) -> None:
    church = Church.objects.create(name=f"Fictional Group Policy {role}")
    person = Person.objects.create(church=church, full_name=f"Group Person {role}")
    membership = make_membership(
        church,
        role=role,
        suffix=f"group.{role}",
        person=person,
    )
    own_group = Group.objects.create(
        church=church,
        name="Own Group",
        kind=Group.Kind.SMALL_GROUP,
    )
    Group.objects.create(
        church=church,
        name="Unrelated Group",
        kind=Group.Kind.MINISTRY,
    )
    GroupMembership.objects.create(
        church=church,
        group=own_group,
        person=person,
        role=GroupMembership.Role.LEADER,
        joined_at=timezone.now().date(),
    )
    other_church = Church.objects.create(name=f"Other Group Policy {role}")
    Group.objects.create(
        church=other_church,
        name="Cross Church Group",
        kind=Group.Kind.ACTIVITY,
    )

    visible_names = set(
        groups_visible_to(Group.objects.all(), membership).values_list(
            "name",
            flat=True,
        )
    )

    assert visible_names == expected_groups


@pytest.mark.parametrize(
    ("role", "expected_people"),
    (
        (ChurchMembership.Role.ADMIN, {"Assigned Person", "Unassigned Person"}),
        (ChurchMembership.Role.PASTOR, {"Assigned Person", "Unassigned Person"}),
        (ChurchMembership.Role.LEADER, {"Assigned Person"}),
        (ChurchMembership.Role.MEMBER, set()),
    ),
)
def test_assigned_and_unassigned_follow_up_matrix(
    role: str,
    expected_people: set[str],
) -> None:
    church = Church.objects.create(name=f"Fictional Follow-up Policy {role}")
    membership = make_membership(
        church,
        role=role,
        suffix=f"followup.{role}",
    )
    assigned_person = Person.objects.create(
        church=church,
        full_name="Assigned Person",
    )
    unassigned_person = Person.objects.create(
        church=church,
        full_name="Unassigned Person",
    )
    FollowUp.objects.create(
        church=church,
        person=assigned_person,
        source=FollowUp.Source.WALK_IN,
        assigned_to=membership.user,
    )
    FollowUp.objects.create(
        church=church,
        person=unassigned_person,
        source=FollowUp.Source.FRIEND_INVITE,
    )

    visible_people = set(
        follow_ups_visible_to(FollowUp.objects.all(), membership).values_list(
            "person__full_name",
            flat=True,
        )
    )

    assert visible_people == expected_people


@pytest.mark.parametrize(
    ("role", "expected_titles"),
    (
        (ChurchMembership.Role.ADMIN, {"Public Care", "Secret Care"}),
        (ChurchMembership.Role.PASTOR, {"Public Care", "Secret Care"}),
        (ChurchMembership.Role.LEADER, {"Public Care"}),
        (ChurchMembership.Role.MEMBER, set()),
    ),
)
def test_confidential_records_and_fields_are_absent_from_server_queryset(
    role: str,
    expected_titles: set[str],
) -> None:
    church = Church.objects.create(name=f"Fictional Care Policy {role}")
    membership = make_membership(
        church,
        role=role,
        suffix=f"care.{role}",
    )
    person = Person.objects.create(church=church, full_name="Care Person")
    public_case = CareCase.objects.create(
        church=church,
        person=person,
        kind=CareCase.Kind.PRACTICAL,
        title="Public Care",
        details="Public operational details",
        assigned_to=membership.user,
        created_by=membership.user,
    )
    confidential_case = CareCase.objects.create(
        church=church,
        person=person,
        kind=CareCase.Kind.PASTORAL,
        title="Secret Care",
        details="Secret details must never leak",
        is_confidential=True,
        assigned_to=membership.user,
        created_by=membership.user,
    )
    visible = care_cases_visible_to(CareCase.objects.all(), membership)
    payload = list(visible.values("id", "title", "details"))

    assert {row["title"] for row in payload} == expected_titles
    serialized = str(payload)
    if role not in {ChurchMembership.Role.ADMIN, ChurchMembership.Role.PASTOR}:
        assert confidential_case.id not in {row["id"] for row in payload}
        assert "Secret Care" not in serialized
        assert "Secret details must never leak" not in serialized
    if role == ChurchMembership.Role.MEMBER:
        assert public_case.id not in {row["id"] for row in payload}


def test_matrix_uses_real_domain_relations_without_sensitive_fixture_data() -> None:
    church = Church.objects.create(name="Fictional Matrix Coverage Church")
    admin_membership = make_membership(
        church,
        role=ChurchMembership.Role.ADMIN,
        suffix="domain.coverage",
    )
    person = Person.objects.create(church=church, full_name="Fictional Coverage Person")
    event = Event.objects.create(
        church=church,
        title="Fictional Coverage Event",
        starts_at=timezone.now(),
        ends_at=timezone.now() + timedelta(hours=1),
        created_by=admin_membership.user,
    )
    EventRegistration.objects.create(
        church=church,
        event=event,
        person=person,
    )
    ConsentRecord.objects.create(
        church=church,
        person=person,
        status=ConsentRecord.Status.GRANTED,
        notice_version="fictional-test-only",
        consented_at=timezone.now(),
        method=ConsentRecord.Method.STAFF_RECORDED,
        recorded_by=admin_membership.user,
    )

    assert event.registrations.filter(person=person).exists()
    assert person.consent_records.filter(notice_version="fictional-test-only").exists()
