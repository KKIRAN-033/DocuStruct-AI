# Phase 2 Research: Page Routing, Normalization & Digital Extraction

## Executive Summary
Phase 2 establishes the core page routing and deterministic extraction pipeline for native digital PDFs in DocuStruct AI:
1. `app/ingestion/page_router.py`: Classifies individual PDF pages into `DIGITAL`, `SCANNED`, `HYBRID`, or `EMPTY_OR_UNREADABLE` using explainable geometric and textual signals.
2. `app/extraction/normalizer.py`: Performs deterministic text and numeric normalization, preserves identifier leading zeros, and flags spreadsheet formula-injection risks without prepending apostrophes or mutating cell values.
3. `app/extraction/digital_extractor.py`: Extracts tabular data from native digital PDF pages using ruling-line geometry (via `pdfplumber`) with a coordinate-interval fallback, constructing structured `CanonicalTable` objects.
4. Comprehensive unit test suites testing real behavior on reproducible synthetic PDFs without external unapproved dependencies.

---

## 1. Page Classification & Routing Architecture (`page_router.py`)

### 1.1 Requirements & Signal Detection
Per MASTER_DIRECTIVE.md Section 11, each page must be classified using deterministic, explainable signals:
- **Printable Character Count (`printable_char_count`)**: Number of non-whitespace printable ASCII/Unicode characters in the page text stream extracted via `pymupdf`.
- **Garbled Character Ratio (`garbled_char_ratio`)**: Fraction of non-printable or replacement/to-unicode error characters relative to total character count.
- **Embedded Image Coverage (`image_coverage_ratio`)**: Total area of embedded raster images relative to total page area (`page.rect.width * page.rect.height`). Overlapping image bounding boxes should be unioned or clamped to avoid >1.0 coverage.
- **Vector Line Count (`vector_line_count`)**: Count of vector stroke/path drawings obtained via `page.get_drawings()`.

### 1.2 Classification Decision Tree
Using thresholds configured in `thresholds.yaml` (loaded via `CalibrationConfig`):
1. **EMPTY_OR_UNREADABLE**:
   - `printable_char_count == 0` AND `image_coverage_ratio < image_coverage_scanned_min` (0.40) AND `vector_line_count == 0`.
   - `processing_status = EMPTY_PAGE`, `table_presence = CONFIRMED_ABSENT`.
2. **SCANNED**:
   - `printable_char_count < char_count_digital_min` (50) AND `image_coverage_ratio >= image_coverage_scanned_min` (0.40).
   - `processing_status = INCOMPLETE_DEFERRED_TO_OCR`, `table_presence = UNKNOWN_PENDING_OCR`.
   - Design invariant: Scanned pages are NEVER classified as zero-table documents (`CONFIRMED_ABSENT`).
3. **HYBRID**:
   - `printable_char_count >= char_count_digital_min` (50) AND `image_coverage_ratio >= 0.20` with significant unprocessed raster regions.
   - `processing_status = INCOMPLETE_DEFERRED_TO_OCR`, `table_presence = UNKNOWN_PENDING_OCR`, `deferred_regions_count >= 1`.
4. **DIGITAL**:
   - `printable_char_count >= char_count_digital_min` (50) AND `garbled_char_ratio <= garbled_ratio_max` (0.10) AND image coverage does not obstruct tables.
   - `processing_status = EXTRACTED`, `table_presence = CONFIRMED_PRESENT` (if tables found) or `CONFIRMED_ABSENT` (if no tables found).

### 1.3 Sequential Resource Discipline
- Open document handle once or page-by-page.
- Always access pages sequentially (`page = doc.load_page(i)`), release page references, and explicitly close doc handles.
- Never render pages to full-color pixmaps in Phase 1 (avoids 100+ MB per-page RAM spikes).

---

## 2. Deterministic Normalization & Formula-Risk Detection (`normalizer.py`)

