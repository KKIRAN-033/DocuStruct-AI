"""DocuStruct AI — Verification and Quality Gate Package."""

from app.verification.quality_gate import (
    MANDATORY_VERBATIM_DISCLAIMER,
    REASON_ARITHMETIC_SCOPE_AMBIGUOUS,
    REASON_DEFERRED_REGIONS_REMAIN,
    REASON_EXECUTION_FAILED,
    REASON_NO_TABLES_FOUND,
    REASON_OCR_REQUIRED_FOR_SCANNED,
    REASON_SOURCE_ARITHMETIC_DISCREPANCY,
    REASON_STITCH_REVIEW_REQUIRED,
    REASON_STRUCTURAL_CHECKS_FAILED,
    SUMMARY_LABELS,
    evaluate_document_quality,
    evaluate_document_verification_status,
    evaluate_table_arithmetic_consistency,
    identify_numeric_columns,
    identify_summary_rows,
)

__all__ = [
    "MANDATORY_VERBATIM_DISCLAIMER",
    "REASON_ARITHMETIC_SCOPE_AMBIGUOUS",
    "REASON_DEFERRED_REGIONS_REMAIN",
    "REASON_EXECUTION_FAILED",
    "REASON_NO_TABLES_FOUND",
    "REASON_OCR_REQUIRED_FOR_SCANNED",
    "REASON_SOURCE_ARITHMETIC_DISCREPANCY",
    "REASON_STITCH_REVIEW_REQUIRED",
    "REASON_STRUCTURAL_CHECKS_FAILED",
    "SUMMARY_LABELS",
    "evaluate_document_quality",
    "evaluate_document_verification_status",
    "evaluate_table_arithmetic_consistency",
    "identify_numeric_columns",
    "identify_summary_rows",
]
