from datetime import datetime

from django.utils import timezone
from rest_framework import serializers

from .models import ConsentRecord


class ConsentRecordSerializer(serializers.ModelSerializer):
    recorded_by = serializers.CharField(source="recorded_by.username", read_only=True)
    supersedes_id = serializers.IntegerField(read_only=True)
    recorded_at = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = ConsentRecord
        fields = (
            "id",
            "status",
            "notice_version",
            "consented_at",
            "method",
            "recorded_by",
            "supersedes_id",
            "recorded_at",
        )
        read_only_fields = ("id",)

    def validate_consented_at(self, value: datetime) -> datetime:
        if value > timezone.now():
            raise serializers.ValidationError(
                "The consent decision time cannot be in the future."
            )
        return value
