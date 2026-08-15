from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework import serializers

from accounts.models import ChurchMembership, User

from .attention import attention_for, church_today
from .models import FollowUp, FollowUpDueDateChange, Interaction


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
    attention = serializers.SerializerMethodField()
    postpone_reason = serializers.ChoiceField(
        choices=FollowUpDueDateChange.Reason.choices,
        required=False,
        write_only=True,
    )
    postpone_interaction = serializers.PrimaryKeyRelatedField(
        queryset=Interaction.objects.none(),
        required=False,
        write_only=True,
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
            "attention",
            "postpone_reason",
            "postpone_interaction",
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
        self.fields["postpone_interaction"].queryset = Interaction.objects.filter(
            church=membership.church
        )

    def get_person(self, instance: FollowUp) -> dict[str, object]:
        return {
            "id": instance.person_id,
            "full_name": instance.person.full_name,
            "preferred_name": instance.person.preferred_name,
            "phone": instance.person.phone,
            "email": instance.person.email,
            "wechat_id": instance.person.wechat_id,
            "has_whatsapp": instance.person.has_whatsapp,
            "preferred_contact": instance.person.preferred_contact,
        }

    def get_attention(self, instance: FollowUp) -> dict[str, object]:
        return attention_for(instance)

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        instance = self.instance
        status = attrs.get(
            "status",
            instance.status if instance is not None else FollowUp.Status.NEW,
        )
        assigned_to = attrs.get(
            "assigned_to",
            instance.assigned_to if instance is not None else None,
        )
        due_at = attrs.get(
            "due_at",
            instance.due_at if instance is not None else None,
        )
        outcome = attrs.get(
            "outcome",
            instance.outcome if instance is not None else None,
        )
        normalized_outcome = outcome.strip() if isinstance(outcome, str) else outcome

        postpone_reason = attrs.get("postpone_reason")
        postpone_interaction = attrs.get("postpone_interaction")

        errors: dict[str, str] = {}
        if instance is not None and (
            postpone_reason is not None or postpone_interaction is not None
        ):
            previous_due_at = instance.due_at
            moving_later = (
                "due_at" in attrs
                and due_at is not None
                and previous_due_at is not None
                and due_at > previous_due_at
            )
            if not moving_later:
                misuse_message = (
                    "Postponement evidence can only accompany a later due date."
                )
                if postpone_reason is not None:
                    errors["postpone_reason"] = misuse_message
                if postpone_interaction is not None:
                    errors["postpone_interaction"] = misuse_message
        if instance is not None and "due_at" in attrs:
            previous_due_at = instance.due_at
            moving_later = (
                due_at is not None
                and previous_due_at is not None
                and due_at > previous_due_at
            )
            prior_postponements = instance.due_date_changes.filter(
                previous_due_at__isnull=False,
                new_due_at__isnull=False,
                new_due_at__gt=F("previous_due_at"),
            ).count()
            reason_required = moving_later and (
                previous_due_at < church_today(instance.church)
                or prior_postponements > 0
            )
            if postpone_interaction is not None:
                if (
                    postpone_interaction.follow_up_id != instance.id
                    or postpone_interaction.church_id != instance.church_id
                    or postpone_interaction.created_at
                    <= instance.due_schedule_changed_at
                ):
                    errors["postpone_interaction"] = (
                        "Choose an interaction for this follow-up created after the "
                        "current due schedule was established."
                    )
            if reason_required and not postpone_reason and not postpone_interaction:
                errors["postpone_reason"] = (
                    "Choose an operational reason or a qualifying interaction to "
                    "postpone this due date."
                )
        if status == FollowUp.Status.CLOSED:
            if not normalized_outcome:
                errors["outcome"] = "Record an outcome before closing the follow-up."
        elif (
            assigned_to is not None
            or status
            in (
                FollowUp.Status.ASSIGNED,
                FollowUp.Status.IN_PROGRESS,
                FollowUp.Status.CONNECTED,
            )
        ) and due_at is None:
            errors["due_at"] = (
                "Set a due date when a worker is assigned or the follow-up "
                "is Assigned, In progress, or Connected."
            )

        if errors:
            raise serializers.ValidationError(errors)
        if "outcome" in attrs:
            attrs["outcome"] = normalized_outcome or None
        return attrs

    @transaction.atomic
    def update(self, instance: FollowUp, validated_data: dict[str, object]):
        postpone_reason = validated_data.pop("postpone_reason", None)
        postpone_interaction = validated_data.pop("postpone_interaction", None)
        previous_due_at = instance.due_at
        previous_status = instance.status
        new_status = validated_data.get("status", instance.status)
        if new_status == FollowUp.Status.CLOSED and instance.closed_at is None:
            validated_data["closed_at"] = timezone.now()
        elif new_status != FollowUp.Status.CLOSED:
            validated_data["closed_at"] = None
        if new_status != previous_status:
            validated_data["status_changed_at"] = timezone.now()
        updated = super().update(instance, validated_data)
        if "due_at" in validated_data and updated.due_at != previous_due_at:
            schedule_changed_at = timezone.now()
            updated.due_schedule_changed_at = schedule_changed_at
            updated.save(update_fields=("due_schedule_changed_at", "updated_at"))
            FollowUpDueDateChange.objects.create(
                follow_up=updated,
                church=updated.church,
                previous_due_at=previous_due_at,
                new_due_at=updated.due_at,
                actor=self.context["request"].user,
                reason=postpone_reason,
                interaction=postpone_interaction,
            )
            getattr(updated, "_prefetched_objects_cache", {}).pop(
                "due_date_changes", None
            )
        return updated


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
