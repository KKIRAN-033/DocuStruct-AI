"""
DocuStruct AI — Models Package

Re-exports all state enumerations and domain models for convenient access.
"""

from app.models.state import (
    CellQualityStatus,
    DataType,
    JobExecutionState,
    PageProcessingStatus,
    PageType,
    StitchDecision,
    TablePresenceStatus,
    ValidationOutcome,
    VerificationStatus,
)
from app.models.domain import (
    BoundingBox,
    CanonicalTable,
    CellRecord,
    CorrectionRecord,
    DocumentEvaluationReport,
    PageExtractionResult,
    PageProfile,
    StitchAuditEvent,
    ValidationIssue,
)

__all__ = [
    # State enumerations
    "CellQualityStatus",
    "DataType",
    "JobExecutionState",
    "PageProcessingStatus",
    "PageType",
    "StitchDecision",
    "TablePresenceStatus",
    "ValidationOutcome",
    "VerificationStatus",
    # Domain models
    "BoundingBox",
    "CanonicalTable",
    "CellRecord",
    "CorrectionRecord",
    "DocumentEvaluationReport",
    "PageExtractionResult",
    "PageProfile",
    "StitchAuditEvent",
    "ValidationIssue",
]
