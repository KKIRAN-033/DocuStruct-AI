"""DocuStruct AI — API Tests for Image Document Uploads

Verifies that image formats (.png, .jpg, .webp) uploaded to /api/v1/extract
are automatically wrapped/converted to PDF and routed to Vision AI extraction.
"""

from __future__ import annotations

import io
from unittest.mock import MagicMock, patch

import pymupdf
import pytest
from httpx import ASGITransport, AsyncClient

from app.api.app import app


@pytest.mark.asyncio
async def test_upload_png_image_auto_converts_and_extracts(monkeypatch) -> None:
    """Uploading a PNG image directly to /api/v1/extract runs successfully."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-mock")

    # Generate a small 100x100 PNG image
    doc = pymupdf.open()
    page = doc.new_page(width=200, height=200)
    page.insert_text(pymupdf.Point(20, 40), "Invoice Photo")
    pix = page.get_pixmap()
    png_bytes = pix.tobytes("png")
    doc.close()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": (
                        "{\"tables\": [{\"title\": \"Photo Table\", "
                        "\"headers\": [\"Desc\", \"Total\"], "
                        "\"rows\": [[\"Widget\", \"$10.00\"]]}]}"
                    )
                }
            }
        ]
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        with patch("httpx.Client.post", return_value=mock_resp):
            response = await client.post(
                "/api/v1/extract",
                files={
                    "file": ("invoice_photo.png", io.BytesIO(png_bytes), "image/png"),
                },
            )

    assert response.status_code == 200
    data = response.json()
    assert data["execution_state"] == "COMPLETED"
    assert len(data["canonical_tables"]) == 1
    tbl = data["canonical_tables"][0]
    assert tbl["title"] == "Photo Table"
    assert tbl["original_headers"] == ["Desc", "Total"]
    assert tbl["extraction_method"] == "VISION_AI"
