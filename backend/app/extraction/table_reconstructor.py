"""
DocuStruct AI — Multipage Table Reconstructor & Evidence-Gated Corrections

Conservative cross-page table reconstruction evaluating the seven decision
factors, multiline sliding-window header stripping (1–3 rows), row index
re-sequencing, and evidence-gated cell corrections.

Design invariants (from MASTER_DIRECTIVE.md Sections 14 and 15):
    - Differing column counts are never reconciled by inventing, deleting,
      or shifting columns.
    - Column overlap is computed table-relatively against outer span,
      not absolute page coordinates.
    - Legitimate duplicate rows are strictly preserved, never deduplicated.
    - Repeated headers are stripped only when confirmed by text similarity
      and body-type incompatibility.
    - Cell corrections strictly require independent deterministic evidence
      from permitted sources.
    - Totals are NEVER auto-balanced (e.g. 100 + 200 = 350 preserves 350).
    - Algebraic candidates are stored only in inferred_candidate_value with
      CellQualityStatus.ILLEGIBLE_OR_MISSING.
"""

from __future__ import annotations

import logging
import re
import uuid
from decimal import Decimal
from typing import Any, Optional

from rapidfuzz import fuzz

from app.config.calibration import CalibrationConfig
from app.extraction.normalizer import normalize_cell
from app.models.domain import (
    BoundingBox,
    CanonicalTable,
    CellRecord,
    CorrectionRecord,
    StitchAuditEvent,
)
from app.models.state import (
    CellQualityStatus,
    DataType,
    StitchDecision,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Permitted Evidence Sources (Section 15)
# ═══════════════════════════════════════════════════════════════════════════

PERMITTED_EVIDENCE_SOURCES: frozenset[str] = frozenset({
    "NATIVE_PDF_CHAR_STREAM",
    "INDEPENDENT_WORD_COORDINATES",
    "VECTOR_GRID_GEOMETRY",
})


# ═══════════════════════════════════════════════════════════════════════════
# 1. Table-Relative Column Overlap & Schema Analysis (Section 14)
# ═══════════════════════════════════════════════════════════════════════════


def compute_relative_column_intervals(
    table: CanonicalTable,
) -> list[tuple[float, float]]:
    """Compute normalized relative column intervals [0.0, 1.0] across columns.

    Normalizes column coordinates against the table's outer horizontal span
    to eliminate page margin shifts (e.g. alternating odd/even page gutters).
    """
    col_count = len(table.normalized_headers)
    if col_count == 0 and table.rows:
        col_count = max(len(r) for r in table.rows)
    if col_count == 0:
        return []

    # Collect min x0 and max x1 for each column across rows with bboxes
    col_x0 = [float("inf")] * col_count
    col_x1 = [float("-inf")] * col_count
    has_bbox = False

    for row in table.rows:
        for c_idx, cell in enumerate(row):
            if c_idx < col_count and cell.bbox is not None:
                has_bbox = True
                col_x0[c_idx] = min(col_x0[c_idx], cell.bbox.x0)
                col_x1[c_idx] = max(col_x1[c_idx], cell.bbox.x1)

    # Determine outer horizontal table span
    if table.page_bbox is not None and table.page_bbox.x1 > table.page_bbox.x0:
        table_x0 = table.page_bbox.x0
        table_x1 = table.page_bbox.x1
    elif has_bbox:
        valid_x0 = [x for x in col_x0 if x != float("inf")]
        valid_x1 = [x for x in col_x1 if x != float("-inf")]
        table_x0 = min(valid_x0) if valid_x0 else 0.0
        table_x1 = max(valid_x1) if valid_x1 else 1.0
    else:
        table_x0 = 0.0
        table_x1 = 1.0

    span_width = table_x1 - table_x0
    if span_width <= 0.0 or not has_bbox:
        # Uniform fallback intervals if geometry is missing or degenerate
        return [
            (round(i / col_count, 4), round((i + 1) / col_count, 4))
            for i in range(col_count)
        ]

    intervals: list[tuple[float, float]] = []
    for c_idx in range(col_count):
        if col_x0[c_idx] != float("inf") and col_x1[c_idx] != float("-inf"):
            rel_0 = max(0.0, min(1.0, (col_x0[c_idx] - table_x0) / span_width))
            rel_1 = max(0.0, min(1.0, (col_x1[c_idx] - table_x0) / span_width))
            intervals.append((round(rel_0, 4), round(rel_1, 4)))
        else:
            rel_0 = round(c_idx / col_count, 4)
            rel_1 = round((c_idx + 1) / col_count, 4)
            intervals.append((rel_0, rel_1))

    return intervals


def compute_column_overlap_ratio(
    intervals_a: list[tuple[float, float]],
    intervals_b: list[tuple[float, float]],
) -> float:
    """Compute average Intersection-over-Union (IoU) across corresponding columns.

    Returns 0.0 if column counts differ.
    """
    if len(intervals_a) != len(intervals_b) or not intervals_a:
        return 0.0

    total_iou = 0.0
    for (a0, a1), (b0, b1) in zip(intervals_a, intervals_b):
        inter_start = max(a0, b0)
        inter_end = min(a1, b1)
        intersection = max(0.0, inter_end - inter_start)

        union_start = min(a0, b0)
        union_end = max(a1, b1)
        union = max(0.0, union_end - union_start)

        if union > 0.0:
            total_iou += intersection / union

    return round(total_iou / len(intervals_a), 4)


def compute_type_compatibility(
    table_a: CanonicalTable,
    table_b: CanonicalTable,
) -> float:
    """Compute dominant DataType compatibility across body columns."""
    cols_a = len(table_a.normalized_headers)
    cols_b = len(table_b.normalized_headers)
    if cols_a != cols_b or cols_a == 0:
        return 0.0

    # Extract dominant body types
    def _dominant_types(table: CanonicalTable, col_count: int) -> list[Optional[DataType]]:
        dom: list[Optional[DataType]] = [None] * col_count
        body_rows = table.rows[table.header_row_count:] if len(table.rows) > table.header_row_count else table.rows
        for c in range(col_count):
            type_counts: dict[DataType, int] = {}
            for row in body_rows:
                if c < len(row):
                    dt = row[c].data_type
                    if dt != DataType.EMPTY:
                        type_counts[dt] = type_counts.get(dt, 0) + 1
            if type_counts:
                dom[c] = max(type_counts.items(), key=lambda item: item[1])[0]
        return dom

    dom_a = _dominant_types(table_a, cols_a)
    dom_b = _dominant_types(table_b, cols_b)

    matches = 0
    numeric_types = {DataType.INTEGER, DataType.DECIMAL, DataType.HIGH_PRECISION_DECIMAL}

    for t_a, t_b in zip(dom_a, dom_b):
        if t_a is None or t_b is None:
            # Neutral / unconstrained
            matches += 1
        elif t_a == t_b:
            matches += 1
        elif t_a in numeric_types and t_b in numeric_types:
            # Numeric compatibility
            matches += 1

    return round(matches / cols_a, 4)


# ═══════════════════════════════════════════════════════════════════════════
# 2. Header Similarity & Row Index Continuity
# ═══════════════════════════════════════════════════════════════════════════


def evaluate_header_similarity(
    headers_a: list[str],
    headers_b: list[str],
) -> float:
    """Compute average string similarity between corresponding header titles."""
    if not headers_a or not headers_b or len(headers_a) != len(headers_b):
        return 0.0

    scores: list[float] = []
    for ha, hb in zip(headers_a, headers_b):
        score = fuzz.ratio(ha.strip().lower(), hb.strip().lower()) / 100.0
        scores.append(score)

    return round(sum(scores) / len(scores), 4)


def check_serial_continuity(
    upper_table: CanonicalTable,
    lower_table: CanonicalTable,
) -> tuple[bool, Optional[str]]:
    """Inspect leading columns for sequential serial indexing."""
    body_upper = upper_table.rows[upper_table.header_row_count:] if len(upper_table.rows) > upper_table.header_row_count else []
    body_lower = lower_table.rows[lower_table.header_row_count:] if len(lower_table.rows) > lower_table.header_row_count else []

    if not body_upper or not body_lower:
        return False, "INSUFFICIENT_BODY_ROWS"

    # Check column 0 in last upper row and first lower row
    last_upper_cell = body_upper[-1][0].accepted_value.strip()
    first_lower_cell = body_lower[0][0].accepted_value.strip()

    if last_upper_cell.isdigit() and first_lower_cell.isdigit():
        val_u = int(last_upper_cell)
        val_l = int(first_lower_cell)
        if val_l == val_u + 1:
            return True, "CONTINUOUS_SEQUENCE"
        if val_l == 1 and val_u > 1:
            return False, "INDEX_RESET"

    return False, "NO_SERIAL_DETECTED"


# ═══════════════════════════════════════════════════════════════════════════
# 3. Seven-Factor Stitch Evaluation Engine
# ═══════════════════════════════════════════════════════════════════════════


def evaluate_stitch_pair(
    upper_table: CanonicalTable,
    lower_table: CanonicalTable,
    calibration: Optional[CalibrationConfig] = None,
) -> tuple[StitchDecision, StitchAuditEvent]:
    """Evaluate two adjacent candidate tables across sequential pages.

    Evaluates the 7 decision factors:
    1. Column count and schema compatibility.
    2. Table-relative normalized column overlap.
    3. Repeated-header text similarity.
    4. Column data-type compatibility.
    5. Page-transition geometry.
    6. Row-index continuity.
    7. Duplicate data preservation.
    """
    if calibration is None:
        calibration = CalibrationConfig.load_defaults()

    upper_pages = sorted(upper_table.source_pages)
    lower_pages = sorted(lower_table.source_pages)
    upper_p = upper_pages[-1]
    lower_p = lower_pages[0]

    reasons: list[str] = []

    # Factor 5: Page-transition context
    if lower_p != upper_p + 1:
        reasons.append("PAGES_NOT_SEQUENTIAL")
        event = StitchAuditEvent(
            upper_table_id=upper_table.table_id,
            lower_table_id=lower_table.table_id,
            upper_page=upper_p,
            lower_page=lower_p,
            decision=StitchDecision.STITCH_REJECTED,
            header_similarity_score=0.0,
            col_overlap_ratio=0.0,
            type_compatibility_ratio=0.0,
            repeated_header_rows_stripped=0,
            reasons=reasons,
        )
        return StitchDecision.STITCH_REJECTED, event

    # Factor 1: Column count & schema compatibility
    cols_a = len(upper_table.normalized_headers)
    cols_b = len(lower_table.normalized_headers)

    if cols_a != cols_b:
        # Check if upper table ends with an explicit Grand Total
        has_grand_total = False
        if upper_table.rows:
            last_row = upper_table.rows[-1]
            for cell in last_row:
                text_lower = cell.accepted_value.lower()
                if "grand total" in text_lower or "total" in text_lower:
                    has_grand_total = True
                    break

        if has_grand_total:
            reasons.append("DIFFERING_COLUMN_COUNTS_UPPER_TABLE_ENDS_WITH_TOTAL")
            decision = StitchDecision.STITCH_REJECTED
        else:
            reasons.append("DIFFERING_COLUMN_COUNTS_POTENTIAL_EXTRACTION_ARTIFACT")
            decision = StitchDecision.STITCH_REVIEW_REQUIRED

        event = StitchAuditEvent(
            upper_table_id=upper_table.table_id,
            lower_table_id=lower_table.table_id,
            upper_page=upper_p,
            lower_page=lower_p,
            decision=decision,
            header_similarity_score=0.0,
            col_overlap_ratio=0.0,
            type_compatibility_ratio=0.0,
            repeated_header_rows_stripped=0,
            reasons=reasons,
        )
        return decision, event

    # Factor 2: Relative column overlap
    intervals_a = compute_relative_column_intervals(upper_table)
    intervals_b = compute_relative_column_intervals(lower_table)
    overlap_ratio = compute_column_overlap_ratio(intervals_a, intervals_b)

    # Factor 4: Type compatibility
    type_compat = compute_type_compatibility(upper_table, lower_table)

    # Factor 3: Header similarity against lower table headers
    lower_hdr_text = lower_table.normalized_headers
    if not lower_hdr_text and lower_table.rows:
        lower_hdr_text = [c.accepted_value for c in lower_table.rows[0]]
    header_sim = evaluate_header_similarity(upper_table.normalized_headers, lower_hdr_text)

    # Factor 6: Row continuity
    is_continuous, serial_reason = check_serial_continuity(upper_table, lower_table)

    # Factor 1 & 3: Check for distinct header schemas
    # If lower table has an explicit, predominantly non-numeric header row whose
    # text similarity to upper table headers is low (< 0.60), reject stitching
    # because the two candidates represent distinct tables/datasets.
    has_distinct_header = False
    if lower_table.rows:
        first_row = lower_table.rows[0]
        num_numeric_cells = sum(
            1
            for c in first_row
            if c.numeric_decimal is not None
            or (c.accepted_value and c.accepted_value.strip().replace(".", "", 1).replace(",", "").isdigit())
        )
        if num_numeric_cells == 0 and header_sim < 0.60:
            has_distinct_header = True

    # Decision logic
    min_overlap = calibration.stitch_min_relative_col_overlap
    min_type_comp = calibration.stitch_min_type_compatibility

    if has_distinct_header:
        decision = StitchDecision.STITCH_REJECTED
        reasons.append("DIFFERING_HEADER_SCHEMAS")
    elif overlap_ratio >= min_overlap and type_compat >= min_type_comp:
        decision = StitchDecision.STITCH_CONFIRMED
        reasons.append("COLUMN_OVERLAP_CONFIRMED")
        reasons.append("TYPE_COMPATIBILITY_CONFIRMED")
        if is_continuous:
            reasons.append(f"SERIAL_CONTINUITY_{serial_reason}")
    elif overlap_ratio < 0.50 or type_compat < 0.50:
        decision = StitchDecision.STITCH_REJECTED
        if overlap_ratio < 0.50:
            reasons.append("INSUFFICIENT_COLUMN_OVERLAP")
        if type_compat < 0.50:
            reasons.append("INSUFFICIENT_TYPE_COMPATIBILITY")
    else:
        decision = StitchDecision.STITCH_REVIEW_REQUIRED
        reasons.append("AMBIGUOUS_OVERLAP_OR_TYPE_COMPATIBILITY")

    event = StitchAuditEvent(
        upper_table_id=upper_table.table_id,
        lower_table_id=lower_table.table_id,
        upper_page=upper_p,
        lower_page=lower_p,
        decision=decision,
        header_similarity_score=header_sim,
        col_overlap_ratio=overlap_ratio,
        type_compatibility_ratio=type_compat,
        repeated_header_rows_stripped=0,
        reasons=reasons,
    )
    return decision, event


# ═══════════════════════════════════════════════════════════════════════════
# 4. Multiline Header Stripping (1–3 Row Sliding Window)
# ═══════════════════════════════════════════════════════════════════════════


def strip_repeated_headers(
    upper_headers: list[str],
    lower_rows: list[list[CellRecord]],
    threshold: float = 0.85,
) -> tuple[list[list[CellRecord]], int]:
    """Test sliding windows of 1, 2, or 3 leading rows of lower table for repeated headers.

    Strips repeated rows only when text similarity reaches threshold and
    candidate rows do not represent numeric body data.
    """
    if not upper_headers or not lower_rows:
        return lower_rows, 0

    col_count = len(upper_headers)
    max_window = min(3, len(lower_rows))
    best_window = 0

    for w in range(1, max_window + 1):
        # Concatenate text per column across the w leading rows
        candidate_headers: list[str] = []
        is_predominantly_numeric = False
        num_cells = 0
        total_cells = 0

        for c in range(col_count):
            col_words: list[str] = []
            for r in range(w):
                if c < len(lower_rows[r]):
                    text = lower_rows[r][c].accepted_value.strip()
                    if text:
                        col_words.append(text)
                    if lower_rows[r][c].numeric_decimal is not None:
                        num_cells += 1
                    total_cells += 1
            candidate_headers.append(" ".join(col_words))

        if total_cells > 0 and (num_cells / total_cells) > 0.40:
            # Over 40% numeric cells indicates genuine data rows, not headers
            continue

        sim = evaluate_header_similarity(upper_headers, candidate_headers)
        if sim >= threshold:
            best_window = w

    if best_window > 0:
        return lower_rows[best_window:], best_window

    return lower_rows, 0


def strip_internal_repeated_headers(
    headers: list[str],
    rows: list[list[CellRecord]],
    header_row_count: int = 1,
    threshold: float = 0.80,
) -> tuple[list[list[CellRecord]], int]:
    """Identify and remove any intermediate repeated header rows throughout the table rows.

    Preserves the primary leading header rows (indices < header_row_count).
    Checks each subsequent row to determine if its cell values match the table headers
    and contain predominantly non-numeric text.
    """
    if not headers or not rows:
        return rows, 0

    cleaned_rows: list[list[CellRecord]] = []
    stripped_count = 0
    norm_hdrs = [re.sub(r"[^a-zA-Z0-9]+", "", str(h)).lower() for h in headers]

    for r_idx, row in enumerate(rows):
        # Always preserve primary leading header rows
        if r_idx < header_row_count:
            cleaned_rows.append(row)
            continue
        if len(row) == len(headers):
            num_cells = 0
            match_scores: list[float] = []
            for c_idx, cell in enumerate(row):
                val = (cell.accepted_value or cell.raw_value).strip()
                if cell.numeric_decimal is not None:
                    num_cells += 1
                clean_val = re.sub(r"[^a-zA-Z0-9]+", "", val).lower()
                target_hdr = norm_hdrs[c_idx] if c_idx < len(norm_hdrs) else ""
                if clean_val and target_hdr:
                    ratio = fuzz.ratio(clean_val, target_hdr) / 100.0
                    match_scores.append(ratio)
                elif not clean_val and not target_hdr:
                    match_scores.append(1.0)
                else:
                    match_scores.append(0.0)

            avg_match = sum(match_scores) / len(match_scores) if match_scores else 0.0
            if num_cells == 0 and avg_match >= threshold:
                stripped_count += 1
                continue

        cleaned_rows.append(row)

    if stripped_count > 0:
        reindexed_rows: list[list[CellRecord]] = []
        for new_r_idx, row in enumerate(cleaned_rows):
            new_row = [c.model_copy(update={"row_idx": new_r_idx}) for c in row]
            reindexed_rows.append(new_row)
        return reindexed_rows, stripped_count

    return rows, 0


# ═══════════════════════════════════════════════════════════════════════════
# 5. Multipage Table Concatenation
# ═══════════════════════════════════════════════════════════════════════════


def stitch_canonical_tables(
    upper_table: CanonicalTable,
    lower_table: CanonicalTable,
    audit_event: StitchAuditEvent,
) -> CanonicalTable:
    """Concatenate two confirmed tables, updating row indices and preserving duplicates."""
    # Strip repeated headers from lower table
    remaining_rows, stripped_count = strip_repeated_headers(
        upper_table.normalized_headers,
        lower_table.rows,
        threshold=audit_event.header_similarity_score if audit_event.header_similarity_score >= 0.85 else 0.85,
    )
    audit_event.repeated_header_rows_stripped = stripped_count

    # Re-index lower rows starting from length of upper table
    base_offset = len(upper_table.rows)
    reindexed_lower_rows: list[list[CellRecord]] = []

    for r_idx, row in enumerate(remaining_rows):
        new_row: list[CellRecord] = []
        for cell in row:
            new_cell = cell.model_copy(update={
                "table_id": upper_table.table_id,
                "row_idx": base_offset + r_idx,
            })
            new_row.append(new_cell)
        reindexed_lower_rows.append(new_row)

    combined_rows = upper_table.rows + reindexed_lower_rows
    combined_pages = sorted(list(set(upper_table.source_pages + lower_table.source_pages)))

    # Combined audit events
    all_stitch_events = upper_table.stitch_events + lower_table.stitch_events + [audit_event]

    return CanonicalTable(
        table_id=upper_table.table_id,
        title=upper_table.title or lower_table.title,
        source_pages=combined_pages,
        page_bbox=upper_table.page_bbox,
        original_headers=upper_table.original_headers,
        normalized_headers=upper_table.normalized_headers,
        header_row_count=upper_table.header_row_count,
        column_types=upper_table.column_types or lower_table.column_types,
        column_semantic_roles=upper_table.column_semantic_roles or lower_table.column_semantic_roles,
        rows=combined_rows,
        extraction_method=upper_table.extraction_method,
        stitch_events=all_stitch_events,
        validation_issues=upper_table.validation_issues + lower_table.validation_issues,
        correction_records=upper_table.correction_records + lower_table.correction_records,
        structural_checks_passed=upper_table.structural_checks_passed and lower_table.structural_checks_passed,
        math_validation_outcome=upper_table.math_validation_outcome,
        verification_status=upper_table.verification_status,
    )


def reconstruct_multipage_tables(
    tables: list[CanonicalTable],
    calibration: Optional[CalibrationConfig] = None,
) -> list[CanonicalTable]:
    """Iterate through candidate tables, evaluate pairs, and stitch confirmed continuations."""
    if not tables:
        return []

    def _clean_table_headers(t: CanonicalTable) -> CanonicalTable:
        hdrs = t.original_headers or t.normalized_headers
        cleaned_rows, stripped = strip_internal_repeated_headers(
            hdrs,
            t.rows,
            header_row_count=t.header_row_count,
        )
        if stripped > 0:
            return t.model_copy(update={"rows": cleaned_rows})
        return t

    if len(tables) == 1:
        return [_clean_table_headers(tables[0])]

    # Sort tables by first source page and y0
    sorted_tables = sorted(
        tables,
        key=lambda t: (min(t.source_pages) if t.source_pages else 0, t.page_bbox.y0 if t.page_bbox else 0.0),
    )

    reconstructed: list[CanonicalTable] = []
    current_table = sorted_tables[0]

    for next_table in sorted_tables[1:]:
        decision, audit_event = evaluate_stitch_pair(
            current_table, next_table, calibration=calibration,
        )
        if decision == StitchDecision.STITCH_CONFIRMED:
            current_table = stitch_canonical_tables(current_table, next_table, audit_event)
        else:
            current_table.stitch_events.append(audit_event)
            reconstructed.append(current_table)
            current_table = next_table

    reconstructed.append(current_table)
    return [_clean_table_headers(t) for t in reconstructed]


# ═══════════════════════════════════════════════════════════════════════════
# 6. Evidence-Gated Cell Corrections (Section 15)
# ═══════════════════════════════════════════════════════════════════════════


def apply_evidence_gated_correction(
    cell: CellRecord,
    proposed_value: str,
    evidence_source: str,
    evidence_summary: str,
    is_algebraic_inference: bool = False,
) -> tuple[CellRecord, Optional[CorrectionRecord]]:
    """Apply an evidence-gated correction or record an algebraic candidate.

    Enforces Section 15 invariants:
    - Evidence must come strictly from PERMITTED_EVIDENCE_SOURCES.
    - raw_value is never modified.
    - Totals are NEVER auto-balanced to force math consistency.
    - Algebraic candidates are stored in inferred_candidate_value with
      ILLEGIBLE_OR_MISSING status.
    """
    if evidence_source not in PERMITTED_EVIDENCE_SOURCES:
        # Reject unapproved evidence source (e.g. LLM_GUESS, HEURISTIC)
        return cell, None

    audit_id = f"corr_{uuid.uuid4().hex[:8]}"

    if is_algebraic_inference:
        # Algebraic deduction from surrounding totals:
        # Never overwrite raw_value or accepted_value
        updated_cell = cell.model_copy(update={
            "inferred_candidate_value": proposed_value,
            "quality_status": CellQualityStatus.ILLEGIBLE_OR_MISSING,
        })
        record = CorrectionRecord(
            audit_id=audit_id,
            table_id=cell.table_id,
            source_page=cell.source_page,
            row_idx=cell.row_idx,
            col_idx=cell.col_idx,
            original_raw_value=cell.raw_value,
            proposed_value=proposed_value,
            accepted_value=cell.accepted_value,
            inferred_candidate_only=True,
            evidence_source=evidence_source,
            evidence_summary=evidence_summary,
            deterministic_check_passed=True,
            decision="INFERRED_CANDIDATE_RECORDED",
            resulting_cell_status=CellQualityStatus.ILLEGIBLE_OR_MISSING,
        )
        return updated_cell, record

    # Valid deterministic independent evidence
    norm = normalize_cell(proposed_value)
    updated_cell = cell.model_copy(update={
        "accepted_value": norm["accepted_value"],
        "numeric_decimal": norm["numeric_decimal"],
        "data_type": norm["data_type"],
        "quality_status": CellQualityStatus.CORRECTED_WITH_EVIDENCE,
    })
    record = CorrectionRecord(
        audit_id=audit_id,
        table_id=cell.table_id,
        source_page=cell.source_page,
        row_idx=cell.row_idx,
        col_idx=cell.col_idx,
        original_raw_value=cell.raw_value,
        proposed_value=proposed_value,
        accepted_value=norm["accepted_value"],
        inferred_candidate_only=False,
        evidence_source=evidence_source,
        evidence_summary=evidence_summary,
        deterministic_check_passed=True,
        decision="CORRECTION_ACCEPTED",
        resulting_cell_status=CellQualityStatus.CORRECTED_WITH_EVIDENCE,
    )
    return updated_cell, record
