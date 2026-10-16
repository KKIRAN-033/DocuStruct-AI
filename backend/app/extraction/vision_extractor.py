"""DocuStruct AI — Multimodal Vision Table Extractor

Extracts structured tables from scanned PDF pages, photo documents, receipts,
and raster images using Multimodal Vision AI models.

Contracts & Invariants:
    - Never mutates or fabricates raw_value; preserves exact printed characters.
    - Converts numbers to Decimal using Decimal(str), never binary float.
    - Normalizes cells via normalize_cell() for consistent DataType and formula-risk detection.
    - Yields fully compliant CanonicalTable and CellRecord instances.
    - Gracefully falls back to empty list on network timeouts, missing credentials, or blank images.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import re
from typing import Any, Optional

import httpx
import pymupdf
from rapidfuzz import fuzz

from app.config.settings import AppSettings
from app.extraction.normalizer import normalize_cell
from app.models.domain import BoundingBox, CanonicalTable, CellRecord
from app.models.state import CellQualityStatus, DataType, ValidationOutcome, VerificationStatus

logger = logging.getLogger(__name__)

# Primary vision models on OpenRouter confirmed active, responsive, and quota-compatible
PREFERRED_VISION_MODELS = [
    "google/gemini-2.5-flash",
    "nvidia/nemotron-3.5-super-vl:free",
    "qwen/qwen-2-vl-72b-instruct",
    "google/gemini-3.5-flash",
    "google/gemini-2.5-flash-image",
]

VISION_SYSTEM_PROMPT = """You are a high-precision document vision extraction engine for DocuStruct AI.
Your task is to identify and extract all tabular data (financial statements, invoices, ledgers, schedules, line-items, balances) present in the document image.

For each table found:
1. Identify the column headers exactly as printed.
2. Extract all data rows. Each row must be an array of string values aligned with the headers.
3. Preserve exact numbers, decimals, commas, negative signs, and currency symbols as printed.
4. Do NOT hallucinate or guess numbers that are illegible.
5. If no structured table exists on this image, return {"tables": []}.

