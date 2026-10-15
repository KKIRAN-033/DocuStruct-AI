---
phase: 3
plan: 1
wave: 1
depends_on: []
files_modified:
  - backend/app/extraction/table_reconstructor.py
  - backend/app/extraction/__init__.py
autonomous: true
must_haves:
  truths:
    - "Seven decision factors are evaluated deterministically for adjacent candidate tables."
    - "Table-relative column overlap is calculated relative to outer horizontal span, not absolute page coordinates."
    - "Differing column counts are never reconciled by inventing, deleting, or shifting columns."
    - "Every evaluated adjacent-table pair produces a structured StitchAuditEvent audit record."
  artifacts:
    - "backend/app/extraction/table_reconstructor.py exists"
    - "backend/app/extraction/__init__.py exports evaluate_stitch_pair"
---

# Plan 3.1: Multipage Table Reconstructor & 7-Factor Decision Engine

## Objective
Implement `backend/app/extraction/table_reconstructor.py` with the 7-factor evaluation engine that deterministically decides whether two candidate tables on sequential pages should be merged (`STITCH_CONFIRMED`), kept separate (`STITCH_REJECTED`), or flagged for review (`STITCH_REVIEW_REQUIRED`), generating complete `StitchAuditEvent` records in compliance with MASTER_DIRECTIVE.md Section 14 and REQ-08.

## Context
- `MASTER_DIRECTIVE.md` (Section 14)
- `.gsd/SPEC.md` (Goal 3)
- `.gsd/REQUIREMENTS.md` (REQ-08, REQ-13)
- `.gsd/phases/3/RESEARCH.md`
- `backend/app/config/calibration.py`
- `backend/app/models/domain.py`
- `backend/app/models/state.py`

## Tasks

<task type="auto">
  <name>Implement column overlap and type compatibility metrics</name>
  <files>
    backend/app/extraction/table_reconstructor.py
    backend/app/extraction/__init__.py
  </files>
  <action>
    Create `backend/app/extraction/table_reconstructor.py` with geometric and schema compatibility functions:
    1. `compute_relative_column_intervals(table: CanonicalTable) -> list[tuple[float, float]]`:
       - Extract horizontal bounds $[x_0, x_1]$ for each column from cell bounding boxes across table rows.
       - If no cell bboxes exist, interpolate uniform intervals $[i/N, (i+1)/N]$ across $N$ columns.
       - Normalize intervals relative to table outer span $[X_0, X_1]$: `rel_x0 = (x0 - X0) / (X1 - X0)`, `rel_x1 = (x1 - X0) / (X1 - X0)`.
       - Handle zero-width span defensively (return empty or normalized uniform intervals).
    2. `compute_column_overlap_ratio(intervals_a: list[tuple[float, float]], intervals_b: list[tuple[float, float]]) -> float`:
       - If column counts differ, return 0.0.
       - Compute average Intersection-over-Union (IoU) across corresponding column intervals:
         $$\text{IoU}_i = \frac{\max(0, \min(a_{i,1}, b_{i,1}) - \max(a_{i,0}, b_{i,0}))}{\max(a_{i,1}, b_{i,1}) - \min(a_{i,0}, b_{i,0})}$$
       - Return average IoU bounded in $[0.0, 1.0]$.
    3. `compute_type_compatibility(table_a: CanonicalTable, table_b: CanonicalTable) -> float`:
       - For each column, determine dominant DataType from non-empty body cells (excluding header row).
       - If column counts differ, return 0.0.
       - Calculate ratio of matching dominant column types between `table_a` and `table_b` bounded in $[0.0, 1.0]$.
    
    AVOID: Comparing absolute page coordinates; tables on even/odd pages often have alternating gutter margins, requiring table-relative normalization.
  </action>
  <verify>
    powershell -Command "python -c 'from app.extraction.table_reconstructor import compute_column_overlap_ratio; print(compute_column_overlap_ratio([(0.0, 0.5), (0.5, 1.0)], [(0.0, 0.5), (0.5, 1.0)]))'"
  </verify>
  <done>
    `compute_column_overlap_ratio` returns 1.0 for identical relative column geometries; `compute_type_compatibility` correctly determines dominant body cell type match fractions.
  </done>
</task>

<task type="auto">
  <name>Implement 7-factor stitch evaluator</name>
  <files>
    backend/app/extraction/table_reconstructor.py
    backend/app/extraction/__init__.py
  </files>
  <action>
    In `backend/app/extraction/table_reconstructor.py`, implement:
    1. `evaluate_header_similarity(headers_a: list[str], headers_b: list[str]) -> float`:
       - Compare corresponding header strings using `rapidfuzz.fuzz.ratio(h_a, h_b) / 100.0`.
       - Return average similarity score in $[0.0, 1.0]$.
    2. `check_serial_continuity(upper_table: CanonicalTable, lower_table: CanonicalTable) -> tuple[bool, Optional[str]]`:
       - Inspect column 0 or numeric identifier columns for sequential integers ($N \to N+1$).
       - If upper ends with $K$ and lower starts with $K+1$, return `(True, "CONTINUOUS_SEQUENCE")`.
       - If lower starts with $1$, return `(False, "INDEX_RESET")`.
       - Otherwise return `(False, "NO_SERIAL_DETECTED")`.
    3. `evaluate_stitch_pair(upper_table: CanonicalTable, lower_table: CanonicalTable, calibration: Optional[CalibrationConfig] = None) -> tuple[StitchDecision, StitchAuditEvent]`:
       - Load calibration defaults if `calibration` is None.
       - Evaluate sequential pages: `upper_table.source_pages[-1] + 1 == lower_table.source_pages[0]`. If not sequential, decision is `STITCH_REJECTED`.
       - Check differing column counts:
         * If column counts differ and upper table has an explicit "Grand Total" or "Total" ending row, decision is `STITCH_REJECTED`.
         * If column counts differ but overlap is plausible, decision is `STITCH_REVIEW_REQUIRED`.
       - Calculate `col_overlap_ratio`, `type_compatibility_ratio`, and `header_similarity_score`.
       - If `col_overlap_ratio >= calibration.stitch_min_relative_col_overlap` (0.75) and `type_compatibility_ratio >= calibration.stitch_min_type_compatibility` (0.85):
         * Decision is `STITCH_CONFIRMED`.
       - Construct and return `(decision, StitchAuditEvent(...))` with complete reasons list.
    4. Export `evaluate_stitch_pair` in `backend/app/extraction/__init__.py`.
  </action>
  <verify>
    powershell -Command "python -c 'from app.extraction.table_reconstructor import evaluate_stitch_pair; print(callable(evaluate_stitch_pair))'"
  </verify>
  <done>
    `evaluate_stitch_pair` evaluates the 7 factors and returns `(StitchDecision, StitchAuditEvent)` with evidence reasons.
  </done>
</task>

## Success Criteria
- [ ] Table-relative column overlap computed independently of absolute page margins.
- [ ] Dominant body-cell data types compared across corresponding columns.
- [ ] RapidFuzz string similarity evaluated for repeated headers.
- [ ] Differing column counts trigger `STITCH_REJECTED` or `STITCH_REVIEW_REQUIRED`, never forced merging.
- [ ] `StitchAuditEvent` generated with complete audit trail metrics.
