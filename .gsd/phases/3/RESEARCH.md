# Phase 3 Technical Research: Multipage Reconstruction & Evidence-Gated Corrections

## 1. Domain Overview & Problem Statement

Phase 3 implements the conservative cross-page table stitcher (`table_reconstructor.py`) and evidence-gated correction contracts (`CorrectionRecord`), fulfilling **REQ-08**, **REQ-09**, and **REQ-13** from `MASTER_DIRECTIVE.md` Sections 14 and 15.

In enterprise and financial PDFs, tables frequently span across multiple pages. Unlike naive table concatenation, `DocuStruct AI` enforces conservative, explainable reconstruction:
1. Tables must never be blindly merged across pages without evaluating structural and semantic continuity.
2. Columns must never be invented, deleted, or shifted to force a rectangular merge.
3. Repeated headers spanning 1 to 3 rows must be identified using sliding-window text similarity and body-type validation before removal.
4. Duplicate rows (e.g., identical transaction lines) must strictly be preserved.
5. Cell corrections must strictly be evidence-gated: arithmetic discrepancies (`100 + 200 = 350`) must NEVER be auto-balanced; algebraic inferences are stored only in `inferred_candidate_value` with `ILLEGIBLE_OR_MISSING` status.

---

## 2. The Seven Decision Factors for Multipage Stitching

`MASTER_DIRECTIVE.md` Section 14 mandates evaluating seven deterministic decision factors:

### Factor 1: Column Count and Schema Compatibility
- If column counts differ:
  - If independent evidence supports separate tables (intervening title/heading, upper table ends with an explicit "Grand Total", incompatible headers), return `STITCH_REJECTED`.
  - If continuation is plausible but column counts differ due to extraction artifacts (missing vertical borders, dropped empty columns, merged cells), return `STITCH_REVIEW_REQUIRED`. Preserve both tables separately.
  - Never invent, drop, or shift columns.

### Factor 2: Table-Relative Normalized Column Overlap
- Rather than comparing absolute page coordinates (which vary due to margin shifts between odd and even pages), normalize each column's horizontal interval $[x_0, x_1]$ relative to the table's outer horizontal bounding box $[X_0, X_1]$:
  $$\text{rel\_x0} = \frac{x_0 - X_0}{X_1 - X_0}, \quad \text{rel\_x1} = \frac{x_1 - X_0}{X_1 - X_0}$$
- Compute the Jaccard-like or intersection-over-union overlap ratio between column boundaries of upper and lower tables.
- Threshold: `stitch_min_relative_col_overlap = 0.75` (from `CalibrationConfig`).

### Factor 3: Repeated-Header Text Similarity
- Multipage tables frequently repeat the table header at the top of continuation pages.
- Evaluate sliding windows of 1, 2, and 3 leading rows of the lower table against the upper table's canonical headers.
- Use `rapidfuzz.fuzz.ratio` (normalized to $[0.0, 1.0]$) to calculate string similarity.
- Threshold: `header_similarity_confirm = 0.85` (from `CalibrationConfig`).
- Header stripping is applied ONLY when:
  1. Rows are at the very top of the lower table (index 0).
  2. Average header similarity reaches $\ge 0.85$.
  3. Corresponding lower rows are inconsistent with body data types.
  4. Number of stripped rows is logged in `StitchAuditEvent.repeated_header_rows_stripped`.

### Factor 4: Column Data-Type Compatibility
- Compare the dominant data types of corresponding body columns between upper and lower tables.
- Compute the fraction of columns whose dominant types match (`INTEGER` vs `INTEGER`, `DECIMAL` vs `DECIMAL`, `STRING` vs `STRING`).
- Threshold: `stitch_min_type_compatibility = 0.85` (from `CalibrationConfig`).

### Factor 5: Page-Transition Context
- Evaluate geometric proximity:
  - Upper table ends near bottom of content zone on page $N$.
  - Lower table begins near top of content zone on page $N+1$.
