from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Count, Prefetch, Q
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.access import groups_visible_to
from accounts.models import ChurchMembership
from groups.models import Group
from tenancy.permissions import HasActiveChurchMembership

from .models import Event, EventRegistration
from .permissions import HasEventAccess
from .serializers import (
    EventRegistrationCreateSerializer,
    EventRegistrationSerializer,
    EventSerializer,
)
from .services import cancel_registration, register_for_event


class EventQuerysetMixin:
    permission_classes = (HasActiveChurchMembership, HasEventAccess)
    serializer_class = EventSerializer

    def get_queryset(self):
        active_registration_statuses = (
            EventRegistration.Status.REGISTERED,
            EventRegistration.Status.WALK_IN,
        )
        queryset = (
            Event.objects.for_church(self.request.church)
            .select_related("group", "created_by")
            .annotate(
                registered_count=Count(
                    "registrations",
                    filter=Q(registrations__status__in=active_registration_statuses),
                ),
                waitlisted_count=Count(
                    "registrations",
                    filter=Q(registrations__status=EventRegistration.Status.WAITLISTED),
                ),
            )
            .order_by("starts_at", "id")
        )
        person_id = self.request.church_membership.person_id
        if person_id is not None:
            queryset = queryset.prefetch_related(
                Prefetch(
                    "registrations",
                    queryset=EventRegistration.objects.filter(
                        person_id=person_id
                    ).select_related("person"),
                    to_attr="my_event_registration",
                )
            )
        return queryset


class EventListCreateView(EventQuerysetMixin, generics.ListCreateAPIView):
    @transaction.atomic
    def perform_create(self, serializer: EventSerializer) -> None:
        serializer.save(
            church=self.request.church,
            created_by=self.request.user,
        )


class EventDetailView(EventQuerysetMixin, generics.RetrieveUpdateDestroyAPIView):
    @transaction.atomic
    def perform_update(self, serializer: EventSerializer) -> None:
        serializer.save()

    @transaction.atomic
    def perform_destroy(self, instance: Event) -> None:
        instance.delete()


class EventGroupChoicesView(APIView):
    permission_classes = (HasActiveChurchMembership, HasEventAccess)

    def get(self, request):
        groups = groups_visible_to(
            Group.objects.filter(is_active=True).order_by("name", "id"),
            request.church_membership,
        )
        return Response([{"id": group.id, "name": group.name} for group in groups])


class EventRegistrationListCreateView(APIView):
    permission_classes = (HasActiveChurchMembership,)

    def _event(self, request: Request, event_id: int) -> Event:
        return generics.get_object_or_404(
            Event.objects.for_church(request.church),
            pk=event_id,
        )

    def _registrations(self, request: Request, event: Event):
        queryset = EventRegistration.objects.for_church(request.church).filter(
            event=event
        )
        membership = request.church_membership
        if membership.role == ChurchMembership.Role.MEMBER:
            queryset = queryset.filter(person_id=membership.person_id)
        return queryset.select_related("person").order_by("registered_at", "id")

    def get(self, request: Request, event_id: int) -> Response:
        event = self._event(request, event_id)
        registrations = self._registrations(request, event)
        return Response(EventRegistrationSerializer(registrations, many=True).data)

    def post(self, request: Request, event_id: int) -> Response:
        event = self._event(request, event_id)
        serializer = EventRegistrationCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        try:
            registration = register_for_event(
                event=event,
                person=serializer.validated_data["person"],
                needs_transport=serializer.validated_data["needs_transport"],
                note=serializer.validated_data.get("note", ""),
            )
        except DjangoValidationError as error:
            raise ValidationError({"detail": error.messages[0]}) from error
        registration = EventRegistration.objects.select_related("person").get(
            pk=registration.pk
        )
        return Response(
            EventRegistrationSerializer(registration).data,
            status=status.HTTP_201_CREATED,
        )


class EventRegistrationCancelView(EventRegistrationListCreateView):
    def post(
        self,
        request: Request,
        event_id: int,
        registration_id: int,
    ) -> Response:
        event = self._event(request, event_id)
        registration = generics.get_object_or_404(
            self._registrations(request, event),
            pk=registration_id,
        )
        cancelled = cancel_registration(registration)
        cancelled = EventRegistration.objects.select_related("person").get(
            pk=cancelled.pk
        )
        return Response(EventRegistrationSerializer(cancelled).data)
