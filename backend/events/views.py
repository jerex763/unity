from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.http import Http404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import Throttled, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.access import groups_visible_to
from accounts.models import ChurchMembership
from audit.models import AuditEvent
from audit.services import record_audit_event
from groups.models import Group
from people.models import Person, PersonQuerySet
from people.normalization import normalize_email, normalize_phone, normalize_wechat_id
from tenancy.permissions import HasActiveChurchMembership

from .models import Event, EventRegistration, PublicRegistrationLink
from .permissions import HasEventAccess, HasEventCheckIn
from .serializers import (
    EventRegistrationCreateSerializer,
    EventRegistrationSerializer,
    EventSerializer,
    ManualCheckInSerializer,
    PublicRegistrationSerializer,
    WalkInCreateSerializer,
)
from .services import (
    PublicRegistrationError,
    PublicRegistrationIdentityConflict,
    PublicRegistrationRateLimited,
    anonymous_public_registration_outcome,
    cancel_public_registration,
    cancel_registration,
    enforce_public_client_rate_limit,
    enforce_valid_public_token_rate_limit,
    public_cancellation_token_is_valid,
    public_event_for_token,
    register_for_event,
    register_public_visitor,
    registration_is_open,
    revoke_public_registration_link,
    rotate_public_registration_link,
    set_manual_check_in,
)


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
            .select_related("group", "created_by", "public_registration_link")
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


def _masked_contact_hint(person: Person) -> str | None:
    if person.email:
        local, separator, domain = person.email.partition("@")
        if separator:
            domain_name, dot, suffix = domain.rpartition(".")
            masked_domain = f"{domain_name[:1]}***.{suffix}" if dot else "***"
            return f"Email · {local[:1]}***@{masked_domain}"
    if person.phone:
        digits = "".join(character for character in person.phone if character.isdigit())
        return f"Phone · ending {digits[-4:]}" if digits else "Phone available"
    if person.wechat_id:
        return f"WeChat · {person.wechat_id[:1]}***"
    return None


def _locked_contact_candidates(
    people: PersonQuerySet,
    contact_predicate: Q,
) -> list[Person]:
    return list(people.select_for_update().filter(contact_predicate).order_by("pk"))


class EventCheckInPersonSearchView(EventRegistrationListCreateView):
    permission_classes = (HasActiveChurchMembership, HasEventCheckIn)
    http_method_names = ("get", "head", "options")

    def get(self, request: Request, event_id: int) -> Response:
        event = self._event(request, event_id)
        query = " ".join(request.query_params.get("q", "").split())[:100]
        if len(query) < 2:
            return Response([])

        contact_query = Q()
        normalized_email = normalize_email(query)
        normalized_phone = normalize_phone(query)
        normalized_wechat_id = normalize_wechat_id(query)
        if normalized_email:
            contact_query |= Q(normalized_email__icontains=normalized_email)
        if normalized_phone:
            contact_query |= Q(normalized_phone__icontains=normalized_phone)
        if normalized_wechat_id:
            contact_query |= Q(normalized_wechat_id__icontains=normalized_wechat_id)

        people = list(
            Person.objects.for_church(request.church)
            .filter(anonymized_at__isnull=True, deactivated_at__isnull=True)
            .exclude(membership_status=Person.MembershipStatus.INACTIVE)
            .filter(
                Q(full_name__icontains=query)
                | Q(preferred_name__icontains=query)
                | contact_query
            )
            .order_by("full_name", "id")[:20]
        )
        registration_statuses = dict(
            EventRegistration.objects.for_church(request.church)
            .filter(event=event, person_id__in=[person.id for person in people])
            .values_list("person_id", "status")
        )
        return Response(
            [
                {
                    "id": person.id,
                    "full_name": person.full_name,
                    "preferred_name": person.preferred_name,
                    "membership_status": person.membership_status,
                    "current_registration_status": registration_statuses.get(person.id),
                    "contact_hint": _masked_contact_hint(person),
                }
                for person in people
            ]
        )


