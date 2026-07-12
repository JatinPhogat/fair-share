from django.test import TestCase
from importer.parser import (
    normalize_name, parse_split_details, parse_participants,
    detect_anomalies, read_file,
)


class NormalizeNameTest(TestCase):
    def test_lowercase(self):
        self.assertEqual(normalize_name("priya"), "Priya")

    def test_trailing_space(self):
        self.assertEqual(normalize_name("rohan "), "Rohan")

    def test_variant(self):
        self.assertEqual(normalize_name("Priya S"), "Priya")

    def test_empty(self):
        self.assertEqual(normalize_name(""), "")

    def test_unknown_name(self):
        self.assertEqual(normalize_name("Kabir"), "Kabir")


class ParseSplitDetailsTest(TestCase):
    def test_percentage(self):
        result = parse_split_details("Aisha 30%; Rohan 30%; Priya 30%; Meera 20%")
        self.assertEqual(result["Aisha"], "30%")
        self.assertEqual(result["Meera"], "20%")

    def test_shares(self):
        result = parse_split_details("Aisha 1; Rohan 2; Priya 1; Dev 2")
        self.assertEqual(result["Rohan"], "2")

    def test_unequal_amounts(self):
        result = parse_split_details("Rohan 700; Priya 400; Meera 400")
        self.assertEqual(result["Rohan"], "700")

    def test_empty(self):
        self.assertEqual(parse_split_details(""), {})
        self.assertEqual(parse_split_details(None), {})


class ParseParticipantsTest(TestCase):
    def test_semicolon_separated(self):
        result = parse_participants("Aisha;Rohan;Priya;Meera")
        self.assertEqual(result, ["Aisha", "Rohan", "Priya", "Meera"])

    def test_normalizes_names(self):
        result = parse_participants("aisha;rohan ;Priya S")
        self.assertEqual(result, ["Aisha", "Rohan", "Priya"])


