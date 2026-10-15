---
phase: 2
plan: 1
wave: 1
depends_on: []
files_modified:
  - backend/app/ingestion/page_router.py
  - backend/app/ingestion/__init__.py
autonomous: true
must_haves:
  truths:
    - "Page router classifies PDF pages into DIGITAL, SCANNED, HYBRID, and EMPTY_OR_UNREADABLE using explainable signals."
    - "Scanned pages are marked INCOMPLETE_DEFERRED_TO_OCR and UNKNOWN_PENDING_OCR, never CONFIRMED_ABSENT."
    - "Empty pages are correctly detected and marked EMPTY_PAGE and CONFIRMED_ABSENT."
    - "Document and page handles are closed deterministically without memory leaks."
  artifacts:
    - "backend/app/ingestion/page_router.py exists"
    - "PageProfile objects are returned with valid signal metrics"
---

# Plan 2.1: Page Router & Incremental Routing

## Objective
Implement `backend/app/ingestion/page_router.py` to inspect individual PDF pages, extract geometric and text signals (printable characters, garbled ratio, image coverage, vector lines), and classify pages into `DIGITAL`, `SCANNED`, `HYBRID`, or `EMPTY_OR_UNREADABLE` in accordance with MASTER_DIRECTIVE.md Section 11 and REQ-05.

## Context
- `MASTER_DIRECTIVE.md` (Section 11, Section 19)
- `.gsd/SPEC.md` (Goal 1)
- `.gsd/REQUIREMENTS.md` (REQ-05, NFR-01, NFR-02)
- `.gsd/phases/2/RESEARCH.md`
- `backend/app/models/state.py`
- `backend/app/models/domain.py`
- `backend/app/config/calibration.py`

## Tasks

<task type="auto">
  <name>Implement page signal analyzer</name>
  <files>
    backend/app/ingestion/page_router.py
  </files>
  <action>
    Create `backend/app/ingestion/page_router.py` with `analyze_page_signals(page: pymupdf.Page) -> dict[str, Any]`:
    1. Extract page dimensions from `page.rect`. If dimensions <= 0, handle safely.
    2. Extract raw text with `page.get_text("text")`.
       - Count non-whitespace printable characters (`printable_char_count`).
       - Calculate `garbled_char_ratio`: count replacement characters (`\ufffd`), unprintable control characters (excluding `\n`, `\r`, `\t`), and divide by total character count. Return 0.0 if empty.
    3. Calculate `image_coverage_ratio`:
       - Retrieve image list with `page.get_images(full=True)`.
       - For each image, retrieve its page bbox via `page.get_image_rects(xref)`.
       - Compute approximate total bounding area covered by images divided by total page area (`page.rect.width * page.rect.height`), capped at 1.0.
    4. Count vector drawings with `page.get_drawings()`.
       - `vector_line_count = len(drawings)`.
    5. Count deferred raster regions: if `image_coverage_ratio >= 0.20`, set `deferred_regions_count = len(images)`.
    
    AVOID: Rendering pages to full pixmaps (`page.get_pixmap()`) because it consumes tens of megabytes of RAM per page on 300+ DPI documents, violating NFR-01.
  </action>
  <verify>
    powershell -Command "python -c 'import pymupdf; from app.ingestion.page_router import analyze_page_signals; doc = pymupdf.open(); p = doc.new_page(); s = analyze_page_signals(p); print(s[\"printable_char_count\"]); doc.close()'"
  </verify>
  <done>
    `analyze_page_signals` returns a dictionary containing `printable_char_count`, `garbled_char_ratio`, `image_coverage_ratio`, `vector_line_count`, and `deferred_regions_count`.
  </done>
</task>

<task type="auto">
  <name>Implement page classifier and document routing coordinator</name>
  <files>
    backend/app/ingestion/page_router.py
    backend/app/ingestion/__init__.py
  </files>
  <action>
    In `backend/app/ingestion/page_router.py`, implement:
    1. `classify_page(page_number: int, signals: dict[str, Any], calibration: Optional[CalibrationConfig] = None) -> PageProfile`:
       - If `signals["printable_char_count"] == 0` and `signals["image_coverage_ratio"] < calibration.image_coverage_scanned_min` (0.40) and `signals["vector_line_count"] == 0`:
         * `page_type = PageType.EMPTY_OR_UNREADABLE`, `processing_status = PageProcessingStatus.EMPTY_PAGE`, `table_presence = TablePresenceStatus.CONFIRMED_ABSENT`.
       - Else if `signals["printable_char_count"] < calibration.char_count_digital_min` (50) and `signals["image_coverage_ratio"] >= calibration.image_coverage_scanned_min` (0.40):
         * `page_type = PageType.SCANNED`, `processing_status = PageProcessingStatus.INCOMPLETE_DEFERRED_TO_OCR`, `table_presence = TablePresenceStatus.UNKNOWN_PENDING_OCR`.
       - Else if `signals["printable_char_count"] >= calibration.char_count_digital_min` (50) and `signals["image_coverage_ratio"] >= 0.20`:
         * `page_type = PageType.HYBRID`, `processing_status = PageProcessingStatus.INCOMPLETE_DEFERRED_TO_OCR`, `table_presence = TablePresenceStatus.UNKNOWN_PENDING_OCR`.
       - Else:
         * `page_type = PageType.DIGITAL`, `processing_status = PageProcessingStatus.EXTRACTED`, `table_presence = TablePresenceStatus.CONFIRMED_PRESENT` (initial status, updated during table extraction).
       - Construct and return validated `PageProfile` model from `app.models.domain`.
    2. `route_document_pages(file_path: Path, calibration: Optional[CalibrationConfig] = None) -> list[PageProfile]`:
       - Open document via `pymupdf.open(str(file_path))` wrapped in a strict `try/finally` block ensuring document closure.
       - Iterate sequentially over pages: `page = doc.load_page(i)`.
       - Analyze signals, classify page, append to profiles list.
       - Release page reference each iteration.
    3. Update `backend/app/ingestion/__init__.py` to export `analyze_page_signals`, `classify_page`, and `route_document_pages`.

    AVOID: Marking scanned documents as `CONFIRMED_ABSENT` for table presence; MASTER_DIRECTIVE Section 11 strictly mandates `UNKNOWN_PENDING_OCR` for scanned content.
  </action>
  <verify>
    powershell -Command "python -c 'from app.ingestion.page_router import classify_page, route_document_pages; from app.models.state import PageType; p = classify_page(1, {\"printable_char_count\": 0, \"garbled_char_ratio\": 0.0, \"image_coverage_ratio\": 0.0, \"vector_line_count\": 0, \"deferred_regions_count\": 0}); print(p.page_type == PageType.EMPTY_OR_UNREADABLE)'"
  </verify>
  <done>
    `classify_page` classifies empty, scanned, hybrid, and digital profiles according to thresholds; `route_document_pages` runs end-to-end on a PDF with clean resource closure.
  </done>
</task>

## Success Criteria
- [ ] `page_router.py` implemented with deterministic signal analysis.
- [ ] Classification logic correctly identifies `DIGITAL`, `SCANNED`, `HYBRID`, and `EMPTY_OR_UNREADABLE`.
- [ ] `PageProfile` models returned with complete metrics matching schema.
- [ ] Guaranteed closure of `pymupdf.Document` handles.
- [ ] Clean package exports in `backend/app/ingestion/__init__.py`.
