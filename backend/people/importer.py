import csv
from dataclasses import dataclass, field
from datetime import date
from io import TextIOBase

from django.core.exceptions import ValidationError
from django.db import transaction

from tenancy.models import Church

from .models import Person

MAX_IMPORT_ROWS = 10_000
SUPPORTED_COLUMNS = {
    "full_name",
    "preferred_name",
    "gender",
    "date_of_birth",
    "email",
    "phone",
    "has_whatsapp",
    "home_country",
    "suburb",
    "occupation",
    "university",
    "course",
    "interests",
    "membership_status",
    "discipleship_stage",
    "faith_background",
    "notes",
}


@dataclass
class ImportError:
    row: int
    message: str


@dataclass
class ImportResult:
    created: int = 0
    updated: int = 0
    errors: list[ImportError] = field(default_factory=list)
    dry_run: bool = False

    @property
    def succeeded(self) -> bool:
        return not self.errors


def _optional(value: str | None) -> str | None:
    normalized = (value or "").strip()
    return normalized or None


def _boolean(value: str | None) -> bool:
    normalized = (value or "").strip().lower()
    if normalized in {"1", "true", "yes", "y"}:
        return True
    if normalized in {"0", "false", "no", "n", ""}:
        return False
    raise ValueError("has_whatsapp must be yes/no, true/false, or 1/0")


def _person_values(row: dict[str, str | None]) -> dict[str, object]:
    full_name = " ".join((row.get("full_name") or "").split())
    if not full_name:
        raise ValueError("full_name is required")
    gender = _optional(row.get("gender")) or Person.Gender.UNSPECIFIED
    membership_status = (
        _optional(row.get("membership_status")) or Person.MembershipStatus.VISITOR
    )
    if gender not in Person.Gender.values:
        raise ValueError(f"gender must be one of: {', '.join(Person.Gender.values)}")
    if membership_status not in Person.MembershipStatus.values:
        raise ValueError(
            "membership_status must be one of: "
            + ", ".join(Person.MembershipStatus.values)
        )
    discipleship_stage = _optional(row.get("discipleship_stage"))
    if (
        discipleship_stage is not None
        and discipleship_stage not in Person.DiscipleshipStage.values
    ):
        raise ValueError(
            "discipleship_stage must be one of: "
            + ", ".join(Person.DiscipleshipStage.values)
        )
    birth_date = _optional(row.get("date_of_birth"))
    try:
        parsed_birth_date = date.fromisoformat(birth_date) if birth_date else None
    except ValueError as error:
        raise ValueError("date_of_birth must use YYYY-MM-DD") from error
    email = _optional(row.get("email"))
    values = {
        "full_name": full_name,
        "preferred_name": _optional(row.get("preferred_name")),
        "gender": gender,
        "date_of_birth": parsed_birth_date,
        "email": email.lower() if email else None,
        "phone": _optional(row.get("phone")),
        "has_whatsapp": _boolean(row.get("has_whatsapp")),
        "home_country": (_optional(row.get("home_country")) or "").upper() or None,
        "suburb": _optional(row.get("suburb")),
        "occupation": _optional(row.get("occupation")),
        "university": _optional(row.get("university")),
        "course": _optional(row.get("course")),
        "interests": [
            item.strip()
            for item in (row.get("interests") or "").split(";")
            if item.strip()
        ],
        "membership_status": membership_status,
        "discipleship_stage": discipleship_stage,
        "faith_background": _optional(row.get("faith_background")),
        "notes": (row.get("notes") or "").strip(),
    }
    return {name: value for name, value in values.items() if name in row}


def _find_existing(church: Church, values: dict[str, object]) -> Person | None:
    people = Person.objects.for_church(church)
    email = values.get("email")
    phone = values.get("phone")
    if email:
        matches = people.filter(email__iexact=email)
    elif phone:
        matches = people.filter(phone=phone)
    else:
        matches = people.filter(full_name__iexact=values["full_name"])
    count = matches.count()
    if count > 1:
        raise ValueError("multiple existing people match this row")
    return matches.first()


@transaction.atomic
def import_people_csv(
    source: TextIOBase,
    *,
    church: Church,
    dry_run: bool = False,
) -> ImportResult:
    result = ImportResult(dry_run=dry_run)
    reader = csv.DictReader(source)
    headers = set(reader.fieldnames or ())
    if "full_name" not in headers:
        result.errors.append(ImportError(row=1, message="full_name header is required"))
        transaction.set_rollback(True)
        return result
    unknown = headers - SUPPORTED_COLUMNS
    if unknown:
        result.errors.append(
            ImportError(
                row=1,
                message=f"unsupported columns: {', '.join(sorted(unknown))}",
            )
        )
        transaction.set_rollback(True)
        return result

    for index, row in enumerate(reader, start=2):
        if index > MAX_IMPORT_ROWS + 1:
            result.errors.append(
                ImportError(row=index, message=f"maximum {MAX_IMPORT_ROWS} rows")
            )
            break
        try:
            values = _person_values(row)
            existing = _find_existing(church, values)
            person = existing or Person(church=church)
            for name, value in values.items():
                setattr(person, name, value)
            # JSONField treats an empty list as blank during model-form style
            # validation, while an empty interests list is a valid model default.
            person.full_clean(exclude={"interests"})
            person.save()
            if existing:
                result.updated += 1
            else:
                result.created += 1
        except (ValueError, ValidationError) as error:
            if isinstance(error, ValidationError):
                message = "; ".join(error.messages)
            else:
                message = str(error)
            result.errors.append(ImportError(row=index, message=message))

    if result.errors or dry_run:
        transaction.set_rollback(True)
    return result
