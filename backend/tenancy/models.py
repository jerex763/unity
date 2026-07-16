from django.db import models


class Church(models.Model):
    """Tenant root for all church-owned data."""

    name = models.CharField(max_length=200)
    timezone = models.CharField(max_length=50, default="Australia/Sydney")
    locale = models.CharField(max_length=10, default="en-AU")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "church"

    def __str__(self) -> str:
        return self.name