### 2.1 Separation of Values
The data contract requires preserving the value chain separately:
- `raw_value`: Exact immutable extracted text from the source PDF.
- `normalized_value`: Standardized string representation (e.g., standard decimal notation `-450.50`).
- `accepted_value`: Downstream-consumable string value.
- `numeric_decimal`: `Optional[Decimal]` for exact arithmetic; must be constructed via `Decimal(str_val)` and NEVER converted through binary `float`.
- `data_type`: Inferred `DataType` (`STRING`, `IDENTIFIER`, `INTEGER`, `DECIMAL`, `HIGH_PRECISION_DECIMAL`, `DATE`, `EMPTY`).
- `formula_risk_detected`: Boolean flag indicating formula-risk prefix.

### 2.2 Numeric Normalization Rules
1. **Grouping Styles**:
   - Standard: `1,234,567.89` → `-1234567.89` (strip commas if valid 3-digit grouping).
   - Indian grouping: `12,34,567.89` (2-digit grouping after first 3 digits) → `1234567.89`.
   - Reject malformed grouping: e.g. `12,345,67.89` must not have commas silently stripped; retain as raw string or flag anomaly.
2. **Negative Representations**:
   - Leading minus: `-450.50` → `normalized_value = "-450.50"`, `Decimal("-450.50")`.
   - Trailing accounting minus: `450.50-` → `normalized_value = "-450.50"`, `Decimal("-450.50")`.
   - Parenthesized accounting negative: `(450.50)` → `normalized_value = "-450.50"`, `Decimal("-450.50")`.
3. **High-Precision Decimals**:
   - Numbers with >4 decimal places (e.g. exchange rates `0.00012345`) classified as `HIGH_PRECISION_DECIMAL` with full precision preserved in `Decimal`.

### 2.3 Identifier Leading-Zero Preservation
Columns representing identifiers (Account, Invoice, GSTIN, PAN, Aadhaar, Phone, ID, Code, Ref, No) must retain significant leading zeros:
- Example: `"0012345"` → `data_type = DataType.IDENTIFIER`, `normalized_value = "0012345"`, `numeric_decimal = None`.
- Never convert `"0012345"` to `12345`.

### 2.4 Formula-Risk Boundary & Security Invariants
- Prefixes checked on nonnumeric `STRING` or `IDENTIFIER` cells: `=`, `+`, `-`, `@`, `\t` (tab), `\r` (carriage return).
- **CRITICAL INVARIANT**: Valid numeric negatives (e.g. `-450.50`, `(450.50)`) MUST NOT trigger `formula_risk_detected`. Numeric parsing must precede formula-risk evaluation!
- **CRITICAL INVARIANT**: Never prepend an apostrophe (`'`) or mutate cell values. Only set `formula_risk_detected = True`. Escaping belongs exclusively at Phase 3 Excel export boundaries.

---

## 3. Digital Table Extraction Architecture (`digital_extractor.py`)

### 3.1 Primary Strategy: Ruling-Line Extraction (`pdfplumber`)
- `pdfplumber.PDF.pages[i].find_tables(table_settings)`
- Settings:
  - `vertical_strategy: "lines"`
  - `horizontal_strategy: "lines"`
  - `intersection_tolerance: 3`
  - `snap_tolerance: 3`
- Extracts exact cell bounding boxes in PDF points.
- Identifies table borders, headers, and rows from geometric line intersections.

### 3.2 Fallback Strategy: Coordinate Interval / Text Alignment
- When ruling lines are absent (borderless table):
  - Extract native word positions using `page.extract_words(keep_blank_chars=False)`.
  - Cluster horizontal word positions (`x0`, `x1`) into column intervals.
  - Group words vertically by `top` / `bottom` into distinct row slices.
  - Construct table grid without inventing or dropping ragged cells.

### 3.3 Defensive Resource Management & Windows File Locking
- Open `pdfplumber.open(path)` inside `try...finally` ensuring `pdf.close()` is called unconditionally.
- Construct `CanonicalTable` with `table_id = f"table_p{page_num}_{idx}"`.
- Ensure all cells are populated as `CellRecord` instances linked to `page_bbox` and cell `BoundingBox`.
