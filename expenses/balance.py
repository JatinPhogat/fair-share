from decimal import Decimal
from collections import defaultdict

from expenses.models import Expense, ExpenseSplit, Payment, GroupMembership


def calculate_balances(group) -> list[dict]:
    members = GroupMembership.objects.filter(group=group)
    paid = defaultdict(Decimal)
    owed = defaultdict(Decimal)

    for expense in Expense.objects.filter(group=group):
        paid[expense.paid_by_id] += expense.amount_inr

    for split in ExpenseSplit.objects.filter(expense__group=group):
        owed[split.member_id] += split.share_amount_inr

    # Factor in settlements
    for payment in Payment.objects.filter(group=group):
        paid[payment.from_member_id] += payment.amount_inr
        paid[payment.to_member_id] -= payment.amount_inr

    result = []
    for m in members:
        total_paid = paid.get(m.id, Decimal("0"))
        total_owed = owed.get(m.id, Decimal("0"))
        result.append({
            "member_id": m.id,
            "member_name": m.display_name,
            "total_paid": total_paid,
            "total_owed": total_owed,
            "net_balance": total_paid - total_owed,
        })

    return result


def simplify_debts(group) -> list[dict]:
    """Greedy debt simplification: minimize the number of transactions."""
    balances = calculate_balances(group)

    creditors = []
    debtors = []
    for b in balances:
        net = b["net_balance"]
        if net > 0:
            creditors.append({"id": b["member_id"], "name": b["member_name"], "amount": net})
        elif net < 0:
            debtors.append({"id": b["member_id"], "name": b["member_name"], "amount": abs(net)})

    creditors.sort(key=lambda x: x["amount"], reverse=True)
    debtors.sort(key=lambda x: x["amount"], reverse=True)

    settlements = []
    i, j = 0, 0
    while i < len(debtors) and j < len(creditors):
        debtor = debtors[i]
        creditor = creditors[j]
        transfer = min(debtor["amount"], creditor["amount"])

        if transfer > Decimal("0.01"):
            settlements.append({
                "from_id": debtor["id"],
                "from_name": debtor["name"],
                "to_id": creditor["id"],
                "to_name": creditor["name"],
                "amount": round(transfer, 2),
            })

        debtor["amount"] -= transfer
        creditor["amount"] -= transfer

        if debtor["amount"] < Decimal("0.01"):
            i += 1
        if creditor["amount"] < Decimal("0.01"):
            j += 1

    return settlements
