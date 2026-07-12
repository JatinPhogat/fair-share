from rest_framework import serializers
from .models import Group, GroupMembership, Expense, ExpenseSplit, Payment


class GroupMembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupMembership
        fields = ["id", "display_name", "joined_at", "left_at", "user"]
        read_only_fields = ["id"]


class GroupSerializer(serializers.ModelSerializer):
    memberships = GroupMembershipSerializer(many=True, read_only=True)

    class Meta:
        model = Group
        fields = ["id", "name", "description", "default_currency", "created_at", "memberships"]
        read_only_fields = ["id", "created_at"]


class GroupCreateSerializer(serializers.ModelSerializer):
    members = serializers.ListField(child=serializers.DictField(), write_only=True)

    class Meta:
        model = Group
        fields = ["id", "name", "description", "default_currency", "members"]

    def create(self, validated_data):
        members_data = validated_data.pop("members")
        validated_data["created_by"] = self.context["request"].user
        group = Group.objects.create(**validated_data)

        for m in members_data:
            GroupMembership.objects.create(
                group=group,
                display_name=m["display_name"],
                joined_at=m.get("joined_at", group.created_at.date()),
                left_at=m.get("left_at"),
                user=None,
            )

        return group


class ExpenseSplitSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source="member.display_name", read_only=True)

    class Meta:
        model = ExpenseSplit
        fields = ["id", "member", "member_name", "share_amount_inr"]


class ExpenseSerializer(serializers.ModelSerializer):
    splits = ExpenseSplitSerializer(many=True, read_only=True)
    paid_by_name = serializers.CharField(source="paid_by.display_name", read_only=True)

    class Meta:
        model = Expense
        fields = [
            "id", "description", "paid_by", "paid_by_name", "amount",
            "currency", "amount_inr", "date", "split_type", "notes",
            "splits", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ExpenseCreateSerializer(serializers.Serializer):
    description = serializers.CharField(max_length=500)
    paid_by = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField(max_length=3, default="INR")
    date = serializers.DateField()
    split_type = serializers.ChoiceField(choices=Expense.SPLIT_TYPES)
    split_with = serializers.ListField(child=serializers.IntegerField())
    split_details = serializers.DictField(required=False, default=dict)
    notes = serializers.CharField(required=False, default="", allow_blank=True)


class PaymentSerializer(serializers.ModelSerializer):
    from_name = serializers.CharField(source="from_member.display_name", read_only=True)
    to_name = serializers.CharField(source="to_member.display_name", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id", "from_member", "from_name", "to_member", "to_name",
            "amount", "currency", "amount_inr", "date", "notes", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class BalanceSerializer(serializers.Serializer):
    member_id = serializers.IntegerField()
    member_name = serializers.CharField()
    total_paid = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_owed = serializers.DecimalField(max_digits=12, decimal_places=2)
    net_balance = serializers.DecimalField(max_digits=12, decimal_places=2)


class DebtSerializer(serializers.Serializer):
    from_id = serializers.IntegerField()
    from_name = serializers.CharField()
    to_id = serializers.IntegerField()
    to_name = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
