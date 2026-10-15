"""DocuStruct AI — Table Arithmetic Consistency Evaluator & Document Quality Gate

Evaluates arithmetic relationships within canonical tables using exact Decimal
calculations, detects summary rows/columns, reports SOURCE_ARITHMETIC_DISCREPANCY
and ARITHMETIC_SCOPE_AMBIGUOUS without auto-correcting values or falsely corroborating
cells, and enforces conservative document-level verification precedence.

References:
    - MASTER_DIRECTIVE.md Sections 16, 17, and 20
    - REQ-10, REQ-11, REQ-13
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional
import uuid

from app.models.domain import (
    CanonicalTable,
    CellRecord,
    DocumentEvaluationReport,
    ValidationIssue,
)
from app.models.state import (
    CellQualityStatus,
    DataType,
    JobExecutionState,
    PageProcessingStatus,
    PageType,
    StitchDecision,
    TablePresenceStatus,
    ValidationOutcome,
    VerificationStatus,
)

# ── Standard Reason Codes ───────────────────────────────────────────────────

REASON_NO_TABLES_FOUND = "NO_TABLES_FOUND"
REASON_OCR_REQUIRED_FOR_SCANNED = "OCR_REQUIRED_FOR_SCANNED_CONTENT"
REASON_DEFERRED_REGIONS_REMAIN = "DEFERRED_REGIONS_REMAIN"
REASON_SOURCE_ARITHMETIC_DISCREPANCY = "SOURCE_ARITHMETIC_DISCREPANCY"
REASON_ARITHMETIC_SCOPE_AMBIGUOUS = "ARITHMETIC_SCOPE_AMBIGUOUS"
REASON_STITCH_REVIEW_REQUIRED = "STITCH_REVIEW_REQUIRED"
REASON_STRUCTURAL_CHECKS_FAILED = "STRUCTURAL_CHECKS_FAILED"
REASON_EXECUTION_FAILED = "EXECUTION_FAILED"

# ── Mandatory Verbatim Disclaimer ───────────────────────────────────────────

MANDATORY_VERBATIM_DISCLAIMER = (
    "Structural integrity and internal arithmetic consistency were verified. "
    "This does not independently prove every source cell is correct and cannot "
    "rule out offsetting cell errors or errors in non-numeric text."
)

# ── Summary Label Vocabulary ────────────────────────────────────────────────

SUMMARY_LABELS: frozenset[str] = frozenset({
    "total",
    "grand total",
    "sub total",
    "subtotal",
    "sum",
    "net total",
    "total amount",
    "totals",
})

SUBTOTAL_LABELS: frozenset[str] = frozenset({
    "sub total",
    "subtotal",
})

GRAND_TOTAL_LABELS: frozenset[str] = frozenset({
    "grand total",
})

_IDENTIFIER_HEADER_KEYWORDS: frozenset[str] = frozenset({
    "id",
    "code",
    "account",
    "no",
    "number",
    "item",
    "sku",
    "date",
    "year",
    "serial",
    "phone",
    "pin",
    "zip",
})


# ── Scope & Summary Row Detection ───────────────────────────────────────────


def identify_summary_rows(table: CanonicalTable) -> list[tuple[int, str]]:
    """Identify genuine summary rows (Total, Subtotal, Grand Total).

    Rules:
    - Scans rows after header_row_count.
    - Inspects column 0 and column 1 for summary markers.
    - Rejects long prose strings (>35 chars or >4 words) to avoid false positives
      on contractual or narrative sentences containing the word 'total'.
    - Confirms the row contains at least one non-empty numeric cell.
    - Classifies as 'GRAND_TOTAL', 'SUBTOTAL', or 'TOTAL'.
    """
    summary_rows: list[tuple[int, str]] = []
    total_rows = len(table.rows)

    for r_idx in range(table.header_row_count, total_rows):
        row = table.rows[r_idx]
        if not row:
            continue

        # Check column 0, then column 1 if column 0 is empty/symbol
        label_text = ""
        for c_idx in range(min(2, len(row))):
            val = (row[c_idx].accepted_value or "").strip().lower()
            if val:
                label_text = val
                break

        if not label_text:
            continue

        # Reject narrative prose (e.g. "Total liability shall not exceed...")
        words = label_text.split()
        if len(label_text) > 35 or len(words) > 4:
            continue

        # Classify summary type
        summary_type: Optional[str] = None
        if label_text in GRAND_TOTAL_LABELS or label_text.startswith("grand total"):
            summary_type = "GRAND_TOTAL"
        elif label_text in SUBTOTAL_LABELS or label_text.startswith("subtotal") or label_text.startswith("sub total"):
            summary_type = "SUBTOTAL"
        elif (
            label_text in SUMMARY_LABELS
            or label_text.startswith("total ")
            or label_text.endswith(" total")
            or label_text.startswith("sum ")
        ):
            summary_type = "TOTAL"

        if summary_type is None:
            continue

        # Verify the candidate row has at least one cell with numeric_decimal
        has_numeric = any(cell.numeric_decimal is not None for cell in row)
        if has_numeric:
            summary_rows.append((r_idx, summary_type))

    return summary_rows


def identify_numeric_columns(table: CanonicalTable) -> list[int]:
    """Identify column indices that contain predominantly numeric body data.

    Excludes columns where >= 50% are identifiers or headers indicate codes/dates.
    """
    if not table.rows:
        return []

    num_cols = max(len(r) for r in table.rows)
    numeric_cols: list[int] = []

    body_rows = table.rows[table.header_row_count:]
    if not body_rows:
        return []

    for c in range(num_cols):
        # Check header keyword if available
        header_val = ""
        if c < len(table.normalized_headers):
            header_val = table.normalized_headers[c].strip().lower()
        elif c < len(table.original_headers):
            header_val = table.original_headers[c].strip().lower()

        if any(kw == header_val or f" {kw}" in header_val or f"{kw} " in header_val for kw in _IDENTIFIER_HEADER_KEYWORDS):
            continue

        numeric_count = 0
        non_empty_count = 0
        for row in body_rows:
            if c < len(row):
                cell = row[c]
                if cell.accepted_value.strip():
                    non_empty_count += 1
                    if cell.numeric_decimal is not None:
                        numeric_count += 1

        if non_empty_count > 0 and (numeric_count / non_empty_count) >= 0.5:
            numeric_cols.append(c)

    return numeric_cols


# ── Table Arithmetic Consistency Evaluator ──────────────────────────────────


def evaluate_table_arithmetic_consistency(
    table: CanonicalTable,
) -> tuple[ValidationOutcome, list[ValidationIssue]]:
    """Validate table arithmetic relationships using exact Decimal arithmetic.

    Contracts:
    - Never uses binary float conversion; sums using Decimal.
    - Emits SOURCE_ARITHMETIC_DISCREPANCY when expected sum != printed total.
    - Preserves printed raw_value and accepted_value; does not auto-balance totals.
    - Flags total cell as ANOMALY_FLAGGED upon discrepancy.
    - Emits ARITHMETIC_SCOPE_AMBIGUOUS when scope cannot be determined.
    - Participating body cells are NEVER falsely marked CORROBORATED.
    """
    issues: list[ValidationIssue] = []

    body_rows_count = len(table.rows) - table.header_row_count
    if body_rows_count <= 0:
        table.math_validation_outcome = ValidationOutcome.NOT_APPLICABLE
        return ValidationOutcome.NOT_APPLICABLE, []

    numeric_columns = identify_numeric_columns(table)
    summary_rows = identify_summary_rows(table)

    if not summary_rows or not numeric_columns:
        table.math_validation_outcome = ValidationOutcome.NOT_APPLICABLE
        return ValidationOutcome.NOT_APPLICABLE, []

    summary_row_indices = {r_idx for r_idx, _ in summary_rows}
    verified_sum_count = 0
    tolerance = Decimal("0.001")

    for s_idx, (sum_row_idx, sum_type) in enumerate(summary_rows):
        # Determine contributing rows
        contributing_row_indices: list[int] = []

        if sum_type == "SUBTOTAL":
            # Contributing rows are regular body rows from preceding summary row up to this subtotal
            prev_sum_idx = -1
            for prev_idx, _ in summary_rows[:s_idx]:
                prev_sum_idx = max(prev_sum_idx, prev_idx)
            start_row = table.header_row_count if prev_sum_idx == -1 else prev_sum_idx + 1
            for r in range(start_row, sum_row_idx):
                if r not in summary_row_indices:
                    contributing_row_indices.append(r)

        elif sum_type == "GRAND_TOTAL":
            # If subtotals exist prior to grand total, check if grand total is sum of subtotals
            preceding_subtotals = [
                r for r, t in summary_rows[:s_idx] if t == "SUBTOTAL"
            ]
            if preceding_subtotals:
                contributing_row_indices = preceding_subtotals
            else:
                # Sum all preceding regular body rows
                for r in range(table.header_row_count, sum_row_idx):
                    if r not in summary_row_indices:
                        contributing_row_indices.append(r)

        else:  # "TOTAL"
            # Sum all preceding regular body rows back to header or preceding grand total/total
            prev_total_idx = -1
            for prev_idx, prev_t in summary_rows[:s_idx]:
                if prev_t in ("TOTAL", "GRAND_TOTAL"):
                    prev_total_idx = max(prev_total_idx, prev_idx)
            start_row = table.header_row_count if prev_total_idx == -1 else prev_total_idx + 1
            for r in range(start_row, sum_row_idx):
                if r not in summary_row_indices:
                    contributing_row_indices.append(r)

        if not contributing_row_indices:
            # Ambiguous calculation scope
            issue_id = f"MATH-AMBIG-{table.table_id}-{sum_row_idx}"
            source_page = (
                table.rows[sum_row_idx][0].source_page
                if table.rows[sum_row_idx]
                else (table.source_pages[0] if table.source_pages else 1)
            )
            issues.append(
                ValidationIssue(
                    issue_id=issue_id,
                    table_id=table.table_id,
                    source_page=source_page,
                    row_idx=sum_row_idx,
                    col_idx=None,
                    issue_code=REASON_ARITHMETIC_SCOPE_AMBIGUOUS,
                    severity="WARNING",
                    description=(
                        f"Summary row at index {sum_row_idx} ({sum_type}) has no "
                        "identifiable preceding contributing rows in calculation scope."
                    ),
                    resolved=False,
                )
            )
            continue

        # Evaluate each numeric column
        for col_idx in numeric_columns:
            if col_idx >= len(table.rows[sum_row_idx]):
                continue

            total_cell = table.rows[sum_row_idx][col_idx]
            if total_cell.numeric_decimal is None:
                continue

            # Sum contributing cells using exact Decimal
            expected_sum = Decimal("0")
            contributing_numeric_count = 0
            for r in contributing_row_indices:
                if col_idx < len(table.rows[r]):
                    cell = table.rows[r][col_idx]
                    if cell.numeric_decimal is not None:
                        expected_sum += cell.numeric_decimal
                        contributing_numeric_count += 1

            if contributing_numeric_count == 0:
                continue

            diff = abs(total_cell.numeric_decimal - expected_sum)
            if diff > tolerance:
                # Discrepancy detected
                total_cell.quality_status = CellQualityStatus.ANOMALY_FLAGGED
                issue_id = f"MATH-DISC-{table.table_id}-{sum_row_idx}-{col_idx}"
                issues.append(
                    ValidationIssue(
                        issue_id=issue_id,
                        table_id=table.table_id,
                        source_page=total_cell.source_page,
                        row_idx=sum_row_idx,
                        col_idx=col_idx,
                        issue_code=REASON_SOURCE_ARITHMETIC_DISCREPANCY,
                        severity="ERROR",
                        description=(
                            f"Printed total {total_cell.numeric_decimal} differs from "
                            f"computed sum {expected_sum} in column {col_idx}."
                        ),
                        expected_value=str(expected_sum),
                        actual_value=str(total_cell.numeric_decimal),
                        resolved=False,
                    )
                )
            else:
                verified_sum_count += 1
                # Non-negotiable: Participating body cells are NOT set to CORROBORATED
                # solely because the sum matches.

    # Determine validation outcome
    has_discrepancy = any(iss.issue_code == REASON_SOURCE_ARITHMETIC_DISCREPANCY for iss in issues)
    has_ambiguity = any(iss.issue_code == REASON_ARITHMETIC_SCOPE_AMBIGUOUS for iss in issues)

    if has_discrepancy or has_ambiguity:
        outcome = ValidationOutcome.FAILED_VALIDATION
    elif verified_sum_count > 0:
        outcome = ValidationOutcome.PASSED
    else:
        outcome = ValidationOutcome.NOT_APPLICABLE

    table.math_validation_outcome = outcome
    table.validation_issues.extend(issues)
    return outcome, issues


# ── Conservative Document Quality Gate ──────────────────────────────────────


def evaluate_document_verification_status(
    report: DocumentEvaluationReport,
) -> tuple[VerificationStatus, list[str]]:
    """Determine document-level verification status and reason codes.

    Enforces conservative decision precedence order:
    1. Fatal execution failure -> FAILED (EXECUTION_FAILED)
    2. Zero-table digital document -> FAILED (NO_TABLES_FOUND)
    3. Scanned content -> REVIEW_REQUIRED (OCR_REQUIRED_FOR_SCANNED_CONTENT)
    4. Deferred regions remain -> REVIEW_REQUIRED (DEFERRED_REGIONS_REMAIN)
    5. Unresolved stitch reviews -> REVIEW_REQUIRED (STITCH_REVIEW_REQUIRED)
    6. Arithmetic discrepancies / ambiguities -> REVIEW_REQUIRED (SOURCE_ARITHMETIC_DISCREPANCY / ARITHMETIC_SCOPE_AMBIGUOUS)
    7. Structural integrity check failures -> REVIEW_REQUIRED (STRUCTURAL_CHECKS_FAILED)
    8. Audited corrections / High-precision decimals / Math N/A -> VERIFIED_WITH_WARNINGS
    9. Clean execution, verified math, zero anomalies -> VERIFIED
    """
    reasons: list[str] = []

    # 1. Fatal Execution State
    if report.execution_state == JobExecutionState.FAILED:
        return VerificationStatus.FAILED, [REASON_EXECUTION_FAILED]

    # Check scanned content presence
    has_scanned_pages = any(
        p.page_type == PageType.SCANNED
        or p.processing_status == PageProcessingStatus.INCOMPLETE_DEFERRED_TO_OCR
        or p.table_presence == TablePresenceStatus.UNKNOWN_PENDING_OCR
        for p in report.page_profiles
    )

    # Check deferred regions count
    total_deferred_regions = sum(p.deferred_regions_count for p in report.page_profiles)

    # 2. Fully Inspected Zero-Table Digital Document
    # Only triggers if all pages were inspected, zero tables found, zero deferred regions,
    # and NO scanned pages exist (scanned pages must be routed to Step 3).
    total_tables = len(report.canonical_tables)
    if total_tables == 0:
        if not has_scanned_pages and total_deferred_regions == 0:
            all_confirmed_absent = (
                len(report.page_profiles) > 0
                and all(
                    p.table_presence == TablePresenceStatus.CONFIRMED_ABSENT
                    for p in report.page_profiles
                )
            )
            if all_confirmed_absent:
                return VerificationStatus.FAILED, [REASON_NO_TABLES_FOUND]

    # 3. Scanned Content Present
    if has_scanned_pages:
        return VerificationStatus.REVIEW_REQUIRED, [REASON_OCR_REQUIRED_FOR_SCANNED]

    # 4. Deferred Regions Remain
    if total_deferred_regions > 0:
        return VerificationStatus.REVIEW_REQUIRED, [REASON_DEFERRED_REGIONS_REMAIN]

    # 5. Unresolved Stitch Reviews
    all_stitch_events = list(report.stitch_events)
    for tbl in report.canonical_tables:
        all_stitch_events.extend(tbl.stitch_events)

    has_unresolved_stitch = any(
        evt.decision == StitchDecision.STITCH_REVIEW_REQUIRED
        for evt in all_stitch_events
    )
    if has_unresolved_stitch:
        return VerificationStatus.REVIEW_REQUIRED, [REASON_STITCH_REVIEW_REQUIRED]

    # 6. Arithmetic Discrepancies and Ambiguities
    all_issues = list(report.validation_issues)
    for tbl in report.canonical_tables:
        all_issues.extend(tbl.validation_issues)

    has_arithmetic_discrepancy = any(
        iss.issue_code == REASON_SOURCE_ARITHMETIC_DISCREPANCY for iss in all_issues
    )
    has_arithmetic_ambiguity = any(
        iss.issue_code == REASON_ARITHMETIC_SCOPE_AMBIGUOUS for iss in all_issues
    )
    table_math_failed = any(
        tbl.math_validation_outcome == ValidationOutcome.FAILED_VALIDATION
        for tbl in report.canonical_tables
    )

    if has_arithmetic_discrepancy or table_math_failed:
        reasons_to_report = [REASON_SOURCE_ARITHMETIC_DISCREPANCY]
        if has_arithmetic_ambiguity:
            reasons_to_report.append(REASON_ARITHMETIC_SCOPE_AMBIGUOUS)
        return VerificationStatus.REVIEW_REQUIRED, reasons_to_report
    elif has_arithmetic_ambiguity:
        return VerificationStatus.REVIEW_REQUIRED, [REASON_ARITHMETIC_SCOPE_AMBIGUOUS]

    # 7. Structural Integrity Failures
    has_structural_failure = any(
        not tbl.structural_checks_passed for tbl in report.canonical_tables
    )
    if has_structural_failure:
        return VerificationStatus.REVIEW_REQUIRED, [REASON_STRUCTURAL_CHECKS_FAILED]

    # 8. Audited Corrections, High Precision, or Math Not Applicable
    has_corrections = len(report.correction_records) > 0 or any(
        len(tbl.correction_records) > 0 for tbl in report.canonical_tables
    )
    has_high_precision = any(
        cell.data_type == DataType.HIGH_PRECISION_DECIMAL
        for tbl in report.canonical_tables
        for row in tbl.rows
        for cell in row
    )
    all_math_not_applicable = bool(report.canonical_tables) and all(
        tbl.math_validation_outcome == ValidationOutcome.NOT_APPLICABLE
        for tbl in report.canonical_tables
    )

    if has_corrections or has_high_precision or all_math_not_applicable:
        return VerificationStatus.VERIFIED_WITH_WARNINGS, []

    # 9. Clean Execution
    return VerificationStatus.VERIFIED, []


def evaluate_document_quality(
    report: DocumentEvaluationReport,
) -> DocumentEvaluationReport:
    """Coordinate full document-level quality gate and disclaimer attachment.

    1. Executes table-level arithmetic consistency evaluation across all canonical tables.
    2. Collects newly discovered validation issues into the report.
    3. Evaluates overall verification status using conservative decision precedence.
    4. Merges status reason codes without duplication.
    5. Appends the mandatory verbatim disclaimer to report.limitation_disclaimers.
    """
    # 1. Run table arithmetic consistency checks
    for table in report.canonical_tables:
        outcome, issues = evaluate_table_arithmetic_consistency(table)
        for issue in issues:
            if issue not in report.validation_issues:
                report.validation_issues.append(issue)

    # 2. Determine verification status
    status, reason_codes = evaluate_document_verification_status(report)
    report.verification_status = status

    # 3. Merge status reason codes
    for rc in reason_codes:
        if rc not in report.status_reason_codes:
            report.status_reason_codes.append(rc)

    # 4. Attach mandatory verbatim disclaimer
    if MANDATORY_VERBATIM_DISCLAIMER not in report.limitation_disclaimers:
        report.limitation_disclaimers.append(MANDATORY_VERBATIM_DISCLAIMER)

    return report
