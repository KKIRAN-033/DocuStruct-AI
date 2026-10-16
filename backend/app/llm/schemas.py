"""DocuStruct AI — Multi-LLM Structured Output Contracts.

Typed, validated Pydantic v2 schemas for all multi-model outputs, ensuring
complete rejection of malformed, ungrounded, or unsupported model predictions.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.llm.models import CandidateModel, ProviderHealth


class PageClassificationEnrichment(BaseModel):
    """Structured page-level layout, script, and borderless table analysis."""

    model_config = ConfigDict(extra="forbid")

    layout_analysis: str = Field(description="Structural analysis of page layout and text blocks.")
    has_borderless_tables: bool = Field(description="Whether borderless or whitespace-separated tables exist.")
    script_detection: list[str] = Field(
        default_factory=list,
        description="Detected written language scripts (e.g., 'Latin', 'CJK', 'Arabic').",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score in the classification assessment [0.0, 1.0].",
    )


class TableInterpretationResult(BaseModel):
    """Structured table interpretation, column identification, and ragged row rationale."""

    model_config = ConfigDict(extra="forbid")

    detected_columns: list[str] = Field(description="List of detected logical table column headers.")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score in the structural interpretation [0.0, 1.0].",
    )
    ragged_row_rationale: Optional[str] = Field(
        default=None,
        description="Physical explanation for ragged or jagged rows if present.",
    )


class DiscrepancyHypothesis(BaseModel):
    """Hypothesis explaining an extraction conflict or arithmetic inconsistency."""

    model_config = ConfigDict(extra="forbid")

    table_id: str = Field(description="Identifier of the target table.")
    row_idx: int = Field(ge=0, description="0-based row index.")
    col_idx: int = Field(ge=0, description="0-based column index.")
    hypothesis_type: str = Field(
        description="Type of discrepancy (e.g. 'DECIMAL_SHIFT', 'OCR_CHARACTER_CONFUSION', 'HEADER_MISALIGNMENT').",
    )
    explanation: str = Field(description="Technical rationale for the discrepancy.")
    recommended_action: str = Field(
        default="HUMAN_REVIEW",
        description="Action recommendation (e.g. 'HUMAN_REVIEW', 'REJECT').",
    )


class CorrectionProposal(BaseModel):
    """Proposed correction for a table cell, strictly requiring traceable evidence."""

    model_config = ConfigDict(extra="forbid")

    table_id: str = Field(description="Identifier of the target table.")
    row_idx: int = Field(ge=0, description="0-based row index.")
    col_idx: int = Field(ge=0, description="0-based column index.")
    original_value: str = Field(description="The exact uncorrected cell value from extraction.")
    proposed_value: str = Field(description="The suggested corrected value.")
    evidence_source: str = Field(description="Source of physical evidence backing this proposal.")
    evidence_summary: str = Field(description="Summary of the corroborating character/coordinate evidence.")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score for the proposed correction [0.0, 1.0].",
    )


class UserExplanationPayload(BaseModel):
    """User-facing, plain-English explanation of validation issues and quality flags."""

    model_config = ConfigDict(extra="forbid")

    issue_id: str = Field(description="Identifier of the referenced validation issue.")
    summary: str = Field(description="Clear, non-technical explanation of the issue.")
    recommendation: str = Field(description="Actionable suggestion for document correction.")
    technical_context: Optional[str] = Field(
        default=None,
        description="Underlying rule code or arithmetic formula context.",
    )


class ModelsStatusResponse(BaseModel):
    """Status envelope returned by GET /api/v1/models/status."""

    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    models: list[CandidateModel] = Field(description="Current registry states of all 7 candidate models.")
    providers: dict[str, ProviderHealth] = Field(description="Health and configuration status of all 5 providers.")
    timestamp: str = Field(description="ISO 8601 UTC timestamp of status generation.")
