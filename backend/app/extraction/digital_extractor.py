"""
DocuStruct AI — Native Digital Table Extractor

Extracts tables from native digital PDF pages using two strategies:

1. **Ruling-line extraction** (primary) — ``pdfplumber`` line-based
   geometry for ruled tables.
2. **Coordinate-interval fallback** — native word positions clustered
   into columns and rows for borderless tables.

Design invariants (from MASTER_DIRECTIVE.md Section 13):
    - Ragged rows and legitimate duplicate rows are never pruned.
    - Cells are never shifted merely to make rows rectangular.
    - ``pdfplumber.PDF`` handles are closed in ``finally`` blocks.
    - Coordinates are in PDF points (1/72 inch).
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any, Optional

import pdfplumber

from app.extraction.normalizer import normalize_cell
from app.models.domain import (
    BoundingBox,
    CanonicalTable,
    CellRecord,
)
from app.models.state import (
    CellQualityStatus,
    DataType,
    ValidationOutcome,
    VerificationStatus,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════

RULING_LINE_SETTINGS: dict[str, Any] = {
    "vertical_strategy": "lines",
    "horizontal_strategy": "lines",
    "intersection_tolerance": 3,
    "snap_tolerance": 3,
}


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════


def _make_cell_record(
    table_id: str,
    row_idx: int,
    col_idx: int,
    page_num: int,
    text: str,
    extraction_method: str,
    bbox: Optional[BoundingBox],
    col_header: Optional[str] = None,
) -> CellRecord:
    """Create a normalised CellRecord from raw extracted text."""
    norm = normalize_cell(text, col_header=col_header)
    return CellRecord(
        table_id=table_id,
        row_idx=row_idx,
        col_idx=col_idx,
        source_page=page_num,
        bbox=bbox,
        extraction_method=extraction_method,
        raw_value=norm["raw_value"],
        normalized_value=norm["normalized_value"],
        accepted_value=norm["accepted_value"],
        numeric_decimal=norm["numeric_decimal"],
        data_type=norm["data_type"],
        quality_status=CellQualityStatus.EXTRACTED_AS_IS,
        formula_risk_detected=norm["formula_risk_detected"],
    )


def _page_bbox(page: pdfplumber.page.Page) -> BoundingBox:
    """Create a page-level BoundingBox from pdfplumber page dimensions."""
    return BoundingBox(
        x0=0.0,
        y0=0.0,
        x1=float(page.width),
        y1=float(page.height),
        page_width=float(page.width),
        page_height=float(page.height),
        coord_exact=True,
    )


def _cell_bbox(
    cell: tuple[float, float, float, float],
    page_width: float,
    page_height: float,
    coord_exact: bool = True,
) -> Optional[BoundingBox]:
    """Convert a pdfplumber cell tuple (x0, top, x1, bottom) to BoundingBox."""
    x0, top, x1, bottom = cell
    if x0 is None or top is None or x1 is None or bottom is None:
        return None
    if page_width <= 0 or page_height <= 0:
        return None
    return BoundingBox(
        x0=float(x0),
        y0=float(top),
        x1=float(x1),
        y1=float(bottom),
        page_width=page_width,
        page_height=page_height,
        coord_exact=coord_exact,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Strategy 1: Ruling-line extraction
# ═══════════════════════════════════════════════════════════════════════════


def extract_ruled_tables(
    page: pdfplumber.page.Page,
    page_num: int,
) -> list[CanonicalTable]:
    """Extract tables using pdfplumber line-based geometry.

    Parameters
    ----------
    page : pdfplumber.page.Page
        A pdfplumber page object.
    page_num : int
        1-based page number.

    Returns
    -------
    list[CanonicalTable]
        Tables found on this page via ruling lines.
    """
    try:
        tables_found = page.find_tables(table_settings=RULING_LINE_SETTINGS)
    except Exception:
        return []

    if not tables_found:
        return []

    pw = float(page.width)
    ph = float(page.height)
    results: list[CanonicalTable] = []

    for idx, table_obj in enumerate(tables_found):
        raw_rows = table_obj.extract()
        if not raw_rows or len(raw_rows) < 1:
            continue

        table_id = f"table_p{page_num}_{idx}"

        # Header candidates from first row
        header_row = raw_rows[0]
        original_headers = [
            (cell if cell is not None else "") for cell in header_row
        ]
        normalized_headers = [h.strip() for h in original_headers]

        # Build cell records for all rows (including header row at idx 0)
        all_rows: list[list[CellRecord]] = []
        cells_data = table_obj.cells or []

        for row_idx, row_data in enumerate(raw_rows):
            row_cells: list[CellRecord] = []
            for col_idx, cell_text in enumerate(row_data):
                text = cell_text if cell_text is not None else ""

                # Try to find matching cell bbox
                cell_tuple_idx = row_idx * len(row_data) + col_idx
                bbox = None
                if cell_tuple_idx < len(cells_data):
                    ct = cells_data[cell_tuple_idx]
                    bbox = _cell_bbox(ct, pw, ph, coord_exact=True)

                col_h = normalized_headers[col_idx] if col_idx < len(normalized_headers) else None
                cr = _make_cell_record(
                    table_id=table_id,
                    row_idx=row_idx,
                    col_idx=col_idx,
                    page_num=page_num,
                    text=text,
                    extraction_method="LINE_BASED_RULING",
                    bbox=bbox,
                    col_header=col_h,
                )
                row_cells.append(cr)
            all_rows.append(row_cells)

        # Build table bbox from the table object's bbox
        table_bbox = None
        if hasattr(table_obj, "bbox") and table_obj.bbox:
            tb = table_obj.bbox
            table_bbox = _cell_bbox(tb, pw, ph, coord_exact=True)

        ct = CanonicalTable(
            table_id=table_id,
            source_pages=[page_num],
            page_bbox=table_bbox,
            original_headers=original_headers,
            normalized_headers=normalized_headers,
            header_row_count=1,
            rows=all_rows,
            extraction_method="LINE_BASED_RULING",
            structural_checks_passed=True,
        )
        results.append(ct)

    return results


# ═══════════════════════════════════════════════════════════════════════════
# Strategy 2: Coordinate-interval fallback (borderless tables)
# ═══════════════════════════════════════════════════════════════════════════


def extract_borderless_tables(
    page: pdfplumber.page.Page,
    page_num: int,
) -> list[CanonicalTable]:
    """Extract tables from borderless layouts using word coordinate clustering.

    Parameters
    ----------
    page : pdfplumber.page.Page
        A pdfplumber page object.
    page_num : int
        1-based page number.

    Returns
    -------
    list[CanonicalTable]
        Tables inferred from coordinate alignment, if any.
    """
    try:
        words = page.extract_words(keep_blank_chars=False)
    except Exception:
        return []

    if not words or len(words) < 4:
        return []

    pw = float(page.width)
    ph = float(page.height)
    row_tolerance = 4.0  # points

    # --- Group words into lines by 'top' coordinate ---
    lines: list[list[dict]] = []
    sorted_words = sorted(words, key=lambda w: (float(w["top"]), float(w["x0"])))

    current_line: list[dict] = [sorted_words[0]]
    current_top = float(sorted_words[0]["top"])

    for w in sorted_words[1:]:
        w_top = float(w["top"])
        if abs(w_top - current_top) <= row_tolerance:
            current_line.append(w)
        else:
            lines.append(current_line)
            current_line = [w]
            current_top = w_top
    lines.append(current_line)

    if len(lines) < 2:
        return []

    # --- Merge words within each line into cell fragments separated by gutters ---
    # Standard word-spacing in text is <= 14pt; column gutters are significantly wider
    word_gap_threshold = 14.0
    line_fragments: list[list[dict]] = []

    for line in lines:
        fragments: list[dict] = []
        cur_frag_words = [line[0]]
        for w in line[1:]:
            gap = float(w["x0"]) - float(cur_frag_words[-1]["x1"])
            if gap <= word_gap_threshold:
                cur_frag_words.append(w)
            else:
                fragments.append({
                    "text": " ".join(fw["text"] for fw in cur_frag_words),
                    "x0": min(float(fw["x0"]) for fw in cur_frag_words),
                    "top": min(float(fw["top"]) for fw in cur_frag_words),
                    "x1": max(float(fw["x1"]) for fw in cur_frag_words),
                    "bottom": max(float(fw["bottom"]) for fw in cur_frag_words),
                })
                cur_frag_words = [w]
        fragments.append({
            "text": " ".join(fw["text"] for fw in cur_frag_words),
            "x0": min(float(fw["x0"]) for fw in cur_frag_words),
            "top": min(float(fw["top"]) for fw in cur_frag_words),
            "x1": max(float(fw["x1"]) for fw in cur_frag_words),
            "bottom": max(float(fw["bottom"]) for fw in cur_frag_words),
        })
        line_fragments.append(fragments)

    # Narrative text check: In prose, lines have 0 gutters (1 fragment per line).
    # A borderless table requires at least 2 lines with multiple columns.
    multi_col_lines = sum(1 for frags in line_fragments if len(frags) >= 2)
    if multi_col_lines < 2:
        return []

    # --- Identify column boundaries by clustering fragment x0 positions ---
    frag_x0s = sorted({round(frag["x0"], 1) for frags in line_fragments for frag in frags})
    col_tolerance = 12.0
    col_boundaries: list[float] = [frag_x0s[0]]
    for x in frag_x0s[1:]:
        if x - col_boundaries[-1] > col_tolerance:
            col_boundaries.append(x)

    if len(col_boundaries) < 2:
        return []

    # --- Build grid ---
    table_id = f"table_p{page_num}_borderless"

    # Header candidates from first line fragments
    header_texts = [""] * len(col_boundaries)
    for frag in line_fragments[0]:
        col_idx = _find_column(frag["x0"], col_boundaries, col_tolerance)
        if col_idx < len(header_texts):
            header_texts[col_idx] = frag["text"]

    original_headers = [h.strip() for h in header_texts]
    normalized_headers = [h.strip() for h in original_headers]

    all_rows: list[list[CellRecord]] = []
    for row_idx, frags in enumerate(line_fragments):
        cell_texts = [""] * len(col_boundaries)
        cell_bboxes: list[Optional[tuple[float, float, float, float]]] = [None] * len(col_boundaries)

        for frag in frags:
            col_idx = _find_column(frag["x0"], col_boundaries, col_tolerance)
            if col_idx < len(cell_texts):
                cell_texts[col_idx] = frag["text"]
                cell_bboxes[col_idx] = (frag["x0"], frag["top"], frag["x1"], frag["bottom"])

        row_cells: list[CellRecord] = []
        for col_idx, text in enumerate(cell_texts):
            bbox = None
            if cell_bboxes[col_idx] is not None:
                bbox = _cell_bbox(
                    cell_bboxes[col_idx], pw, ph, coord_exact=False,
                )
            col_h = normalized_headers[col_idx] if col_idx < len(normalized_headers) else None
            cr = _make_cell_record(
                table_id=table_id,
                row_idx=row_idx,
                col_idx=col_idx,
                page_num=page_num,
                text=text,
                extraction_method="COORDINATE_INTERVAL_FALLBACK",
                bbox=bbox,
                col_header=col_h,
            )
            row_cells.append(cr)
        all_rows.append(row_cells)

    ct = CanonicalTable(
        table_id=table_id,
        source_pages=[page_num],
        page_bbox=_page_bbox(page),
        original_headers=original_headers,
        normalized_headers=normalized_headers,
        header_row_count=1,
        rows=all_rows,
        extraction_method="COORDINATE_INTERVAL_FALLBACK",
        structural_checks_passed=False,
    )
    return [ct]


def _find_column(
    x0: float,
    boundaries: list[float],
    tolerance: float,
) -> int:
    """Find the column index for a word's x0 position."""
    best_idx = 0
    best_dist = abs(x0 - boundaries[0])
    for i, b in enumerate(boundaries[1:], 1):
        dist = abs(x0 - b)
        if dist < best_dist:
            best_dist = dist
            best_idx = i
    return best_idx


