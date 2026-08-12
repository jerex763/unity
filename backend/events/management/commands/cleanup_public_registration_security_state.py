from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from events.models import (
    PublicRegistrationIdentityLock,
    PublicRegistrationRateLimit,
)


class Command(BaseCommand):
    help = "Delete expired public-registration rate buckets and stale identity locks."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--identity-days", type=int, default=30)

    @transaction.atomic
    def handle(self, *args: object, **options: object) -> None:
        identity_days = int(options["identity_days"])
        if identity_days < 1:
            raise ValueError("--identity-days must be at least 1")
        now = timezone.now()
        rate_cutoff = now - timedelta(days=1)
        identity_cutoff = now - timedelta(days=identity_days)
        rate_deleted, _ = PublicRegistrationRateLimit.objects.filter(
            window_started_at__lt=rate_cutoff
        ).delete()
        stale_locks = PublicRegistrationIdentityLock.objects.select_for_update().filter(
            updated_at__lt=identity_cutoff
        )
        identity_deleted, _ = stale_locks.delete()
        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {rate_deleted} rate rows and "
                f"{identity_deleted} identity locks."
            )
        )
