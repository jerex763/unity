import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import ChurchMembership, User
from accounts.permissions import Capability, has_capability, has_church_role
from accounts.views import ACTIVE_CHURCH_SESSION_KEY
from tenancy.models import Church

pytestmark = pytest.mark.django_db


@pytest.fixture
def church() -> Church:
    return Church.objects.create(name="Harbour Community Church")


@pytest.fixture
def user() -> User:
    return User.objects.create_user(
        username="fictional.login",
        password="test-password-only",
        first_name="Fictional",
        last_name="Worker",
    )


def add_membership(
    user: User,
    church: Church,
    role: str = ChurchMembership.Role.LEADER,
    *,
    is_active: bool = True,
) -> ChurchMembership:
    return ChurchMembership.objects.create(
        user=user,
        church=church,
        role=role,
        is_active=is_active,
    )


def test_login_selects_only_membership_and_exposes_safe_session_payload(
    church: Church,
    user: User,
) -> None:
    membership = add_membership(user, church)
    client = APIClient()

    response = client.post(
        reverse("accounts:login"),
        {"username": user.username, "password": "test-password-only"},
        format="json",
    )

    assert response.status_code == 200
    assert response.json() == {
        "user": {
            "id": user.id,
            "username": "fictional.login",
            "first_name": "Fictional",
            "last_name": "Worker",
        },
        "membership": {
            "church_id": church.id,
            "church_name": church.name,
            "role": membership.role,
        },
    }
    assert "password" not in response.json()["user"]
    assert client.session[ACTIVE_CHURCH_SESSION_KEY] == church.id
    assert "csrftoken" in response.cookies

    session_response = client.get(reverse("accounts:session"))
    assert session_response.status_code == 200
    assert session_response.json() == response.json()


def test_login_requires_church_for_multiple_memberships(user: User) -> None:
    first_church = Church.objects.create(name="Harbour Community Church")
    second_church = Church.objects.create(name="Hills Community Church")
    add_membership(user, first_church, ChurchMembership.Role.LEADER)
    add_membership(user, second_church, ChurchMembership.Role.MEMBER)
    client = APIClient()
    credentials = {
        "username": user.username,
        "password": "test-password-only",
    }

    missing_church = client.post(
        reverse("accounts:login"),
        credentials,
        format="json",
    )
    selected_church = client.post(
        reverse("accounts:login"),
        {**credentials, "church_id": second_church.id},
        format="json",
    )

    assert missing_church.status_code == 400
    assert "church_id" in missing_church.json()
    assert selected_church.status_code == 200
    assert selected_church.json()["membership"]["church_id"] == second_church.id
    assert selected_church.json()["membership"]["role"] == ChurchMembership.Role.MEMBER


def test_login_rejects_invalid_credentials_or_membership(
    church: Church,
    user: User,
) -> None:
    client = APIClient()

    invalid_password = client.post(
        reverse("accounts:login"),
        {"username": user.username, "password": "wrong-password"},
        format="json",
    )
    no_membership = client.post(
        reverse("accounts:login"),
        {"username": user.username, "password": "test-password-only"},
        format="json",
    )
    add_membership(user, church, is_active=False)
    inactive_membership = client.post(
        reverse("accounts:login"),
        {
            "username": user.username,
            "password": "test-password-only",
            "church_id": church.id,
        },
        format="json",
    )

    assert invalid_password.status_code == 401
    assert no_membership.status_code == 403
    assert inactive_membership.status_code == 403


def test_logout_requires_csrf_and_clears_session(church: Church, user: User) -> None:
    add_membership(user, church)
    client = APIClient(enforce_csrf_checks=True)
    login_response = client.post(
        reverse("accounts:login"),
        {"username": user.username, "password": "test-password-only"},
        format="json",
    )
    csrf_token = login_response.cookies["csrftoken"].value

    missing_csrf = client.post(reverse("accounts:logout"), format="json")
    logout_response = client.post(
        reverse("accounts:logout"),
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert missing_csrf.status_code == 403
    assert logout_response.status_code == 204
    assert ACTIVE_CHURCH_SESSION_KEY not in client.session
    assert client.get(reverse("accounts:session")).status_code == 403


@pytest.mark.parametrize(
    ("role", "allowed"),
    (
        (
            ChurchMembership.Role.ADMIN,
            set(Capability),
        ),
        (
            ChurchMembership.Role.PASTOR,
            {
                Capability.VIEW_SENSITIVE_PERSON,
                Capability.VIEW_CONFIDENTIAL_CARE,
                Capability.LEAD_MINISTRY,
                Capability.SELF_SERVICE,
            },
        ),
        (
            ChurchMembership.Role.LEADER,
            {Capability.LEAD_MINISTRY, Capability.SELF_SERVICE},
        ),
        (
            ChurchMembership.Role.MEMBER,
            {Capability.SELF_SERVICE},
        ),
    ),
)
def test_role_capability_matrix(
    church: Church,
    user: User,
    role: str,
    allowed: set[Capability],
) -> None:
    add_membership(user, church, role)

    for capability in Capability:
        assert has_capability(user, church, capability) is (capability in allowed)
    assert has_church_role(user, church, {role})


def test_role_helpers_do_not_cross_church(church: Church, user: User) -> None:
    other_church = Church.objects.create(name="Hills Community Church")
    add_membership(user, church, ChurchMembership.Role.ADMIN)

    assert not has_capability(user, other_church, Capability.MANAGE_CHURCH)
    assert not has_church_role(
        user,
        other_church,
        {ChurchMembership.Role.ADMIN},
    )
