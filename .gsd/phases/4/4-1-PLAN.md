---
phase: 4
plan: 1
wave: 1
depends_on: []
files_modified:
  - backend/app/verification/quality_gate.py
  - backend/app/verification/__init__.py
autonomous: true
must_haves:
  truths:
    - "Arithmetic consistency is evaluated strictly using exact Decimal math, never binary float."
    - "Summary rows (Total, Grand Total, Subtotal, Sum) are detected without confusing narrative text containing 'total'."
    - "Discrepancies preserve all printed source values and emit SOURCE_ARITHMETIC_DISCREPANCY without auto-correcting totals."
    - "Ambiguous calculation scopes generate ARITHMETIC_SCOPE_AMBIGUOUS instead of assuming verified status."
    - "Contributing cells are never marked CORROBORATED solely because sum matches."
  artifacts:
    - "backend/app/verification/quality_gate.py exists"
    - "backend/app/verification/__init__.py exports evaluate_table_arithmetic_consistency"
---

# Plan 4.1: Deterministic Table Arithmetic Consistency Evaluator

## Objective
Implement `evaluate_table_arithmetic_consistency` in `backend/app/verification/quality_gate.py` to validate arithmetic relationships in tables using exact `Decimal` calculations, detecting summary rows/columns, reporting `SOURCE_ARITHMETIC_DISCREPANCY` and `ARITHMETIC_SCOPE_AMBIGUOUS` without auto-correcting values or falsely corroborating cells, in compliance with MASTER_DIRECTIVE.md Section 16 and REQ-10.

## Context
- `MASTER_DIRECTIVE.md` (Section 16)
- `.gsd/SPEC.md` (Goal 4)
- `.gsd/REQUIREMENTS.md` (REQ-10, CON-03, CON-04)
- `.gsd/phases/4/RESEARCH.md`
- `backend/app/models/domain.py`
- `backend/app/models/state.py`

## Tasks

<task type="auto">
  <name>Implement summary row and calculation scope detector</name>
  <files>
    backend/app/verification/quality_gate.py
    backend/app/verification/__init__.py
  </files>
  <action>
    Create `backend/app/verification/quality_gate.py` with summary row detection and column scope functions:
    1. Define summary label keywords:
       `SUMMARY_LABELS = frozenset({"total", "grand total", "sub total", "subtotal", "sum", "net total", "total amount", "totals"})`.
    2. `identify_summary_rows(table: CanonicalTable) -> list[tuple[int, str]]`:
       - Examine rows from `table.header_row_count` to end of `table.rows`.
       - Inspect the label column (column 0 or 1):
         * Normalize text: `label = row[c].accepted_value.strip().lower()`.
         * Match exact phrase against `SUMMARY_LABELS` or prefix (e.g. `label.startswith("total ")`).
         * Reject long prose fields (>30 chars or >4 words) to avoid false positives on contract/policy clauses.
       - Verify the row contains at least one non-empty numeric cell.
       - Classify type: `"GRAND_TOTAL"`, `"SUBTOTAL"`, or `"TOTAL"`.
       - Return `list[(row_idx, summary_type)]`.
    3. `identify_numeric_columns(table: CanonicalTable) -> list[int]`:
       - For each column, count body cells with `numeric_decimal is not None`.
       - If at least 50% of non-empty body cells in the column are numeric, include as a valid numeric column.
       - Exclude columns that are predominantly identifiers (leading zeros, header matches "account", "id", "code").
    
    AVOID: Matching "total" when it appears as part of an ordinary sentence; summary row labels are short, distinct categorical markers.
  </action>
  <verify>
    powershell -Command "python -c 'from app.verification.quality_gate import identify_summary_rows; print(callable(identify_summary_rows))'"
  </verify>
  <done>
    `identify_summary_rows` identifies genuine summary rows and classifies summary types without false positives on prose.
  </done>
</task>

<task type="auto">
  <name>Implement exact Decimal arithmetic validation</name>
  <files>
    backend/app/verification/quality_gate.py
    backend/app/verification/__init__.py
  </files>
  <action>
    In `backend/app/verification/quality_gate.py`, implement:
    1. `evaluate_table_arithmetic_consistency(table: CanonicalTable) -> tuple[ValidationOutcome, list[ValidationIssue]]`:
       - If no body rows or no numeric columns: return `(ValidationOutcome.NOT_APPLICABLE, [])`.
       - Detect summary rows via `identify_summary_rows(table)`.
       - If no summary rows found: return `(ValidationOutcome.NOT_APPLICABLE, [])`.
       - For each summary row `(sum_idx, sum_type)`:
         * Determine contributing rows: body rows immediately preceding `sum_idx` back to header row or preceding subtotal.
         * If contributing rows count == 0:
           - Record `ValidationIssue(issue_code="ARITHMETIC_SCOPE_AMBIGUOUS", severity="WARNING", description="No contributing body rows found for summary row", resolved=False)`.
           - Continue.
         * For each numeric column `col_idx`:
           - Total cell = `table.rows[sum_idx][col_idx]`.
           - If `total_cell.numeric_decimal is None`: continue.
           - Sum contributing body cells using exact Decimal:
             `expected_sum = sum(table.rows[r][col_idx].numeric_decimal for r in contributing if table.rows[r][col_idx].numeric_decimal is not None, Decimal("0"))`.
           - Compare: `diff = abs(total_cell.numeric_decimal - expected_sum)`.
           - If `diff > Decimal("0.001")`:
             * Discrepancy found!
             * Mark cell: `total_cell.quality_status = CellQualityStatus.ANOMALY_FLAGGED`.
             * Create `ValidationIssue(issue_code="SOURCE_ARITHMETIC_DISCREPANCY", severity="ERROR", expected_value=str(expected_sum), actual_value=str(total_cell.numeric_decimal), description=f"Printed total {total_cell.numeric_decimal} differs from expected sum {expected_sum}", resolved=False)`.
             * Preserve printed `raw_value` and `accepted_value`; NEVER auto-correct.
       - Decide outcome:
         * If any `SOURCE_ARITHMETIC_DISCREPANCY` issue exists: return `(ValidationOutcome.FAILED_VALIDATION, issues)`.
         * If any `ARITHMETIC_SCOPE_AMBIGUOUS` issue exists: return `(ValidationOutcome.FAILED_VALIDATION, issues)`.
         * If at least one check passed and 0 issues: return `(ValidationOutcome.PASSED, [])`.
         * Otherwise return `(ValidationOutcome.NOT_APPLICABLE, [])`.
       - Update `table.math_validation_outcome` and `table.validation_issues`.
    2. Export `evaluate_table_arithmetic_consistency` in `backend/app/verification/__init__.py`.
  </action>
  <verify>
    powershell -Command "python -c 'from app.verification.quality_gate import evaluate_table_arithmetic_consistency; print(callable(evaluate_table_arithmetic_consistency))'"
  </verify>
  <done>
    `evaluate_table_arithmetic_consistency` validates sums via exact Decimal arithmetic, emits `SOURCE_ARITHMETIC_DISCREPANCY` and `ARITHMETIC_SCOPE_AMBIGUOUS` when applicable, and never auto-balances values.
  </done>
</task>

## Success Criteria
- [ ] Summary rows detected conservatively without false positives on prose.
- [ ] Exact `Decimal` arithmetic enforced (zero float conversions).
- [ ] `SOURCE_ARITHMETIC_DISCREPANCY` emitted on sum mismatch while preserving printed values.
- [ ] `ARITHMETIC_SCOPE_AMBIGUOUS` emitted when scope cannot be determined.
- [ ] Clean package exports in `backend/app/verification/__init__.py`.
