from decimal import Decimal

from django.conf import settings
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Group, GroupMembership, Expense, ExpenseSplit, Payment
from .serializers import (
    GroupSerializer, GroupCreateSerializer, GroupMembershipSerializer,
    ExpenseSerializer, ExpenseCreateSerializer,
    PaymentSerializer, BalanceSerializer, DebtSerializer,
)
from .balance import calculate_balances, simplify_debts


class GroupViewSet(viewsets.ModelViewSet):
    serializer_class = GroupSerializer

    def get_queryset(self):
        return Group.objects.all()

    def get_serializer_class(self):
        if self.action == "create":
            return GroupCreateSerializer
        return GroupSerializer

    @action(detail=True, methods=["post"], url_path="add-member")
    def add_member(self, request, pk=None):
        group = self.get_object()
        serializer = GroupMembershipSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(group=group)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def balances(self, request, pk=None):
        group = self.get_object()
        data = calculate_balances(group)
        serializer = BalanceSerializer(data, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def debts(self, request, pk=None):
        group = self.get_object()
        data = simplify_debts(group)
        serializer = DebtSerializer(data, many=True)
        return Response(serializer.data)


class ExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer

    def get_queryset(self):
        group_id = self.kwargs.get("group_pk")
        if group_id:
            return Expense.objects.filter(group_id=group_id)
        return Expense.objects.all()

    def get_serializer_class(self):
        if self.action == "create":
            return ExpenseCreateSerializer
        return ExpenseSerializer

    def create(self, request, *args, **kwargs):
        serializer = ExpenseCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        group_id = self.kwargs.get("group_pk")
        paid_by = GroupMembership.objects.get(id=data["paid_by"])
        exchange_rate = Decimal(str(settings.EXCHANGE_RATES.get("USD_TO_INR", 85)))

        amount = data["amount"]
        currency = data["currency"]
        amount_inr = amount * exchange_rate if currency == "USD" else amount

        expense = Expense.objects.create(
            group_id=group_id,
            description=data["description"],
            paid_by=paid_by,
            amount=amount,
            currency=currency,
            amount_inr=amount_inr,
            date=data["date"],
            split_type=data["split_type"],
            notes=data.get("notes", ""),
        )

        member_ids = data["split_with"]
        members = GroupMembership.objects.filter(id__in=member_ids)
        split_type = data["split_type"]
        details = data.get("split_details", {})

        if split_type == "equal":
            share = amount_inr / len(members)
            for m in members:
                ExpenseSplit.objects.create(expense=expense, member=m, share_amount_inr=round(share, 2))

        elif split_type == "unequal":
            for m in members:
                share = Decimal(str(details.get(str(m.id), 0)))
                if currency == "USD":
                    share = share * exchange_rate
                ExpenseSplit.objects.create(expense=expense, member=m, share_amount_inr=share)

        elif split_type == "percentage":
            for m in members:
                pct = Decimal(str(details.get(str(m.id), 0)))
                share = amount_inr * pct / 100
                ExpenseSplit.objects.create(expense=expense, member=m, share_amount_inr=round(share, 2))

        elif split_type == "share":
            total_shares = sum(Decimal(str(details.get(str(m.id), 1))) for m in members)
            for m in members:
                shares = Decimal(str(details.get(str(m.id), 1)))
                share = amount_inr * shares / total_shares
                ExpenseSplit.objects.create(expense=expense, member=m, share_amount_inr=round(share, 2))

        return Response(ExpenseSerializer(expense).data, status=status.HTTP_201_CREATED)


class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer

    def get_queryset(self):
        group_id = self.kwargs.get("group_pk")
        if group_id:
            return Payment.objects.filter(group_id=group_id)
        return Payment.objects.all()

    def perform_create(self, serializer):
        group_id = self.kwargs.get("group_pk")
        amount = serializer.validated_data["amount"]
        currency = serializer.validated_data.get("currency", "INR")
        exchange_rate = Decimal(str(settings.EXCHANGE_RATES.get("USD_TO_INR", 85)))
        amount_inr = amount * exchange_rate if currency == "USD" else amount
        serializer.save(group_id=group_id, amount_inr=amount_inr)
