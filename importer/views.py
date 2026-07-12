from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from rest_framework import status as http_status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser

from expenses.models import Group, GroupMembership, Expense, ExpenseSplit, Payment
from .models import ImportSession, ImportRow, ImportAnomaly
from .serializers import ImportSessionSerializer, ImportUploadSerializer, ImportAnomalySerializer
from .parser import read_file, detect_anomalies, normalize_name, parse_participants, parse_split_details


class ImportUploadView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        serializer = ImportUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data["file"]
        group_id = serializer.validated_data["group_id"]
        exchange_rate = serializer.validated_data.get("exchange_rate_usd", Decimal("85.0"))

        try:
            group = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            return Response({"error": "Group not found"}, status=http_status.HTTP_404_NOT_FOUND)

        session = ImportSession.objects.create(
            uploaded_file=uploaded_file,
            group=group,
            uploaded_by=request.user,
            exchange_rate_usd=exchange_rate,
        )

        rows_data = read_file(uploaded_file)
        group_members = list(
            GroupMembership.objects.filter(group=group).values_list("display_name", flat=True)
        )
        member_dates = {}
        for m in GroupMembership.objects.filter(group=group):
            member_dates[m.display_name] = {
                "joined": m.joined_at,
                "left": m.left_at,
            }

        anomalies = detect_anomalies(rows_data, group_members, member_dates)

        anomaly_map = {}
        for a in anomalies:
            anomaly_map.setdefault(a["row_number"], []).append(a)

        for i, row_data in enumerate(rows_data):
            row_num = i + 2
            row_anomalies = anomaly_map.get(row_num, [])
            has_errors = any(a["severity"] == "error" for a in row_anomalies)

            import_row = ImportRow.objects.create(
                session=session,
                row_number=row_num,
                raw_data=row_data,
                parsed_data=row_data,
                status=ImportRow.STATUS_FLAGGED if row_anomalies else ImportRow.STATUS_OK,
            )

            for a in row_anomalies:
                ImportAnomaly.objects.create(
                    row=import_row,
                    anomaly_type=a["anomaly_type"],
                    description=a["description"],
                    severity=a["severity"],
                    auto_resolution=a.get("auto_resolution", ""),
                )

        return Response(
            ImportSessionSerializer(session).data,
            status=http_status.HTTP_201_CREATED,
        )


class ImportSessionDetailView(APIView):
    def get(self, request, pk):
        try:
            session = ImportSession.objects.get(id=pk)
        except ImportSession.DoesNotExist:
            return Response({"error": "Not found"}, status=http_status.HTTP_404_NOT_FOUND)

        return Response(ImportSessionSerializer(session).data)


class ImportRowResolveView(APIView):
    def patch(self, request, session_pk, row_pk):
        try:
            row = ImportRow.objects.get(id=row_pk, session_id=session_pk)
        except ImportRow.DoesNotExist:
            return Response({"error": "Not found"}, status=http_status.HTTP_404_NOT_FOUND)

        new_status = request.data.get("status")
        if new_status in [ImportRow.STATUS_OK, ImportRow.STATUS_SKIPPED, ImportRow.STATUS_MODIFIED]:
            row.status = new_status

        if "parsed_data" in request.data:
            row.parsed_data = request.data["parsed_data"]

        row.save()

        anomaly_resolutions = request.data.get("anomaly_resolutions", {})
        for anomaly_id, resolution in anomaly_resolutions.items():
            try:
                anomaly = ImportAnomaly.objects.get(id=anomaly_id, row=row)
                anomaly.user_resolution = resolution
                anomaly.resolved = True
                anomaly.save()
            except ImportAnomaly.DoesNotExist:
                continue

        from .serializers import ImportRowSerializer
        return Response(ImportRowSerializer(row).data)


