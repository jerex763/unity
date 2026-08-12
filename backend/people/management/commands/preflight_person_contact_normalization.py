from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from people.models import Person
from people.normalization import normalize_email


class Command(BaseCommand):
    help = (
        "Fail before migration when historical same-church emails collide after "
        "normalization. No contact values are printed."
    )

    def handle(self, *args: object, **options: object) -> None:
        if Person._meta.db_table not in connection.introspection.table_names():
            self.stdout.write("Person table does not exist yet; preflight passed.")
            return

        matches: dict[tuple[int, str], list[int]] = defaultdict(list)
        for row in Person.objects.values("id", "church_id", "email").iterator():
            normalized = normalize_email(row["email"])
            if normalized:
                matches[(row["church_id"], normalized)].append(row["id"])
        collisions = [
            (church_id, sorted(ids))
            for (church_id, _normalized), ids in matches.items()
            if len(ids) > 1
        ]
        if collisions:
            details = "; ".join(
                f"church_id={church_id} person_ids={ids}"
                for church_id, ids in sorted(collisions)
            )
            raise CommandError(
                "Normalized email collisions must be reviewed before migration: "
                + details
            )
        self.stdout.write(self.style.SUCCESS("Person contact normalization passed."))
