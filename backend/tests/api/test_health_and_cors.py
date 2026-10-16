"""DocuStruct AI — Health Endpoint & CORS Middleware Tests.

Validates:
    - ``GET /api/v1/health`` returns 200 OK with correct HealthResponse schema.
    - CORS preflight (OPTIONS) allows Vite development origins.
    - CORS rejects unauthorized origins.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.app import app

client = TestClient(app)


# ── Health Endpoint ──────────────────────────────────────────────────────────


class TestHealthEndpoint:
    """GET /api/v1/health contract tests."""

    def test_health_returns_200(self) -> None:
        """Health check returns HTTP 200 with expected schema fields."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
        assert data["backend_ready"] is True

    def test_health_response_has_no_extra_fields(self) -> None:
        """Verify that the health response has exactly three expected keys."""
        response = client.get("/api/v1/health")
        data = response.json()
        assert set(data.keys()) == {"status", "version", "backend_ready"}


# ── CORS Preflight ───────────────────────────────────────────────────────────


class TestCORSConfiguration:
    """CORS middleware validation for Vite development origins."""

    def test_cors_preflight_localhost_5173(self) -> None:
        """OPTIONS preflight with localhost:5173 origin returns CORS headers."""
        response = client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://localhost:5173"

    def test_cors_preflight_127_0_0_1_5173(self) -> None:
        """OPTIONS preflight with 127.0.0.1:5173 origin returns CORS headers."""
        response = client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://127.0.0.1:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"

    def test_cors_unauthorized_origin_rejected(self) -> None:
        """Non-whitelisted origin does not receive an allow-origin header."""
        response = client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://evil.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        # CORS middleware either omits the header or does not echo the origin
        allow_origin = response.headers.get("access-control-allow-origin")
        assert allow_origin != "http://evil.example.com"

    def test_cors_simple_get_with_origin(self) -> None:
        """A simple GET with a valid origin receives the allow-origin header."""
        response = client.get(
            "/api/v1/health",
            headers={"Origin": "http://localhost:5173"},
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
