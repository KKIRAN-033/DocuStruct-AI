"""DocuStruct AI — Discrepancy Adjudication Orchestration Worker.

Adjudicates conflicting extraction hypotheses and structural discrepancies without
mutating table cells. Unresolved disagreements are routed for human review.
"""

from __future__ import annotations

import logging
from typing import Optional

from app.llm.enums import TaskType
from app.llm.schemas import DiscrepancyHypothesis
from app.llm.workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class DiscrepancyWorker(BaseWorker):
    """Worker analyzing extraction conflicts and generating structured DiscrepancyHypotheses."""

    async def adjudicate_discrepancy(
        self,
        table_id: str,
        row_idx: int,
        col_idx: int,
        extracted_value: str,
        conflicting_hypotheses: list[str],
        context: Optional[str] = None,
    ) -> DiscrepancyHypothesis:
        """Adjudicate conflicting extraction candidates across models or extraction passes.

        Cell values are never modified by this worker. If models are unavailable
        or unconfigured, triggers deterministic fallback returning a safe
        HUMAN_REVIEW recommendation.
        """
        system_prompt = (
            "You are an expert table extraction conflict adjudicator. "
            "Analyze the extracted value and conflicting hypotheses. "
            "Explain the technical root cause (e.g. DECIMAL_SHIFT, OCR_CHARACTER_CONFUSION, "
            "HEADER_MISALIGNMENT) and recommend an action. If uncertain, recommend HUMAN_REVIEW."
        )
        prompt = (
            f"Table ID: {table_id}\n"
            f"Coordinates: Row {row_idx}, Column {col_idx}\n"
            f"Primary Extracted Value: {extracted_value!r}\n"
            f"Conflicting Candidates: {conflicting_hypotheses}\n"
            f"Context: {context or 'None'}\n\n"
            "Return a structured DiscrepancyHypothesis JSON."
        )

        res = await self.execute_task(
            task=TaskType.CONFLICTING_HYPOTHESES,
            prompt=prompt,
            response_model=DiscrepancyHypothesis,
            system_prompt=system_prompt,
        )

        if res.success and isinstance(res.result, DiscrepancyHypothesis):
            return res.result

        # Deterministic fallback when AI is unavailable or failed
        logger.info(
            "AI adjudication unavailable for table %s cell (%d, %d). "
            "Returning deterministic fallback hypothesis.",
            table_id,
            row_idx,
            col_idx,
        )
        return DiscrepancyHypothesis(
            table_id=table_id,
            row_idx=row_idx,
            col_idx=col_idx,
            hypothesis_type="UNRESOLVED_EXTRACTION_CONFLICT",
            explanation=(
                f"Automated extraction produced {len(conflicting_hypotheses)} conflicting hypotheses "
                f"against primary value {extracted_value!r}. AI models unavailable or failed. "
                "Deterministic safety preserved raw cell value."
            ),
            recommended_action="HUMAN_REVIEW",
        )
