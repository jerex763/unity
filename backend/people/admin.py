import re
from io import StringIO

from django.contrib import admin
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.core import signing
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import QuerySet
from django.http import HttpRequest
from django.shortcuts import render
from django.template.response import TemplateResponse
from django.urls import path

from accounts.models import ChurchMembership
from config.admin import SuperuserOnlyAdminMixin

from .forms import (
    FictionalTestPersonCleanupForm,
    PersonAdminForm,
    PersonCsvImportForm,
)
from .importer import import_people_csv
from .lifecycle import deactivate_person, hard_delete_person
from .models import ConsentRecord, Household, Person, Relationship


@admin.register(Household)
class HouseholdAdmin(SuperuserOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("name", "church", "updated_at")
    list_filter = ("church",)
    search_fields = ("name", "church__name")
    list_select_related = ("church",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Person)
class PersonAdmin(SuperuserOnlyAdminMixin, admin.ModelAdmin):
    fictional_cleanup_manifest_max_age = 300
    fictional_cleanup_manifest_salt = "people.person.fictional-test-cleanup.v1"
    form = PersonAdminForm
    change_list_template = "admin/people/person/change_list.html"
    actions = (
        "deactivate_selected_people",
        "hard_delete_fictional_test_people",
    )
    sensitive_fields = ("discipleship_stage", "faith_background")
    list_display = (
        "full_name",
        "preferred_name",
        "church",
        "membership_status",
        "email",
        "phone",
        "wechat_id",
        "updated_at",
    )
    list_filter = (
        "church",
        "membership_status",
        "gender",
        "has_whatsapp",
    )
    search_fields = ("full_name", "preferred_name", "email", "phone", "wechat_id")
    autocomplete_fields = ("household", "invited_by")
    list_select_related = ("church", "household", "invited_by")
    readonly_fields = (
        "created_at",
        "updated_at",
        "deactivated_at",
        "anonymized_at",
    )

    def get_urls(self):
        return [
            path(
                "import-csv/",
                self.admin_site.admin_view(self.import_csv_view),
                name="people_person_import_csv",
            )
        ] + super().get_urls()

    def import_csv_view(self, request: HttpRequest):
        if not self.has_change_permission(request):
            raise PermissionDenied
        result = None
        form = PersonCsvImportForm(request.POST or None, request.FILES or None)
        if request.method == "POST" and form.is_valid():
            upload = form.cleaned_data["csv_file"]
            try:
                result = import_people_csv(
                    StringIO(upload.read().decode("utf-8-sig")),
                    church=form.cleaned_data["church"],
                    dry_run=form.cleaned_data["dry_run"],
                )
            except UnicodeDecodeError:
                form.add_error("csv_file", "The CSV must be UTF-8 encoded.")
        context = {
            **self.admin_site.each_context(request),
            "title": "Import people from CSV",
            "form": form,
            "result": result,
        }
        return render(
            request,
            "admin/people/person/import_csv.html",
            context,
        )

    @admin.action(description="Deactivate selected people (preserves history)")
    def deactivate_selected_people(
        self,
        request: HttpRequest,
        queryset,
    ) -> None:
        count = 0
        for person in queryset:
            was_active = person.membership_status != Person.MembershipStatus.INACTIVE
            deactivate_person(person)
            count += int(was_active)
        self.message_user(request, f"Deactivated {count} people.")

    def _render_fictional_test_cleanup_confirmation(
        self,
        request: HttpRequest,
        *,
        people: list[Person],
        form: FictionalTestPersonCleanupForm,
        selection_manifest: str,
    ) -> TemplateResponse:
        context = {
            **self.admin_site.each_context(request),
            "title": "Confirm fictional test person cleanup",
            "opts": self.model._meta,
            "form": form,
            "selected_people": people,
            "action_checkbox_name": ACTION_CHECKBOX_NAME,
            "selection_manifest": selection_manifest,
        }
        return TemplateResponse(
            request,
            "admin/people/person/confirm_fictional_test_cleanup.html",
            context,
        )

    def _sign_fictional_cleanup_selection(
        self,
        request: HttpRequest,
        person_ids: list[int],
    ) -> str:
        return signing.dumps(
            {
                "version": 1,
                "user_id": request.user.pk,
                "person_ids": person_ids,
            },
            salt=self.fictional_cleanup_manifest_salt,
        )

    def _load_fictional_cleanup_selection(
        self,
        request: HttpRequest,
    ) -> tuple[list[int], str | None]:
        selection_manifest = request.POST.get("selection_manifest", "")
        try:
            payload = signing.loads(
                selection_manifest,
                salt=self.fictional_cleanup_manifest_salt,
                max_age=self.fictional_cleanup_manifest_max_age,
            )
        except signing.SignatureExpired:
            return [], "The cleanup confirmation expired. Select the targets again."
        except signing.BadSignature:
            return [], "The cleanup selection could not be verified. Select it again."

        if not isinstance(payload, dict) or set(payload) != {
            "version",
            "user_id",
            "person_ids",
        }:
            return [], "The cleanup selection is invalid. Select the targets again."
        person_ids = payload["person_ids"]
        valid_ids = (
            isinstance(person_ids, list)
            and bool(person_ids)
            and all(
                type(person_id) is int and person_id > 0 for person_id in person_ids
            )
            and person_ids == sorted(set(person_ids))
        )
        if (
            payload["version"] != 1
            or payload["user_id"] != request.user.pk
            or not valid_ids
        ):
            return [], "The cleanup selection is invalid. Select the targets again."
        return person_ids, None

    @staticmethod
    def _submitted_selection_matches(
        submitted_ids: list[str],
        signed_ids: list[int],
    ) -> bool:
        expected_ids = [str(person_id) for person_id in signed_ids]
        if len(submitted_ids) != len(set(submitted_ids)):
            return False
        return sorted(submitted_ids) == sorted(expected_ids)

    @staticmethod
    def _contains_run_id_token(value: str, run_id: str) -> bool:
        return (
            re.search(
                rf"(?<![A-Za-z0-9]){re.escape(run_id)}(?![A-Za-z0-9])",
                value,
            )
            is not None
        )

    @classmethod
    def _is_eligible_fictional_test_person(
        cls,
        person: Person,
        run_id: str,
    ) -> bool:
        email = person.email or ""
        email_suffix = "@example.test"
        has_test_domain = email.lower().endswith(email_suffix)
        email_local_part = email[: -len(email_suffix)] if has_test_domain else ""
        return (
            person.membership_status == Person.MembershipStatus.VISITOR
            and has_test_domain
            and "@" not in email_local_part
            and cls._contains_run_id_token(person.full_name, run_id)
            and cls._contains_run_id_token(email_local_part, run_id)
        )

    @admin.action(description="Hard-delete selected fictional test people")
    def hard_delete_fictional_test_people(
        self,
        request: HttpRequest,
        queryset: QuerySet[Person],
    ) -> TemplateResponse | None:
        if request.POST.get("select_across") == "1":
            self.message_user(
                request,
                (
                    "Select individual fictional test people; "
                    "select-all cleanup is disabled."
                ),
                level="error",
            )
            return None

        if "confirm_cleanup" not in request.POST:
            people = list(queryset.order_by("church_id", "full_name", "pk"))
            person_ids = sorted(person.pk for person in people)
            return self._render_fictional_test_cleanup_confirmation(
                request,
                people=people,
                form=FictionalTestPersonCleanupForm(),
                selection_manifest=self._sign_fictional_cleanup_selection(
                    request,
                    person_ids,
                ),
            )

        form = FictionalTestPersonCleanupForm(request.POST)
        signed_ids, manifest_error = self._load_fictional_cleanup_selection(request)
        selection_manifest = request.POST.get("selection_manifest", "")
        if manifest_error is not None:
            form.add_error(None, manifest_error)
            return self._render_fictional_test_cleanup_confirmation(
                request,
                people=[],
                form=form,
                selection_manifest="",
            )

        signed_people = list(
            Person.objects.filter(pk__in=signed_ids).order_by(
                "church_id", "full_name", "pk"
            )
        )
        submitted_ids = request.POST.getlist(ACTION_CHECKBOX_NAME)
        if not self._submitted_selection_matches(submitted_ids, signed_ids):
            form.add_error(
                None,
                (
                    "The submitted targets differ from the confirmed selection. "
                    "Nothing was deleted."
                ),
            )
            return self._render_fictional_test_cleanup_confirmation(
                request,
                people=signed_people,
                form=form,
                selection_manifest=selection_manifest,
            )

        if not form.is_valid():
            return self._render_fictional_test_cleanup_confirmation(
                request,
                people=signed_people,
                form=form,
                selection_manifest=selection_manifest,
            )

        with transaction.atomic():
            people = list(
                Person.objects.select_for_update()
                .filter(pk__in=signed_ids)
                .order_by("church_id", "full_name", "pk")
            )
            selection_is_current = sorted(person.pk for person in people) == signed_ids
            run_id = form.cleaned_data["run_id"]
            linked_person_ids = set(
                ChurchMembership.objects.filter(person_id__in=signed_ids).values_list(
                    "person_id", flat=True
                )
            )
            all_are_eligible = all(
                self._is_eligible_fictional_test_person(person, run_id)
                and person.pk not in linked_person_ids
                for person in people
            )
            if not selection_is_current or not all_are_eligible:
                form.add_error(
                    None,
                    (
                        "Nothing was deleted. Every selected person must still be an "
                        "unlinked visitor whose name and @example.test email contain "
                        "this RUN_ID."
                    ),
                )
                return self._render_fictional_test_cleanup_confirmation(
                    request,
                    people=people,
                    form=form,
                    selection_manifest=selection_manifest,
                )

            for person in people:
                hard_delete_person(
                    person=person,
                    actor=request.user,
                    reason=Person.HardDeleteReason.TEST_DATA,
                    request=request,
                )

        self.message_user(
            request,
            f"Hard-deleted {len(people)} fictional test people; audit rows were kept.",
        )
        return None

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: object | None = None,
    ) -> bool:
        return False

    def get_exclude(
        self,
        request: HttpRequest,
        obj: Person | None = None,
    ) -> tuple[str, ...] | None:
        excluded = tuple(super().get_exclude(request, obj) or ())
        if request.user.is_superuser:
            return excluded or None
        return (*excluded, *self.sensitive_fields)


@admin.register(Relationship)
class RelationshipAdmin(SuperuserOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("from_person", "to_person", "kind", "church", "updated_at")
    list_filter = ("church", "kind")
    search_fields = ("from_person__full_name", "to_person__full_name")
    autocomplete_fields = ("from_person", "to_person")
    list_select_related = ("church", "from_person", "to_person")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ConsentRecord)
class ConsentRecordAdmin(SuperuserOnlyAdminMixin, admin.ModelAdmin):
    list_display = (
        "person",
        "status",
        "notice_version",
        "consented_at",
        "method",
        "recorded_by",
        "church",
    )
    list_filter = ("church", "status", "method", "notice_version", "consented_at")
    search_fields = (
        "person__full_name",
        "recorded_by__username",
        "notice_version",
    )
    list_select_related = ("church", "person", "recorded_by", "supersedes")
    date_hierarchy = "consented_at"
    readonly_fields = (
        "church",
        "person",
        "status",
        "notice_version",
        "consented_at",
        "method",
        "recorded_by",
        "supersedes",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: object | None = None,
    ) -> bool:
        return False

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: object | None = None,
    ) -> bool:
        return False
