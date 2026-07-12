from django.db import models
from django.conf import settings


class Group(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_groups",
    )
    default_currency = models.CharField(max_length=3, default="INR")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "groups"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name

    def active_members(self, as_of=None):
        qs = self.memberships.filter(left_at__isnull=True)
        if as_of:
            qs = self.memberships.filter(
                joined_at__lte=as_of
            ).filter(
                models.Q(left_at__isnull=True) | models.Q(left_at__gt=as_of)
            )
        return qs


class GroupMembership(models.Model):
    """Tracks who is in a group and when they joined/left.

    `user` is nullable to support non-registered participants (guests like Dev, Kabir).
    `display_name` is the canonical name used for matching during import.
    """
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="memberships",
    )
    display_name = models.CharField(max_length=100)
    joined_at = models.DateField()
    left_at = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "group_memberships"
        unique_together = [("group", "display_name")]
        ordering = ["joined_at"]

    def __str__(self) -> str:
        return f"{self.display_name} in {self.group.name}"

    def is_active(self, on_date=None) -> bool:
        if on_date is None:
            return self.left_at is None
        if self.joined_at > on_date:
            return False
        if self.left_at and self.left_at <= on_date:
            return False
        return True


class Expense(models.Model):
    SPLIT_EQUAL = "equal"
    SPLIT_UNEQUAL = "unequal"
    SPLIT_PERCENTAGE = "percentage"
    SPLIT_SHARE = "share"
    SPLIT_TYPES = [
        (SPLIT_EQUAL, "Equal"),
        (SPLIT_UNEQUAL, "Unequal"),
        (SPLIT_PERCENTAGE, "Percentage"),
        (SPLIT_SHARE, "By shares"),
    ]

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="expenses")
    description = models.CharField(max_length=500)
    paid_by = models.ForeignKey(
        GroupMembership, on_delete=models.CASCADE, related_name="expenses_paid"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="INR")
    amount_inr = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="Converted amount in INR for balance calculation",
    )
    date = models.DateField()
    split_type = models.CharField(max_length=20, choices=SPLIT_TYPES)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "expenses"
        ordering = ["-date", "-created_at"]

    def __str__(self) -> str:
        return f"{self.description} - {self.currency} {self.amount}"


class ExpenseSplit(models.Model):
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name="splits")
    member = models.ForeignKey(
        GroupMembership, on_delete=models.CASCADE, related_name="expense_splits"
    )
    share_amount_inr = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "expense_splits"
        unique_together = [("expense", "member")]

    def __str__(self) -> str:
        return f"{self.member.display_name} owes ₹{self.share_amount_inr} for {self.expense.description}"


class Payment(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="payments")
    from_member = models.ForeignKey(
        GroupMembership, on_delete=models.CASCADE, related_name="payments_made"
    )
    to_member = models.ForeignKey(
        GroupMembership, on_delete=models.CASCADE, related_name="payments_received"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="INR")
    amount_inr = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "payments"
        ordering = ["-date"]

    def __str__(self) -> str:
        return f"{self.from_member.display_name} → {self.to_member.display_name}: ₹{self.amount_inr}"
