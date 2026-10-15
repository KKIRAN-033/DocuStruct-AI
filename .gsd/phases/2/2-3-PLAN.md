---
phase: 2
plan: 3
wave: 2
depends_on: [2.1, 2.2]
files_modified:
  - backend/app/extraction/digital_extractor.py
  - backend/app/extraction/__init__.py
autonomous: true
must_haves:
  truths:
    - "Digital table extractor uses ruling-line extraction as primary strategy via pdfplumber."
    - "Borderless tables without ruling lines are extracted using coordinate-interval fallback."
    - "Cells are populated as CellRecord instances with BoundingBox geometry in PDF points."
    - "Ragged rows and legitimate duplicate rows are preserved, never pruned or padded."
    - "CanonicalTable instances have unique deterministic identifiers (e.g. table_p1_0)."
    - "pdfplumber PDF handles are closed in finally blocks to prevent Windows file locks."
  artifacts:
    - "backend/app/extraction/digital_extractor.py exists"
    - "backend/app/extraction/__init__.py exports extract_tables_from_page and extract_document_tables"
---

# Plan 2.3: Native Digital Table Extractor

## Objective
Implement `backend/app/extraction/digital_extractor.py` to extract tables from native digital PDF pages using `pdfplumber` ruling-line geometry as the primary strategy and horizontal coordinate intervals as the fallback strategy, constructing validated `CanonicalTable` and `CellRecord` domain models in accordance with MASTER_DIRECTIVE.md Section 13 and REQ-07.

## Context
- `MASTER_DIRECTIVE.md` (Section 13, Section 19)
- `.gsd/SPEC.md` (Goal 1)
- `.gsd/REQUIREMENTS.md` (REQ-07, REQ-13, NFR-02)
- `.gsd/phases/2/RESEARCH.md`
- `backend/app/models/domain.py`
- `backend/app/models/state.py`
- `backend/app/extraction/normalizer.py`

## Tasks

<task type="auto">
  <name>Implement line-based table extraction via pdfplumber</name>
  <files>
    backend/app/extraction/digital_extractor.py
    backend/app/extraction/__init__.py
  </files>
  <action>
    Create `backend/app/extraction/digital_extractor.py` implementing ruling-line extraction:
    1. Define table settings:
       `RULING_LINE_SETTINGS = {"vertical_strategy": "lines", "horizontal_strategy": "lines", "intersection_tolerance": 3, "snap_tolerance": 3}`.
    2. `extract_ruled_tables(page: pdfplumber.page.Page, page_num: int) -> list[CanonicalTable]`:
       - Use `page.find_tables(table_settings=RULING_LINE_SETTINGS)`.
       - For each found table:
         * Extract cell bounding boxes and text via table cells.
         * If table has no rows or is empty, skip.
         * Treat row 0 as header candidates: populate `original_headers` and `normalized_headers`.
         * For each row:
           - For each cell, extract text and cell bbox: `(x0, top, x1, bottom)`. Convert coordinates to PDF points relative to lower-left corner if needed, or document orientation. Set `coord_exact = True`.
           - Normalize cell text with `normalize_cell(cell_text, col_header)`.
           - Construct `CellRecord` with `table_id`, `row_idx`, `col_idx`, `source_page=page_num`, `bbox=BoundingBox(...)`, `extraction_method="LINE_BASED_RULING"`, `quality_status=CellQualityStatus.EXTRACTED_AS_IS`.
         * Construct `CanonicalTable`: `table_id=f"table_p{page_num}_{idx}"`, `source_pages=[page_num]`, `page_bbox=BoundingBox(...)`, `rows=rows_list`, `extraction_method="LINE_BASED_RULING"`, `structural_checks_passed=True`.
    
    AVOID: Silently dropping rows that appear empty when they may represent spacer rows in financial statements.
  </action>
  <verify>
    powershell -Command "python -c 'from app.extraction.digital_extractor import extract_ruled_tables; print(callable(extract_ruled_tables))'"
  </verify>
  <done>
    `extract_ruled_tables` successfully converts pdfplumber line-based tables into structured `CanonicalTable` and `CellRecord` models.
  </done>
</task>

<task type="auto">
  <name>Implement coordinate-interval fallback and document extraction runner</name>
  <files>
    backend/app/extraction/digital_extractor.py
    backend/app/extraction/__init__.py
  </files>
  <action>
    In `backend/app/extraction/digital_extractor.py`, implement:
    1. `extract_borderless_tables(page: pdfplumber.page.Page, page_num: int) -> list[CanonicalTable]`:
       - Fallback strategy when `extract_ruled_tables` finds no tables:
       - Extract word tokens with `page.extract_words(keep_blank_chars=False)`.
       - If word count < 4 (not enough text for a table), return empty list.
       - Group words into horizontal lines using `top` tolerance (e.g. 3-4 points).
       - Identify column intervals by clustering `x0` and `x1` coordinate boundaries.
       - If at least 2 distinct columns and 2 distinct rows are identified:
         * Form 2D grid of `CellRecord` instances with `extraction_method="COORDINATE_INTERVAL_FALLBACK"`.
         * Normalize each cell with `normalize_cell`.
         * Set `coord_exact = False` on BoundingBox since coordinates are interval-inferred.
         * Construct `CanonicalTable` with `extraction_method="COORDINATE_INTERVAL_FALLBACK"`.
       - Preserve ragged rows: do not force padding or truncate uneven rows.
    2. `extract_tables_from_page(page: pdfplumber.page.Page, page_num: int) -> list[CanonicalTable]`:
       - First call `extract_ruled_tables(page, page_num)`.
       - If tables found, return them.
       - Otherwise, call `extract_borderless_tables(page, page_num)`.
    3. `extract_document_tables(file_path: Path) -> list[CanonicalTable]`:
       - Open document via `pdfplumber.open(str(file_path))` in a strict `try/finally` block:
         ```python
         pdf = pdfplumber.open(str(file_path))
         try:
             tables = []
             for page_idx, page in enumerate(pdf.pages, start=1):
                 tables.extend(extract_tables_from_page(page, page_idx))
             return tables
         finally:
             pdf.close()
         ```
       - Guarantees `pdf.close()` is executed unconditionally, preventing Windows file locking (`PermissionError`).
    4. Export `extract_tables_from_page`, `extract_document_tables`, `extract_ruled_tables`, `extract_borderless_tables` in `backend/app/extraction/__init__.py`.

    AVOID: Keeping `pdfplumber.PDF` instances open outside context managers or `finally` blocks; unclosed handles cause fatal Windows `PermissionError` during workspace cleanup.
  </action>
  <verify>
    powershell -Command "python -c 'from app.extraction.digital_extractor import extract_document_tables; print(callable(extract_document_tables))'"
  </verify>
  <done>
    `extract_tables_from_page` handles both ruled and borderless fallback extraction; `extract_document_tables` runs across pages with guaranteed handle closure on Windows.
  </done>
</task>

## Success Criteria
- [ ] Ruling-line extraction implemented with `pdfplumber` line geometry.
- [ ] Coordinate-interval fallback implemented for borderless tables.
- [ ] Cell bounding boxes recorded in PDF points with exact/inferred flags.
- [ ] Ragged rows and duplicate rows preserved without truncation or artificial padding.
- [ ] Guaranteed closure of `pdfplumber.PDF` handles in `finally` blocks.
- [ ] Clean package exports in `backend/app/extraction/__init__.py`.
