from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import Capability
from audit.models import AuditEvent
from audit.services import record_audit_event
from tenancy.permissions import HasActiveChurchMembership, HasChurchCapability

from .models import ConsentRecord, Person
from .serializers import ConsentRecordSerializer


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
