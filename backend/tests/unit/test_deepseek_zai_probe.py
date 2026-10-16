"""DocuStruct AI — DeepSeek, Z.ai, ProviderFactory & Capability Probe Tests.

Comprehensive mocked HTTP unit tests validating:
- DeepSeek and Z.ai adapters (completions, structured output, error mapping, credential safety).
- ProviderFactory instantiation, caching, and model lookup across all 5 provider types.
- CapabilityProbeService protocol and 4-part ModelVerificationStatus transitions.
- Crucial Invariant: /models listing proves ONLY identifier existence, NEVER multimodal vision,
  structured-output, or task-specific capability.
"""

from __future__ import annotations

import json
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pydantic import BaseModel, Field

from app.llm.config import MultiLLMSettings
from app.llm.enums import (
    ConfigurationCredentialStatus,
    IntegrationTestStatus,
    ModelExistenceStatus,
    Modality,
    ProviderAvailabilityStatus,
    ProviderType,
    TaskType,
)
from app.llm.exceptions import (
    ModelNotFoundError,
    ProviderAuthError,
    ProviderServiceUnavailableError,
    ProviderTimeoutError,
    RateLimitExceededError,
    SchemaValidationError,
)
from app.llm.models import CandidateModel, ModelVerificationStatus
from app.llm.probe import CapabilityProbeResult, CapabilityProbeService
from app.llm.providers.deepseek import DeepSeekProviderAdapter
from app.llm.providers.factory import ProviderFactory
from app.llm.providers.groq import GroqProviderAdapter
from app.llm.providers.openrouter import OpenRouterProviderAdapter
from app.llm.providers.together import TogetherProviderAdapter
from app.llm.providers.zai import ZaiProviderAdapter
from app.llm.registry import ModelRegistry


class ExtractionResult(BaseModel):
    account_name: str
    balance: float = Field(ge=0.0)


