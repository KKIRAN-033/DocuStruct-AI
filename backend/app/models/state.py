"""
DocuStruct AI — State Enumerations

String-backed enumerations for all lifecycle, verification,
classification, and data-type states used throughout DocuStruct AI.

Design rules (from MASTER_DIRECTIVE.md Section 8):
    - Execution state is strictly distinct from verification status.
    - A completed execution can still require review.
    - Terminal states must not be silently exited.
"""

from __future__ import annotations

from enum import Enum


class JobExecutionState(str, Enum):
    """Document processing lifecycle states.

    Tracks the *execution* progress of a single document through
    the pipeline.  Verification outcome is tracked separately by
    :class:`VerificationStatus`.
    """

    QUEUED = "QUEUED"
    UNDERSTANDING = "UNDERSTANDING"
    EXTRACTING = "EXTRACTING"
    RECONSTRUCTING = "RECONSTRUCTING"
    VERIFYING = "VERIFYING"
    DIAGNOSING = "DIAGNOSING"
    CORRECTING = "CORRECTING"
    REVALIDATING = "REVALIDATING"
    DELIVERING = "DELIVERING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class VerificationStatus(str, Enum):
    """Document-level verification outcome.

    Assigned by the quality gate after all extraction, stitching,
    and arithmetic consistency checks are complete.
    """

    VERIFIED = "VERIFIED"
    VERIFIED_WITH_WARNINGS = "VERIFIED_WITH_WARNINGS"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    FAILED = "FAILED"


class PageType(str, Enum):
    """Page content classification.

    Determined by the page router based on character counts,
    garbled ratios, image coverage, and vector line presence.
    """

    DIGITAL = "DIGITAL"
    SCANNED = "SCANNED"
    HYBRID = "HYBRID"
    EMPTY_OR_UNREADABLE = "EMPTY_OR_UNREADABLE"


class PageProcessingStatus(str, Enum):
    """Outcome of processing an individual page.

    ``INCOMPLETE_DEFERRED_TO_OCR`` is the Phase 1 response to
    scanned content — it is acknowledged but not extracted.
    """

    EXTRACTED = "EXTRACTED"
    INCOMPLETE_DEFERRED_TO_OCR = "INCOMPLETE_DEFERRED_TO_OCR"
    EMPTY_PAGE = "EMPTY_PAGE"
    FAILED_PAGE = "FAILED_PAGE"


class TablePresenceStatus(str, Enum):
    """Whether a page contains recognisable table structures."""

    CONFIRMED_PRESENT = "CONFIRMED_PRESENT"
    CONFIRMED_ABSENT = "CONFIRMED_ABSENT"
    UNKNOWN_PENDING_OCR = "UNKNOWN_PENDING_OCR"


class ValidationOutcome(str, Enum):
    """Result of a table-level arithmetic consistency check."""

    PASSED = "PASSED"
    PASSED_WITH_WARNINGS = "PASSED_WITH_WARNINGS"
    FAILED_VALIDATION = "FAILED_VALIDATION"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class StitchDecision(str, Enum):
    """Decision from the multipage table reconstructor."""

    STITCH_CONFIRMED = "STITCH_CONFIRMED"
    STITCH_REJECTED = "STITCH_REJECTED"
    STITCH_REVIEW_REQUIRED = "STITCH_REVIEW_REQUIRED"


class CellQualityStatus(str, Enum):
    """Quality classification for an individual cell value."""

    EXTRACTED_AS_IS = "EXTRACTED_AS_IS"
    CORROBORATED = "CORROBORATED"
    CORRECTED_WITH_EVIDENCE = "CORRECTED_WITH_EVIDENCE"
    LOW_CONFIDENCE_WARNING = "LOW_CONFIDENCE_WARNING"
    ANOMALY_FLAGGED = "ANOMALY_FLAGGED"
    ILLEGIBLE_OR_MISSING = "ILLEGIBLE_OR_MISSING"


class DataType(str, Enum):
    """Inferred semantic type for a cell value.

    ``HIGH_PRECISION_DECIMAL`` is distinct from ``DECIMAL`` for
    values requiring more than typical accounting precision.
    ``IDENTIFIER`` preserves leading zeros that would be lost
    in numeric conversion.
    """

    STRING = "STRING"
    IDENTIFIER = "IDENTIFIER"
    INTEGER = "INTEGER"
    DECIMAL = "DECIMAL"
    HIGH_PRECISION_DECIMAL = "HIGH_PRECISION_DECIMAL"
    DATE = "DATE"
    EMPTY = "EMPTY"
