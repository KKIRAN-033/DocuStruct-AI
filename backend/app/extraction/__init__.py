"""
DocuStruct AI — Extraction Package

Provides cell normalisation, formula-risk detection, and digital
table extraction.
"""

from app.extraction.digital_extractor import (
    extract_borderless_tables,
    extract_document_tables,
    extract_ruled_tables,
    extract_tables_from_page,
)
from app.extraction.normalizer import (
    detect_formula_risk,
    normalize_cell,
    normalize_whitespace,
    parse_numeric_value,
)
from app.extraction.table_reconstructor import (
    PERMITTED_EVIDENCE_SOURCES,
    apply_evidence_gated_correction,
    compute_column_overlap_ratio,
    compute_relative_column_intervals,
    compute_type_compatibility,
    evaluate_header_similarity,
    evaluate_stitch_pair,
    reconstruct_multipage_tables,
    stitch_canonical_tables,
    strip_repeated_headers,
)

__all__ = [
    "PERMITTED_EVIDENCE_SOURCES",
    "apply_evidence_gated_correction",
    "compute_column_overlap_ratio",
    "compute_relative_column_intervals",
    "compute_type_compatibility",
    "detect_formula_risk",
    "evaluate_header_similarity",
    "evaluate_stitch_pair",
    "extract_borderless_tables",
    "extract_document_tables",
    "extract_ruled_tables",
    "extract_tables_from_page",
    "normalize_cell",
    "normalize_whitespace",
    "parse_numeric_value",
    "reconstruct_multipage_tables",
    "stitch_canonical_tables",
    "strip_repeated_headers",
]
