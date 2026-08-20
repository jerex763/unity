from django.utils import timezone
from rest_framework import serializers

from accounts.access import groups_visible_to, people_visible_to
from groups.models import Group
from people.models import Person

from .models import Event, EventRegistration
from .services import registration_is_open


class EventRegistrationSerializer(serializers.ModelSerializer):
    person = serializers.SerializerMethodField()

    class Meta:
        model = EventRegistration
        fields = (
            "id",
            "person",
            "status",
            "note",
            "registered_at",
            "checked_in_at",
            "checkin_method",
        )
        read_only_fields = fields

    def get_person(self, instance: EventRegistration) -> dict[str, object]:
        return {
            "id": instance.person_id,
            "full_name": instance.person.full_name,
            "preferred_name": instance.person.preferred_name,
        }


class EventRegistrationCreateSerializer(serializers.Serializer):
    person = serializers.PrimaryKeyRelatedField(
        queryset=Person.objects.none(),
        required=False,
    )
    note = serializers.CharField(allow_blank=True, max_length=200, required=False)

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        membership = self.context["request"].church_membership
        self.fields["person"].queryset = people_visible_to(
            Person.objects.all(),
            membership,
        )

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        membership = self.context["request"].church_membership
        if "person" not in attrs:
            if membership.person is None:
                raise serializers.ValidationError(
                    {"person": "Choose a person for this registration."}
                )
            attrs["person"] = membership.person
        return attrs


class WalkInCreateSerializer(serializers.Serializer):
    person = serializers.IntegerField(min_value=1, required=False)
    full_name = serializers.CharField(max_length=200, required=False)
    preferred_name = serializers.CharField(
        allow_blank=True,
        max_length=100,
        required=False,
    )
    email = serializers.EmailField(allow_blank=True, required=False)
    phone = serializers.CharField(allow_blank=True, max_length=30, required=False)
    has_whatsapp = serializers.BooleanField(default=False)
    wechat_id = serializers.CharField(
        allow_blank=True,
        max_length=100,
        required=False,
    )
    preferred_contact = serializers.ChoiceField(
        allow_blank=True,
        choices=Person.PreferredContact.choices,
        required=False,
    )
    note = serializers.CharField(allow_blank=True, max_length=200, required=False)

    def validate_full_name(self, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise serializers.ValidationError("Full name is required.")
        return normalized

    def validate_email(self, value: str) -> str:
        return value.strip().lower()

    def validate_phone(self, value: str) -> str:
        return value.strip()

    def validate_wechat_id(self, value: str) -> str:
        return value.strip()

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        if attrs.get("person"):
            return attrs
        if not attrs.get("full_name"):
            raise serializers.ValidationError({"full_name": "Full name is required."})
        if not any(attrs.get(field) for field in ("email", "phone", "wechat_id")):
            raise serializers.ValidationError(
                {
                    "contact": (
                        "Provide at least one contact method: email, phone, "
                        "or WeChat ID."
                    )
                }
            )
        if attrs.get("has_whatsapp") and not attrs.get("phone"):
            raise serializers.ValidationError(
                {"has_whatsapp": "WhatsApp requires a phone number."}
            )
        self._validate_preferred_contact(attrs)
        return attrs

    @staticmethod
    def _validate_preferred_contact(attrs: dict[str, object]) -> None:
        preferred = attrs.get("preferred_contact")
        available = {
            Person.PreferredContact.PHONE: bool(attrs.get("phone")),
            Person.PreferredContact.WHATSAPP: bool(
                attrs.get("phone") and attrs.get("has_whatsapp")
            ),
            Person.PreferredContact.WECHAT: bool(attrs.get("wechat_id")),
            Person.PreferredContact.EMAIL: bool(attrs.get("email")),
        }
        if preferred and not available[preferred]:
            raise serializers.ValidationError(
                {"preferred_contact": "Choose an available contact method."}
            )


class ManualCheckInSerializer(serializers.Serializer):
    checked_in = serializers.BooleanField()


class PublicRegistrationSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=200)
    email = serializers.EmailField(allow_blank=True, required=False)
    phone = serializers.CharField(allow_blank=True, max_length=30, required=False)
    has_whatsapp = serializers.BooleanField(default=False)
    wechat_id = serializers.CharField(
        allow_blank=True,
        max_length=100,
        required=False,
    )
    preferred_contact = serializers.ChoiceField(
        allow_blank=True,
        choices=Person.PreferredContact.choices,
        required=False,
    )
    consent = serializers.BooleanField()
    notice_version = serializers.CharField(max_length=50)
    website = serializers.CharField(allow_blank=True, required=False, write_only=True)

    def validate_full_name(self, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise serializers.ValidationError("This field is required.")
        return normalized

    def validate_email(self, value: str) -> str:
        return value.strip().lower()

    def validate_phone(self, value: str) -> str:
        return value.strip()

    def validate_wechat_id(self, value: str) -> str:
        return value.strip()

    def validate_consent(self, value: bool) -> bool:
        if not value:
            raise serializers.ValidationError("Consent is required.")
        return value

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        if attrs.get("website"):
            raise serializers.ValidationError({"detail": "Unable to process request."})
        if not any(attrs.get(field) for field in ("email", "phone", "wechat_id")):
            raise serializers.ValidationError(
                {
                    "contact": (
                        "Provide at least one contact method: email, phone, "
                        "or WeChat ID."
                    )
                }
            )
        if attrs.get("has_whatsapp") and not attrs.get("phone"):
            raise serializers.ValidationError(
                {"has_whatsapp": "WhatsApp requires a phone number."}
            )
        WalkInCreateSerializer._validate_preferred_contact(attrs)
        return attrs


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
    places_available = serializers.SerializerMethodField()
    my_registration = serializers.SerializerMethodField()
    public_registration_enabled = serializers.SerializerMethodField()

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
            "places_available",
            "my_registration",
            "public_registration_enabled",
            "registered_count",
            "waitlisted_count",
            "created_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "registration_open",
            "places_available",
            "my_registration",
            "public_registration_enabled",
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
        if (
            self.instance is None
            and starts_at is not None
            and starts_at < timezone.now()
        ):
            errors["starts_at"] = "Start time cannot be in the past."
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
        return registration_is_open(instance, now=timezone.now())

    def get_places_available(self, instance: Event) -> bool:
        registered_count = getattr(instance, "registered_count", 0)
        return instance.capacity is None or registered_count < instance.capacity

    def get_my_registration(self, instance: Event) -> dict[str, object] | None:
        registrations = getattr(instance, "my_event_registration", ())
        if not registrations:
            return None
        return EventRegistrationSerializer(registrations[0]).data

    def get_registered_count(self, instance: Event) -> int:
        return getattr(instance, "registered_count", 0)

    def get_waitlisted_count(self, instance: Event) -> int:
        return getattr(instance, "waitlisted_count", 0)

    def get_public_registration_enabled(self, instance: Event) -> bool:
        link = getattr(instance, "public_registration_link", None)
        return link is not None and link.revoked_at is None
