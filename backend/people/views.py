from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.access import follow_ups_visible_to, people_visible_to
from accounts.permissions import Capability
from audit.models import AuditEvent
from audit.services import record_audit_event
from care.models import FollowUp
from events.models import EventRegistration
from groups.models import GroupMembership
from tenancy.permissions import HasActiveChurchMembership, HasChurchCapability

from .lifecycle import anonymize_person, deactivate_person, hard_delete_person
from .models import ConsentRecord, Person
from .permissions import HasPersonDirectoryAccess
from .serializers import (
    ConsentRecordSerializer,
    HardDeletePersonSerializer,
    PersonDetailSerializer,
    PersonSerializer,
)


class PersonQuerysetMixin:
    permission_classes = (HasActiveChurchMembership, HasPersonDirectoryAccess)
    serializer_class = PersonSerializer

    def get_queryset(self):
        return people_visible_to(
            Person.objects.select_related("household", "invited_by").prefetch_related(
                Prefetch(
                    "group_memberships",
                    queryset=GroupMembership.objects.filter(
                        left_at__isnull=True,
                        group__is_active=True,
                    )
                    .select_related("group")
                    .order_by("group__name", "group_id"),
                    to_attr="active_group_memberships",
                )
            ),
            self.request.church_membership,
        )


class PersonListCreateView(PersonQuerysetMixin, generics.ListCreateAPIView):
    @transaction.atomic
    def perform_create(self, serializer: PersonSerializer) -> None:
        serializer.save(church=self.request.church)


class PersonDetailView(PersonQuerysetMixin, generics.RetrieveUpdateAPIView):
    http_method_names = ("get", "put", "patch", "head", "options")
    serializer_class = PersonDetailSerializer

    def get_queryset(self):
        follow_ups = follow_ups_visible_to(
            FollowUp.objects.select_related("assigned_to"),
            self.request.church_membership,
        ).order_by("-created_at", "-id")
        return (
            super()
            .get_queryset()
            .prefetch_related(
                Prefetch(
                    "event_registrations",
                    queryset=EventRegistration.objects.filter(
                        checked_in_at__isnull=False,
                    )
                    .select_related("event")
                    .order_by("-event__starts_at", "-event_id"),
                    to_attr="attended_event_registrations",
                ),
                Prefetch(
                    "follow_ups",
                    queryset=follow_ups,
                    to_attr="visible_follow_up_history",
                ),
            )
        )


class PersonConsentView(APIView):
    permission_classes = (HasActiveChurchMembership, HasChurchCapability)
    required_capability = Capability.MANAGE_PERSON_CONSENT

    def _person(self, request: Request, person_id: int) -> Person:
        return get_object_or_404(
            Person.objects.for_church(request.church),
            pk=person_id,
        )

    def get(self, request: Request, person_id: int) -> Response:
        person = self._person(request, person_id)
        latest = person.consent_records.select_related("recorded_by").first()
        if latest is None:
            return Response(
                {
                    "id": None,
                    "status": "unknown",
                    "notice_version": None,
                    "consented_at": None,
                    "method": None,
                    "recorded_by": None,
                    "supersedes_id": None,
                    "recorded_at": None,
                }
            )
        return Response(ConsentRecordSerializer(latest).data)

    @transaction.atomic
    def post(self, request: Request, person_id: int) -> Response:
        person = get_object_or_404(
            Person.objects.select_for_update().for_church(request.church),
            pk=person_id,
        )
        previous = (
            ConsentRecord.objects.select_for_update()
            .filter(person=person)
            .order_by("-created_at", "-id")
            .first()
        )
        serializer = ConsentRecordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = serializer.save(
            church=request.church,
            person=person,
            recorded_by=request.user,
            supersedes=previous,
        )
        record_audit_event(
            action=AuditEvent.Action.CONSENT_RECORDED,
            actor=request.user,
            church=request.church,
            target=record,
            request=request,
        )
        return Response(
            ConsentRecordSerializer(record).data,
            status=status.HTTP_201_CREATED,
        )


class PersonLifecycleView(APIView):
    permission_classes = (HasActiveChurchMembership, HasChurchCapability)

    def _locked_person(self, request: Request, person_id: int) -> Person:
        return get_object_or_404(
            Person.objects.select_for_update().for_church(request.church),
            pk=person_id,
        )

    @staticmethod
    def _response(person: Person) -> Response:
        return Response(
            {
                "id": person.id,
                "membership_status": person.membership_status,
                "deactivated_at": person.deactivated_at,
                "anonymized_at": person.anonymized_at,
            }
        )


class PersonDeactivateView(PersonLifecycleView):
    required_capability = Capability.LEAD_MINISTRY

    @transaction.atomic
    def post(self, request: Request, person_id: int) -> Response:
        person = self._locked_person(request, person_id)
        return self._response(deactivate_person(person))


class PersonAnonymizeView(PersonLifecycleView):
    required_capability = Capability.MANAGE_DESTRUCTIVE

    @transaction.atomic
    def post(self, request: Request, person_id: int) -> Response:
        person = self._locked_person(request, person_id)
        return self._response(anonymize_person(person))


class PersonHardDeleteView(PersonLifecycleView):
    required_capability = Capability.MANAGE_DESTRUCTIVE

    @transaction.atomic
    def delete(self, request: Request, person_id: int) -> Response:
        person = self._locked_person(request, person_id)
        serializer = HardDeletePersonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        hard_delete_person(
            person=person,
            actor=request.user,
            reason=serializer.validated_data["reason"],
            request=request,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
