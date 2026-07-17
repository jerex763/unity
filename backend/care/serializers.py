from django.utils import timezone
from rest_framework import serializers

from accounts.models import ChurchMembership, User

from .models import FollowUp, Interaction


class FollowUpSerializer(serializers.ModelSerializer):
    person = serializers.SerializerMethodField()
    assigned_to = serializers.PrimaryKeyRelatedField(
        allow_null=True,
        queryset=User.objects.none(),
        required=False,
    )
    assigned_to_name = serializers.CharField(
        source="assigned_to.username",
        read_only=True,
    )

    class Meta:
        model = FollowUp
        fields = (
            "id",
            "person",
            "source",
            "engagement",
            "status",
            "assigned_to",
            "assigned_to_name",
            "due_at",
            "closed_at",
            "outcome",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "person", "source", "closed_at", "created_at")

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        membership = self.context["request"].church_membership
        workers = User.objects.filter(
            church_memberships__church=membership.church,
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
            self.fields["assigned_to"].read_only = True
        self.fields["assigned_to"].queryset = workers

    def get_person(self, instance: FollowUp) -> dict[str, object]:
        return {
            "id": instance.person_id,
            "full_name": instance.person.full_name,
            "preferred_name": instance.person.preferred_name,
            "phone": instance.person.phone,
            "email": instance.person.email,
        }

    def update(self, instance: FollowUp, validated_data: dict[str, object]):
        new_status = validated_data.get("status", instance.status)
        if new_status == FollowUp.Status.CLOSED and instance.closed_at is None:
            validated_data["closed_at"] = timezone.now()
        elif new_status != FollowUp.Status.CLOSED:
            validated_data["closed_at"] = None
        return super().update(instance, validated_data)


class InteractionSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = Interaction
        fields = (
            "id",
            "kind",
            "occurred_at",
            "summary",
            "visibility",
            "author",
            "created_at",
        )
        read_only_fields = ("id", "author", "created_at")

    def validate_visibility(self, value: str) -> str:
        membership = self.context["request"].church_membership
        if (
            membership.role == ChurchMembership.Role.LEADER
            and value == Interaction.Visibility.PASTORS_ONLY
        ):
            raise serializers.ValidationError(
                "Leaders cannot create pastors-only interactions."
            )
        return value
