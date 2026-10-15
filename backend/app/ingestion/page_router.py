"""
DocuStruct AI — Page Router & Classification

Classifies individual PDF pages as DIGITAL, SCANNED, HYBRID, or
EMPTY_OR_UNREADABLE using deterministic, explainable signals:
printable character count, garbled-character ratio, embedded image
coverage, and vector-line count.

Design invariants (from MASTER_DIRECTIVE.md Section 11):
    - A scanned page is NEVER classified as CONFIRMED_ABSENT.
    - Pages are processed sequentially; page handles are released
      after each iteration.
    - Full-page pixmap rendering is never used (avoids 100+ MB spikes).
"""

from __future__ import annotations

import logging
import unicodedata
from pathlib import Path
from typing import Any, Optional

import pymupdf  # PyMuPDF

from app.config.calibration import CalibrationConfig
from app.models.domain import PageProfile
from app.models.state import (
    PageProcessingStatus,
    PageType,
    TablePresenceStatus,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Page signal analysis
# ═══════════════════════════════════════════════════════════════════════════


def analyze_page_signals(page: pymupdf.Page) -> dict[str, Any]:
    """Extract deterministic classification signals from a single page.

    Parameters
    ----------
    page : pymupdf.Page
        An open PyMuPDF page object.

    Returns
    -------
    dict
        Keys: ``printable_char_count``, ``garbled_char_ratio``,
        ``image_coverage_ratio``, ``vector_line_count``,
        ``deferred_regions_count``.
    """
    # --- Page dimensions ---
    rect = page.rect
    page_width = rect.width
    page_height = rect.height
    page_area = page_width * page_height if page_width > 0 and page_height > 0 else 0.0

    # --- Text signals ---
    raw_text = page.get_text("text") or ""
    total_chars = len(raw_text)

    printable_count = 0
    garbled_count = 0

    for ch in raw_text:
        if ch in ("\n", "\r", "\t", " "):
            continue  # whitespace — skip for both counts
        cat = unicodedata.category(ch)
        if cat.startswith("C"):
            # Control characters (excluding whitespace handled above)
            garbled_count += 1
        elif ch == "\ufffd":
            # Unicode replacement character
            garbled_count += 1
        else:
            printable_count += 1

    # garbled_char_ratio: fraction of garbled characters among all
    # non-whitespace characters (printable + garbled)
    non_ws_total = printable_count + garbled_count
    garbled_ratio = garbled_count / non_ws_total if non_ws_total > 0 else 0.0

    # --- Image coverage ---
    images = page.get_images(full=True)
    image_area = 0.0
    for img_info in images:
        xref = img_info[0]
        try:
            rects = page.get_image_rects(xref)
            for r in rects:
                if r.is_empty or r.is_infinite:
                    continue
                image_area += r.width * r.height
        except Exception:
            # Defensive: skip images whose rects cannot be obtained
            pass

    image_coverage = min(image_area / page_area, 1.0) if page_area > 0 else 0.0

    # --- Vector line count ---
    try:
        drawings = page.get_drawings()
        vector_line_count = len(drawings)
    except Exception:
        vector_line_count = 0

    # --- Deferred raster regions ---
    deferred_regions = len(images) if image_coverage >= 0.20 else 0

    return {
        "printable_char_count": printable_count,
        "garbled_char_ratio": round(garbled_ratio, 6),
        "image_coverage_ratio": round(image_coverage, 6),
        "vector_line_count": vector_line_count,
        "deferred_regions_count": deferred_regions,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Page classification
# ═══════════════════════════════════════════════════════════════════════════


def classify_page(
    page_number: int,
    signals: dict[str, Any],
    calibration: Optional[CalibrationConfig] = None,
) -> PageProfile:
    """Classify a page using its extracted signals and configured thresholds.

    Parameters
    ----------
    page_number : int
        1-based page number.
    signals : dict
        Output of :func:`analyze_page_signals`.
    calibration : CalibrationConfig, optional
        Threshold configuration.  Loads defaults when ``None``.

    Returns
    -------
    PageProfile
        Validated domain model with classification and metrics.
    """
    if calibration is None:
        calibration = CalibrationConfig.load_defaults()

    chars = signals["printable_char_count"]
    garbled = signals["garbled_char_ratio"]
    img_cov = signals["image_coverage_ratio"]
    vectors = signals["vector_line_count"]
    deferred = signals["deferred_regions_count"]

    char_min = calibration.min_chars_for_digital
    img_scanned_min = calibration.min_image_coverage_for_scanned
    garbled_max = calibration.max_garbled_char_ratio

    # Decision tree (MASTER_DIRECTIVE.md Section 11)
    if chars == 0 and img_cov < img_scanned_min and vectors == 0:
        # Genuinely empty page
        page_type = PageType.EMPTY_OR_UNREADABLE
        processing_status = PageProcessingStatus.EMPTY_PAGE
        table_presence = TablePresenceStatus.CONFIRMED_ABSENT
    elif chars < char_min and img_cov >= img_scanned_min:
        # Scanned — never mark CONFIRMED_ABSENT
        page_type = PageType.SCANNED
        processing_status = PageProcessingStatus.INCOMPLETE_DEFERRED_TO_OCR
        table_presence = TablePresenceStatus.UNKNOWN_PENDING_OCR
    elif chars >= char_min and img_cov >= 0.20:
        # Hybrid — native text + significant raster regions
        page_type = PageType.HYBRID
        processing_status = PageProcessingStatus.INCOMPLETE_DEFERRED_TO_OCR
        table_presence = TablePresenceStatus.UNKNOWN_PENDING_OCR
    else:
        # Digital — readable native content
        if garbled > garbled_max:
            # Excessive garbled characters — treat as unreadable
            page_type = PageType.EMPTY_OR_UNREADABLE
            processing_status = PageProcessingStatus.FAILED_PAGE
            table_presence = TablePresenceStatus.CONFIRMED_ABSENT
        else:
            page_type = PageType.DIGITAL
            processing_status = PageProcessingStatus.EXTRACTED
            # Initial assumption — updated during extraction
            table_presence = TablePresenceStatus.CONFIRMED_PRESENT

    return PageProfile(
        page_number=page_number,
        page_type=page_type,
        processing_status=processing_status,
        table_presence=table_presence,
        printable_char_count=chars,
        garbled_char_ratio=garbled,
        image_coverage_ratio=img_cov,
        vector_line_count=vectors,
        deferred_regions_count=deferred,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Document-level routing
# ═══════════════════════════════════════════════════════════════════════════


def route_document_pages(
    file_path: Path,
    calibration: Optional[CalibrationConfig] = None,
) -> list[PageProfile]:
    """Classify all pages in a PDF sequentially.

    Opens the document with ``pymupdf.open`` inside a strict
    ``try/finally`` block to guarantee handle closure.

    Parameters
    ----------
    file_path : Path
        Path to a validated PDF file.
    calibration : CalibrationConfig, optional
        Threshold configuration.

    Returns
    -------
    list[PageProfile]
        One profile per page, in page order.
    """
    if calibration is None:
        calibration = CalibrationConfig.load_defaults()

    doc: Optional[pymupdf.Document] = None
    try:
        doc = pymupdf.open(str(Path(file_path).resolve()))
        profiles: list[PageProfile] = []

        for page_idx in range(doc.page_count):
            page = doc.load_page(page_idx)
            signals = analyze_page_signals(page)
            profile = classify_page(
                page_number=page_idx + 1,
                signals=signals,
                calibration=calibration,
            )
            profiles.append(profile)
            # Release page reference
            del page

        return profiles
    finally:
        if doc is not None:
            doc.close()
