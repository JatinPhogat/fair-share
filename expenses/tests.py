from decimal import Decimal
from datetime import date

from django.test import TestCase
from django.contrib.auth import get_user_model

from expenses.models import Group, GroupMembership, Expense, ExpenseSplit, Payment
from expenses.balance import calculate_balances, simplify_debts

User = get_user_model()


class BalanceCalculationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@test.com", username="testuser", password="testpass123"
        )
        self.group = Group.objects.create(name="Test Group", created_by=self.user)
        self.alice = GroupMembership.objects.create(
            group=self.group, display_name="Alice", joined_at=date(2026, 1, 1)
        )
        self.bob = GroupMembership.objects.create(
            group=self.group, display_name="Bob", joined_at=date(2026, 1, 1)
        )
        self.charlie = GroupMembership.objects.create(
            group=self.group, display_name="Charlie", joined_at=date(2026, 1, 1)
        )

    def test_equal_split_balances(self):
        expense = Expense.objects.create(
            group=self.group, description="Dinner", paid_by=self.alice,
            amount=300, currency="INR", amount_inr=300,
            date=date(2026, 2, 1), split_type="equal",
        )
        for member in [self.alice, self.bob, self.charlie]:
            ExpenseSplit.objects.create(
                expense=expense, member=member, share_amount_inr=Decimal("100")
            )

        balances = calculate_balances(self.group)
        alice_bal = next(b for b in balances if b["member_name"] == "Alice")
        bob_bal = next(b for b in balances if b["member_name"] == "Bob")

        self.assertEqual(alice_bal["total_paid"], Decimal("300"))
        self.assertEqual(alice_bal["total_owed"], Decimal("100"))
        self.assertEqual(alice_bal["net_balance"], Decimal("200"))
        self.assertEqual(bob_bal["net_balance"], Decimal("-100"))

    def test_payment_affects_balance(self):
        expense = Expense.objects.create(
            group=self.group, description="Rent", paid_by=self.alice,
            amount=600, currency="INR", amount_inr=600,
            date=date(2026, 2, 1), split_type="equal",
        )
        for member in [self.alice, self.bob, self.charlie]:
            ExpenseSplit.objects.create(
                expense=expense, member=member, share_amount_inr=Decimal("200")
            )

        Payment.objects.create(
            group=self.group, from_member=self.bob, to_member=self.alice,
            amount=200, currency="INR", amount_inr=200, date=date(2026, 2, 5),
        )

        balances = calculate_balances(self.group)
        alice_bal = next(b for b in balances if b["member_name"] == "Alice")
        bob_bal = next(b for b in balances if b["member_name"] == "Bob")

        # Alice: paid 600 (expense) - 200 (received payment counted as negative), owed 200
        # Bob: paid 200 (payment), owed 200 → net = 0
        self.assertEqual(bob_bal["net_balance"], Decimal("0"))

    def test_all_settled_no_debts(self):
        expense = Expense.objects.create(
            group=self.group, description="Food", paid_by=self.alice,
            amount=200, currency="INR", amount_inr=200,
            date=date(2026, 2, 1), split_type="equal",
        )
        for member in [self.alice, self.bob]:
            ExpenseSplit.objects.create(
                expense=expense, member=member, share_amount_inr=Decimal("100")
            )

        Payment.objects.create(
            group=self.group, from_member=self.bob, to_member=self.alice,
            amount=100, currency="INR", amount_inr=100, date=date(2026, 2, 5),
        )

        debts = simplify_debts(self.group)
        meaningful_debts = [d for d in debts if d["amount"] > Decimal("0.01")]
        self.assertEqual(len(meaningful_debts), 0)


class DebtSimplificationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test2@test.com", username="testuser2", password="testpass123"
        )
        self.group = Group.objects.create(name="Simplify Group", created_by=self.user)
        self.a = GroupMembership.objects.create(
            group=self.group, display_name="A", joined_at=date(2026, 1, 1)
        )
        self.b = GroupMembership.objects.create(
            group=self.group, display_name="B", joined_at=date(2026, 1, 1)
        )
        self.c = GroupMembership.objects.create(
            group=self.group, display_name="C", joined_at=date(2026, 1, 1)
        )

    def test_simplifies_to_minimum_transactions(self):
        # A pays 300 split equally (A, B, C each owe 100)
        # B pays 150 split equally (each owe 50)
        # Net: A = 300-100-50=150, B = 150-100-50=0, C = -100-50=-150
        # Should simplify to: C pays A 150
        e1 = Expense.objects.create(
            group=self.group, description="E1", paid_by=self.a,
            amount=300, currency="INR", amount_inr=300,
            date=date(2026, 2, 1), split_type="equal",
        )
        for m in [self.a, self.b, self.c]:
            ExpenseSplit.objects.create(expense=e1, member=m, share_amount_inr=Decimal("100"))

        e2 = Expense.objects.create(
            group=self.group, description="E2", paid_by=self.b,
            amount=150, currency="INR", amount_inr=150,
            date=date(2026, 2, 2), split_type="equal",
        )
        for m in [self.a, self.b, self.c]:
            ExpenseSplit.objects.create(expense=e2, member=m, share_amount_inr=Decimal("50"))

        debts = simplify_debts(self.group)
        self.assertEqual(len(debts), 1)
        self.assertEqual(debts[0]["from_name"], "C")
        self.assertEqual(debts[0]["to_name"], "A")
        self.assertEqual(debts[0]["amount"], Decimal("150"))

    def test_no_expenses_no_debts(self):
        debts = simplify_debts(self.group)
        self.assertEqual(len(debts), 0)