class EventWalkInCreateView(EventRegistrationListCreateView):
    permission_classes = (HasActiveChurchMembership, HasEventCheckIn)

    @transaction.atomic
    def post(self, request: Request, event_id: int) -> Response:
        event = generics.get_object_or_404(
            Event.objects.select_for_update().for_church(request.church),
            pk=event_id,
        )
        if event.ends_at <= timezone.now():
            raise ValidationError({"detail": "Walk-in check-in is closed."})
        serializer = WalkInCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        people = Person.objects.for_church(request.church)
        person_id = values.get("person")
        person = None
        if person_id is not None:
            person = generics.get_object_or_404(
                people.select_for_update()
                .filter(
                    anonymized_at__isnull=True,
                    deactivated_at__isnull=True,
                )
                .exclude(membership_status=Person.MembershipStatus.INACTIVE),
                pk=person_id,
            )
        else:
            normalized_contacts = tuple(
                (field, value)
                for field, value in (
                    ("normalized_email", normalize_email(values.get("email"))),
                    ("normalized_phone", normalize_phone(values.get("phone"))),
                    (
                        "normalized_wechat_id",
                        normalize_wechat_id(values.get("wechat_id")),
                    ),
                )
                if value
            )
            contact_predicate = Q()
            for field, value in normalized_contacts:
                contact_predicate |= Q(**{field: value})
            locked_candidates = (
                _locked_contact_candidates(people, contact_predicate)
                if normalized_contacts
                else []
            )
            if any(
                candidate.anonymized_at is not None
                or candidate.deactivated_at is not None
                or candidate.membership_status == Person.MembershipStatus.INACTIVE
                for candidate in locked_candidates
            ):
                raise ValidationError(
                    {
                        "detail": (
                            "This contact needs Pastor or Admin review before check-in."
                        )
                    }
                )
            match_sets = [
                [
                    candidate.pk
                    for candidate in locked_candidates
                    if getattr(candidate, field) == value
                ]
                for field, value in normalized_contacts
            ]
            anchor = next((ids[0] for ids in match_sets if len(ids) == 1), None)
            if anchor is None and any(len(ids) > 1 for ids in match_sets):
                raise ValidationError({"detail": "Unable to match this contact."})
            if anchor is not None and any(
                ids and anchor not in ids for ids in match_sets
            ):
                raise ValidationError({"detail": "Unable to match this contact."})
            person = next(
                (
                    candidate
                    for candidate in locked_candidates
                    if candidate.pk == anchor
                ),
                None,
            )
            if anchor is not None and person is None:
                raise ValidationError(
                    {
                        "detail": (
                            "This contact needs Pastor or Admin review before check-in."
                        )
                    }
                )
        if person is None:
            person = Person(
                church=request.church,
                full_name=values["full_name"],
                preferred_name=values.get("preferred_name") or None,
                email=values.get("email") or None,
                phone=values.get("phone") or None,
                wechat_id=values.get("wechat_id") or None,
                has_whatsapp=values["has_whatsapp"],
                preferred_contact=values.get("preferred_contact") or None,
                membership_status=Person.MembershipStatus.VISITOR,
            )
            person.full_clean(exclude={"interests"})
            person.save()
        registration = (
            EventRegistration.objects.select_for_update()
            .filter(event=event, person=person)
            .first()
        )
        if registration is None:
            registration = EventRegistration.objects.create(
                church=request.church,
                event=event,
                person=person,
                status=EventRegistration.Status.WALK_IN,
                note=values.get("note", "").strip(),
            )
        elif registration.status == EventRegistration.Status.CANCELLED:
            registration.status = EventRegistration.Status.WALK_IN
            registration.note = values.get("note", "").strip()
            registration.registered_at = timezone.now()
            registration.cancellation_token_digest = None
            registration.save(
                update_fields=(
                    "status",
                    "note",
                    "registered_at",
                    "cancellation_token_digest",
                    "updated_at",
                )
            )
        try:
            registration = set_manual_check_in(registration, checked_in=True)
        except DjangoValidationError as error:
            raise ValidationError({"detail": error.messages[0]}) from error
        registration = EventRegistration.objects.select_related("person").get(
            pk=registration.pk
        )
        return Response(
            EventRegistrationSerializer(registration).data,
            status=status.HTTP_201_CREATED,
        )


class EventRegistrationCheckInView(EventRegistrationListCreateView):
    permission_classes = (HasActiveChurchMembership, HasEventCheckIn)

    def post(
        self,
        request: Request,
        event_id: int,
        registration_id: int,
    ) -> Response:
        event = self._event(request, event_id)
        registration = generics.get_object_or_404(
            EventRegistration.objects.select_related("person").for_church(
                request.church
            ),
            pk=registration_id,
            event=event,
        )
        serializer = ManualCheckInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            updated = set_manual_check_in(
                registration,
                checked_in=serializer.validated_data["checked_in"],
            )
        except DjangoValidationError as error:
            raise ValidationError({"detail": error.messages[0]}) from error
        updated = EventRegistration.objects.select_related("person").get(pk=updated.pk)
        return Response(EventRegistrationSerializer(updated).data)


