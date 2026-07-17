import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.constants import ACTIVE_CHURCH_SESSION_KEY
from accounts.models import ChurchMembership, User
from care.models import CareCase, FollowUp, Interaction
from people.models import Person
from tenancy.models import Church

pytestmark = pytest.mark.django_db


def access(church: Church, role: str, suffix: str) -> tuple[APIClient, User]:
    user = User.objects.create_user(username=f"fictional.interaction.{suffix}")
    ChurchMembership.objects.create(user=user, church=church, role=role)
    client = APIClient()
    client.force_login(user)
    session = client.session
    session[ACTIVE_CHURCH_SESSION_KEY] = church.id
    session.save()
    return client, user


def test_pastor_logs_and_reads_follow_up_interaction() -> None:
    church = Church.objects.create(name="Fictional Interaction Church")
    client, pastor = access(church, ChurchMembership.Role.PASTOR, "pastor")
    person = Person.objects.create(church=church, full_name="Interaction Person")
    follow_up = FollowUp.objects.create(
        church=church,
        person=person,
        source=FollowUp.Source.EVENT_VISIT,
    )
    url = reverse("care:follow-up-interactions", args=(follow_up.id,))

    created = client.post(
        url,
        {
            "kind": Interaction.Kind.CALL,
            "summary": "Fictional welcome call",
            "visibility": Interaction.Visibility.PASTORS_ONLY,
        },
        format="json",
    )
    listed = client.get(url)

    assert created.status_code == 201
    assert created.json()["author"] == pastor.username
    assert listed.json()[0]["summary"] == "Fictional welcome call"
    interaction = Interaction.objects.get(pk=created.json()["id"])
    assert interaction.person == person
    assert interaction.follow_up == follow_up


def test_leader_visibility_and_parent_access_are_enforced() -> None:
    church = Church.objects.create(name="Fictional Interaction Access")
    client, leader = access(church, ChurchMembership.Role.LEADER, "leader")
    _, other = access(church, ChurchMembership.Role.LEADER, "other")
    person = Person.objects.create(church=church, full_name="Leader Interaction")
    own = FollowUp.objects.create(
        church=church,
        person=person,
        source=FollowUp.Source.EVENT_VISIT,
        assigned_to=leader,
    )
    hidden = FollowUp.objects.create(
        church=church,
        person=Person.objects.create(church=church, full_name="Hidden Interaction"),
        source=FollowUp.Source.OTHER,
        assigned_to=other,
    )
    Interaction.objects.create(
        church=church,
        person=person,
        author=other,
        follow_up=own,
        kind=Interaction.Kind.MESSAGE,
        summary="Hidden pastoral note",
        visibility=Interaction.Visibility.PASTORS_ONLY,
    )

    own_url = reverse("care:follow-up-interactions", args=(own.id,))
    assert client.get(own_url).json() == []
    denied_write = client.post(
        own_url,
        {
            "kind": Interaction.Kind.CALL,
            "summary": "Must be rejected",
            "visibility": Interaction.Visibility.PASTORS_ONLY,
        },
        format="json",
    )
    assert denied_write.status_code == 400
    assert (
        client.get(
            reverse("care:follow-up-interactions", args=(hidden.id,))
        ).status_code
        == 404
    )


def test_care_case_interaction_uses_same_api_contract() -> None:
    church = Church.objects.create(name="Fictional Care Interaction")
    client, admin = access(church, ChurchMembership.Role.ADMIN, "admin")
    person = Person.objects.create(church=church, full_name="Care Person")
    care_case = CareCase.objects.create(
        church=church,
        person=person,
        kind=CareCase.Kind.PRACTICAL,
        title="Fictional practical care",
        details="Fictional details",
        created_by=admin,
    )
    url = reverse("care:care-case-interactions", args=(care_case.id,))

    response = client.post(
        url,
        {
            "kind": Interaction.Kind.VISIT,
            "summary": "Fictional care visit",
            "visibility": Interaction.Visibility.STAFF,
        },
        format="json",
    )

    assert response.status_code == 201
    assert Interaction.objects.get(pk=response.json()["id"]).care_case == care_case
