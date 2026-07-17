import pytest
from django.test import override_settings
from django.urls import path, reverse
from rest_framework import generics, serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.test import APIClient
from rest_framework.views import APIView

from accounts.constants import ACTIVE_CHURCH_SESSION_KEY
from accounts.models import ChurchMembership, User
from accounts.permissions import Capability
from care.models import CareCase, FollowUp, Interaction
from events.models import Event, EventRegistration
from groups.models import Group, GroupMembership
from people.models import ConsentRecord, Household, Person, Relationship
from tenancy.api import ChurchScopedQuerysetMixin
from tenancy.models import Church, ChurchScopedQuerySet
from tenancy.permissions import HasActiveChurchMembership, HasChurchCapability

pytestmark = pytest.mark.django_db


class ScopedPersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Person
        fields = ("id", "full_name")


class ScopedPersonList(ChurchScopedQuerysetMixin, generics.ListAPIView):
    queryset = Person.objects.all()
    serializer_class = ScopedPersonSerializer


class ScopedPersonDetail(ChurchScopedQuerysetMixin, generics.RetrieveAPIView):
    queryset = Person.objects.all()
    serializer_class = ScopedPersonSerializer


class ChurchAdminProbe(APIView):
    permission_classes = (HasActiveChurchMembership, HasChurchCapability)
    required_capability = Capability.MANAGE_CHURCH

    def get(self, request: Request) -> Response:
        return Response(
            {
                "church_id": request.church.id,
                "membership_id": request.church_membership.id,
            }
        )


urlpatterns = [
    path("test/people/", ScopedPersonList.as_view(), name="scoped-person-list"),
    path(
        "test/people/<int:pk>/",
        ScopedPersonDetail.as_view(),
        name="scoped-person-detail",
    ),
    path("test/admin-probe/", ChurchAdminProbe.as_view(), name="church-admin-probe"),
]


def authenticated_client(
    user: User,
    church: Church,
) -> APIClient:
    client = APIClient()
    client.force_login(user)
    session = client.session
    session[ACTIVE_CHURCH_SESSION_KEY] = church.id
    session.save()
    return client


@override_settings(ROOT_URLCONF=__name__)
def test_list_and_detail_querysets_cannot_cross_church() -> None:
    current_church = Church.objects.create(name="Harbour Community Church")
    other_church = Church.objects.create(name="Hills Community Church")
    user = User.objects.create_user(username="fictional.scoped.user")
    ChurchMembership.objects.create(
        user=user,
        church=current_church,
        role=ChurchMembership.Role.LEADER,
    )
    visible_person = Person.objects.create(
        church=current_church,
        full_name="Visible Example",
    )
    hidden_person = Person.objects.create(
        church=other_church,
        full_name="Hidden Example",
    )
    client = authenticated_client(user, current_church)

    list_response = client.get(reverse("scoped-person-list"))
    own_detail = client.get(reverse("scoped-person-detail", args=(visible_person.id,)))
    other_detail = client.get(reverse("scoped-person-detail", args=(hidden_person.id,)))

    assert list_response.status_code == 200
    assert list_response.json() == [
        {"id": visible_person.id, "full_name": visible_person.full_name}
    ]
    assert own_detail.status_code == 200
    assert other_detail.status_code == 404


@override_settings(ROOT_URLCONF=__name__)
def test_missing_or_inactive_membership_is_rejected_and_session_is_cleared() -> None:
    church = Church.objects.create(name="Harbour Community Church")
    user = User.objects.create_user(username="fictional.inactive.access")
    membership = ChurchMembership.objects.create(
        user=user,
        church=church,
        role=ChurchMembership.Role.LEADER,
    )
    client = authenticated_client(user, church)
    membership.is_active = False
    membership.save(update_fields=("is_active", "updated_at"))

    response = client.get(reverse("scoped-person-list"))

    assert response.status_code == 403
    assert ACTIVE_CHURCH_SESSION_KEY not in client.session


@override_settings(ROOT_URLCONF=__name__)
def test_malformed_active_church_session_is_cleared() -> None:
    user = User.objects.create_user(username="fictional.malformed.session")
    client = APIClient()
    client.force_login(user)
    session = client.session
    session[ACTIVE_CHURCH_SESSION_KEY] = "not-a-church-id"
    session.save()

    response = client.get(reverse("scoped-person-list"))

    assert response.status_code == 403
    assert ACTIVE_CHURCH_SESSION_KEY not in client.session


@override_settings(ROOT_URLCONF=__name__)
def test_capability_permission_uses_active_church_role() -> None:
    church = Church.objects.create(name="Harbour Community Church")
    user = User.objects.create_user(username="fictional.capability.user")
    membership = ChurchMembership.objects.create(
        user=user,
        church=church,
        role=ChurchMembership.Role.LEADER,
    )
    client = authenticated_client(user, church)

    denied = client.get(reverse("church-admin-probe"))
    membership.role = ChurchMembership.Role.ADMIN
    membership.save(update_fields=("role", "updated_at"))
    allowed = client.get(reverse("church-admin-probe"))

    assert denied.status_code == 403
    assert allowed.status_code == 200
    assert allowed.json() == {
        "church_id": church.id,
        "membership_id": membership.id,
    }


def test_every_church_owned_model_uses_scoped_queryset() -> None:
    church_owned_models = (
        Household,
        Person,
        Relationship,
        ConsentRecord,
        Group,
        GroupMembership,
        Event,
        EventRegistration,
        FollowUp,
        CareCase,
        Interaction,
    )

    for model in church_owned_models:
        assert isinstance(model.objects.all(), ChurchScopedQuerySet)