class EventPublicLinkView(APIView):
    permission_classes = (HasActiveChurchMembership, HasEventAccess)

    def _event(self, request: Request, event_id: int) -> Event:
        return generics.get_object_or_404(
            Event.objects.for_church(request.church), pk=event_id
        )

    def post(self, request: Request, event_id: int) -> Response:
        event = self._event(request, event_id)
        try:
            link, token = rotate_public_registration_link(
                event=event, created_by=request.user
            )
        except DjangoValidationError as error:
            raise ValidationError({"detail": error.messages[0]}) from error
        record_audit_event(
            action=AuditEvent.Action.PUBLIC_EVENT_LINK_CREATED,
            actor=request.user,
            church=request.church,
            target=link,
            request=request,
        )
        return Response(
            {"url": request.build_absolute_uri(f"/register/{token}")},
            status=status.HTTP_201_CREATED,
        )

    def delete(self, request: Request, event_id: int) -> Response:
        event = self._event(request, event_id)
        link = generics.get_object_or_404(
            PublicRegistrationLink.objects.for_church(request.church), event=event
        )
        revoke_public_registration_link(link)
        record_audit_event(
            action=AuditEvent.Action.PUBLIC_EVENT_LINK_REVOKED,
            actor=request.user,
            church=request.church,
            target=link,
            request=request,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class PublicEventRegistrationView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    @staticmethod
    def _client_identifier(request: Request) -> str:
        remote = (request.META.get("REMOTE_ADDR") or "unknown").strip()
        trusted_hops = max(settings.PUBLIC_REGISTRATION_TRUSTED_PROXY_HOPS, 0)
        if trusted_hops == 0:
            return remote[:128]
        forwarded = [
            value.strip()
            for value in request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")
            if value.strip()
        ]
        chain = [*forwarded, remote]
        client_index = len(chain) - trusted_hops - 1
        if client_index < 0:
            return remote[:128]
        return chain[client_index][:128]

    def _event(self, request: Request, token: str) -> Event:
        client_identifier = self._client_identifier(request)
        try:
            enforce_public_client_rate_limit(client_identifier=client_identifier)
        except PublicRegistrationRateLimited as error:
            raise Throttled(
                detail="Unable to process request. Please try again later."
            ) from error
        event = public_event_for_token(token)
        if event is None:
            raise Http404
        try:
            enforce_valid_public_token_rate_limit(
                token=token,
                client_identifier=client_identifier,
            )
        except PublicRegistrationRateLimited as error:
            raise Throttled(
                detail="Unable to process request. Please try again later."
            ) from error
        return event

    def get(self, request: Request, token: str) -> Response:
        event = self._event(request, token)
        return Response(
            {
                "title": event.title,
                "description": event.description,
                "starts_at": event.starts_at,
                "ends_at": event.ends_at,
                "location": event.location,
                "registration_open": registration_is_open(event),
                "privacy_notice": {
                    "version": settings.PRIVACY_NOTICE_VERSION,
                    "text": settings.PRIVACY_NOTICE_TEXT,
                },
            }
        )

    def post(self, request: Request, token: str) -> Response:
        event = self._event(request, token)
        serializer = PublicRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        try:
            outcome = register_public_visitor(
                event=event,
                full_name=values["full_name"],
                email=values.get("email") or None,
                phone=values.get("phone") or None,
                wechat_id=values.get("wechat_id") or None,
                has_whatsapp=values["has_whatsapp"],
                preferred_contact=values.get("preferred_contact") or None,
                notice_version=values["notice_version"],
            )
        except PublicRegistrationIdentityConflict:
            # Contact ambiguity is indistinguishable from success to anonymous
            # callers. This prevents the endpoint becoming an identity oracle.
            outcome = anonymous_public_registration_outcome()
        except PublicRegistrationError as error:
            raise ValidationError(
                {"detail": "Unable to process registration."}
            ) from error
        if outcome.registration is not None:
            record_audit_event(
                action=AuditEvent.Action.PUBLIC_EVENT_REGISTERED,
                church=event.church,
                target=outcome.registration,
                request=request,
            )
        return Response(
            {
                "accepted": True,
                "event_title": event.title,
                "cancellation_url": request.build_absolute_uri(
                    f"/registration/cancel/{outcome.cancellation_token}"
                ),
            },
            status=status.HTTP_201_CREATED,
        )


class PublicEventCancellationView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    def post(self, request: Request, token: str) -> Response:
        client_identifier = PublicEventRegistrationView._client_identifier(request)
        try:
            enforce_public_client_rate_limit(client_identifier=client_identifier)
            if public_cancellation_token_is_valid(token):
                enforce_valid_public_token_rate_limit(
                    token=token,
                    client_identifier=client_identifier,
                )
            registration = cancel_public_registration(token)
        except PublicRegistrationRateLimited as error:
            raise Throttled(
                detail="Unable to process request. Please try again later."
            ) from error
        if registration is not None:
            record_audit_event(
                action=AuditEvent.Action.PUBLIC_EVENT_CANCELLED,
                church=registration.church,
                target=registration,
                request=request,
            )
        return Response({"status": "cancelled"})
