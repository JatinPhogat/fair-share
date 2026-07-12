# AI_USAGE.md — AI Tools and Usage

## Tools Used

- **Gemini (via Antigravity IDE)** — Primary development collaborator for architecture, code generation, anomaly analysis, and documentation.

## Key Prompts

1. **"Analyze expenses_export.xlsx and identify all deliberate data problems"** — Used to parse the spreadsheet and catalog anomalies before writing the importer.
2. **"Build an anomaly detection engine that handles duplicates, settlements, name variants, date issues, and percentage validation"** — Generated the parser module with detection functions.
3. **"Create a greedy debt simplification algorithm"** — Generated the balance calculation and min-transaction settlement logic.

## Three Cases Where AI Produced Something Wrong

### Case 1: Exchange Rate Applied Twice

**What happened:** The initial expense creation code in `importer/views.py` converted USD→INR for the `amount_inr` field, then also converted each individual split amount from USD to INR again. This double-conversion meant USD expenses had splits 85× too large.

**How I caught it:** Manual trace-through of an expense flow — created a $100 USD expense split 4 ways. Expected each split to be ₹2,125 (8500/4). Got ₹180,625 instead. The split calculation was converting the already-converted `amount_inr` again.

**What I changed:** The split calculation now always uses `amount_inr` (already converted) for equal/share/percentage splits. Only the `unequal` split type needs conversion since those values come directly from the CSV in the original currency.

### Case 2: Duplicate Detection Flagging Unrelated Expenses

**What happened:** The initial fuzzy matching threshold was 0.4, which caused false positives. "Groceries BigBasket" on Feb 3 and "Groceries BigBasket" on Mar 3 were flagged as duplicates despite being a month apart, because the similarity check didn't account for date differences properly.

**How I caught it:** Ran the parser against the full CSV and reviewed the anomaly report. Saw legitimate monthly recurring expenses being flagged.

**What I changed:** Tightened the similarity threshold to 0.6 and added a requirement that the date must also match exactly for a duplicate flag. Different dates = different expenses, even with identical descriptions.

### Case 3: Settlement Import Creating Circular Payments

**What happened:** The AI-generated settlement detection initially treated "Sam deposit share" (row 37) as a regular expense with equal split, then also detected it as a settlement. This created both an Expense record and a Payment record for the same transaction.

**How I caught it:** Balance calculation for Sam was off. Traced through the import commit code and saw both code paths executing.

**What I changed:** Made settlement detection exclusive — if a row is identified as a settlement, it only creates a Payment record and skips the expense creation path entirely. Added early return in `_create_expense_from_row`.
