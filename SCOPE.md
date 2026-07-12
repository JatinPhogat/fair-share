# SCOPE.md — Anomaly Log & Database Schema

## Database Schema

```
users
├── id (PK)
├── email (UNIQUE)
├── username
├── password (hashed)
└── date_joined

groups
├── id (PK)
├── name
├── description
├── default_currency
├── created_by → users.id
└── created_at

group_memberships
├── id (PK)
├── group → groups.id
├── user → users.id (nullable, for guests)
├── display_name
├── joined_at (date)
├── left_at (date, nullable)
└── UNIQUE(group, display_name)

expenses
├── id (PK)
├── group → groups.id
├── description
├── paid_by → group_memberships.id
├── amount
├── currency (INR/USD)
├── amount_inr (converted)
├── date
├── split_type (equal/unequal/percentage/share)
├── notes
└── created_at

expense_splits
├── id (PK)
├── expense → expenses.id
├── member → group_memberships.id
├── share_amount_inr
└── UNIQUE(expense, member)

payments (settlements)
├── id (PK)
├── group → groups.id
├── from_member → group_memberships.id
├── to_member → group_memberships.id
├── amount
├── currency
├── amount_inr
├── date
├── notes
└── created_at

import_sessions
├── id (PK)
├── uploaded_file
├── group → groups.id
├── uploaded_by → users.id
├── status (pending/reviewed/committed)
├── exchange_rate_usd
└── created_at

import_rows
├── id (PK)
├── session → import_sessions.id
├── row_number
├── raw_data (JSON)
├── parsed_data (JSON)
├── status (ok/flagged/skipped/modified)
└── UNIQUE(session, row_number)

import_anomalies
├── id (PK)
├── row → import_rows.id
├── anomaly_type
├── description
├── severity (error/warning/info)
├── auto_resolution
├── user_resolution
└── resolved (bool)
```

## Anomaly Log

Every data problem found in `expenses_export.csv` and how the importer handles it:

| # | Row | Problem | Type | Severity | How Handled |
|---|-----|---------|------|----------|-------------|
| 1 | 5–6 | **Duplicate entry** — "Dinner at Marina Bites" (row 5) and "dinner - marina bites" (row 6). Same date (Feb 8), same payer (Dev), same amount (3200). | `duplicate` | warning | Fuzzy string matching on description + exact match on date/payer/amount. Row 6 flagged as duplicate, user can keep or skip. |
| 2 | 13 | **Settlement logged as expense** — "Rohan paid Aisha back", ₹5000. No split_type. Notes say "this is a settlement not an expense??" | `settlement` | warning | Keywords "paid back" in description + null split_type detected. Imported as a Payment record (from Rohan to Aisha), not an Expense. |
| 3 | 12 | **Missing paid_by** — "House cleaning supplies", paid_by is empty. Notes: "can't remember who paid" | `missing_field` | error | Flagged as error requiring user resolution before commit. Cannot create expense without a payer. |
| 4 | 14 | **Percentages sum to 110%** — Pizza Friday: Aisha 30% + Rohan 30% + Priya 30% + Meera 20% = 110% | `percentage_mismatch` | error | Validator sums all percentage values. 110 ≠ 100 triggers error. User must correct before commit. On commit, we normalize: each share = (their_pct / total_pct) × amount, so the ratios are preserved even if the user approves as-is. |
| 5 | 8 | **Inconsistent name casing** — "priya" (lowercase) instead of "Priya" | `name_casing` | info | All names are run through `normalize_name()` which strips whitespace and applies title-case. Auto-resolved. |
| 6 | 10 | **Name variant** — "Priya S" used instead of "Priya" | `name_variant` | warning | `KNOWN_NAME_VARIANTS` lookup table maps "priya s" → "Priya". Flagged for user confirmation. |
| 7 | 19, 20, 22, 25 | **Multi-currency (USD)** — Goa trip expenses in USD without exchange rate in the data | `multi_currency` | info | User provides USD→INR exchange rate at import time (defaults to 85.0). All USD amounts converted to INR for balance calculation. Original currency preserved on the expense record. |
| 8 | 26 | **Wrong year** — Airport cab date is 2014-03-01 instead of 2026-03-01 | `date_anomaly` | error | Any date with year < 2020 is flagged. Auto-suggestion: replace year with 2026. On commit, dates with year < 2020 are corrected to 2026. |
| 9 | 27 | **Missing currency** — "Groceries DMart" on Mar 15, currency is None. Notes: "forgot to set currency" | `currency_missing` | warning | Null/empty currency detected. Defaults to INR with warning. |
| 10 | 30 | **Zero amount** — "Dinner order Swiggy" has amount = 0. Notes: "counted twice earlier - fixing later" | `zero_amount` | warning | Zero-amount expenses are flagged. On commit, zero-amount rows are skipped entirely. |
| 11 | 25 | **Negative amount** — "Parasailing refund", -$30 USD | `negative_amount` | warning | Negative amounts treated as refunds. On commit, the absolute value is used and notes are prefixed with "[REFUND]". The split still happens normally (everyone gets money back). |
| 12 | 22 | **Unknown participant** — "Dev's friend Kabir" is not a group member | `unknown_participant` | warning | Participant names that don't match any group member and have no close fuzzy match are flagged. On commit, unknown participants are added as guest members (GroupMembership with user=null). |
| 13 | 23–24 | **Duplicate with different amounts** — "Dinner at Thalassa" ₹2400 (Aisha) vs "Thalassa dinner" ₹2450 (Rohan). Notes on row 24: "Aisha also logged this I think hers is wrong" | `duplicate` | error | Same-date entries with similar descriptions but different amounts flagged as error. User must decide which to keep. Notes suggest row 24 (₹2450 by Rohan) is correct. |
| 14 | 33 | **Ambiguous date** — Deep cleaning service dated 2026-05-04. Notes: "is this April 5 or May 4? format is a mess" | `date_anomaly` | warning | Notes containing "date" or "format" trigger additional review flag. The date as parsed (May 4) is presented to user for confirmation. |
| 15 | 35 | **Meera included after move-out** — Groceries on Apr 2 includes Meera, who left end of March | `membership_violation` | warning | Cross-references expense date against member's `left_at`. Meera left 2026-03-31 but is in the split_with for an April expense. Flagged for user to remove Meera from this split. |
| 16 | 26 | **Trailing whitespace in name** — "rohan " (with trailing space) | `name_casing` | info | `normalize_name()` strips all leading/trailing whitespace. Auto-resolved. |
| 17 | 31 | **Percentages sum to 110%** — Weekend brunch: same pattern as row 14 (30+30+30+20 = 110%) | `percentage_mismatch` | error | Same detection as anomaly #4. Percentages normalized on commit. |
| 18 | 41 | **Conflicting split_type and split_details** — Furniture expense has split_type="equal" but includes share details "Aisha 1; Rohan 1; Priya 1; Sam 1" | `split_mismatch` | info | When split_type is "equal" but split_details are present, we flag the mismatch. Since all shares are equal (1:1:1:1), the result is the same either way. We use the equal split and ignore the redundant details. |
| 19 | 37 | **Settlement-like transaction** — "Sam deposit share" ₹15000 paid to Aisha. split_type="equal", single recipient. | `settlement` | warning | Description contains "deposit" keyword and only one person in split_with. Flagged as potential settlement. On commit, imported as a Payment from Sam to Aisha. |
| 20 | 9 | **Fractional amount** — Cylinder refill is 899.995 (3 decimal places) | — | — | Decimal field handles this naturally. Amount stored as-is, rounded to 2 decimal places for display and split calculation. Not flagged as anomaly since it's valid data. |
