"""DocuStruct AI — FastAPI Application.

Minimal, stateless HTTP adapter wrapping the existing synchronous
``run_phase1_pipeline()`` pipeline.

Design Invariants (DECISION-008):
    - This is a thin adapter layer — no business logic lives here.
    - The existing pipeline, domain models, and security gate are not modified.
    - Windows file-handle safety: upload temp files are explicitly closed
      before invoking the pipeline, and unconditionally unlinked in ``finally``.
    - Event loop safety: synchronous pipeline execution is offloaded to a worker
      thread pool using ``starlette.concurrency.run_in_threadpool``.
    - Operational errors (corrupt PDF, encrypted, etc.) return HTTP 200 with
      ``execution_state=FAILED``; only infrastructure errors raise HTTP 4xx/5xx.
    - Body size limit note: ``MAX_UPLOAD_BYTES`` (25 MiB) bounds disk-spooling
      during endpoint streaming. Because Starlette processes multipart form data
      prior to handler execution, upstream ingress infrastructure (e.g., Nginx
      ``client_max_body_size 25M``, Traefik, or AWS ALB) should enforce request
      body limits at the network edge in production.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool
import pymupdf
from dotenv import load_dotenv

# Automatically load environment variables from backend/.env or root .env
_backend_env = Path(__file__).resolve().parent.parent.parent / ".env"
if _backend_env.exists():
    load_dotenv(dotenv_path=_backend_env)
_root_env = Path(__file__).resolve().parent.parent.parent.parent / ".env"
if _root_env.exists():
    load_dotenv(dotenv_path=_root_env)

from app.api.schemas import HealthResponse
from app.ingestion.security_gate import sanitize_filename
from app.llm.config import MultiLLMSettings
from app.llm.enums import ProviderType
from app.llm.models import ProviderHealth
from app.llm.providers.factory import ProviderFactory
from app.llm.registry import ModelRegistry
from app.llm.schemas import ModelsStatusResponse
from app.models.domain import CanonicalTable, DocumentEvaluationReport
from app.pipeline import run_phase1_pipeline

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

MAX_UPLOAD_BYTES = 52_428_800  # 50 MiB
CHUNK_SIZE = 65_536  # 64 KiB

# ── Application Instance ────────────────────────────────────────────────────

app = FastAPI(
    title="INCUXAI API",
    version="1.0.0",
    docs_url="/docs",
)

# ── CORS Middleware ──────────────────────────────────────────────────────────

import os

_env_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
_allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
] + _env_origins

# Allow all Vercel deployments (*.vercel.app) by default
_allow_origin_regex = os.getenv("CORS_ORIGIN_REGEX", r"^https://.*\.vercel\.app$")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=_allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _sanitize_attachment_filename(table_id: str, extension: str) -> str:
    """Sanitize ``table_id`` for safe inclusion in ``Content-Disposition`` headers.

    Prevents quote breakout, CRLF injection (HTTP response splitting),
    path traversal, and control characters from corrupting response headers.
    """
    safe_id = re.sub(r'[\x00-\x1f\x7f"\\/]', "", table_id).strip()
    if not safe_id:
        safe_id = "table"
    return f"{safe_id}.{extension}"


# ── Health Endpoint ──────────────────────────────────────────────────────────


@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Return backend health status.

    Always returns 200 OK when the server is running.
    """
    return HealthResponse()


# ── Models Status Endpoint ──────────────────────────────────────────────────


