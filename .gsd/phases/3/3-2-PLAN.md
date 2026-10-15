---
phase: 3
plan: 2
wave: 1
depends_on: []
files_modified:
  - backend/app/extraction/table_reconstructor.py
  - backend/app/extraction/__init__.py
autonomous: true
must_haves:
  truths:
    - "Repeated headers spanning 1 to 3 rows are evaluated using sliding windows and stripped only when confirmed."
    - "Legitimate duplicate rows are never pruned or deduplicated during stitching."
    - "Stitched tables preserve all source page references, cell bounding boxes, and original raw values."
    - "Cell corrections strictly require independent deterministic evidence from permitted sources."
    - "Totals are never auto-balanced; arithmetic discrepancies are preserved as SOURCE_ARITHMETIC_DISCREPANCY."
    - "Algebraic candidates are stored only in inferred_candidate_value with ILLEGIBLE_OR_MISSING status."
  artifacts:
    - "backend/app/extraction/table_reconstructor.py exports reconstruct_multipage_tables"
    - "backend/app/extraction/table_reconstructor.py exports apply_evidence_gated_correction"
---

# Plan 3.2: Header Stripping, Table Stitching & Evidence-Gated Corrections

## Objective
Implement sliding-window repeated header stripping (1–3 rows), canonical table concatenation with serial row index re-sequencing in `reconstruct_multipage_tables()`, and evidence-gated cell corrections (`apply_evidence_gated_correction()`) enforcing strict permitted evidence sources and prohibiting auto-balancing totals, in accordance with MASTER_DIRECTIVE.md Sections 14 and 15 and REQ-08/REQ-09.

## Context
- `MASTER_DIRECTIVE.md` (Sections 14, 15)
- `.gsd/SPEC.md` (Goals 2, 3)
- `.gsd/REQUIREMENTS.md` (REQ-08, REQ-09, REQ-13)
- `.gsd/phases/3/RESEARCH.md`
- `backend/app/extraction/table_reconstructor.py`
- `backend/app/models/domain.py`
- `backend/app/models/state.py`

## Tasks

<task type="auto">
  <name>Implement sliding-window header stripping and multipage table stitching</name>
  <files>
    backend/app/extraction/table_reconstructor.py
    backend/app/extraction/__init__.py
  </files>
  <action>
    In `backend/app/extraction/table_reconstructor.py`, implement:
    1. `strip_repeated_headers(upper_headers: list[str], lower_rows: list[list[CellRecord]], threshold: float = 0.85) -> tuple[list[list[CellRecord]], int]`:
       - Test sliding windows of $W \in \{1, 2, 3\}$ rows at index 0 of `lower_rows`.
       - For each window $W$, concatenate cell texts in each column across rows $0 \dots W-1$.
       - Compute average similarity against `upper_headers` using RapidFuzz.
       - If similarity $\ge \text{threshold}$, identify candidate header block.
       - Validate that candidate rows are not consistent with numeric body patterns.
       - Strip the confirmed $W$ rows from `lower_rows` and return `(remaining_rows, W)`.
       - If no window satisfies criteria, return `(lower_rows, 0)`.
    2. `stitch_canonical_tables(upper_table: CanonicalTable, lower_table: CanonicalTable, audit_event: StitchAuditEvent) -> CanonicalTable`:
       - Strip repeated headers from lower table using `strip_repeated_headers`.
       - Update `audit_event.repeated_header_rows_stripped`.
       - Concatenate rows: `new_rows = upper_table.rows + reindexed_lower_rows` where `row_idx` of lower cells is offset by `len(upper_table.rows)`.
       - Preserve `col_idx`, `source_page`, `bbox`, `raw_value`, `data_type` of every cell.
       - Combine `source_pages`: sorted union of `upper_table.source_pages` and `lower_table.source_pages`.
       - Append `audit_event` to `stitch_events`.
       - Set `table_id = upper_table.table_id`.
       - Return unified `CanonicalTable`.
    3. `reconstruct_multipage_tables(tables: list[CanonicalTable], calibration: Optional[CalibrationConfig] = None) -> list[CanonicalTable]`:
       - Sort tables by `(min(source_pages), page_bbox.y0 if page_bbox else 0)`.
       - Iterate through adjacent table pairs; call `evaluate_stitch_pair()`.
       - If `STITCH_CONFIRMED`, stitch via `stitch_canonical_tables()` and continue chaining.
       - If `STITCH_REJECTED` or `STITCH_REVIEW_REQUIRED`, append audit event to table and keep tables separate.
       - Return list of reconstructed canonical tables.
    
    AVOID: Pruning identical adjacent rows in `stitch_canonical_tables()`; duplicate transactions must be strictly preserved.
  </action>
  <verify>
    powershell -Command "python -c 'from app.extraction.table_reconstructor import reconstruct_multipage_tables; print(callable(reconstruct_multipage_tables))'"
  </verify>
  <done>
    `strip_repeated_headers` strips 1–3 repeated header rows with audit logging; `reconstruct_multipage_tables` stitches confirmed tables across pages with serial row index continuity.
  </done>