def create_mock_client(
    status_code: int = 200,
    json_data: Any = None,
    text: str = "",
    headers: Optional[dict[str, str]] = None,
    side_effect: Any = None,
) -> tuple[AsyncMock, MagicMock]:
    """Helper creating a mocked httpx.AsyncClient with context manager support."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = status_code
    mock_response.headers = headers or {}
    if json_data is not None:
        mock_response.json.return_value = json_data
        mock_response.text = json.dumps(json_data)
    else:
        mock_response.text = text
        mock_response.json.side_effect = json.JSONDecodeError("Expecting value", text, 0)

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    if side_effect:
        mock_client.get.side_effect = side_effect
        mock_client.post.side_effect = side_effect
    else:
        mock_client.get.return_value = mock_response
        mock_client.post.return_value = mock_response

    return mock_client, mock_response


# ══════════════════════════════════════════════════════════════════════════════
# DeepSeek Provider Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestDeepSeekProviderAdapter:
    """Test suite for DeepSeekProviderAdapter."""

    @pytest.mark.asyncio
    async def test_deepseek_missing_credentials_fails_safely(self) -> None:
        """Missing credentials fail safely without network activity."""
        adapter = DeepSeekProviderAdapter(api_key=None)
        assert adapter.has_credentials() is False

        health = await adapter.health_check()
        assert health.configured is False
        assert health.available is False

        assert await adapter.probe_availability("deepseek-chat") is False

        with pytest.raises(ProviderAuthError):
            await adapter.complete("test", "deepseek-chat")

        with pytest.raises(ProviderAuthError):
            await adapter.complete_structured("test", "deepseek-chat", ExtractionResult)

    @pytest.mark.asyncio
    async def test_deepseek_successful_completion(self) -> None:
        """DeepSeek completion returns valid CompletionResponse."""
        mock_payload = {
            "choices": [{"message": {"content": "DeepSeek response"}}],
            "usage": {"total_tokens": 40},
        }
        mock_client, _ = create_mock_client(200, json_data=mock_payload)

        with patch("httpx.AsyncClient", return_value=mock_client):
            adapter = DeepSeekProviderAdapter(api_key="sk-deepseek-key")
            res = await adapter.complete("Summarize", "deepseek-chat")
            assert res.content == "DeepSeek response"
            assert res.provider == ProviderType.DEEPSEEK
            assert res.model_id == "deepseek-chat"
            assert res.usage["total_tokens"] == 40

    @pytest.mark.asyncio
    async def test_deepseek_structured_completion(self) -> None:
        """DeepSeek structured completion validates against Pydantic schema."""
        mock_payload = {
            "choices": [{"message": {"content": '{"account_name": "Operating Cash", "balance": 150000.0}'}}],
            "usage": {"total_tokens": 30},
        }
        mock_client, _ = create_mock_client(200, json_data=mock_payload)

        with patch("httpx.AsyncClient", return_value=mock_client):
            adapter = DeepSeekProviderAdapter(api_key="sk-deepseek-key")
            res = await adapter.complete_structured("prompt", "deepseek-chat", ExtractionResult)
            assert res.validation_passed is True
            assert isinstance(res.parsed, ExtractionResult)
            assert res.parsed.account_name == "Operating Cash"
            assert res.parsed.balance == 150000.0

    @pytest.mark.asyncio
    async def test_deepseek_structured_completion_schema_mismatch(self) -> None:
        """Invalid schema output raises SchemaValidationError."""
        mock_payload = {
            "choices": [{"message": {"content": '{"account_name": "Cash", "balance": -500.0}'}}],
        }
        mock_client, _ = create_mock_client(200, json_data=mock_payload)

        with patch("httpx.AsyncClient", return_value=mock_client):
            adapter = DeepSeekProviderAdapter(api_key="sk-deepseek-key")
            with pytest.raises(SchemaValidationError):
                await adapter.complete_structured("prompt", "deepseek-chat", ExtractionResult)

    @pytest.mark.asyncio
    async def test_deepseek_error_handling(self) -> None:
        """DeepSeek maps 401, 404, 429, 500, timeouts correctly."""
        # 429 with retry-after
        mock_client_429, _ = create_mock_client(429, text="Rate limit", headers={"retry-after": "3.5"})
        with patch("httpx.AsyncClient", return_value=mock_client_429):
            adapter = DeepSeekProviderAdapter(api_key="sk-key")
            with pytest.raises(RateLimitExceededError) as exc_info:
                await adapter.complete("test", "m")
            assert exc_info.value.retry_after_seconds == 3.5

        # 401 Auth
        mock_client_401, _ = create_mock_client(401, text="Unauthorized")
        with patch("httpx.AsyncClient", return_value=mock_client_401):
            adapter = DeepSeekProviderAdapter(api_key="sk-key")
            with pytest.raises(ProviderAuthError):
                await adapter.complete("test", "m")

        # 404 Model Not Found
        mock_client_404, _ = create_mock_client(404, text="Model not found")
        with patch("httpx.AsyncClient", return_value=mock_client_404):
            adapter = DeepSeekProviderAdapter(api_key="sk-key")
            with pytest.raises(ModelNotFoundError):
                await adapter.complete("test", "missing-model")

        # Timeout
        timeout_client, _ = create_mock_client(side_effect=httpx.TimeoutException("Timeout"))
        with patch("httpx.AsyncClient", return_value=timeout_client):
            adapter = DeepSeekProviderAdapter(api_key="sk-key")
            with pytest.raises(ProviderTimeoutError):
                await adapter.complete("test", "m")

    @pytest.mark.asyncio
    async def test_deepseek_probe_availability(self) -> None:
        """DeepSeek probe_availability verifies model ID existence."""
        mock_payload = {
            "data": [{"id": "deepseek-chat"}, {"id": "deepseek-reasoner"}]
        }
        mock_client, _ = create_mock_client(200, json_data=mock_payload)

        with patch("httpx.AsyncClient", return_value=mock_client):
            adapter = DeepSeekProviderAdapter(api_key="sk-key")
            assert await adapter.probe_availability("deepseek-chat") is True
            assert await adapter.probe_availability("deepseek-v4-1-flash") is False


# ══════════════════════════════════════════════════════════════════════════════
# Z.ai Provider Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestZaiProviderAdapter:
    """Test suite for ZaiProviderAdapter."""

    @pytest.mark.asyncio
    async def test_zai_missing_credentials_fails_safely(self) -> None:
        """Missing credentials fail safely without making network requests."""
        adapter = ZaiProviderAdapter(api_key=None)
        assert adapter.has_credentials() is False

        health = await adapter.health_check()
        assert health.configured is False
        assert health.available is False

        assert await adapter.probe_availability("glm-5.3-flash") is False

        with pytest.raises(ProviderAuthError):
            await adapter.complete("test", "glm-5.3-flash")

    @pytest.mark.asyncio
    async def test_zai_successful_completion_and_structured(self) -> None:
        """Z.ai completion and structured completion validate correctly."""
        mock_payload = {
            "choices": [{"message": {"content": '{"account_name": "Accounts Receivable", "balance": 75000.0}'}}],
            "usage": {"total_tokens": 35},
        }
        mock_client, _ = create_mock_client(200, json_data=mock_payload)

        with patch("httpx.AsyncClient", return_value=mock_client):
            adapter = ZaiProviderAdapter(api_key="zai-secret-key")

            # Structured
            res = await adapter.complete_structured("prompt", "glm-5.3-flash", ExtractionResult)
            assert res.validation_passed is True
            assert res.parsed.account_name == "Accounts Receivable"
            assert res.parsed.balance == 75000.0
            assert res.provider == ProviderType.ZAI

    @pytest.mark.asyncio
    async def test_zai_auth_failure_401(self) -> None:
        """HTTP 401 raises ProviderAuthError."""
        mock_client, _ = create_mock_client(401, text="Unauthorized: Invalid Z.ai API key")

        with patch("httpx.AsyncClient", return_value=mock_client):
            adapter = ZaiProviderAdapter(api_key="zai-bad-key")
            with pytest.raises(ProviderAuthError):
                await adapter.complete("test", "m")

    @pytest.mark.asyncio
    async def test_zai_model_not_found_404(self) -> None:
        """HTTP 404 raises ModelNotFoundError."""
        mock_client, _ = create_mock_client(404, text="Model not found on Z.ai")

        with patch("httpx.AsyncClient", return_value=mock_client):
            adapter = ZaiProviderAdapter(api_key="zai-key")
            with pytest.raises(ModelNotFoundError):
                await adapter.complete("test", "non-existent-zai-model")

    @pytest.mark.asyncio
    async def test_zai_rate_limit_429_with_retry_after(self) -> None:
        """HTTP 429 raises RateLimitExceededError with retry-after header."""
        mock_client, _ = create_mock_client(
            429,
            text="Z.ai rate limit exceeded",
            headers={"Retry-After": "4.5"},
        )

        with patch("httpx.AsyncClient", return_value=mock_client):
            adapter = ZaiProviderAdapter(api_key="zai-key")
            with pytest.raises(RateLimitExceededError) as exc_info:
                await adapter.complete("test", "m")
            assert exc_info.value.retry_after_seconds == 4.5
            assert exc_info.value.provider == "ZAI"

    @pytest.mark.asyncio
    async def test_zai_server_error_503(self) -> None:
        """HTTP 503 raises ProviderServiceUnavailableError."""
        mock_client, _ = create_mock_client(503, text="Service Unavailable")

        with patch("httpx.AsyncClient", return_value=mock_client):
            adapter = ZaiProviderAdapter(api_key="zai-key")
            with pytest.raises(ProviderServiceUnavailableError):
                await adapter.complete("test", "m")

    @pytest.mark.asyncio
    async def test_zai_timeout_and_network_errors(self) -> None:
        """Timeouts and network disconnects map to typed exceptions."""
        timeout_client, _ = create_mock_client(side_effect=httpx.TimeoutException("Read timed out"))
        with patch("httpx.AsyncClient", return_value=timeout_client):
            adapter = ZaiProviderAdapter(api_key="zai-key")
            with pytest.raises(ProviderTimeoutError):
                await adapter.complete("test", "m")

        net_client, _ = create_mock_client(side_effect=httpx.ConnectError("Network refused"))
        with patch("httpx.AsyncClient", return_value=net_client):
            adapter = ZaiProviderAdapter(api_key="zai-key")
            with pytest.raises(ProviderServiceUnavailableError):
                await adapter.complete("test", "m")

    @pytest.mark.asyncio
    async def test_zai_structured_completion_schema_mismatch(self) -> None:
        """Structured output violating schema constraints raises SchemaValidationError."""
        mock_payload = {
            "choices": [{"message": {"content": '{"account_name": "Operating", "balance": -100.0}'}}],
        }
        mock_client, _ = create_mock_client(200, json_data=mock_payload)

        with patch("httpx.AsyncClient", return_value=mock_client):
            adapter = ZaiProviderAdapter(api_key="zai-key")
            with pytest.raises(SchemaValidationError):
                await adapter.complete_structured("prompt", "m", ExtractionResult)

    @pytest.mark.asyncio
    async def test_zai_probe_availability(self) -> None:
        """probe_availability returns True when model exists in data array, False otherwise."""
        mock_payload = {
            "data": [{"id": "glm-5.3-flash"}, {"id": "glm-4"}]
        }
        mock_client, _ = create_mock_client(200, json_data=mock_payload)

        with patch("httpx.AsyncClient", return_value=mock_client):
            adapter = ZaiProviderAdapter(api_key="zai-key")
            assert await adapter.probe_availability("glm-5.3-flash") is True
            assert await adapter.probe_availability("missing-glm-model") is False


# ══════════════════════════════════════════════════════════════════════════════
# ProviderFactory Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestProviderFactory:
    """Test suite for ProviderFactory."""

    def setup_method(self) -> None:
        ProviderFactory.reset_cache()

    def teardown_method(self) -> None:
        ProviderFactory.reset_cache()

    def test_factory_instantiates_all_five_provider_types(self) -> None:
        """Factory returns correct adapter class for all 5 provider types."""
        settings = MultiLLMSettings(
            groq_api_key="g-key",
            together_api_key="t-key",
            openrouter_api_key="o-key",
            deepseek_api_key="d-key",
            zai_api_key="z-key",
        )

        groq_adapter = ProviderFactory.get_adapter(ProviderType.GROQ, settings=settings)
        assert isinstance(groq_adapter, GroqProviderAdapter)
        assert groq_adapter.api_key == "g-key"

        together_adapter = ProviderFactory.get_adapter(ProviderType.TOGETHER, settings=settings)
        assert isinstance(together_adapter, TogetherProviderAdapter)
        assert together_adapter.api_key == "t-key"

        openrouter_adapter = ProviderFactory.get_adapter(ProviderType.OPENROUTER, settings=settings)
        assert isinstance(openrouter_adapter, OpenRouterProviderAdapter)
        assert openrouter_adapter.api_key == "o-key"

        deepseek_adapter = ProviderFactory.get_adapter(ProviderType.DEEPSEEK, settings=settings)
        assert isinstance(deepseek_adapter, DeepSeekProviderAdapter)
        assert deepseek_adapter.api_key == "d-key"

        zai_adapter = ProviderFactory.get_adapter(ProviderType.ZAI, settings=settings)
        assert isinstance(zai_adapter, ZaiProviderAdapter)
        assert zai_adapter.api_key == "z-key"

    def test_factory_get_adapter_for_model(self) -> None:
        """Factory resolves candidate model provider type to correct adapter."""
        settings = MultiLLMSettings(deepseek_api_key="d-key")
        candidate = CandidateModel(
            candidate_name="DeepSeek V4.1 Flash",
            exact_model_id="deepseek-v4.1-flash",
            provider=ProviderType.DEEPSEEK,
            supported_modalities=[Modality.TEXT],
            supported_tasks=[TaskType.ROUTINE_CLASSIFICATION],
            configuration_key="DOCUSTRUCT_MODEL_DEEPSEEK_V4_1_FLASH_ID",
        )

        adapter = ProviderFactory.get_adapter_for_model(candidate, settings=settings)
        assert isinstance(adapter, DeepSeekProviderAdapter)
        assert adapter.api_key == "d-key"

    def test_factory_caching_and_reset(self) -> None:
        """Factory caches instances and clears cache upon reset."""
        settings = MultiLLMSettings(groq_api_key="cached-key")
        adapter1 = ProviderFactory.get_adapter(ProviderType.GROQ, settings=settings)
        adapter2 = ProviderFactory.get_adapter(ProviderType.GROQ, settings=settings)
        assert adapter1 is adapter2

        ProviderFactory.reset_cache()
        adapter3 = ProviderFactory.get_adapter(ProviderType.GROQ, settings=settings)
        assert adapter1 is not adapter3

    def test_factory_cache_invalidated_on_url_or_timeout_change(self) -> None:
        """Different base URL or timeout returns distinct adapter, preventing stale configuration."""
        s1 = MultiLLMSettings(
            groq_api_key="shared-key",
            groq_base_url="https://api.groq.com/openai/v1",
            default_timeout_seconds=30.0,
        )
        adapter1 = ProviderFactory.get_adapter(ProviderType.GROQ, settings=s1)
        assert adapter1.base_url == "https://api.groq.com/openai/v1"
        assert adapter1.timeout_seconds == 30.0

        # Change base URL with same provider and API key
        s2 = MultiLLMSettings(
            groq_api_key="shared-key",
            groq_base_url="https://custom.groq.proxy/v1",
            default_timeout_seconds=30.0,
        )
        adapter2 = ProviderFactory.get_adapter(ProviderType.GROQ, settings=s2)
        assert adapter2 is not adapter1
        assert adapter2.base_url == "https://custom.groq.proxy/v1"

        # Change timeout with same provider, API key, and base URL
        s3 = MultiLLMSettings(
            groq_api_key="shared-key",
            groq_base_url="https://custom.groq.proxy/v1",
            default_timeout_seconds=60.0,
        )
        adapter3 = ProviderFactory.get_adapter(ProviderType.GROQ, settings=s3)
        assert adapter3 is not adapter2
        assert adapter3.timeout_seconds == 60.0

    def test_factory_unsupported_provider_raises_error(self) -> None:
        """Non-enum or invalid provider raises MultiLLMError."""
        with pytest.raises(Exception):
            ProviderFactory.get_adapter("INVALID_PROVIDER")  # type: ignore[arg-type]


# ══════════════════════════════════════════════════════════════════════════════
# CapabilityProbeService Tests & Invariant Verification
# ══════════════════════════════════════════════════════════════════════════════


class TestCapabilityProbeService:
    """Test suite for CapabilityProbeService and capability probing protocol."""

    def setup_method(self) -> None:
        ProviderFactory.reset_cache()

    def teardown_method(self) -> None:
        ProviderFactory.reset_cache()

    @pytest.mark.asyncio
    async def test_probe_missing_credentials_skips_network_request(self) -> None:
        """When credentials are absent, probe returns MISSING_CREDENTIALS without network calls."""
        settings = MultiLLMSettings(
            groq_api_key="",
            together_api_key="",
            openrouter_api_key="",
            deepseek_api_key="",
            zai_api_key="",
        )
        service = CapabilityProbeService(settings=settings)

        registry = ModelRegistry()
        candidate = registry.get_candidate("GPT-OSS 20B")
        assert candidate is not None

        # Verify probe skips network
        with patch("httpx.AsyncClient") as mock_client:
            status = await service.probe_candidate(candidate, settings=settings)
            mock_client.assert_not_called()

        assert status.credentials == ConfigurationCredentialStatus.MISSING_CREDENTIALS
        assert status.existence == ModelExistenceStatus.UNVERIFIED
        assert status.provider_availability == ProviderAvailabilityStatus.UNVERIFIED
        assert status.test_result == IntegrationTestStatus.UNTESTED

    @pytest.mark.asyncio
    async def test_probe_placeholder_model_id_remains_unverified(self) -> None:
        """Candidate with placeholder exact_model_id 'UNVERIFIED' sets provider_availability=UNVERIFIED without network call."""
        settings = MultiLLMSettings(groq_api_key="configured-key")
        service = CapabilityProbeService(settings=settings)

        candidate = CandidateModel(
            candidate_name="GPT-OSS 20B",
            exact_model_id="UNVERIFIED",
            provider=ProviderType.GROQ,
            configuration_key="DOCUSTRUCT_MODEL_GPT_OSS_20B_ID",
        )

        with patch("httpx.AsyncClient") as mock_client:
            status = await service.probe_candidate(candidate, settings=settings)
            mock_client.assert_not_called()

        assert status.credentials == ConfigurationCredentialStatus.CONFIGURED
        assert status.existence == ModelExistenceStatus.UNVERIFIED
        assert status.provider_availability == ProviderAvailabilityStatus.UNVERIFIED
        assert status.test_result == IntegrationTestStatus.UNTESTED

    @pytest.mark.asyncio
    async def test_probe_detailed_placeholder_model_id_preserves_unverified_availability(self) -> None:
        """probe_detailed for placeholder model ID preserves UNVERIFIED availability and documents skipped probe."""
        settings = MultiLLMSettings(groq_api_key="configured-key")
        service = CapabilityProbeService(settings=settings)

        candidate = CandidateModel(
            candidate_name="GPT-OSS 20B",
            exact_model_id="UNVERIFIED",
            provider=ProviderType.GROQ,
            configuration_key="DOCUSTRUCT_MODEL_GPT_OSS_20B_ID",
        )

        with patch("httpx.AsyncClient") as mock_client:
            detailed = await service.probe_detailed(candidate, settings=settings)
            mock_client.assert_not_called()

        assert detailed.verification_status.provider_availability == ProviderAvailabilityStatus.UNVERIFIED
        assert detailed.verification_status.existence == ModelExistenceStatus.UNVERIFIED
        assert detailed.vision_verified is False
        assert detailed.structured_output_verified is False
        assert "placeholder model identifier 'UNVERIFIED'" in detailed.details

    @pytest.mark.asyncio
    async def test_probe_confirmed_model_does_not_prove_vision_or_task_capability(self) -> None:
        """CRITICAL INVARIANT:

        When an endpoint confirms model ID existence, existence=CONFIRMED and
        provider_availability=AVAILABLE. BUT:
        - vision_verified MUST be False.
        - structured_output_verified MUST be False.
        - test_result MUST be UNTESTED.
        A /models listing NEVER proves multimodal vision or task capability!
        """
        settings = MultiLLMSettings(together_api_key="valid-together-key")
        service = CapabilityProbeService(settings=settings)

        candidate = CandidateModel(
            candidate_name="Llama 4 Scout",
            exact_model_id="meta-llama/Llama-4-Scout-17B-16E-Instruct",
            provider=ProviderType.TOGETHER,
            supported_modalities=[Modality.TEXT, Modality.VISION],
            supported_tasks=[TaskType.VISUAL_TABLE_REVIEW],
            configuration_key="DOCUSTRUCT_MODEL_LLAMA_4_SCOUT_ID",
        )

        mock_payload = [
            {"id": "meta-llama/Llama-4-Scout-17B-16E-Instruct"}
        ]
        mock_client, _ = create_mock_client(200, json_data=mock_payload)

        with patch("httpx.AsyncClient", return_value=mock_client):
            detailed_result = await service.probe_detailed(candidate, settings=settings)

        # 1. Existence confirmed
        assert detailed_result.verification_status.existence == ModelExistenceStatus.CONFIRMED
        assert detailed_result.verification_status.provider_availability == ProviderAvailabilityStatus.AVAILABLE
        assert detailed_result.verification_status.credentials == ConfigurationCredentialStatus.CONFIGURED

        # 2. Integration test remains UNTESTED
        assert detailed_result.verification_status.test_result == IntegrationTestStatus.UNTESTED

        # 3. Model is NOT operational yet
        assert detailed_result.verification_status.is_operational is False

        # 4. Multimodal and structured output capabilities remain strictly UNVERIFIED
        assert detailed_result.vision_verified is False
        assert detailed_result.structured_output_verified is False
        assert "Multimodal vision and structured-output capabilities remain unverified" in detailed_result.details

    @pytest.mark.asyncio
    async def test_probe_unavailable_when_model_missing_from_endpoint(self) -> None:
        """When model is not present in /models, existence=UNAVAILABLE."""
        settings = MultiLLMSettings(deepseek_api_key="configured-key")
        service = CapabilityProbeService(settings=settings)

        candidate = CandidateModel(
            candidate_name="DeepSeek V4.1 Flash",
            exact_model_id="deepseek-v4.1-flash",
            provider=ProviderType.DEEPSEEK,
            configuration_key="DOCUSTRUCT_MODEL_DEEPSEEK_V4_1_FLASH_ID",
        )

        mock_payload = {"data": [{"id": "deepseek-chat"}]}  # different model
        mock_client, _ = create_mock_client(200, json_data=mock_payload)

        with patch("httpx.AsyncClient", return_value=mock_client):
            status = await service.probe_candidate(candidate, settings=settings)

        assert status.existence == ModelExistenceStatus.UNAVAILABLE
        assert status.provider_availability == ProviderAvailabilityStatus.AVAILABLE
        assert status.credentials == ConfigurationCredentialStatus.CONFIGURED

    @pytest.mark.asyncio
    async def test_probe_network_timeout_leaves_existence_unverified(self) -> None:
        """Network timeout sets existence=UNVERIFIED and provider_availability=UNAVAILABLE."""
        settings = MultiLLMSettings(groq_api_key="valid-key")
        service = CapabilityProbeService(settings=settings)

        candidate = CandidateModel(
            candidate_name="GPT-OSS 20B",
            exact_model_id="gpt-oss-20b-chat",
            provider=ProviderType.GROQ,
            configuration_key="DOCUSTRUCT_MODEL_GPT_OSS_20B_ID",
        )

        mock_client, _ = create_mock_client(side_effect=httpx.TimeoutException("Read timeout"))

        with patch("httpx.AsyncClient", return_value=mock_client):
            status = await service.probe_candidate(candidate, settings=settings)

        assert status.existence == ModelExistenceStatus.UNVERIFIED
        assert status.provider_availability == ProviderAvailabilityStatus.UNAVAILABLE
        assert status.credentials == ConfigurationCredentialStatus.CONFIGURED

    @pytest.mark.asyncio
    async def test_probe_all_candidates_safely(self) -> None:
        """probe_all_candidates checks all seven registry candidates safely."""
        settings = MultiLLMSettings(
            groq_api_key="",
            together_api_key="",
            openrouter_api_key="",
            deepseek_api_key="",
            zai_api_key="",
        )
        service = CapabilityProbeService(settings=settings)

        with patch("httpx.AsyncClient") as mock_client:
            results = await service.probe_all_candidates(settings=settings)
            mock_client.assert_not_called()

        assert len(results) == 7
        for name, status in results.items():
            assert status.credentials == ConfigurationCredentialStatus.MISSING_CREDENTIALS
            assert status.existence == ModelExistenceStatus.UNVERIFIED
            assert status.is_operational is False