@app.get("/api/v1/models/status", response_model=ModelsStatusResponse)
async def get_models_status() -> ModelsStatusResponse:
    """Return declarative registry status and verification states for all candidates.

    Design Invariants:
        - Fast and read-only: does not trigger slow network calls or reachability probes.
        - Secrets safety: sensitive provider API keys and credentials are never exposed.
        - Operational truth: unverified model IDs, missing credentials, or unprobed
          capabilities remain strictly UNVERIFIED or False.
    """
    settings = MultiLLMSettings()
    registry = ModelRegistry(settings=settings)
    models = registry.list_candidates()

    providers_health: dict[str, ProviderHealth] = {}
    for p_type in ProviderType:
        adapter = ProviderFactory.get_adapter(p_type, settings=settings)
        health = await adapter.health_check()
        providers_health[p_type.value] = health

    return ModelsStatusResponse(
        models=models,
        providers=providers_health,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


# ── Extraction Endpoint ─────────────────────────────────────────────────────


@app.post("/api/v1/extract", response_model=DocumentEvaluationReport)
async def extract_document(
    file: UploadFile = File(...),
) -> DocumentEvaluationReport:
    """Upload a PDF and run the Phase 1 extraction pipeline.

    Upload lifecycle:
        1. Sanitize the filename.
        2. Stream the upload to a unique temp file with 25 MiB ceiling.
        3. Close the file descriptor (Windows locking safety).
        4. Offload synchronous ``run_phase1_pipeline()`` to a threadpool.
        5. Unconditionally unlink the temp file in ``finally``.

    Returns
    -------
    DocumentEvaluationReport
        On operational errors (corrupt/encrypted PDF, etc.) the pipeline
        returns ``execution_state=FAILED`` inside a normal 200 response
        rather than raising an HTTP error.
    """
    safe_name = sanitize_filename(file.filename or "upload.pdf")
    lower_name = safe_name.lower()
    is_image = any(lower_name.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".webp", ".tiff", ".bmp"))

    temp_dir = Path(tempfile.gettempdir()) / "docustruct_uploads"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"{uuid.uuid4()}_{safe_name}"
    pdf_temp_path: Optional[Path] = None

    try:
        # Stream upload to disk with 25 MiB ceiling
        total_bytes = 0
        with open(temp_path, "wb") as out_f:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > MAX_UPLOAD_BYTES:
                    # Close and clean up before raising
                    out_f.close()
                    if temp_path.exists():
                        temp_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail="File size exceeds 50 MiB limit.",
                    )
                out_f.write(chunk)
        # File descriptor is now closed — safe for PyMuPDF / pdfplumber on Windows

        pipeline_input_path = temp_path
        is_image_file = is_image
        if not is_image_file and temp_path.exists() and temp_path.stat().st_size >= 4:
            with open(temp_path, "rb") as probe_f:
                magic = probe_f.read(12)
            if (
                magic.startswith(b"\x89PNG")
                or magic.startswith(b"\xff\xd8\xff")
                or magic.startswith(b"BM")
                or magic.startswith(b"II*\x00")
                or magic.startswith(b"MM\x00*")
                or (len(magic) >= 12 and magic.startswith(b"RIFF") and magic[8:12] == b"WEBP")
            ):
                is_image_file = True

        if is_image_file:
            # Convert raster image to single-page PDF via PyMuPDF for universal ingestion
            img_doc = pymupdf.open(str(temp_path))
            pdf_bytes = img_doc.convert_to_pdf()
            img_doc.close()

            pdf_temp_path = temp_dir / f"{uuid.uuid4()}_{Path(safe_name).stem}.pdf"
            with open(pdf_temp_path, "wb") as pf:
                pf.write(pdf_bytes)
            pipeline_input_path = pdf_temp_path

        return await run_in_threadpool(
            run_phase1_pipeline,
            file_path=pipeline_input_path,
            original_filename=safe_name,
        )
    finally:
        # Guarantee cleanup on all paths (success, pipeline error, etc.)
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        if pdf_temp_path is not None and pdf_temp_path.exists():
            pdf_temp_path.unlink(missing_ok=True)


# ── Server-Side Export Endpoints (Fallback) ─────────────────────────────────


@app.post("/api/v1/export/csv")
async def export_csv(table: CanonicalTable) -> StreamingResponse:
    """Convert a ``CanonicalTable`` to RFC 4180 CSV and stream it back.

    Primary export is client-side per DECISION-009.  This endpoint exists
    as a server-side fallback for edge cases.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer, quoting=csv.QUOTE_ALL)

    # Write headers
    writer.writerow(table.normalized_headers or table.original_headers)

    # Write data rows
    for row in table.rows:
        writer.writerow([cell.accepted_value for cell in row])

    content = buffer.getvalue()
    safe_filename = _sanitize_attachment_filename(table.table_id, "csv")
    return StreamingResponse(
        iter([content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}"',
        },
    )


@app.post("/api/v1/export/json")
async def export_json(table: CanonicalTable) -> StreamingResponse:
    """Convert a ``CanonicalTable`` to structured JSON and stream it back.

    Response format:
        {
            "table_id": "<id>",
            "headers": ["ColA", "ColB", ...],
            "rows": [
                ["val1", "val2", ...],
                ...
            ]
        }

    Rows are represented as an array of cell value arrays rather than an
    object/dict to prevent silent data loss when column headers are
    duplicated or empty.

    Primary export is client-side per DECISION-009.
    """
    headers = table.normalized_headers or table.original_headers
    rows_data = [
        [cell.accepted_value for cell in row]
        for row in table.rows
    ]

    payload = {
        "table_id": table.table_id,
        "headers": headers,
        "rows": rows_data,
    }

    content = json.dumps(payload, indent=2, ensure_ascii=False)
    safe_filename = _sanitize_attachment_filename(table.table_id, "json")
    return StreamingResponse(
        iter([content]),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}"',
        },
    )


@app.post("/api/v1/export/zip")
async def export_zip(tables: list[CanonicalTable]) -> StreamingResponse:
    """Convert multiple ``CanonicalTable``s to individual RFC 4180 CSV files
    bundled into a single ZIP archive.

    Each CSV file contains UTF-8 BOM so Microsoft Excel immediately opens it
    with correct character encoding and formatting.
    """
    import zipfile

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for idx, table in enumerate(tables):
            csv_buf = io.StringIO()
            # UTF-8 BOM for direct Microsoft Excel compatibility
            csv_buf.write("\ufeff")
            writer = csv.writer(csv_buf, quoting=csv.QUOTE_ALL)
            writer.writerow(table.normalized_headers or table.original_headers)
            for row in table.rows:
                writer.writerow([cell.accepted_value for cell in row])

            table_label = table.title or f"Table_{idx + 1}"
            safe_filename = _sanitize_attachment_filename(f"Table_{idx + 1}_{table_label}", "csv")
            zf.writestr(safe_filename, csv_buf.getvalue())

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="DocuStruct_All_Tables.zip"',
        },
    )
