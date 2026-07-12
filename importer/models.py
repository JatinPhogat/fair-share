from django.db import models
from django.conf import settings
from expenses.models import Group


class ImportSession(models.Model):
    STATUS_PENDING = "pending"
    STATUS_REVIEWED = "reviewed"
    STATUS_COMMITTED = "committed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending Review"),
        (STATUS_REVIEWED, "Reviewed"),
        (STATUS_COMMITTED, "Committed"),
    ]

    uploaded_file = models.FileField(upload_to="imports/")
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="import_sessions")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    exchange_rate_usd = models.DecimalField(
        max_digits=8, decimal_places=2, default=85.0,
        help_text="USD to INR exchange rate used for this import",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "import_sessions"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Import #{self.pk} for {self.group.name} ({self.status})"


class ImportRow(models.Model):
    STATUS_OK = "ok"
    STATUS_FLAGGED = "flagged"
    STATUS_SKIPPED = "skipped"
    STATUS_MODIFIED = "modified"
    STATUS_CHOICES = [
        (STATUS_OK, "OK"),
        (STATUS_FLAGGED, "Flagged"),
        (STATUS_SKIPPED, "Skipped"),
        (STATUS_MODIFIED, "Modified"),
    ]

    session = models.ForeignKey(ImportSession, on_delete=models.CASCADE, related_name="rows")
    row_number = models.PositiveIntegerField()
    raw_data = models.JSONField()
    parsed_data = models.JSONField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OK)

    class Meta:
        db_table = "import_rows"
        ordering = ["row_number"]
        unique_together = [("session", "row_number")]

    def __str__(self) -> str:
        return f"Row {self.row_number}: {self.raw_data.get('description', 'N/A')}"


class ImportAnomaly(models.Model):
    TYPE_DUPLICATE = "duplicate"
    TYPE_MISSING_FIELD = "missing_field"
    TYPE_SETTLEMENT = "settlement"
    TYPE_PERCENTAGE_MISMATCH = "percentage_mismatch"
    TYPE_NAME_VARIANT = "name_variant"
    TYPE_CURRENCY_MISSING = "currency_missing"
    TYPE_MULTI_CURRENCY = "multi_currency"
    TYPE_DATE_ANOMALY = "date_anomaly"
    TYPE_ZERO_AMOUNT = "zero_amount"
    TYPE_NEGATIVE_AMOUNT = "negative_amount"
    TYPE_UNKNOWN_PARTICIPANT = "unknown_participant"
    TYPE_MEMBERSHIP_VIOLATION = "membership_violation"
    TYPE_SPLIT_MISMATCH = "split_mismatch"
    TYPE_NAME_CASING = "name_casing"

    TYPE_CHOICES = [
        (TYPE_DUPLICATE, "Duplicate Entry"),
        (TYPE_MISSING_FIELD, "Missing Required Field"),
        (TYPE_SETTLEMENT, "Settlement as Expense"),
        (TYPE_PERCENTAGE_MISMATCH, "Percentage Sum ≠ 100%"),
        (TYPE_NAME_VARIANT, "Name Variant Detected"),
        (TYPE_CURRENCY_MISSING, "Missing Currency"),
        (TYPE_MULTI_CURRENCY, "Multi-Currency Entry"),
        (TYPE_DATE_ANOMALY, "Date Anomaly"),
        (TYPE_ZERO_AMOUNT, "Zero Amount"),
        (TYPE_NEGATIVE_AMOUNT, "Negative Amount (Refund)"),
        (TYPE_UNKNOWN_PARTICIPANT, "Unknown Participant"),
        (TYPE_MEMBERSHIP_VIOLATION, "Membership Temporal Violation"),
        (TYPE_SPLIT_MISMATCH, "Split Type/Details Mismatch"),
        (TYPE_NAME_CASING, "Name Casing Inconsistency"),
    ]

    SEVERITY_ERROR = "error"
    SEVERITY_WARNING = "warning"
    SEVERITY_INFO = "info"
    SEVERITY_CHOICES = [
        (SEVERITY_ERROR, "Error"),
        (SEVERITY_WARNING, "Warning"),
        (SEVERITY_INFO, "Info"),
    ]

    row = models.ForeignKey(ImportRow, on_delete=models.CASCADE, related_name="anomalies")
    anomaly_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    description = models.TextField()
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    auto_resolution = models.TextField(blank=True, default="")
    user_resolution = models.TextField(blank=True, default="")
    resolved = models.BooleanField(default=False)

    class Meta:
        db_table = "import_anomalies"
        ordering = ["-severity", "row__row_number"]

    def __str__(self) -> str:
        return f"[{self.severity}] Row {self.row.row_number}: {self.anomaly_type}"
