from datetime import timedelta

from django.db import transaction
from django.db.models import Case, Count, F, IntegerField, Q, When
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.access import care_cases_visible_to, follow_ups_visible_to
from accounts.models import ChurchMembership, User
from tenancy.permissions import HasActiveChurchMembership

from .attention import church_today
from .models import CareCase, FollowUp, Interaction
from .permissions import HasFollowUpAccess
from .serializers import FollowUpSerializer, InteractionSerializer


class FollowUpQuerysetMixin:
    permission_classes = (HasActiveChurchMembership, HasFollowUpAccess)
    serializer_class = FollowUpSerializer

    def get_queryset(self):
        today = church_today(self.request.church_membership.church)
        return (
            follow_ups_visible_to(
                FollowUp.objects.select_related(
                    "person", "assigned_to", "church"
                ).prefetch_related("interactions", "due_date_changes"),
                self.request.church_membership,
            )
            .annotate(
                due_priority=Case(
                    When(
                        ~Q(status=FollowUp.Status.CLOSED),
                        due_at__lt=today,
                        then=0,
                    ),
                    When(
                        ~Q(status=FollowUp.Status.CLOSED),
                        due_at=today,
                        then=1,
                    ),
                    When(
                        ~Q(status=FollowUp.Status.CLOSED),
                        due_at__isnull=False,
                        then=2,
                    ),
                    When(~Q(status=FollowUp.Status.CLOSED), then=3),
                    default=4,
                    output_field=IntegerField(),
                )
            )
            .order_by("due_priority", "due_at", "created_at", "id")
        )


class FollowUpListView(FollowUpQuerysetMixin, generics.ListAPIView):
    pass


class MyFollowUpListView(FollowUpQuerysetMixin, generics.ListAPIView):
    def get_queryset(self):
        membership = self.request.church_membership
        queryset = follow_ups_visible_to(
            FollowUp.objects.select_related("person", "assigned_to", "church")
            .prefetch_related("interactions", "due_date_changes")
            .exclude(status=FollowUp.Status.CLOSED),
            membership,
        )
        if membership.role in (
            ChurchMembership.Role.ADMIN,
            ChurchMembership.Role.PASTOR,
        ):
            today = church_today(membership.church)
            unassigned_cutoff = timezone.now() - timedelta(hours=24)
            queryset = queryset.annotate(
                later_postponements=Count(
                    "due_date_changes",
                    filter=Q(
                        due_date_changes__new_due_at__gt=F(
                            "due_date_changes__previous_due_at"
                        )
                    ),
                )
            ).filter(
                Q(assigned_to=self.request.user)
                | Q(
                    status=FollowUp.Status.NEW,
                    assigned_to__isnull=True,
                    created_at__lte=unassigned_cutoff,
                )
                | Q(later_postponements__gte=2)
                | Q(due_at__lte=today - timedelta(days=3))
            )
        else:
            queryset = queryset.filter(assigned_to=self.request.user)
        return queryset.order_by(F("due_at").asc(nulls_last=True), "created_at", "id")


class FollowUpDetailView(
    FollowUpQuerysetMixin,
    generics.RetrieveUpdateAPIView,
):
    http_method_names = ("get", "put", "patch", "head", "options")

    def update(self, request, *args, **kwargs):
        """Lock before validation so scheduling rules observe one true sequence."""
        partial = kwargs.pop("partial", False)
        with transaction.atomic():
            queryset = self.filter_queryset(self.get_queryset()).select_for_update(
                of=("self",)
            )
            instance = get_object_or_404(queryset, pk=kwargs["pk"])
            self.check_object_permissions(request, instance)
            serializer = self.get_serializer(
                instance,
                data=request.data,
                partial=partial,
            )
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data)


class FollowUpWorkerChoicesView(APIView):
    permission_classes = (HasActiveChurchMembership, HasFollowUpAccess)

    def get(self, request):
        membership = request.church_membership
        workers = User.objects.filter(
            church_memberships__church=request.church,
            church_memberships__is_active=True,
            church_memberships__role__in=(
                ChurchMembership.Role.ADMIN,
                ChurchMembership.Role.PASTOR,
                ChurchMembership.Role.LEADER,
            ),
            is_active=True,
        ).distinct()
        if membership.role == ChurchMembership.Role.LEADER:
            workers = workers.filter(pk=membership.user_id)
        return Response(
            [
                {
                    "id": worker.id,
                    "username": worker.username,
                    "name": worker.get_full_name() or worker.username,
                }
                for worker in workers.order_by("first_name", "username", "id")
            ]
        )


class InteractionListCreateMixin(generics.ListCreateAPIView):
    permission_classes = (HasActiveChurchMembership, HasFollowUpAccess)
    serializer_class = InteractionSerializer
    parent_field: str

    def get_parent(self):
        if self.parent_field == "follow_up":
            queryset = follow_ups_visible_to(
                FollowUp.objects.select_related("person"),
                self.request.church_membership,
            )
        else:
            queryset = care_cases_visible_to(
                CareCase.objects.select_related("person"),
                self.request.church_membership,
            )
        return generics.get_object_or_404(
            queryset,
            pk=self.kwargs["parent_id"],
        )

    def get_queryset(self):
        parent = self.get_parent()
        queryset = Interaction.objects.for_church(self.request.church).filter(
            **{self.parent_field: parent}
        )
        if self.request.church_membership.role == ChurchMembership.Role.LEADER:
            queryset = queryset.exclude(visibility=Interaction.Visibility.PASTORS_ONLY)
        return queryset.select_related("author").order_by("-occurred_at", "-id")

    def perform_create(self, serializer: InteractionSerializer) -> None:
        parent = self.get_parent()
        serializer.save(
            church=self.request.church,
            person=parent.person,
            author=self.request.user,
            **{self.parent_field: parent},
        )


class FollowUpInteractionListCreateView(InteractionListCreateMixin):
    parent_field = "follow_up"


class CareCaseInteractionListCreateView(InteractionListCreateMixin):
    parent_field = "care_case"
