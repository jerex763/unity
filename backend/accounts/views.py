from django.contrib.auth import authenticate
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    PermissionDenied,
    ValidationError,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ChurchMembership, User
from .serializers import LoginSerializer

ACTIVE_CHURCH_SESSION_KEY = "active_church_id"


class InvalidCredentials(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Invalid username or password."
    default_code = "invalid_credentials"


def membership_payload(membership: ChurchMembership) -> dict[str, object]:
    return {
        "church_id": membership.church_id,
        "church_name": membership.church.name,
        "role": membership.role,
    }


def session_payload(user: User, membership: ChurchMembership) -> dict[str, object]:
    return {
        "user": {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
        },
        "membership": membership_payload(membership),
    }


def select_membership(user: User, church_id: int | None) -> ChurchMembership:
    memberships = (
        ChurchMembership.objects.active()
        .for_user(user)
        .select_related("church")
        .order_by("church_id")
    )
    if church_id is not None:
        membership = memberships.filter(church_id=church_id).first()
        if membership is None:
            raise PermissionDenied("No active membership exists for that church.")
        return membership

    choices = list(memberships[:2])
    if not choices:
        raise PermissionDenied("An active church membership is required.")
    if len(choices) > 1:
        raise ValidationError(
            {"church_id": "Select a church when the account has multiple memberships."}
        )
    return choices[0]


@method_decorator(ensure_csrf_cookie, name="dispatch")
class LoginView(APIView):
    authentication_classes: tuple = ()
    permission_classes = (AllowAny,)

    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request=request,
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            raise InvalidCredentials

        membership = select_membership(
            user,
            serializer.validated_data.get("church_id"),
        )
        django_login(request, user)
        request.session[ACTIVE_CHURCH_SESSION_KEY] = membership.church_id
        return Response(session_payload(user, membership))


class SessionView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request: Request) -> Response:
        church_id = request.session.get(ACTIVE_CHURCH_SESSION_KEY)
        membership = select_membership(request.user, church_id)
        request.session[ACTIVE_CHURCH_SESSION_KEY] = membership.church_id
        return Response(session_payload(request.user, membership))


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request: Request) -> Response:
        django_logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)
