"""DocuStruct AI — Cell Correction Orchestration Worker.

Enforces strict evidence gating (DECISION-011, MASTER_DIRECTIVE Section 15):
    - Original cell.raw_value is strictly immutable.
    - Totals are NEVER auto-balanced (e.g. 100 + 200 = 350 preserves 350).
    - Only evidence from PERMITTED_EVIDENCE_SOURCES can modify cell.accepted_value.
    - Ungrounded or heuristic model proposals are restricted to inferred_candidate_value
      with CellQualityStatus.ILLEGIBLE_OR_MISSING and flagged for human review.
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from app.extraction.normalizer import normalize_cell
from app.extraction.table_reconstructor import PERMITTED_EVIDENCE_SOURCES
from app.llm.enums import TaskType
from app.llm.fallback import FallbackResult
from app.llm.schemas import CorrectionProposal
from app.llm.workers.base_worker import BaseWorker
from app.models.domain import CellRecord, CorrectionRecord
from app.models.state import CellQualityStatus

logger = logging.getLogger(__name__)


class CorrectionWorker(BaseWorker):
    """Worker requesting and safely applying evidence-gated cell corrections."""

    async def propose_correction(
        self,
        cell: CellRecord,
        table_context: Optional[str] = None,
        suspected_issue: Optional[str] = None,
    ) -> FallbackResult:
        """Query candidate models for a structured CorrectionProposal.

        If models are unconfigured or unavailable, returns a FallbackResult with
        fallback_to_deterministic=True.
        """
        system_prompt = (
            "You are a precision table audit assistant. When analyzing suspicious "
            "or corrupt table cells, provide structured correction proposals strictly backed "
            "by verifiable physical evidence from the PDF stream or coordinates. "
            "Never invent values or auto-balance totals."
        )
        prompt = (
            f"Table ID: {cell.table_id}\n"
            f"Target Cell: Row {cell.row_idx}, Column {cell.col_idx}\n"
            f"Raw Value: {cell.raw_value!r}\n"
            f"Accepted Value: {cell.accepted_value!r}\n"
            f"Suspected Issue: {suspected_issue or 'Unverified cell discrepancy'}\n"
            f"Context: {table_context or 'No additional context provided'}\n\n"
            "Produce a structured CorrectionProposal JSON."
        )

        return await self.execute_task(
            task=TaskType.CORRECTION_PROPOSAL,
            prompt=prompt,
            response_model=CorrectionProposal,
            system_prompt=system_prompt,
        )

    def apply_proposal(
        self,
        cell: CellRecord,
        proposal: CorrectionProposal,
        is_total_or_sum_cell: bool = False,
    ) -> tuple[CellRecord, CorrectionRecord]:
        """Apply a CorrectionProposal to a CellRecord adhering to Section 15 invariants.

        Invariants:
            1. cell.raw_value is NEVER overwritten.
            2. If target cell is a total or sum, auto-balancing is strictly forbidden:
               the proposal cannot modify accepted_value; it is recorded as an
               inferred candidate only.
            3. If proposal.evidence_source is not in PERMITTED_EVIDENCE_SOURCES:
               proposal cannot modify accepted_value; it is recorded in
               inferred_candidate_value with CellQualityStatus.ILLEGIBLE_OR_MISSING.
            4. If evidence is valid from PERMITTED_EVIDENCE_SOURCES and not auto-balancing:
               accepted_value is updated and marked CellQualityStatus.CORRECTED_WITH_EVIDENCE.
        """
        audit_id = f"corr_llm_{uuid.uuid4().hex[:8]}"

        # Invariant 2: Auto-balancing totals prohibition
        if is_total_or_sum_cell:
            logger.info(
                "Proposal targets a total or sum cell (row=%d, col=%d). "
                "Auto-balancing is prohibited by DECISION-007 and DECISION-011. "
                "Recording as inferred candidate only.",
                cell.row_idx,
                cell.col_idx,
            )
            updated_cell = cell.model_copy(
                update={
                    "inferred_candidate_value": proposal.proposed_value,
                    "quality_status": CellQualityStatus.ILLEGIBLE_OR_MISSING,
                    "notes": cell.notes + ["LLM proposed total correction rejected: auto-balancing prohibited"],
                }
            )
            record = CorrectionRecord(
                audit_id=audit_id,
                table_id=cell.table_id,
                source_page=cell.source_page,
                row_idx=cell.row_idx,
                col_idx=cell.col_idx,
                original_raw_value=cell.raw_value,
                proposed_value=proposal.proposed_value,
                accepted_value=cell.accepted_value,
                inferred_candidate_only=True,
                evidence_source=proposal.evidence_source,
                evidence_summary=f"REJECTED_AUTO_BALANCE: {proposal.evidence_summary}",
                deterministic_check_passed=False,
                decision="REJECTED_AUTO_BALANCE_PRESERVED_RAW",
                resulting_cell_status=CellQualityStatus.ILLEGIBLE_OR_MISSING,
            )
            return updated_cell, record

        # Invariant 3: Permitted evidence source check
        if proposal.evidence_source not in PERMITTED_EVIDENCE_SOURCES:
            logger.info(
                "Proposal evidence source '%s' is not in PERMITTED_EVIDENCE_SOURCES. "
                "Recording as inferred candidate only.",
                proposal.evidence_source,
            )
            updated_cell = cell.model_copy(
                update={
                    "inferred_candidate_value": proposal.proposed_value,
                    "quality_status": CellQualityStatus.ILLEGIBLE_OR_MISSING,
                    "notes": cell.notes + [f"Unverified LLM candidate ({proposal.evidence_source}): requires review"],
                }
            )
            record = CorrectionRecord(
                audit_id=audit_id,
                table_id=cell.table_id,
                source_page=cell.source_page,
                row_idx=cell.row_idx,
                col_idx=cell.col_idx,
                original_raw_value=cell.raw_value,
                proposed_value=proposal.proposed_value,
                accepted_value=cell.accepted_value,
                inferred_candidate_only=True,
                evidence_source=proposal.evidence_source,
                evidence_summary=proposal.evidence_summary,
                deterministic_check_passed=False,
                decision="INFERRED_CANDIDATE_RECORDED",
                resulting_cell_status=CellQualityStatus.ILLEGIBLE_OR_MISSING,
            )
            return updated_cell, record

        # Invariant 4: Valid deterministic evidence accepted
        norm = normalize_cell(proposal.proposed_value)
        updated_cell = cell.model_copy(
            update={
                "accepted_value": norm["accepted_value"],
                "numeric_decimal": norm["numeric_decimal"],
                "data_type": norm["data_type"],
                "quality_status": CellQualityStatus.CORRECTED_WITH_EVIDENCE,
                "notes": cell.notes + [f"Corrected with evidence from {proposal.evidence_source}"],
            }
        )
        record = CorrectionRecord(
            audit_id=audit_id,
            table_id=cell.table_id,
            source_page=cell.source_page,
            row_idx=cell.row_idx,
            col_idx=cell.col_idx,
            original_raw_value=cell.raw_value,
            proposed_value=proposal.proposed_value,
            accepted_value=norm["accepted_value"],
            inferred_candidate_only=False,
            evidence_source=proposal.evidence_source,
            evidence_summary=proposal.evidence_summary,
            deterministic_check_passed=True,
            decision="CORRECTION_ACCEPTED",
            resulting_cell_status=CellQualityStatus.CORRECTED_WITH_EVIDENCE,
        )
        return updated_cell, record
