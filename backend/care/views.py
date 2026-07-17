from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.access import care_cases_visible_to, follow_ups_visible_to
from accounts.models import ChurchMembership, User
from tenancy.permissions import HasActiveChurchMembership

from .models import CareCase, FollowUp, Interaction
from .permissions import HasFollowUpAccess
from .serializers import FollowUpSerializer, InteractionSerializer


class FollowUpQuerysetMixin:
    permission_classes = (HasActiveChurchMembership, HasFollowUpAccess)
    serializer_class = FollowUpSerializer

    def get_queryset(self):
        return follow_ups_visible_to(
            FollowUp.objects.select_related("person", "assigned_to"),
            self.request.church_membership,
        ).order_by("status", "due_at", "created_at", "id")


class FollowUpListView(FollowUpQuerysetMixin, generics.ListAPIView):
    pass


class FollowUpDetailView(
    FollowUpQuerysetMixin,
    generics.RetrieveUpdateAPIView,
):
    http_method_names = ("get", "put", "patch", "head", "options")


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
