from django.db import models


class ChurchScopedQuerySet(models.QuerySet):
    def for_church(self, church: "Church") -> "ChurchScopedQuerySet":
        return self.filter(church=church)


class ChurchScopedManager(models.Manager):
    def get_queryset(self) -> ChurchScopedQuerySet:
        return ChurchScopedQuerySet(self.model, using=self._db)

    def for_church(self, church: "Church") -> ChurchScopedQuerySet:
        return self.get_queryset().for_church(church)


class TimeStampedModel(models.Model):
    """Shared creation and update timestamps for persisted domain models."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ChurchScopedModel(TimeStampedModel):
    """Base for records owned by exactly one church."""

    church = models.ForeignKey("tenancy.Church", on_delete=models.CASCADE)
    objects = ChurchScopedManager()

    class Meta:
        abstract = True


class Church(TimeStampedModel):
    """Tenant root for all church-owned data."""

    name = models.CharField(max_length=200)
    timezone = models.CharField(max_length=50, default="Australia/Sydney")
    locale = models.CharField(max_length=10, default="en-AU")

    class Meta:
        db_table = "church"

    def __str__(self) -> str:
        return self.name