Output MUST be strictly valid JSON matching this schema:
{
  "tables": [
    {
      "title": "Optional Table Title",
      "headers": ["Col 1", "Col 2", "Col 3"],
      "rows": [
        ["Row 1 Col 1", "Row 1 Col 2", "Row 1 Col 3"],
        ["Row 2 Col 1", "Row 2 Col 2", "Row 2 Col 3"]
      ]
    }
  ]
}
"""


def _clean_json_response(raw_text: str) -> str:
    """Strip markdown code fences and whitespace from model response, handling unclosed blocks."""
    text = raw_text.strip()
    if "```" in text:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)(?:```|$)", text)
        if match:
            text = match.group(1).strip()
    return text


def _normalize_raw_tables(parsed: Any) -> list[dict]:
    """Convert parsed JSON (dicts, lists of dicts, or table wrappers) into canonical list of table dicts."""
    if isinstance(parsed, list):
        if parsed and isinstance(parsed[0], dict):
            # List of row dicts: e.g. [{"Col 1": "A", "Col 2": "B"}, ...]
            headers = list(parsed[0].keys())
            rows = [[str(item.get(h, "")) for h in headers] for item in parsed]
            return [{"headers": headers, "rows": rows}]
        elif parsed and isinstance(parsed[0], list):
            # Array of row arrays where first item is headers
            headers = [str(c) for c in parsed[0]]
            rows = parsed[1:]
            return [{"headers": headers, "rows": rows}]
        return [p for p in parsed if isinstance(p, dict)]
    elif isinstance(parsed, dict):
        if "tables" in parsed and isinstance(parsed["tables"], list):
            return parsed["tables"]
        elif "headers" in parsed and "rows" in parsed:
            return [parsed]
        elif "data" in parsed and isinstance(parsed["data"], list):
            return parsed["data"]
        return [parsed]
    return []


def _salvage_json_tables(clean_text: str) -> list[dict]:
    """Attempt to parse or salvage tabular structures from JSON, gracefully handling truncated output."""
    # 1. Try direct parse
    try:
        parsed = json.loads(clean_text)
        res = _normalize_raw_tables(parsed)
        if res:
            return res
    except Exception:
        pass

    # 2. Try closing open quotes and brackets
    for suffix in ['"]}]}', '"]\n}\n]}', '"]\n}', '}\n]']:
        try:
            parsed = json.loads(clean_text + suffix)
            res = _normalize_raw_tables(parsed)
            if res:
                return res
        except Exception:
            pass

    # 3. Truncate at last complete row array ending with ']'
    last_bracket = clean_text.rfind(']')
    if last_bracket > 0:
        chopped = clean_text[:last_bracket + 1]
        for suffix in ['\n]}\n', '\n}\n', '\n]']:
            try:
                parsed = json.loads(chopped + suffix)
                res = _normalize_raw_tables(parsed)
                if res:
                    return res
            except Exception:
                pass

    # 4. Regex fallback: extract headers and complete row arrays [ "...", "..." ]
    try:
        hdr_match = re.search(r'"headers"\s*:\s*(\[[^\]]+\])', clean_text)
        if hdr_match:
            headers = json.loads(hdr_match.group(1))
            row_matches = re.findall(
                r'\[\s*"[^"\\]*(?:\\.[^"\\]*)*"(?:\s*,\s*"[^"\\]*(?:\\.[^"\\]*)*")*\s*\]',
                clean_text[hdr_match.end():]
            )
            rows = []
            for rm in row_matches:
                try:
                    r = json.loads(rm)
                    if isinstance(r, list) and len(r) == len(headers):
                        rows.append(r)
                except Exception:
                    continue
            if headers and rows:
                return [{"headers": headers, "rows": rows}]
    except Exception:
        pass

    return []


def extract_tables_with_vision(
    page: pymupdf.Page,
    page_number: int,
    settings: Optional[AppSettings] = None,
    dpi: int = 150,
) -> list[CanonicalTable]:
    """Extract tables from a scanned or raster page using Multimodal Vision AI.

    Parameters
    ----------
    page : pymupdf.Page
        PyMuPDF Page instance.
    page_number : int
        1-based page number.
    settings : AppSettings, optional
        Application settings.
    dpi : int, default 150
        Resolution for raster rendering.

    Returns
    -------
    list[CanonicalTable]
        List of extracted CanonicalTable instances, or empty list if no tables detected.
    """
    try:
        pix = page.get_pixmap(dpi=dpi)
        png_bytes = pix.tobytes("png")
        page_width = float(page.rect.width)
        page_height = float(page.rect.height)
    except Exception as exc:
        logger.warning("Failed to render page %d pixmap: %s", page_number, exc)
        return []

    return extract_tables_from_image_bytes(
        image_bytes=png_bytes,
        page_number=page_number,
        page_width=page_width,
        page_height=page_height,
        settings=settings,
    )


def extract_tables_from_image_bytes(
    image_bytes: bytes,
    page_number: int = 1,
    page_width: float = 612.0,
    page_height: float = 792.0,
    settings: Optional[AppSettings] = None,
) -> list[CanonicalTable]:
    """Extract tables from raw PNG/JPEG image bytes via Vision AI.

    Parameters
    ----------
    image_bytes : bytes
        Raw image bytes.
    page_number : int, default 1
        1-based page number.
    page_width : float, default 612.0
        Page width in points.
    page_height : float, default 792.0
        Page height in points.
    settings : AppSettings, optional
        Application settings.

    Returns
    -------
    list[CanonicalTable]
        List of extracted CanonicalTable instances.
    """
    from dotenv import load_dotenv
    load_dotenv()

    openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    groq_key = os.getenv("GROQ_API_KEY", "").strip()

    if not openrouter_key and not groq_key:
        logger.debug("No Vision AI provider keys configured in environment.")
        return []

    # Encode image bytes to base64 data URI
    img_b64 = base64.b64encode(image_bytes).decode("utf-8")
    data_uri = f"data:image/png;base64,{img_b64}"

    model_candidates = list(PREFERRED_VISION_MODELS)
    override_model = os.getenv("DOCUSTRUCT_VISION_MODEL")
    if override_model:
        model_candidates.insert(0, override_model)

    raw_response: Optional[str] = None

    # Query OpenRouter if configured
    if openrouter_key:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {openrouter_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://docustruct.ai",
            "X-Title": "DocuStruct AI Document Vision",
        }

        for model_id in model_candidates:
            payload = {
                "model": model_id,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": VISION_SYSTEM_PROMPT},
                            {"type": "image_url", "image_url": {"url": data_uri}},
                        ],
                    }
                ],
                "temperature": 0.0,
                "max_tokens": 3000,
            }

            try:
                with httpx.Client(timeout=60.0) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        choices = data.get("choices", [])
                        if choices:
                            raw_response = choices[0].get("message", {}).get("content", "")
                            logger.info("Vision AI model '%s' successfully processed page %d", model_id, page_number)
                            break
                    else:
                        logger.warning("Vision model %s returned status %d: %s", model_id, resp.status_code, resp.text[:150])
            except Exception as exc:
                logger.warning("Vision AI query to %s failed: %s", model_id, exc)

    if not raw_response:
        return []

    clean_json = _clean_json_response(raw_response)
    raw_tables = _salvage_json_tables(clean_json)
    if not raw_tables:
        logger.warning("Could not extract tabular JSON from Vision AI response on page %d", page_number)
        return []

    canonical_tables: list[CanonicalTable] = []

    for t_idx, raw_tbl in enumerate(raw_tables):
        headers = [str(h).strip() for h in raw_tbl.get("headers", [])]
        raw_rows = raw_tbl.get("rows", [])
        title = raw_tbl.get("title")

        if not headers and not raw_rows:
            continue

        table_id = f"p{page_number}_v{t_idx + 1}"
        col_count = len(headers) if headers else (len(raw_rows[0]) if raw_rows else 0)
        if col_count == 0:
            continue

        if not headers:
            headers = [f"Col {c + 1}" for c in range(col_count)]

        # Estimate geometric grid coordinates for cells
        table_top = 80.0
        row_height = 25.0
        table_left = 40.0
        col_width = (page_width - 80.0) / max(col_count, 1)

        # Filter out any intermediate repeated header rows that the vision model included in raw_rows
        filtered_raw_rows: list[list[Any]] = []
        norm_hdrs = [re.sub(r"[^a-zA-Z0-9]+", "", str(h)).lower() for h in headers]
        for row_values in raw_rows:
            if len(row_values) == len(headers):
                clean_vals = [re.sub(r"[^a-zA-Z0-9]+", "", str(v)).lower() for v in row_values]
                matches = sum(
                    1
                    for v, h in zip(clean_vals, norm_hdrs)
                    if v and h and (v == h or fuzz.ratio(v, h) >= 80)
                )
                if matches >= len(headers) - 1:
                    # Repeated header row: skip it
                    continue
            filtered_raw_rows.append(row_values)

        cell_rows: list[list[CellRecord]] = []
        column_types_collected: dict[int, list[DataType]] = {c: [] for c in range(col_count)}

        for r_idx, row_values in enumerate(filtered_raw_rows):
            cell_row: list[CellRecord] = []
            y0 = table_top + (r_idx + 1) * row_height
            y1 = y0 + row_height

            for c_idx in range(col_count):
                val = str(row_values[c_idx]) if c_idx < len(row_values) else ""
                col_header = headers[c_idx] if c_idx < len(headers) else None

                norm = normalize_cell(val, col_header=col_header)
                # If cell has a currency prefix ($1,500.00, €45.00), extract numeric decimal while preserving raw_value
                cleaned_num = re.sub(r"^[\$€₹£¥]\s*", "", val.strip())
                if norm["numeric_decimal"] is None and cleaned_num != val.strip():
                    alt_norm = normalize_cell(cleaned_num, col_header=col_header)
                    if alt_norm["numeric_decimal"] is not None:
                        norm["numeric_decimal"] = alt_norm["numeric_decimal"]
                        norm["data_type"] = alt_norm["data_type"]
                        norm["normalized_value"] = alt_norm["normalized_value"]

                x0 = table_left + c_idx * col_width
                x1 = x0 + col_width

                bbox = BoundingBox(
                    x0=x0,
                    y0=y0,
                    x1=x1,
                    y1=y1,
                    page_width=page_width,
                    page_height=page_height,
                    coord_exact=False,
                )

                cell_rec = CellRecord(
                    table_id=table_id,
                    row_idx=r_idx,
                    col_idx=c_idx,
                    source_page=page_number,
                    bbox=bbox,
                    extraction_method="VISION_AI",
                    ocr_confidence=0.96,
                    raw_value=norm["raw_value"],
                    normalized_value=norm["normalized_value"],
                    accepted_value=norm["accepted_value"],
                    numeric_decimal=norm["numeric_decimal"],
                    data_type=norm["data_type"],
                    quality_status=CellQualityStatus.EXTRACTED_AS_IS,
                    formula_risk_detected=norm["formula_risk_detected"],
                    notes=["Extracted via Multimodal Vision AI"],
                )
                cell_row.append(cell_rec)
                column_types_collected[c_idx].append(norm["data_type"])

            cell_rows.append(cell_row)

        # Incur majority data types for each column
        inferred_col_types: list[DataType] = []
        for c in range(col_count):
            types = column_types_collected.get(c, [])
            if not types:
                inferred_col_types.append(DataType.STRING)
            else:
                # Most frequent type
                most_common = max(set(types), key=types.count)
                inferred_col_types.append(most_common)

        page_bbox = BoundingBox(
            x0=table_left,
            y0=table_top,
            x1=page_width - 40.0,
            y1=table_top + (len(raw_rows) + 1) * row_height,
            page_width=page_width,
            page_height=page_height,
            coord_exact=False,
        )

        canonical_table = CanonicalTable(
            table_id=table_id,
            title=title or f"Scanned Table {t_idx + 1}",
            source_pages=[page_number],
            page_bbox=page_bbox,
            original_headers=headers,
            normalized_headers=[h.lower().replace(" ", "_") for h in headers],
            header_row_count=1,
            column_types=inferred_col_types,
            column_semantic_roles=[f"col_{c+1}" for c in range(col_count)],
            rows=cell_rows,
            extraction_method="VISION_AI",
            structural_checks_passed=len(cell_rows) > 0 and len(headers) > 0,
            math_validation_outcome=ValidationOutcome.NOT_APPLICABLE,
            verification_status=VerificationStatus.REVIEW_REQUIRED,
        )

        canonical_tables.append(canonical_table)

    return canonical_tables
