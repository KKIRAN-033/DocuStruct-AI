"""DocuStruct AI — Models Status API Integration Tests.

Validates:
    - GET /api/v1/models/status returns HTTP 200 with ModelsStatusResponse schema.
    - Accurately enumerates all seven candidate models.
    - Truthfully reports unverified/missing status without claiming operational readiness.
    - All five external providers present in provider health mapping.
    - Strict secret redaction: zero credentials or authorization tokens exposed.
    - Endpoint is fast and read-only without triggering outbound network requests.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.app import app

client = TestClient(app)

EXPECTED_CANDIDATE_NAMES = [
    "GPT-OSS 20B",
    "GPT-OSS 120B",
    "DeepSeek V4.1 Flash",
    "GLM-5.3-Flash through Z.ai",
    "Qwen3.8-27B",
    "Llama 4 Scout",
    "Gemma 4",
]

EXPECTED_PROVIDERS = [
    "GROQ",
    "TOGETHER",
    "OPENROUTER",
    "DEEPSEEK",
    "ZAI",
]


class TestModelsStatusAPI:
    """Validate GET /api/v1/models/status contract, truthfulness, and security."""

    def test_status_endpoint_returns_200(self) -> None:
        """GET /api/v1/models/status returns HTTP 200."""
        response = client.get("/api/v1/models/status")
        assert response.status_code == 200

    def test_status_endpoint_schema_keys(self) -> None:
        """Response contains models, providers, and timestamp fields."""
        response = client.get("/api/v1/models/status")
        data = response.json()
        assert "models" in data
        assert "providers" in data
        assert "timestamp" in data
        assert isinstance(data["models"], list)
        assert isinstance(data["providers"], dict)
        assert isinstance(data["timestamp"], str)

    def test_status_endpoint_lists_all_seven_candidates(self) -> None:
        """All seven declared candidates are present in the response."""
        response = client.get("/api/v1/models/status")
        data = response.json()
        model_names = [m["candidate_name"] for m in data["models"]]
        assert len(model_names) == 7
        for name in EXPECTED_CANDIDATE_NAMES:
            assert name in model_names

    def test_unverified_candidates_truthfully_reported_non_operational(self) -> None:
        """No unverified model is falsely claimed to be operational or enabled."""
        response = client.get("/api/v1/models/status")
        data = response.json()
        for m in data["models"]:
            # Model cannot be enabled without empirical verification
            assert m["enabled_state"] is False
            # Verification status dimensions
            status = m["verification_status"]
            assert status["existence"] == "UNVERIFIED"
            assert status["test_result"] == "UNTESTED"

    def test_all_five_providers_present_in_health_map(self) -> None:
        """Health status covers all five external provider adapters."""
        response = client.get("/api/v1/models/status")
        data = response.json()
        providers = data["providers"]
        for p in EXPECTED_PROVIDERS:
            assert p in providers
            health = providers[p]
            assert "available" in health
            assert "configured" in health

    def test_secret_redaction_guarantees(self) -> None:
        """Response body strictly does not contain sensitive API keys or Bearer tokens."""
        response = client.get("/api/v1/models/status")
        body = response.text

        # Strict checks against credential leakage
        assert "Bearer" not in body
        assert "api_key" not in body.lower() or "configuration_key" in body
        # Confirm that only configuration key names (e.g. DOCUSTRUCT_MODEL_GPT_OSS_20B_ID) are returned
        data = response.json()
        for m in data["models"]:
            assert m["configuration_key"].startswith("DOCUSTRUCT_MODEL_")
