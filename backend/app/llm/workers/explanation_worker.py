"""DocuStruct AI — User Explanation Orchestration Worker.

Translates validation issues, arithmetic discrepancies, and status reason codes into
clear, non-technical explanations. Uses deterministic templates when AI models are unavailable.
"""

from __future__ import annotations

import logging
from typing import Optional

from app.llm.enums import TaskType
from app.llm.schemas import UserExplanationPayload
from app.llm.workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)

# ── Deterministic Explanation Templates ──────────────────────────────────────
DETERMINISTIC_EXPLANATIONS: dict[str, tuple[str, str]] = {
    "MATH_SUM_MISMATCH": (
        "Column or row values do not sum to the extracted total.",
        "Inspect the component values and total cell in the original document to verify the numbers.",
    ),
    "MATH_CROSSFOOT_MISMATCH": (
        "Horizontal row sum and vertical column sum do not match at the corner total.",
        "Check whether row totals or column totals contain omitted deductions or adjustments.",
    ),
    "DECIMAL_SHIFT": (
        "Extracted number appears shifted by one or more decimal places.",
        "Verify decimal point placement in the original document typography.",
    ),
    "OCR_CHARACTER_CONFUSION": (
        "Similar-looking characters (such as '0' vs 'O' or '1' vs 'l') may have been confused.",
        "Inspect high-resolution image of the cell to confirm exact text characters.",
    ),
    "HEADER_MISALIGNMENT": (
        "Extracted column headers do not match the data types in the corresponding columns.",
        "Ensure column boundaries align correctly with the table headers.",
    ),
    "FORMULA_INJECTION_RISK": (
        "Cell starts with a formula trigger character ('=', '+', '-', '@') that could execute code in Excel.",
        "Review cell content before export; values are neutralized for downstream spreadsheet safety.",
    ),
    "ILLEGIBLE_OR_MISSING": (
        "Cell content could not be read with high confidence from the digital document stream.",
        "Manual inspection or higher-resolution scan of this page is recommended.",
    ),
    "UNRESOLVED_DISCREPANCY": (
        "Conflicting extraction results were detected and could not be resolved automatically.",
        "Review cell values against the original PDF and make manual adjustments if necessary.",
    ),
}


class ExplanationWorker(BaseWorker):
    """Worker generating user-facing plain-English issue explanations."""

    async def explain_issue(
        self,
        issue_id: str,
        issue_code: str,
        description: str,
        expected_value: Optional[str] = None,
        actual_value: Optional[str] = None,
        context: Optional[str] = None,
    ) -> UserExplanationPayload:
        """Translate a validation issue into a clear, user-facing explanation.

        Tries AI explanation first via TaskRouter (preference: GPT-OSS 20B).
        If AI is unavailable, unconfigured, or fails, falls back immediately
        to deterministic explanation templates without crashing.
        """
        system_prompt = (
            "You are a helpful document assistant. Translate technical table validation "
            "errors into clear, plain-English summaries and actionable recommendations "
            "for business users. Avoid raw regexes or internal code names."
        )
        prompt = (
            f"Issue ID: {issue_id}\n"
            f"Issue Code: {issue_code}\n"
            f"Internal Description: {description}\n"
            f"Expected Value: {expected_value or 'N/A'}\n"
            f"Actual Value: {actual_value or 'N/A'}\n"
            f"Context: {context or 'N/A'}\n\n"
            "Produce a structured UserExplanationPayload JSON."
        )

        res = await self.execute_task(
            task=TaskType.USER_EXPLANATION,
            prompt=prompt,
            response_model=UserExplanationPayload,
            system_prompt=system_prompt,
        )

        if res.success and isinstance(res.result, UserExplanationPayload):
            return res.result

        # Deterministic template fallback
        logger.debug(
            "Using deterministic explanation template for issue %s (code=%s)",
            issue_id,
            issue_code,
        )
        summary, recommendation = DETERMINISTIC_EXPLANATIONS.get(
            issue_code,
            (
                f"Validation issue detected: {description}",
                "Review the original document page to verify tabular data.",
            ),
        )

        return UserExplanationPayload(
            issue_id=issue_id,
            summary=summary,
            recommendation=recommendation,
            technical_context=f"Issue code: {issue_code}. Expected: {expected_value}, Actual: {actual_value}",
        )
