from rest_framework import serializers
from .models import ImportSession, ImportRow, ImportAnomaly


class ImportAnomalySerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportAnomaly
        fields = [
            "id", "anomaly_type", "description", "severity",
            "auto_resolution", "user_resolution", "resolved",
        ]


class ImportRowSerializer(serializers.ModelSerializer):
    anomalies = ImportAnomalySerializer(many=True, read_only=True)

    class Meta:
        model = ImportRow
        fields = ["id", "row_number", "raw_data", "parsed_data", "status", "anomalies"]


class ImportSessionSerializer(serializers.ModelSerializer):
    rows = ImportRowSerializer(many=True, read_only=True)
    row_count = serializers.SerializerMethodField()
    anomaly_count = serializers.SerializerMethodField()

    class Meta:
        model = ImportSession
        fields = [
            "id", "group", "status", "exchange_rate_usd",
            "created_at", "rows", "row_count", "anomaly_count",
        ]

    def get_row_count(self, obj):
        return obj.rows.count()

    def get_anomaly_count(self, obj):
        return ImportAnomaly.objects.filter(row__session=obj).count()


class ImportUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    group_id = serializers.IntegerField()
    exchange_rate_usd = serializers.DecimalField(
        max_digits=8, decimal_places=2, default=85.0
    )