# ═══════════════════════════════════════════════════════════════════════════
# Page and document-level extraction
# ═══════════════════════════════════════════════════════════════════════════


def extract_tables_from_page(
    page: pdfplumber.page.Page,
    page_num: int,
) -> list[CanonicalTable]:
    """Extract tables from a single page using primary then fallback strategy.

    Parameters
    ----------
    page : pdfplumber.page.Page
        An open pdfplumber page.
    page_num : int
        1-based page number.

    Returns
    -------
    list[CanonicalTable]
    """
    tables = extract_ruled_tables(page, page_num)
    if tables:
        return tables
    return extract_borderless_tables(page, page_num)


def extract_document_tables(file_path: Path) -> list[CanonicalTable]:
    """Extract all tables from a PDF document.

    Opens the document via ``pdfplumber.open`` inside a strict
    ``try/finally`` block ensuring the handle is closed unconditionally.

    Parameters
    ----------
    file_path : Path
        Path to a validated PDF file.

    Returns
    -------
    list[CanonicalTable]
        All tables extracted across all pages.
    """
    pdf = None
    try:
        pdf = pdfplumber.open(str(Path(file_path).resolve()))
        all_tables: list[CanonicalTable] = []
        for page_idx, page in enumerate(pdf.pages, start=1):
            all_tables.extend(extract_tables_from_page(page, page_idx))
        return all_tables
    finally:
        if pdf is not None:
            pdf.close()
