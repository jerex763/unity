from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from people.importer import import_people_csv
from people.models import Person
from tenancy.models import Church

pytestmark = pytest.mark.django_db


def test_csv_import_creates_then_updates_people_idempotently() -> None:
    church = Church.objects.create(name="Fictional Import Church")
    csv_text = (
        "full_name,email,phone,membership_status,interests,home_country\n"
        "Mia Example,MIA@example.test,+61000000001,newcomer,Music;Community,au\n"
    )

    first = import_people_csv(StringIO(csv_text), church=church)
    second = import_people_csv(
        StringIO(csv_text.replace("newcomer", "member")),
        church=church,
    )

    assert (first.created, first.updated, first.errors) == (1, 0, [])
    assert (second.created, second.updated, second.errors) == (0, 1, [])
    person = Person.objects.get(church=church)
    assert person.email == "mia@example.test"
    assert person.membership_status == Person.MembershipStatus.MEMBER
    assert person.interests == ["Music", "Community"]
    assert person.home_country == "AU"

    import_people_csv(
        StringIO("full_name,email\nRenamed Example,mia@example.test\n"),
        church=church,
    )
    person.refresh_from_db()
    assert person.full_name == "Renamed Example"
    assert person.phone == "+61000000001"


def test_csv_import_is_atomic_and_reports_source_rows() -> None:
    church = Church.objects.create(name="Fictional Atomic Import")
    csv_text = (
        "full_name,email,date_of_birth\n"
        "Valid Example,valid@example.test,2000-01-01\n"
        "Broken Example,broken@example.test,not-a-date\n"
    )

    result = import_people_csv(StringIO(csv_text), church=church)

    assert not result.succeeded
    assert [(error.row, error.message) for error in result.errors] == [
        (3, "date_of_birth must use YYYY-MM-DD")
    ]
    assert not Person.objects.filter(church=church).exists()


def test_csv_import_dry_run_rolls_back_valid_rows() -> None:
    church = Church.objects.create(name="Fictional Dry Run Import")

    result = import_people_csv(
        StringIO("full_name,email\nDry Run Person,dry@example.test\n"),
        church=church,
        dry_run=True,
    )

    assert result.succeeded
    assert result.created == 1
    assert not Person.objects.filter(church=church).exists()


def test_csv_import_rejects_unknown_columns_and_invalid_choices() -> None:
    church = Church.objects.create(name="Fictional Invalid Import")

    unknown = import_people_csv(
        StringIO("full_name,password\nPerson Example,secret\n"),
        church=church,
    )
    invalid = import_people_csv(
        StringIO("full_name,gender\nPerson Example,unknown\n"),
        church=church,
    )

    assert "unsupported columns: password" in unknown.errors[0].message
    assert invalid.errors[0].row == 2
    assert "gender must be one of" in invalid.errors[0].message


def test_management_command_imports_and_rejects_bad_batches(
    tmp_path,
    capsys,
) -> None:
    church = Church.objects.create(name="Fictional Command Import")
    valid_path = tmp_path / "valid.csv"
    valid_path.write_text(
        "full_name,email\nCommand Person,command@example.test\n",
        encoding="utf-8",
    )
    invalid_path = tmp_path / "invalid.csv"
    invalid_path.write_text(
        "full_name,date_of_birth\nBroken Person,yesterday\n",
        encoding="utf-8",
    )

    call_command(
        "import_people_csv",
        valid_path,
        church_id=church.id,
    )

    assert "1 created, 0 updated" in capsys.readouterr().out
    with pytest.raises(CommandError, match="row 2"):
        call_command(
            "import_people_csv",
            invalid_path,
            church_id=church.id,
        )
