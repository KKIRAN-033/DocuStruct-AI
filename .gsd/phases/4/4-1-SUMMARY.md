# Phase 4 Plan 1 Summary: Deterministic Table Arithmetic Consistency Evaluator

## Implementation Details
- **Module:** `backend/app/verification/quality_gate.py`
- **Functions:**
  - `identify_summary_rows(table: CanonicalTable) -> list[tuple[int, str]]`:
    - Robustly identifies `GRAND_TOTAL`, `SUBTOTAL`, and `TOTAL` rows using controlled summary keywords (`SUMMARY_LABELS`).
    - Excludes narrative and prose lines containing the word 'total' (>35 characters or >4 words) to prevent false positives on contract/policy clauses.
    - Verifies the row contains at least one numeric cell.
  - `identify_numeric_columns(table: CanonicalTable) -> list[int]`:
    - Checks that >= 50% of non-empty body cells in a column possess parsed `numeric_decimal` values.
    - Excludes columns that are predominantly identifiers, codes, dates, or accounts.
  - `evaluate_table_arithmetic_consistency(table: CanonicalTable) -> tuple[ValidationOutcome, list[ValidationIssue]]`:
    - Uses exact `Decimal` arithmetic for summing contributing body rows.
    - Compares computed sum against total cell with 0.001 tolerance without binary float conversion.
    - On mismatch, emits `ValidationIssue` with issue code `SOURCE_ARITHMETIC_DISCREPANCY` and flags the total cell as `CellQualityStatus.ANOMALY_FLAGGED`.
    - Preserves printed `raw_value` and `accepted_value` without auto-correcting totals.
    - Emits `ARITHMETIC_SCOPE_AMBIGUOUS` when summary rows have zero identifiable preceding contributing body rows.
    - Strictly avoids false corroboration: participating body cells are never marked `CORROBORATED` solely because a sum matches.
    - Updates `table.math_validation_outcome` and `table.validation_issues`.

## Verification Evidence
- Unit test suite `TestTableArithmeticConsistency` in `test_quality_gate.py`:
  - `test_correct_total_row_passed`: Validates matching totals yield `ValidationOutcome.PASSED`.
  - `test_arithmetic_discrepancy_preserves_values_and_flags_anomaly`: Validates 100+200=350 reports discrepancy, preserves 350.00, and flags anomaly.
  - `test_negative_numbers_sum_accurately`: Validates accounting negatives sum accurately with Decimal.
  - `test_subtotals_and_grand_total_evaluation`: Validates subtotals and grand totals calculation scopes.
  - `test_no_total_row_yields_not_applicable`: Validates non-summary tables yield `ValidationOutcome.NOT_APPLICABLE`.
  - `test_ambiguous_calculation_scope`: Validates summary rows without body rows yield `ARITHMETIC_SCOPE_AMBIGUOUS`.
  - `test_no_false_corroboration_of_participating_cells`: Validates body cells remain `EXTRACTED_AS_IS`.
  - `test_prose_label_rejected_as_summary`: Validates narrative rows with "total" are rejected.
