from django.core.exceptions import ImproperlyConfigured
from django.db.models import QuerySet

from .models import ChurchScopedQuerySet
from .permissions import HasActiveChurchMembership


class ChurchScopedQuerysetMixin:
    """Require an active church and scope DRF querysets before object lookup."""

    permission_classes = (HasActiveChurchMembership,)

    def get_queryset(self) -> QuerySet:
        queryset = super().get_queryset()
        church = getattr(self.request, "church", None)
        if church is None:
            return queryset.none()
        if not isinstance(queryset, ChurchScopedQuerySet):
            raise ImproperlyConfigured(
                "ChurchScopedQuerysetMixin requires a ChurchScopedManager queryset."
            )
        return queryset.for_church(church)
