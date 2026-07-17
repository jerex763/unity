from django.db import transaction
from django.db.models import Count, Q
from rest_framework import generics

from tenancy.permissions import HasActiveChurchMembership

from .models import Event, EventRegistration
from .permissions import HasEventAccess
from .serializers import EventSerializer


class EventQuerysetMixin:
    permission_classes = (HasActiveChurchMembership, HasEventAccess)
    serializer_class = EventSerializer

    def get_queryset(self):
        active_registration_statuses = (
            EventRegistration.Status.REGISTERED,
            EventRegistration.Status.WALK_IN,
        )
        return (
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
