"""DocuStruct AI — Shared Test Fixtures and Helpers for LLM Integration Tests."""

from __future__ import annotations

import json
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest


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