- Check that $N_{\text{lower}} == N_{\text{upper}} + 1$.

### Factor 6: Row-Index Continuity
- Inspect leading columns for sequential serial numbering ($1, 2, 3 \dots$).
- If upper table ends with row index $K$ and lower table begins with $K+1$, this is strong evidence supporting continuation.
- An index reset (e.g. restarts at $1$) supports separate tables but is evaluated alongside other factors.

### Factor 7: Duplicate Data Preservation
- Identical data rows between or within pages must NEVER be pruned solely because cell values match.
- Legitimate bank/ledger transactions frequently repeat identical amounts, dates, and descriptions.

### Stitch Decision Precedence
- `STITCH_CONFIRMED`: All mandatory compatibility checks pass (matching column count, overlap $\ge 0.75$, header similarity $\ge 0.85$ if repeated headers exist or body type compatibility $\ge 0.85$, sequential pages), with no material contradictory evidence.
- `STITCH_REJECTED`: Clear contradictory evidence (differing column counts with separate headings, Grand Total row, negative continuity).
- `STITCH_REVIEW_REQUIRED`: Ambiguous evidence or suspected extraction artifacts.

---

## 3. Evidence-Gated Cell Corrections

`MASTER_DIRECTIVE.md` Section 15 governs cell corrections:
- Permitted deterministic evidence sources:
  1. `NATIVE_PDF_CHAR_STREAM`
  2. `INDEPENDENT_WORD_COORDINATES`
  3. `VECTOR_GRID_GEOMETRY`
- Independence Rule: Two evidence sources cannot be the same underlying extraction result represented twice.
- No Auto-Balancing:
  - If a row states $100 + 200 = 350$, the system preserves $350$ and records a validation issue `SOURCE_ARITHMETIC_DISCREPANCY`. It does NOT replace $350$ with $300$.
- Missing/Illegible Values:
  - Algebraic deductions must be stored only in `inferred_candidate_value`.
  - Cell status must be `CellQualityStatus.ILLEGIBLE_OR_MISSING`.
  - `accepted_value` must not be fabricated.
- Every accepted correction generates a `CorrectionRecord` audit item and updates the cell status to `CellQualityStatus.CORRECTED_WITH_EVIDENCE`.

---

## 4. Phase 3 Architecture & Interfaces

```
backend/app/extraction/
├── __init__.py               # Exports reconstruct_multipage_tables, evaluate_stitch_pair, apply_evidence_gated_correction
├── normalizer.py             # Phase 2 (Existing)
├── digital_extractor.py      # Phase 2 (Existing)
└── table_reconstructor.py    # Phase 3 (New)
    ├── evaluate_stitch_pair() -> tuple[StitchDecision, StitchAuditEvent]
    ├── strip_repeated_headers() -> tuple[list[list[CellRecord]], int]
    ├── stitch_canonical_tables() -> CanonicalTable
    ├── reconstruct_multipage_tables() -> list[CanonicalTable]
    └── apply_evidence_gated_correction() -> tuple[CellRecord, Optional[CorrectionRecord]]
```

---

## 5. Execution Plan Wave Breakdown

1. **Wave 1:**
   - **Plan 3.1:** Multipage table reconstructor (`table_reconstructor.py`): 7-factor evaluation, relative column overlap, dominant column typing, `evaluate_stitch_pair()`, and `StitchAuditEvent` logging.
   - **Plan 3.2:** Repeated header stripping (1–3 row sliding window), table concatenation with row index re-sequencing, and evidence-gated correction contracts (`CorrectionRecord`).
2. **Wave 2:**
   - **Plan 3.3:** Comprehensive Phase 3 unit test suite (`backend/tests/unit/test_step_1_6_table_reconstructor.py`) covering continuation, rejection, review, header stripping, serial continuity, duplicate row preservation, and correction contracts.
