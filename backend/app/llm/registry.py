"""DocuStruct AI — Model Registry.

Declarative registry registering all seven named candidate models with
explicit verification status, task affinities, and priority rankings.
Strictly isolates unverified model identifiers and missing credentials.
"""

from __future__ import annotations

from typing import Optional

from app.llm.config import MultiLLMSettings
from app.llm.enums import (
    ConfigurationCredentialStatus,
    IntegrationTestStatus,
    Modality,
    ModelExistenceStatus,
    ProviderAvailabilityStatus,
    ProviderType,
    TaskType,
)
from app.llm.models import (
    CandidateModel,
    ModelVerificationStatus,
    TimeoutRetryPolicy,
)


class ModelRegistry:
    """Registry maintaining declarative state for all seven candidate models."""

    def __init__(self, settings: Optional[MultiLLMSettings] = None) -> None:
        self._settings = settings or MultiLLMSettings()
        self._candidates: dict[str, CandidateModel] = {}
        self._initialize_candidates()
        if settings is not None:
            self.sync_with_settings(self._settings)

    def _initialize_candidates(self) -> None:
        """Register all seven named candidates preserving exact names.

        Invariants:
            - Exact model IDs default to 'UNVERIFIED' until verified.
            - Provider availability and model existence default to UNVERIFIED.
            - Credentials default to MISSING_CREDENTIALS until configured.
            - Enabled state defaults to False.
            - Unverified vision modalities are NOT enabled.
        """
        candidates = [
            # 1. GPT-OSS 20B
            CandidateModel(
                candidate_name="GPT-OSS 20B",
                exact_model_id="UNVERIFIED",
                provider=ProviderType.GROQ,
                supported_modalities=[Modality.TEXT],
                supported_tasks=[
                    TaskType.ROUTINE_CLASSIFICATION,
                    TaskType.CORRECTION_PROPOSAL,
                    TaskType.USER_EXPLANATION,
                ],
                configuration_key="DOCUSTRUCT_MODEL_GPT_OSS_20B_ID",
                enabled_state=False,
                verification_status=ModelVerificationStatus(
                    existence=ModelExistenceStatus.UNVERIFIED,
                    provider_availability=ProviderAvailabilityStatus.UNVERIFIED,
                    credentials=ConfigurationCredentialStatus.MISSING_CREDENTIALS,
                    test_result=IntegrationTestStatus.UNTESTED,
                ),
                routing_priority=1,
                timeout_retry_policy=TimeoutRetryPolicy(
                    timeout_seconds=15.0,
                    max_retries=2,
                    backoff_base_seconds=1.5,
                ),
                fallback_eligibility=True,
            ),
            # 2. GPT-OSS 120B
            CandidateModel(
                candidate_name="GPT-OSS 120B",
                exact_model_id="UNVERIFIED",
                provider=ProviderType.TOGETHER,
                supported_modalities=[Modality.TEXT],
                supported_tasks=[
                    TaskType.COMPLEX_TABLE_INTERPRETATION,
                    TaskType.CONFLICTING_HYPOTHESES,
                ],
                configuration_key="DOCUSTRUCT_MODEL_GPT_OSS_120B_ID",
                enabled_state=False,
                verification_status=ModelVerificationStatus(
                    existence=ModelExistenceStatus.UNVERIFIED,
                    provider_availability=ProviderAvailabilityStatus.UNVERIFIED,
                    credentials=ConfigurationCredentialStatus.MISSING_CREDENTIALS,
                    test_result=IntegrationTestStatus.UNTESTED,
                ),
                routing_priority=1,
                timeout_retry_policy=TimeoutRetryPolicy(
                    timeout_seconds=45.0,
                    max_retries=2,
                    backoff_base_seconds=2.0,
                ),
                fallback_eligibility=True,
            ),
            # 3. DeepSeek V4.1 Flash
            CandidateModel(
                candidate_name="DeepSeek V4.1 Flash",
                exact_model_id="UNVERIFIED",
                provider=ProviderType.DEEPSEEK,
                supported_modalities=[Modality.TEXT],
                supported_tasks=[
                    TaskType.COMPLEX_TABLE_INTERPRETATION,
                    TaskType.CORRECTION_PROPOSAL,
                    TaskType.ROUTINE_CLASSIFICATION,
                ],
                configuration_key="DOCUSTRUCT_MODEL_DEEPSEEK_V4_1_FLASH_ID",
                enabled_state=False,
                verification_status=ModelVerificationStatus(
                    existence=ModelExistenceStatus.UNVERIFIED,
                    provider_availability=ProviderAvailabilityStatus.UNVERIFIED,
                    credentials=ConfigurationCredentialStatus.MISSING_CREDENTIALS,
                    test_result=IntegrationTestStatus.UNTESTED,
                ),
                routing_priority=1,
                timeout_retry_policy=TimeoutRetryPolicy(
                    timeout_seconds=20.0,
                    max_retries=2,
                    backoff_base_seconds=1.5,
                ),
                fallback_eligibility=True,
            ),
            # 4. GLM-5.3-Flash through Z.ai
            CandidateModel(
                candidate_name="GLM-5.3-Flash through Z.ai",
                exact_model_id="UNVERIFIED",
                provider=ProviderType.ZAI,
                supported_modalities=[Modality.TEXT],
                supported_tasks=[
                    TaskType.COMPLEX_TABLE_INTERPRETATION,
                    TaskType.CONFLICTING_HYPOTHESES,
                ],
                configuration_key="DOCUSTRUCT_MODEL_GLM_5_3_FLASH_ID",
                enabled_state=False,
                verification_status=ModelVerificationStatus(
                    existence=ModelExistenceStatus.UNVERIFIED,
                    provider_availability=ProviderAvailabilityStatus.UNVERIFIED,
                    credentials=ConfigurationCredentialStatus.MISSING_CREDENTIALS,
                    test_result=IntegrationTestStatus.UNTESTED,
                ),
                routing_priority=2,
                timeout_retry_policy=TimeoutRetryPolicy(
                    timeout_seconds=30.0,
                    max_retries=2,
                    backoff_base_seconds=2.0,
                ),
                fallback_eligibility=True,
            ),
            # 5. Qwen3.8-27B
            CandidateModel(
                candidate_name="Qwen3.8-27B",
                exact_model_id="UNVERIFIED",
                provider=ProviderType.TOGETHER,
                supported_modalities=[Modality.TEXT],  # Vision remains unverified until evidence confirmed
                supported_tasks=[
                    TaskType.MULTILINGUAL_INTERPRETATION,
                    TaskType.VISUAL_TABLE_REVIEW,
                ],
                configuration_key="DOCUSTRUCT_MODEL_QWEN_3_8_27B_ID",
                enabled_state=False,
                verification_status=ModelVerificationStatus(
                    existence=ModelExistenceStatus.UNVERIFIED,
                    provider_availability=ProviderAvailabilityStatus.UNVERIFIED,
                    credentials=ConfigurationCredentialStatus.MISSING_CREDENTIALS,
                    test_result=IntegrationTestStatus.UNTESTED,
                ),
                routing_priority=1,
                timeout_retry_policy=TimeoutRetryPolicy(
                    timeout_seconds=30.0,
                    max_retries=2,
                    backoff_base_seconds=2.0,
                ),
                fallback_eligibility=True,
            ),
            # 6. Llama 4 Scout
            CandidateModel(
                candidate_name="Llama 4 Scout",
                exact_model_id="UNVERIFIED",
                provider=ProviderType.GROQ,
                supported_modalities=[Modality.TEXT],  # Vision remains unverified until evidence confirmed
                supported_tasks=[
                    TaskType.VISUAL_TABLE_REVIEW,
                    TaskType.ROUTINE_CLASSIFICATION,
                ],
                configuration_key="DOCUSTRUCT_MODEL_LLAMA_4_SCOUT_ID",
                enabled_state=False,
                verification_status=ModelVerificationStatus(
                    existence=ModelExistenceStatus.UNVERIFIED,
                    provider_availability=ProviderAvailabilityStatus.UNVERIFIED,
                    credentials=ConfigurationCredentialStatus.MISSING_CREDENTIALS,
                    test_result=IntegrationTestStatus.UNTESTED,
                ),
                routing_priority=2,
                timeout_retry_policy=TimeoutRetryPolicy(
                    timeout_seconds=25.0,
                    max_retries=2,
                    backoff_base_seconds=1.5,
                ),
                fallback_eligibility=True,
            ),
            # 7. Gemma 4
            CandidateModel(
                candidate_name="Gemma 4",
                exact_model_id="UNVERIFIED",
                provider=ProviderType.GROQ,
                supported_modalities=[Modality.TEXT],  # Vision remains unverified until evidence confirmed
                supported_tasks=[
                    TaskType.VISUAL_TABLE_REVIEW,
                    TaskType.ROUTINE_CLASSIFICATION,
                ],
                configuration_key="DOCUSTRUCT_MODEL_GEMMA_4_ID",
                enabled_state=False,
                verification_status=ModelVerificationStatus(
                    existence=ModelExistenceStatus.UNVERIFIED,
                    provider_availability=ProviderAvailabilityStatus.UNVERIFIED,
                    credentials=ConfigurationCredentialStatus.MISSING_CREDENTIALS,
                    test_result=IntegrationTestStatus.UNTESTED,
                ),
                routing_priority=3,
                timeout_retry_policy=TimeoutRetryPolicy(
                    timeout_seconds=25.0,
                    max_retries=2,
                    backoff_base_seconds=1.5,
                ),
                fallback_eligibility=True,
            ),
        ]

        for candidate in candidates:
            self._candidates[candidate.candidate_name] = candidate

    def sync_with_settings(self, settings: MultiLLMSettings) -> None:
        """Update credentials and exact model ID overrides from environment settings."""
        self._settings = settings
        for candidate in self._candidates.values():
            # Update credentials dimension based on active provider credentials
            has_creds = settings.has_provider_credentials(candidate.provider)
            candidate.verification_status.credentials = (
                ConfigurationCredentialStatus.CONFIGURED
                if has_creds
                else ConfigurationCredentialStatus.MISSING_CREDENTIALS
            )

            # Update exact model ID if specified in environment
            override_id = settings.get_model_id_override(candidate.configuration_key)
            if override_id and override_id.strip():
                candidate.exact_model_id = override_id.strip()

    def list_candidates(self) -> list[CandidateModel]:
        """Return all registered candidate models."""
        return list(self._candidates.values())

    def get_candidate(self, candidate_name: str) -> Optional[CandidateModel]:
        """Retrieve a candidate model by its exact name."""
        return self._candidates.get(candidate_name)

    def get_candidates_for_task(
        self,
        task: TaskType,
        requires_vision: bool = False,
    ) -> list[CandidateModel]:
        """Return candidate models matching task and modality, sorted by priority."""
        matches = [
            c for c in self._candidates.values()
            if task in c.supported_tasks
            and (not requires_vision or Modality.VISION in c.supported_modalities)
        ]
        return sorted(matches, key=lambda c: c.routing_priority)

    def update_verification_status(
        self,
        candidate_name: str,
        status: ModelVerificationStatus,
    ) -> bool:
        """Update the verification status of a registered candidate."""
        candidate = self._candidates.get(candidate_name)
        if candidate is None:
            return False
        candidate.verification_status = status
        return True