</task>

<task type="auto">
  <name>Implement evidence-gated cell corrections</name>
  <files>
    backend/app/extraction/table_reconstructor.py
    backend/app/extraction/__init__.py
  </files>
  <action>
    In `backend/app/extraction/table_reconstructor.py`, implement:
    1. Define permitted evidence sources:
       `PERMITTED_EVIDENCE_SOURCES = frozenset({"NATIVE_PDF_CHAR_STREAM", "INDEPENDENT_WORD_COORDINATES", "VECTOR_GRID_GEOMETRY"})`.
    2. `apply_evidence_gated_correction(cell: CellRecord, proposed_value: str, evidence_source: str, evidence_summary: str, is_algebraic_inference: bool = False) -> tuple[CellRecord, Optional[CorrectionRecord]]`:
       - If `evidence_source not in PERMITTED_EVIDENCE_SOURCES`:
         * Reject correction: return unmodified `(cell, None)`.
       - If `is_algebraic_inference` is True (e.g. deduced from row totals):
         * NEVER overwrite `raw_value` or `accepted_value`.
         * Set `cell.inferred_candidate_value = proposed_value`.
         * Set `cell.quality_status = CellQualityStatus.ILLEGIBLE_OR_MISSING`.
         * Create `CorrectionRecord` with `inferred_candidate_only=True`, `decision="INFERRED_CANDIDATE_RECORDED"`, `resulting_cell_status=CellQualityStatus.ILLEGIBLE_OR_MISSING`.
         * Return `(cell, correction_record)`.
       - Else (valid independent deterministic evidence):
         * Keep `cell.raw_value` immutable.
         * Normalize `proposed_value` with `normalize_cell(proposed_value)`.
         * Update `cell.accepted_value = normalized["accepted_value"]`, `cell.numeric_decimal = normalized["numeric_decimal"]`, `cell.data_type = normalized["data_type"]`.
         * Set `cell.quality_status = CellQualityStatus.CORRECTED_WITH_EVIDENCE`.
         * Create `CorrectionRecord` with `inferred_candidate_only=False`, `decision="CORRECTION_ACCEPTED"`, `resulting_cell_status=CellQualityStatus.CORRECTED_WITH_EVIDENCE`.
         * Return `(cell, correction_record)`.
    3. Update `backend/app/extraction/__init__.py` to export `apply_evidence_gated_correction`, `reconstruct_multipage_tables`, `strip_repeated_headers`, `evaluate_stitch_pair`.
    
    AVOID: Modifying cell values to force mathematical balance (e.g. $100 + 200 = 350 \to 300$); auto-balancing totals is strictly forbidden by MASTER_DIRECTIVE Section 15.
  </action>
  <verify>
    powershell -Command "python -c 'from app.extraction.table_reconstructor import apply_evidence_gated_correction; print(callable(apply_evidence_gated_correction))'"
  </verify>
  <done>
    `apply_evidence_gated_correction` preserves `raw_value`, accepts corrections only from permitted sources, and places algebraic candidates in `inferred_candidate_value` without mutating accepted totals.
  </done>
</task>

## Success Criteria
- [ ] Repeated headers spanning 1–3 rows stripped only when text similarity and data-type incompatibility are satisfied.
- [ ] Multi-page tables stitched with contiguous `row_idx` sequences and combined `source_pages`.
- [ ] Duplicate data rows preserved without deduplication.
- [ ] Evidence-gated cell corrections enforce permitted source enum.
- [ ] Totals are never auto-balanced.
- [ ] Clean exports in `backend/app/extraction/__init__.py`.
