"""DocuStruct AI — Task-Based Multi-Model Capability Router.

Directs extraction and verification workloads to the optimal model based on
declarative task affinities, modality requirements, verified operational status,
and strict pre-flight eligibility checks.
"""

from __future__ import annotations

import logging
from typing import Optional

from app.llm.config import MultiLLMSettings
from app.llm.enums import (
    ConfigurationCredentialStatus,
    IntegrationTestStatus,
    Modality,
    ModelExistenceStatus,
    ProviderAvailabilityStatus,
    TaskType,
)
from app.llm.models import CandidateModel
from app.llm.registry import ModelRegistry

logger = logging.getLogger(__name__)

# ── Initial Candidate Preferences per Task Type ──────────────────────────────
# Registered candidate names strictly match the 7 declarative candidate models.
TASK_CANDIDATE_PREFERENCES: dict[TaskType, list[str]] = {
    TaskType.ROUTINE_CLASSIFICATION: [
        "GPT-OSS 20B",
        "DeepSeek V4.1 Flash",
        "Llama 4 Scout",
    ],
    TaskType.COMPLEX_TABLE_INTERPRETATION: [
        "DeepSeek V4.1 Flash",
        "GPT-OSS 120B",
        "GLM-5.3-Flash through Z.ai",
    ],
    TaskType.CONFLICTING_HYPOTHESES: [
        "GPT-OSS 120B",
        "GLM-5.3-Flash through Z.ai",
    ],
    TaskType.CORRECTION_PROPOSAL: [
        "GPT-OSS 20B",
        "DeepSeek V4.1 Flash",
    ],
    TaskType.MULTILINGUAL_INTERPRETATION: [
        "Qwen3.8-27B",
    ],
    TaskType.VISUAL_TABLE_REVIEW: [
        "Qwen3.8-27B",
        "Llama 4 Scout",
        "Gemma 4",
    ],
    TaskType.USER_EXPLANATION: [
        "GPT-OSS 20B",
    ],
}


def evaluate_candidate_eligibility(
    candidate: CandidateModel,
    task: TaskType,
    requires_vision: bool = False,
) -> tuple[bool, str]:
    """Perform pre-flight verification of a candidate model for a given task.

    Evaluates the complete operational readiness contract:
        1. Enabled state: candidate must be enabled.
        2. Exact model ID: must not be 'UNVERIFIED' or empty.
        3. Credentials: active credentials must be configured.
        4. Model existence: provider model ID confirmed physically present.
        5. Provider availability: provider endpoint confirmed reachable.
        6. Integration test: automated probe must have passed.
        7. Task affinity: candidate must explicitly support the task type.
        8. Modality support: vision-required tasks strictly require confirmed Modality.VISION.

    Returns
    -------
    tuple[bool, str]
        (True, "Eligible") or (False, "<Specific reason for ineligibility>").
    """
    # 1. Enabled state
    if not candidate.enabled_state:
        return False, "Candidate model is disabled (enabled_state=False)"

    # 2. Exact model ID presence
    if not candidate.exact_model_id or candidate.exact_model_id.strip() == "UNVERIFIED":
        return False, "Exact model ID is UNVERIFIED or unconfigured"

    # 3. Provider credentials
    if candidate.verification_status.credentials != ConfigurationCredentialStatus.CONFIGURED:
        return False, "Missing required provider credentials"

    # 4. Model physical existence
    if candidate.verification_status.existence != ModelExistenceStatus.CONFIRMED:
        return False, f"Model existence is {candidate.verification_status.existence.value}"

    # 5. Provider reachability / availability
    if candidate.verification_status.provider_availability != ProviderAvailabilityStatus.AVAILABLE:
        return False, f"Provider availability is {candidate.verification_status.provider_availability.value}"

    # 6. Integration test probe status
    if candidate.verification_status.test_result != IntegrationTestStatus.PASSED:
        return False, f"Integration test status is {candidate.verification_status.test_result.value}"

    # 7. Task compatibility
    if task not in candidate.supported_tasks:
        return False, f"Task {task.value} is not supported by candidate"

    # 8. Modality guard (vision tasks strictly require verified vision)
    needs_vision = requires_vision or (task == TaskType.VISUAL_TABLE_REVIEW)
    if needs_vision and Modality.VISION not in candidate.supported_modalities:
        return False, "Candidate lacks verified VISION modality support"

    return True, "Eligible"


