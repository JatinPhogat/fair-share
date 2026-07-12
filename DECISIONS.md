# DECISIONS.md — Decision Log

Each significant design and engineering decision, the options considered, and the rationale.

---

## 1. Tech Stack: Django + React

**Options considered:**
- Django + React (separate frontend/backend)
- Django with templates (server-rendered)
- FastAPI + React
- Next.js full-stack

**Decision:** Django REST Framework backend + React (Vite) frontend.

**Rationale:** The JD explicitly requires Python (Django) and React. DRF provides robust API scaffolding with serializers, viewsets, and JWT auth out of the box. Vite gives fast dev iteration for the frontend. SQLite is sufficient for the demo and avoids infrastructure complexity.

---

## 2. Time-Aware Membership via GroupMembership Model

**Options considered:**
- Simple M2M relationship between Group and User
- GroupMembership join table with joined_at/left_at dates
- Separate "membership period" model

**Decision:** GroupMembership with `joined_at` and nullable `left_at` fields.

**Rationale:** Sam's requirement ("I moved in mid-April. Why would March electricity affect my balance?") demands temporal membership tracking. A simple M2M can't capture when someone joined or left. The join table approach is the simplest solution that satisfies the requirement. The `is_active(on_date)` method lets us check membership at any point in time.

---

## 3. Guest Participants (Non-Registered Users)

**Options considered:**
- Require all participants to register
- Allow display_name-only members with nullable user FK
- Separate "guest" model

**Decision:** `GroupMembership.user` is nullable. Guests like Dev and Kabir are tracked by `display_name` only.

**Rationale:** The CSV includes Dev (visiting for a weekend trip) and "Dev's friend Kabir" (joined for one activity). Requiring them to register would be impractical. Nullable user FK lets us track their share of expenses without forcing account creation.

---

## 4. Currency Handling: Convert to INR at Import Time

**Options considered:**
- Store everything in original currency, convert at display time
- Convert to a base currency (INR) at import time, store both
- Ignore currency differences

**Decision:** Store both `amount` (original) + `currency` and `amount_inr` (converted) on every expense and payment.

**Rationale:** Priya's request ("The sheet pretends a dollar is a rupee. That can't be right") requires proper currency handling. Storing the converted INR amount alongside the original means balances always work in a single currency. The exchange rate is configurable per import session. We don't need real-time rates for a flat-sharing app — a reasonable fixed rate at import time is sufficient.

---

## 5. Settlement Detection: Keywords + Missing split_type

**Options considered:**
- Manual tagging by user
- Auto-detect based on description keywords
- Separate column in CSV

**Decision:** Auto-detect using keyword matching ("paid back", "settlement", "deposit") combined with missing `split_type`, then flag for user confirmation.

**Rationale:** Row 13 ("Rohan paid Aisha back") has no split_type and notes saying "this is a settlement not an expense??". The importer shouldn't guess silently — it detects the pattern and flags it, letting the user confirm. Confirmed settlements are imported as Payment records instead of Expenses.

---

## 6. Duplicate Detection: Fuzzy Matching

**Options considered:**
- Exact description match only
- Fuzzy string matching (SequenceMatcher) + date/amount/payer
- Hash-based dedup

**Decision:** Fuzzy matching using `difflib.SequenceMatcher` with threshold 0.6, combined with exact date + payer matching.

**Rationale:** The CSV has two duplicate patterns: exact dupes (rows 5-6: "Dinner at Marina Bites" / "dinner - marina bites") and conflicting dupes (rows 23-24: "Dinner at Thalassa" ₹2400 / "Thalassa dinner" ₹2450). Exact matching would miss these because descriptions differ in casing, punctuation, and wording. Fuzzy matching catches both. Same-amount dupes are warnings (skip one); different-amount dupes are errors (user decides).

---

## 7. Percentage Normalization (110% Case)

**Options considered:**
- Reject the row entirely
- Normalize proportionally (each_pct / total_pct × amount)
- Flag and require manual fix

**Decision:** Flag as error. On commit, normalize proportionally if user approves as-is.

**Rationale:** Rows 14 and 31 both have percentages summing to 110% (30+30+30+20). This is clearly a data entry error, but the intent is readable: Meera pays less than the others. Normalizing to (30/110, 30/110, 30/110, 20/110) preserves the intended ratio. The user sees the error and can either fix the numbers or approve the normalization.

---

## 8. Debt Simplification: Greedy Algorithm

**Options considered:**
- Show all individual debts (N² pairs)
- Greedy algorithm (sort by net balance, match largest creditor/debtor)
- Graph-based min-cost flow

**Decision:** Greedy algorithm.

**Rationale:** Aisha wants "one number per person. Who pays whom, how much, done." The greedy approach minimizes the number of transactions. For a small group (4-6 people), it produces optimal or near-optimal results. The graph-based approach is overkill for this scale and harder to explain in the live session.

---

## 9. Import Workflow: Upload → Review → Commit

**Options considered:**
- Auto-import with a report
- Upload → parse → show anomalies → user resolves → commit
- Import everything, flag issues post-hoc

**Decision:** Three-phase workflow: upload/parse, review anomalies with approve/skip per row, then commit.

**Rationale:** Meera's request ("Clean up the duplicates — but I want to approve anything the app deletes or changes") demands user agency over the import. A crashed import or silent guess are both failing answers per the assignment. The review phase shows every anomaly with severity levels and auto-resolution suggestions, but the user has final say.

---

## 10. Split Types: Support All Four from CSV

**Options considered:**
- Equal only (simplest)
- Equal + custom amounts
- All four: equal, unequal, percentage, share

**Decision:** All four split types: equal, unequal, percentage, share (by ratio).

**Rationale:** The CSV uses all four: equal (most entries), unequal (birthday cake), percentage (pizza, brunch), and share (scooter rentals, April rent). The assignment says "Support every split type that appears in the CSV." Each type has a corresponding calculation in the split engine.

---

## 11. Name Resolution: Lookup Table + Fuzzy Fallback

**Options considered:**
- Case-insensitive exact match only
- Hardcoded mapping table
- Mapping table + fuzzy similarity fallback

**Decision:** `KNOWN_NAME_VARIANTS` dictionary for known mappings (e.g., "priya s" → "Priya") plus fuzzy SequenceMatcher for unknown variants.

**Rationale:** The CSV has multiple name issues: "priya" vs "Priya" (casing), "Priya S" vs "Priya" (variant), "rohan " (trailing space). A simple `.lower().strip()` handles casing and whitespace, but "Priya S" needs explicit mapping. The fuzzy fallback catches edge cases we haven't hardcoded.

---

## 12. Frontend State Management: Local State Only

**Options considered:**
- Redux / Zustand global store
- React Context
- Component-local useState + API calls

**Decision:** Component-local state with direct API calls.

**Rationale:** The app has straightforward data flow — each page loads its data, forms submit to the API, and we reload. No complex cross-component state sharing needed. Adding a state management library would be over-engineering for this scale.
