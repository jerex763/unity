from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from people.importer import import_people_csv
from tenancy.models import Church


class Command(BaseCommand):
    help = "Create or update people in one church from a UTF-8 CSV file."

    def add_arguments(self, parser) -> None:
        parser.add_argument("csv_path", type=Path)
        parser.add_argument("--church-id", type=int, required=True)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: object, **options: object) -> None:
        try:
            church = Church.objects.get(pk=options["church_id"])
        except Church.DoesNotExist as error:
            raise CommandError("Church not found.") from error
        path = options["csv_path"]
        try:
            with path.open(encoding="utf-8-sig", newline="") as source:
                result = import_people_csv(
                    source,
                    church=church,
                    dry_run=options["dry_run"],
                )
        except (OSError, UnicodeDecodeError) as error:
            raise CommandError(str(error)) from error
        if result.errors:
            details = "\n".join(
                f"row {item.row}: {item.message}" for item in result.errors
            )
            raise CommandError(f"Import rejected; no changes saved.\n{details}")
        prefix = "Dry run: " if result.dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"{prefix}{result.created} created, {result.updated} updated."
            )
        )