class ImportCommitView(APIView):
    def post(self, request, pk):
        try:
            session = ImportSession.objects.get(id=pk)
        except ImportSession.DoesNotExist:
            return Response({"error": "Not found"}, status=http_status.HTTP_404_NOT_FOUND)

        if session.status == ImportSession.STATUS_COMMITTED:
            return Response({"error": "Already committed"}, status=http_status.HTTP_400_BAD_REQUEST)

        group = session.group
        exchange_rate = session.exchange_rate_usd
        created = 0
        skipped = 0
        payments_created = 0

        for row in session.rows.exclude(status=ImportRow.STATUS_SKIPPED):
            data = row.parsed_data or row.raw_data
            result = self._create_expense_from_row(data, group, exchange_rate)
            if result == "expense":
                created += 1
            elif result == "payment":
                payments_created += 1
            elif result == "skipped":
                skipped += 1

        session.status = ImportSession.STATUS_COMMITTED
        session.save()

        return Response({
            "status": "committed",
            "expenses_created": created,
            "payments_created": payments_created,
            "rows_skipped": skipped,
        })

    def _create_expense_from_row(self, data, group, exchange_rate):
        description = str(data.get("description", "")).strip()
        paid_by_raw = str(data.get("paid_by", "")).strip()
        amount_raw = data.get("amount", 0)
        currency = str(data.get("currency", "INR")).strip().upper()
        split_type = str(data.get("split_type", "")).strip().lower()
        split_with_raw = str(data.get("split_with", ""))
        split_details_raw = data.get("split_details")
        notes = str(data.get("notes") or "")
        date_raw = data.get("date")

        if currency in ("", "NONE"):
            currency = "INR"

        try:
            amount = Decimal(str(amount_raw))
        except (InvalidOperation, ValueError):
            return "skipped"

        if amount == 0:
            return "skipped"

        try:
            if isinstance(date_raw, str):
                expense_date = datetime.strptime(date_raw, "%Y-%m-%d").date()
            else:
                expense_date = date.today()
        except (ValueError, TypeError):
            expense_date = date.today()

        if expense_date.year < 2020:
            expense_date = expense_date.replace(year=2026)

        paid_by_name = normalize_name(paid_by_raw)
        if not paid_by_name:
            return "skipped"

        paid_by, _ = GroupMembership.objects.get_or_create(
            group=group, display_name=paid_by_name,
            defaults={"joined_at": expense_date},
        )

        is_settlement = (
            not split_type or
            split_type == "none" or
            any(kw in description.lower() for kw in ["paid back", "settlement", "deposit share"])
        )

        participants = parse_participants(split_with_raw)
        if is_settlement and len(participants) == 1:
            to_member, _ = GroupMembership.objects.get_or_create(
                group=group, display_name=participants[0],
                defaults={"joined_at": expense_date},
            )
            amount_inr = abs(amount) * exchange_rate if currency == "USD" else abs(amount)
            Payment.objects.create(
                group=group,
                from_member=paid_by,
                to_member=to_member,
                amount=abs(amount),
                currency=currency,
                amount_inr=amount_inr,
                date=expense_date,
                notes=notes,
            )
            return "payment"

        if not split_type or split_type == "none":
            split_type = "equal"

        amount_inr = amount * exchange_rate if currency == "USD" else amount
        if amount < 0:
            amount_inr = abs(amount_inr)
            amount = abs(amount)
            notes = f"[REFUND] {notes}".strip()

        expense = Expense.objects.create(
            group=group,
            description=description,
            paid_by=paid_by,
            amount=amount,
            currency=currency,
            amount_inr=amount_inr,
            date=expense_date,
            split_type=split_type,
            notes=notes,
        )

        for p_name in participants:
            member, _ = GroupMembership.objects.get_or_create(
                group=group, display_name=p_name,
                defaults={"joined_at": expense_date},
            )

            if split_type == "equal":
                share = amount_inr / len(participants) if participants else amount_inr
            elif split_type == "share" and split_details_raw:
                details = parse_split_details(str(split_details_raw))
                total_shares = sum(Decimal(v) for v in details.values()) or Decimal("1")
                my_shares = Decimal(details.get(p_name, "1"))
                share = amount_inr * my_shares / total_shares
            elif split_type == "percentage" and split_details_raw:
                details = parse_split_details(str(split_details_raw))
                pct = Decimal(details.get(p_name, "0").replace("%", ""))
                total_pct = sum(Decimal(v.replace("%", "")) for v in details.values()) or Decimal("100")
                share = amount_inr * pct / total_pct
            elif split_type == "unequal" and split_details_raw:
                details = parse_split_details(str(split_details_raw))
                share = Decimal(details.get(p_name, "0"))
                if currency == "USD":
                    share = share * exchange_rate
            else:
                share = amount_inr / len(participants) if participants else amount_inr

            ExpenseSplit.objects.create(
                expense=expense,
                member=member,
                share_amount_inr=round(share, 2),
            )

        return "expense"
