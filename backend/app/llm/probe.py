"""DocuStruct AI — Model Capability Probe Service.

Dynamic model capability verification protocol. Probes provider endpoints to confirm
candidate model identifier existence without making unverified assumptions.

CRITICAL INVARIANTS:
1. Provider `/models` listing proves ONLY identifier presence on the endpoint.
   It does NOT prove vision, structured-output, or task-specific capability.
2. Missing credentials fail safely without making network requests or exposing secrets.
3. Unverified or missing models remain strictly UNVERIFIED or UNAVAILABLE.
4. Vision capabilities are NEVER enabled or verified solely by existence probing.
"""

from __future__ import annotations

import logging
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.llm.config import MultiLLMSettings
from app.llm.enums import (
    ConfigurationCredentialStatus,
    IntegrationTestStatus,
    ModelExistenceStatus,
    ProviderAvailabilityStatus,
    ProviderType,
)
from app.llm.models import CandidateModel, ModelVerificationStatus
from app.llm.providers.factory import ProviderFactory
from app.llm.registry import ModelRegistry

logger = logging.getLogger(__name__)


class CapabilityProbeResult(BaseModel):
    """Detailed audit record of a candidate model capability probe.

    Explicitly decouples endpoint identifier presence from multimodal and task-specific capabilities.
    """

    model_config = ConfigDict(protected_namespaces=())

    candidate_name: str
    model_id: str
    provider: ProviderType
    verification_status: ModelVerificationStatus
    # INVARIANT: /models listing does NOT prove multimodal vision capability
    vision_verified: bool = False
    # INVARIANT: /models listing does NOT prove JSON schema adherence capability
    structured_output_verified: bool = False
    details: Optional[str] = None


class CapabilityProbeService:
    """Service to probe and verify candidate model availability and existence."""

    def __init__(self, settings: Optional[MultiLLMSettings] = None) -> None:
        self.settings = settings or MultiLLMSettings()

    async def probe_candidate(
        self,
        candidate: CandidateModel,
        settings: Optional[MultiLLMSettings] = None,
    ) -> ModelVerificationStatus:
        """Probe provider endpoint for candidate model identifier.

        Returns updated 4-part ModelVerificationStatus.
        Fails safely without network calls if credentials are absent.
        """
        active_settings = settings or self.settings
        adapter = ProviderFactory.get_adapter_for_model(candidate, settings=active_settings)

        # 1. Credential check — fail safely without network requests if unconfigured
        if not adapter.has_credentials():
            logger.info(
                "Skipping probe for %s on %s: credentials not configured",
                candidate.candidate_name,
                candidate.provider.value,
            )
            return ModelVerificationStatus(
                existence=ModelExistenceStatus.UNVERIFIED,
                provider_availability=ProviderAvailabilityStatus.UNVERIFIED,
                credentials=ConfigurationCredentialStatus.MISSING_CREDENTIALS,
                test_result=IntegrationTestStatus.UNTESTED,
            )

        # 2. Check if candidate has a concrete model ID to probe
        model_id = candidate.exact_model_id
        if not model_id or model_id == "UNVERIFIED":
            logger.info(
                "Candidate %s has placeholder model_id '%s'; cannot probe endpoint",
                candidate.candidate_name,
                model_id,
            )
            return ModelVerificationStatus(
                existence=ModelExistenceStatus.UNVERIFIED,
                provider_availability=ProviderAvailabilityStatus.UNVERIFIED,
                credentials=ConfigurationCredentialStatus.CONFIGURED,
                test_result=IntegrationTestStatus.UNTESTED,
            )

        # 3. Probe provider endpoint
        try:
            confirmed = await adapter.probe_availability(model_id)
            if confirmed:
                logger.info(
                    "Model existence confirmed for %s (%s) on %s",
                    candidate.candidate_name,
                    model_id,
                    candidate.provider.value,
                )
                return ModelVerificationStatus(
                    existence=ModelExistenceStatus.CONFIRMED,
                    provider_availability=ProviderAvailabilityStatus.AVAILABLE,
                    credentials=ConfigurationCredentialStatus.CONFIGURED,
                    test_result=IntegrationTestStatus.UNTESTED,
                )
            else:
                logger.warning(
                    "Model %s (%s) not found on %s endpoint",
                    candidate.candidate_name,
                    model_id,
                    candidate.provider.value,
                )
                return ModelVerificationStatus(
                    existence=ModelExistenceStatus.UNAVAILABLE,
                    provider_availability=ProviderAvailabilityStatus.AVAILABLE,
                    credentials=ConfigurationCredentialStatus.CONFIGURED,
                    test_result=IntegrationTestStatus.UNTESTED,
                )
        except Exception as exc:
            logger.error(
                "Network or protocol error while probing %s (%s) on %s: %s",
                candidate.candidate_name,
                model_id,
                candidate.provider.value,
                exc,
            )
            return ModelVerificationStatus(
                existence=ModelExistenceStatus.UNVERIFIED,
                provider_availability=ProviderAvailabilityStatus.UNAVAILABLE,
                credentials=ConfigurationCredentialStatus.CONFIGURED,
                test_result=IntegrationTestStatus.UNTESTED,
            )

    async def probe_detailed(
        self,
        candidate: CandidateModel,
        settings: Optional[MultiLLMSettings] = None,
    ) -> CapabilityProbeResult:
        """Execute capability probe returning full diagnostic record.

        Enforces invariant that /models listing does NOT prove vision or structured-output capabilities.
        """
        status = await self.probe_candidate(candidate, settings=settings)

        if status.credentials == ConfigurationCredentialStatus.MISSING_CREDENTIALS:
            details = f"Missing API key for provider {candidate.provider.value}; network probe blocked"
        elif candidate.exact_model_id == "UNVERIFIED":
            details = (
                f"Candidate '{candidate.candidate_name}' has placeholder model identifier 'UNVERIFIED'; "
                f"endpoint probe skipped and provider availability remains unverified."
            )
        elif status.existence == ModelExistenceStatus.CONFIRMED:
            details = (
                f"Model identifier '{candidate.exact_model_id}' confirmed on {candidate.provider.value}. "
                f"Multimodal vision and structured-output capabilities remain unverified pending integration tests."
            )
        elif status.existence == ModelExistenceStatus.UNAVAILABLE:
            details = f"Model identifier '{candidate.exact_model_id}' was not found on {candidate.provider.value}"
        else:
            details = f"Unable to verify existence of '{candidate.exact_model_id}' on {candidate.provider.value}"

        return CapabilityProbeResult(
            candidate_name=candidate.candidate_name,
            model_id=candidate.exact_model_id,
            provider=candidate.provider,
            verification_status=status,
            vision_verified=False,  # Always False per invariant: /models listing does not prove vision
            structured_output_verified=False,  # Always False per invariant: /models listing does not prove structured output
            details=details,
        )

    async def probe_all_candidates(
        self,
        registry: Optional[ModelRegistry] = None,
        settings: Optional[MultiLLMSettings] = None,
    ) -> dict[str, ModelVerificationStatus]:
        """Probe all registered candidates and return a mapping of candidate names to verification statuses."""
        reg = registry or ModelRegistry()
        results: dict[str, ModelVerificationStatus] = {}
        for candidate in reg.list_candidates():
            status = await self.probe_candidate(candidate, settings=settings)
            results[candidate.candidate_name] = status
        return results
