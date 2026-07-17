from django.utils import timezone
from rest_framework import serializers

from accounts.access import groups_visible_to
from groups.models import Group

from .models import Event


class EventSerializer(serializers.ModelSerializer):
    group = serializers.PrimaryKeyRelatedField(
        allow_null=True,
        queryset=Group.objects.none(),
        required=False,
    )
    group_name = serializers.CharField(source="group.name", read_only=True)
    created_by = serializers.CharField(source="created_by.username", read_only=True)
    registered_count = serializers.SerializerMethodField()
    waitlisted_count = serializers.SerializerMethodField()
    registration_open = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = (
            "id",
            "group",
            "group_name",
            "title",
            "description",
            "starts_at",
            "ends_at",
            "location",
            "capacity",
            "signup_opens",
            "signup_closes_at",
            "registration_open",
            "registered_count",
            "waitlisted_count",
            "created_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "registration_open",
            "registered_count",
            "waitlisted_count",
            "created_by",
            "created_at",
            "updated_at",
        )

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        membership = getattr(request, "church_membership", None)
        if membership is not None:
            self.fields["group"].queryset = groups_visible_to(
                Group.objects.filter(is_active=True),
                membership,
            )

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        starts_at = attrs.get("starts_at", getattr(self.instance, "starts_at", None))
        ends_at = attrs.get("ends_at", getattr(self.instance, "ends_at", None))
        closes_at = attrs.get(
            "signup_closes_at",
            getattr(self.instance, "signup_closes_at", None),
        )
        errors: dict[str, str] = {}
        if starts_at is not None and ends_at is not None and ends_at <= starts_at:
            errors["ends_at"] = "The event must end after it starts."
        if closes_at is not None and starts_at is not None and closes_at > starts_at:
            errors["signup_closes_at"] = "Signup must close by the event start time."
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def validate_capacity(self, value: int | None) -> int | None:
        if value is not None and value < 1:
            raise serializers.ValidationError("Capacity must be at least one.")
        return value

    def get_registration_open(self, instance: Event) -> bool:
        if not instance.signup_opens:
            return False
        now = timezone.now()
        if instance.signup_closes_at and instance.signup_closes_at <= now:
            return False
        if instance.starts_at <= now:
            return False
        registered_count = getattr(instance, "registered_count", 0)
        return instance.capacity is None or registered_count < instance.capacity

    def get_registered_count(self, instance: Event) -> int:
        return getattr(instance, "registered_count", 0)

    def get_waitlisted_count(self, instance: Event) -> int:
        return getattr(instance, "waitlisted_count", 0)
