from datetime import date, datetime

from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers

from accounts.models import ChurchMembership
from accounts.permissions import ROLE_CAPABILITIES, Capability

from .models import ConsentRecord, Household, Person, Relationship


class PersonLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Person
        fields = ("id", "full_name", "preferred_name", "photo_url")


class RelationshipSerializer(serializers.ModelSerializer):
    person = serializers.SerializerMethodField()

    class Meta:
        model = Relationship
        fields = ("id", "kind", "person", "created_at")
        read_only_fields = fields

    def get_person(self, instance: Relationship) -> dict[str, object]:
        anchor_id = self.context["anchor_person_id"]
        person = (
            instance.to_person
            if instance.from_person_id == anchor_id
            else instance.from_person
        )
        return PersonLinkSerializer(person).data


class RelationshipCreateSerializer(serializers.Serializer):
    person = serializers.PrimaryKeyRelatedField(queryset=Person.objects.none())
    kind = serializers.ChoiceField(choices=Relationship.Kind.choices)

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.fields["person"].queryset = self.context["visible_people"]

    def validate_person(self, value: Person) -> Person:
        if value.pk == self.context["anchor_person"].pk:
            raise serializers.ValidationError("A person cannot be related to themself.")
        return value

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        anchor = self.context["anchor_person"]
        other = attrs["person"]
        first_id, second_id = sorted((anchor.pk, other.pk))
        if Relationship.objects.filter(
            church=anchor.church,
            from_person_id=first_id,
            to_person_id=second_id,
            kind=attrs["kind"],
        ).exists():
            raise serializers.ValidationError(
                {"kind": "This relationship is already recorded."}
            )
        return attrs


class PersonSerializer(serializers.ModelSerializer):
    groups = serializers.SerializerMethodField()
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
            "groups",
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
            membership = getattr(request, "church_membership", None)
            visible_ids = self.context.get("visible_person_ids")
            invited_by = Person.objects.for_church(church)
            if membership is not None and visible_ids is not None:
                invited_by = invited_by.filter(pk__in=visible_ids)
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

    def get_groups(self, instance: Person) -> list[dict[str, object]]:
        memberships = getattr(instance, "active_group_memberships", ())
        return [
            {
                "id": membership.group_id,
                "name": membership.group.name,
                "role": membership.role,
                "joined_at": membership.joined_at.isoformat(),
            }
            for membership in memberships
        ]

    def to_representation(self, instance: Person) -> dict[str, object]:
        data = super().to_representation(instance)
        visible_person_ids = self.context.get("visible_person_ids")
        if (
            visible_person_ids is not None
            and instance.invited_by_id not in visible_person_ids
        ):
            data["invited_by"] = None
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


class PersonDetailSerializer(PersonSerializer):
    events_attended = serializers.SerializerMethodField()
    follow_up_history = serializers.SerializerMethodField()
    inviter = serializers.SerializerMethodField()
    invitees = serializers.SerializerMethodField()
    relationships = serializers.SerializerMethodField()

    class Meta(PersonSerializer.Meta):
        fields = PersonSerializer.Meta.fields + (
            "inviter",
            "invitees",
            "relationships",
            "events_attended",
            "follow_up_history",
        )

    def _visible_people(self):
        return Person.objects.filter(pk__in=self.context["visible_person_ids"])

    def get_inviter(self, instance: Person) -> dict[str, object] | None:
        if (
            instance.invited_by_id is None
            or instance.invited_by_id not in self.context["visible_person_ids"]
        ):
            return None
        return PersonLinkSerializer(instance.invited_by).data

    def get_invitees(self, instance: Person) -> list[dict[str, object]]:
        invitees = (
            self._visible_people()
            .filter(invited_by=instance)
            .order_by("full_name", "id")
        )
        return PersonLinkSerializer(invitees, many=True).data

    def get_relationships(self, instance: Person) -> list[dict[str, object]]:
        visible_ids = self.context["visible_person_ids"]
        relationships = (
            Relationship.objects.for_church(instance.church)
            .filter(Q(from_person=instance) | Q(to_person=instance))
            .filter(from_person_id__in=visible_ids, to_person_id__in=visible_ids)
            .select_related("from_person", "to_person")
            .order_by("kind", "id")
        )
        return RelationshipSerializer(
            relationships,
            many=True,
            context={"anchor_person_id": instance.pk},
        ).data

    def get_events_attended(self, instance: Person) -> list[dict[str, object]]:
        registrations = getattr(instance, "attended_event_registrations", ())
        return [
            {
                "id": registration.event_id,
                "title": registration.event.title,
                "starts_at": registration.event.starts_at.isoformat(),
                "location": registration.event.location,
                "checked_in_at": registration.checked_in_at.isoformat(),
            }
            for registration in registrations
        ]

    def get_follow_up_history(self, instance: Person) -> list[dict[str, object]]:
        follow_ups = getattr(instance, "visible_follow_up_history", ())
        return [
            {
                "id": follow_up.id,
                "source": follow_up.source,
                "status": follow_up.status,
                "assigned_to": (
                    follow_up.assigned_to.username
                    if follow_up.assigned_to is not None
                    else None
                ),
                "due_at": follow_up.due_at.isoformat() if follow_up.due_at else None,
                "closed_at": (
                    follow_up.closed_at.isoformat() if follow_up.closed_at else None
                ),
                "outcome": follow_up.outcome,
            }
            for follow_up in follow_ups
        ]

    def to_representation(self, instance: Person) -> dict[str, object]:
        data = super().to_representation(instance)
        request = self.context.get("request")
        membership = getattr(request, "church_membership", None)
        if membership is None or membership.role == ChurchMembership.Role.MEMBER:
            data.pop("follow_up_history", None)
        return data


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
