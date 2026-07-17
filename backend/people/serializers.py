from datetime import date, datetime

from django.utils import timezone
from rest_framework import serializers

from accounts.models import ChurchMembership
from accounts.permissions import ROLE_CAPABILITIES, Capability

from .models import ConsentRecord, Household, Person


class PersonSerializer(serializers.ModelSerializer):
    interests = serializers.ListField(
        child=serializers.CharField(max_length=100),
        max_length=20,
        required=False,
    )
    household = serializers.PrimaryKeyRelatedField(
        allow_null=True,
        queryset=Household.objects.none(),
        required=False,
    )
    invited_by = serializers.PrimaryKeyRelatedField(
        allow_null=True,
        queryset=Person.objects.none(),
        required=False,
    )

    sensitive_fields = frozenset({"faith_background", "discipleship_stage"})
    staff_only_fields = frozenset({"notes"})

    class Meta:
        model = Person
        fields = (
            "id",
            "full_name",
            "preferred_name",
            "gender",
            "date_of_birth",
            "email",
            "phone",
            "has_whatsapp",
            "photo_url",
            "home_country",
            "suburb",
            "occupation",
            "university",
            "course",
            "interests",
            "household",
            "membership_status",
            "discipleship_stage",
            "faith_background",
            "invited_by",
            "notes",
            "deactivated_at",
            "anonymized_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "deactivated_at",
            "anonymized_at",
            "created_at",
            "updated_at",
        )

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        church = getattr(request, "church", None)
        if church is not None:
            self.fields["household"].queryset = Household.objects.for_church(church)
            invited_by = Person.objects.for_church(church)
            if isinstance(self.instance, Person):
                invited_by = invited_by.exclude(pk=self.instance.pk)
            self.fields["invited_by"].queryset = invited_by

    def _can_view_sensitive(self) -> bool:
        request = self.context.get("request")
        membership = getattr(request, "church_membership", None)
        if membership is None:
            return False
        return Capability.VIEW_SENSITIVE_PERSON in ROLE_CAPABILITIES.get(
            membership.role,
            frozenset(),
        )

    def to_representation(self, instance: Person) -> dict[str, object]:
        data = super().to_representation(instance)
        if not self._can_view_sensitive():
            for field_name in self.sensitive_fields:
                data.pop(field_name, None)
        request = self.context.get("request")
        membership = getattr(request, "church_membership", None)
        if membership is None or membership.role == ChurchMembership.Role.MEMBER:
            for field_name in self.staff_only_fields:
                data.pop(field_name, None)
        return data

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        if not self._can_view_sensitive():
            supplied_sensitive = self.sensitive_fields.intersection(
                self.initial_data.keys()
            )
            if supplied_sensitive:
                raise serializers.ValidationError(
                    {
                        field_name: "Only pastors and admins may set this field."
                        for field_name in sorted(supplied_sensitive)
                    }
                )

        church = self.context["request"].church
        email = attrs.get("email")
        if email:
            duplicate = Person.objects.for_church(church).filter(email__iexact=email)
            if self.instance is not None:
                duplicate = duplicate.exclude(pk=self.instance.pk)
            if duplicate.exists():
                raise serializers.ValidationError(
                    {"email": "A person with this email already exists in this church."}
                )
        return attrs

    def validate_full_name(self, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise serializers.ValidationError("Full name cannot be blank.")
        return normalized

    def validate_email(self, value: str | None) -> str | None:
        return value.strip().lower() if value else None

    def validate_phone(self, value: str | None) -> str | None:
        return value.strip() if value else None

    def validate_home_country(self, value: str | None) -> str | None:
        return value.strip().upper() if value else None

    def validate_date_of_birth(self, value: date | None) -> date | None:
        if value is not None and value > timezone.localdate():
            raise serializers.ValidationError("Date of birth cannot be in the future.")
        return value

    def validate_interests(self, value: list[str]) -> list[str]:
        normalized = list(dict.fromkeys(item.strip() for item in value if item.strip()))
        if len(normalized) != len(value):
            raise serializers.ValidationError("Interests must be non-blank and unique.")
        return normalized


class ConsentRecordSerializer(serializers.ModelSerializer):
    recorded_by = serializers.CharField(source="recorded_by.username", read_only=True)
    supersedes_id = serializers.IntegerField(read_only=True)
    recorded_at = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = ConsentRecord
        fields = (
            "id",
            "status",
            "notice_version",
            "consented_at",
            "method",
            "recorded_by",
            "supersedes_id",
            "recorded_at",
        )
        read_only_fields = ("id",)

    def validate_consented_at(self, value: datetime) -> datetime:
        if value > timezone.now():
            raise serializers.ValidationError(
                "The consent decision time cannot be in the future."
            )
        return value


class HardDeletePersonSerializer(serializers.Serializer):
    reason = serializers.ChoiceField(choices=Person.HardDeleteReason.choices)