class DetectAnomaliesTest(TestCase):
    def setUp(self):
        self.members = ["Aisha", "Rohan", "Priya", "Meera", "Dev", "Sam"]
        self.member_dates = {
            "Aisha": {"joined": None, "left": None},
            "Rohan": {"joined": None, "left": None},
            "Priya": {"joined": None, "left": None},
            "Meera": {"joined": None, "left": "2026-03-31"},
            "Dev": {"joined": None, "left": None},
            "Sam": {"joined": "2026-04-08", "left": None},
        }

    def test_missing_paid_by(self):
        rows = [{"date": "2026-02-22", "description": "Supplies", "paid_by": None,
                 "amount": 780, "currency": "INR", "split_type": "equal",
                 "split_with": "Aisha;Rohan", "split_details": None, "notes": ""}]
        anomalies = detect_anomalies(rows, self.members, self.member_dates)
        types = [a["anomaly_type"] for a in anomalies]
        self.assertIn("missing_field", types)

    def test_zero_amount(self):
        rows = [{"date": "2026-03-22", "description": "Swiggy", "paid_by": "Priya",
                 "amount": 0, "currency": "INR", "split_type": "equal",
                 "split_with": "Aisha;Rohan;Priya", "split_details": None, "notes": ""}]
        anomalies = detect_anomalies(rows, self.members, self.member_dates)
        types = [a["anomaly_type"] for a in anomalies]
        self.assertIn("zero_amount", types)

    def test_negative_amount(self):
        rows = [{"date": "2026-03-12", "description": "Refund", "paid_by": "Dev",
                 "amount": -30, "currency": "USD", "split_type": "equal",
                 "split_with": "Aisha;Rohan;Priya;Dev", "split_details": None, "notes": ""}]
        anomalies = detect_anomalies(rows, self.members, self.member_dates)
        types = [a["anomaly_type"] for a in anomalies]
        self.assertIn("negative_amount", types)

    def test_settlement_detection(self):
        rows = [{"date": "2026-02-25", "description": "Rohan paid Aisha back",
                 "paid_by": "Rohan", "amount": 5000, "currency": "INR",
                 "split_type": None, "split_with": "Aisha",
                 "split_details": None, "notes": "settlement"}]
        anomalies = detect_anomalies(rows, self.members, self.member_dates)
        types = [a["anomaly_type"] for a in anomalies]
        self.assertIn("settlement", types)

    def test_percentage_mismatch(self):
        rows = [{"date": "2026-02-28", "description": "Pizza", "paid_by": "Aisha",
                 "amount": 1440, "currency": "INR", "split_type": "percentage",
                 "split_with": "Aisha;Rohan;Priya;Meera",
                 "split_details": "Aisha 30%; Rohan 30%; Priya 30%; Meera 20%",
                 "notes": ""}]
        anomalies = detect_anomalies(rows, self.members, self.member_dates)
        types = [a["anomaly_type"] for a in anomalies]
        self.assertIn("percentage_mismatch", types)

    def test_missing_currency(self):
        rows = [{"date": "2026-03-15", "description": "Groceries", "paid_by": "Priya",
                 "amount": 2105, "currency": None, "split_type": "equal",
                 "split_with": "Aisha;Rohan;Priya", "split_details": None, "notes": ""}]
        anomalies = detect_anomalies(rows, self.members, self.member_dates)
        types = [a["anomaly_type"] for a in anomalies]
        self.assertIn("currency_missing", types)

    def test_wrong_year(self):
        rows = [{"date": "2014-03-01", "description": "Airport cab", "paid_by": "Rohan",
                 "amount": 1100, "currency": "INR", "split_type": "equal",
                 "split_with": "Aisha;Rohan", "split_details": None, "notes": ""}]
        anomalies = detect_anomalies(rows, self.members, self.member_dates)
        types = [a["anomaly_type"] for a in anomalies]
        self.assertIn("date_anomaly", types)

    def test_duplicate_same_amount(self):
        rows = [
            {"date": "2026-02-08", "description": "Dinner at Marina Bites", "paid_by": "Dev",
             "amount": 3200, "currency": "INR", "split_type": "equal",
             "split_with": "Aisha;Rohan;Priya;Dev", "split_details": None, "notes": ""},
            {"date": "2026-02-08", "description": "dinner - marina bites", "paid_by": "Dev",
             "amount": 3200, "currency": "INR", "split_type": "equal",
             "split_with": "Aisha;Rohan;Priya;Dev", "split_details": None, "notes": ""},
        ]
        anomalies = detect_anomalies(rows, self.members, self.member_dates)
        types = [a["anomaly_type"] for a in anomalies]
        self.assertIn("duplicate", types)

    def test_duplicate_different_amount(self):
        rows = [
            {"date": "2026-03-11", "description": "Dinner at Thalassa", "paid_by": "Aisha",
             "amount": 2400, "currency": "INR", "split_type": "equal",
             "split_with": "Aisha;Rohan;Priya;Dev", "split_details": None, "notes": ""},
            {"date": "2026-03-11", "description": "Thalassa dinner", "paid_by": "Rohan",
             "amount": 2450, "currency": "INR", "split_type": "equal",
             "split_with": "Aisha;Rohan;Priya;Dev", "split_details": None, "notes": ""},
        ]
        anomalies = detect_anomalies(rows, self.members, self.member_dates)
        # Different payers so not flagged as duplicate — this is correct behavior
        dup_anomalies = [a for a in anomalies if a["anomaly_type"] == "duplicate"]
        self.assertEqual(len(dup_anomalies), 0)

    def test_unknown_participant(self):
        rows = [{"date": "2026-03-11", "description": "Parasailing", "paid_by": "Dev",
                 "amount": 150, "currency": "USD", "split_type": "equal",
                 "split_with": "Aisha;Rohan;Priya;Dev;Dev's friend Kabir",
                 "split_details": None, "notes": ""}]
        anomalies = detect_anomalies(rows, self.members, self.member_dates)
        types = [a["anomaly_type"] for a in anomalies]
        self.assertIn("unknown_participant", types)

    def test_name_casing_flagged(self):
        rows = [{"date": "2026-02-14", "description": "Snacks", "paid_by": "priya",
                 "amount": 640, "currency": "INR", "split_type": "equal",
                 "split_with": "Aisha;Rohan;Priya", "split_details": None, "notes": ""}]
        anomalies = detect_anomalies(rows, self.members, self.member_dates)
        types = [a["anomaly_type"] for a in anomalies]
        self.assertIn("name_casing", types)

    def test_split_type_mismatch(self):
        rows = [{"date": "2026-04-18", "description": "Furniture", "paid_by": "Aisha",
                 "amount": 12000, "currency": "INR", "split_type": "equal",
                 "split_with": "Aisha;Rohan;Priya;Sam",
                 "split_details": "Aisha 1; Rohan 1; Priya 1; Sam 1", "notes": ""}]
        anomalies = detect_anomalies(rows, self.members, self.member_dates)
        types = [a["anomaly_type"] for a in anomalies]
        self.assertIn("split_mismatch", types)
