import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from accounts.models import ChurchMembership, User
from tenancy.models import Church


@pytest.mark.django_db
def test_custom_user_is_configured() -> None:
    assert settings.AUTH_USER_MODEL == "accounts.User"
    assert get_user_model() is User


@pytest.mark.django_db
def test_active_membership_grants_access_only_to_its_church_and_role() -> None:
    harbour_church = Church.objects.create(name="Harbour Community Church")
    hills_church = Church.objects.create(name="Hills Community Church")
    user = User.objects.create_user(username="fictional.leader")
    ChurchMembership.objects.create(
        user=user,
        church=harbour_church,
        role=ChurchMembership.Role.LEADER,
    )

    assert user.has_church_access(harbour_church)
    assert user.has_church_access(
        harbour_church,
        roles={ChurchMembership.Role.LEADER},
    )
    assert not user.has_church_access(
        harbour_church,
        roles={ChurchMembership.Role.PASTOR},
    )
    assert not user.has_church_access(hills_church)


@pytest.mark.django_db
def test_inactive_user_or_membership_does_not_grant_access() -> None:
    church = Church.objects.create(name="Riverside Community Church")
    user = User.objects.create_user(username="fictional.member")
    membership = ChurchMembership.objects.create(
        user=user,
        church=church,
        role=ChurchMembership.Role.MEMBER,
        is_active=False,
    )

    assert not user.has_church_access(church)

    membership.is_active = True
    membership.save(update_fields=("is_active", "updated_at"))
    user.is_active = False
    user.save(update_fields=("is_active",))

    assert not user.has_church_access(church)


@pytest.mark.django_db
def test_duplicate_active_membership_is_prevented() -> None:
    church = Church.objects.create(name="Parkside Community Church")
    user = User.objects.create_user(username="fictional.pastor")
    ChurchMembership.objects.create(
        user=user,
        church=church,
        role=ChurchMembership.Role.PASTOR,
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        ChurchMembership.objects.create(
            user=user,
            church=church,
            role=ChurchMembership.Role.ADMIN,
        )


@pytest.mark.django_db
def test_inactive_memberships_preserve_history() -> None:
    church = Church.objects.create(name="Lakeside Community Church")
    user = User.objects.create_user(username="fictional.admin")

    ChurchMembership.objects.create(
        user=user,
        church=church,
        role=ChurchMembership.Role.LEADER,
        is_active=False,
    )
    ChurchMembership.objects.create(
        user=user,
        church=church,
        role=ChurchMembership.Role.ADMIN,
        is_active=True,
    )

    assert ChurchMembership.objects.for_user(user).for_church(church).count() == 2