class TaskRouter:
    """Task-based multi-model capability router with dynamic fallback resolution."""

    def __init__(
        self,
        registry: Optional[ModelRegistry] = None,
        settings: Optional[MultiLLMSettings] = None,
    ) -> None:
        self._settings = settings or MultiLLMSettings()
        self._registry = registry or ModelRegistry(settings=self._settings)

    @property
    def registry(self) -> ModelRegistry:
        """Return the underlying ModelRegistry."""
        return self._registry

    def get_preferences_for_task(self, task: TaskType) -> list[str]:
        """Return the ordered candidate name preferences for a task type."""
        return list(TASK_CANDIDATE_PREFERENCES.get(task, []))

    def evaluate_candidate(
        self,
        candidate_name: str,
        task: TaskType,
        requires_vision: bool = False,
    ) -> tuple[bool, str]:
        """Evaluate a named candidate against eligibility rules."""
        candidate = self._registry.get_candidate(candidate_name)
        if candidate is None:
            return False, f"Candidate '{candidate_name}' not found in registry"
        return evaluate_candidate_eligibility(
            candidate=candidate,
            task=task,
            requires_vision=requires_vision,
        )

    def resolve_execution_chain(
        self,
        task: TaskType,
        requires_vision: bool = False,
    ) -> list[CandidateModel]:
        """Resolve an ordered list of eligible candidate models for a task.

        Evaluation order:
            1. Preferred candidates for the task type, in preference order.
            2. Any remaining eligible registered models with fallback_eligibility=True,
               ordered by routing_priority.

        If no candidates satisfy the pre-flight eligibility checks, returns an
        empty list indicating that deterministic continuation must be triggered.
        """
        needs_vision = requires_vision or (task == TaskType.VISUAL_TABLE_REVIEW)
        preferred_names = self.get_preferences_for_task(task)
        chain: list[CandidateModel] = []
        seen_names: set[str] = set()

        # Phase 1: Evaluate preferred candidates
        for name in preferred_names:
            candidate = self._registry.get_candidate(name)
            if candidate is None or name in seen_names:
                continue

            eligible, reason = evaluate_candidate_eligibility(
                candidate=candidate,
                task=task,
                requires_vision=needs_vision,
            )
            if eligible:
                chain.append(candidate)
                seen_names.add(name)
            else:
                logger.debug(
                    "Candidate '%s' ineligible for task %s: %s",
                    name,
                    task.value,
                    reason,
                )

        # Phase 2: Evaluate alternative eligible fallback candidates
        all_candidates = self._registry.get_candidates_for_task(
            task=task,
            requires_vision=needs_vision,
        )
        for candidate in all_candidates:
            if candidate.candidate_name in seen_names:
                continue
            if not candidate.fallback_eligibility:
                continue

            eligible, reason = evaluate_candidate_eligibility(
                candidate=candidate,
                task=task,
                requires_vision=needs_vision,
            )
            if eligible:
                chain.append(candidate)
                seen_names.add(candidate.candidate_name)
            else:
                logger.debug(
                    "Fallback candidate '%s' ineligible for task %s: %s",
                    candidate.candidate_name,
                    task.value,
                    reason,
                )

        if not chain:
            logger.info(
                "No eligible candidate models available for task %s (requires_vision=%s). "
                "Triggering deterministic continuation.",
                task.value,
                needs_vision,
            )

        return chain
