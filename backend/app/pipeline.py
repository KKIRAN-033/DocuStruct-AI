"""DocuStruct AI — End-to-End Pipeline Coordinator

Coordinates the 19-step Phase 1 pipeline execution sequence from PDF ingestion
through security validation, page routing, table extraction, normalization,
multipage stitching, arithmetic validation, and document-level quality gate evaluation.

Design Invariants (MASTER_DIRECTIVE.md Section 18):
    - Windows file handles (fitz/PyMuPDF and pdfplumber) are guaranteed closed in finally blocks.
    - User's original input file is never deleted.
    - Temporary job workspace is created and always cleaned up in finally blocks.
    - Operational errors return controlled failure reports (execution_state=FAILED).
    - Python heap usage is recorded via tracemalloc when enabled.
"""

from __future__ import annotations

import logging
from pathlib import Path
import tracemalloc
from typing import Any, Optional
import uuid

import pdfplumber

from app.config.calibration import CalibrationConfig
from app.config.settings import AppSettings
from app.extraction.digital_extractor import extract_tables_from_page
from app.extraction.table_reconstructor import reconstruct_multipage_tables
from app.ingestion.page_router import route_document_pages
from app.ingestion.security_gate import (
    CorruptPDFError,
    EncryptedPDFError,
    FileNotFoundValidationError,
    FileSizeExceededError,
    InvalidFileTypeError,
    InvalidPDFSignatureError,
    PageCountExceededError,
    PathTraversalError,
    SecurityGateError,
    cleanup_job_workspace,
    create_job_workspace,
    inspect_and_validate_pdf,
    sanitize_filename,
)
from app.models.domain import (
    CanonicalTable,
    CorrectionRecord,
    DocumentEvaluationReport,
    PageExtractionResult,
    PageProfile,
    StitchAuditEvent,
    ValidationIssue,
)
from app.models.state import (
    JobExecutionState,
    PageProcessingStatus,
    PageType,
    VerificationStatus,
)
from app.verification.quality_gate import (
    MANDATORY_VERBATIM_DISCLAIMER,
    REASON_EXECUTION_FAILED,
    evaluate_document_quality,
)

logger = logging.getLogger(__name__)


def run_phase1_pipeline(
    file_path: Path,
    original_filename: Optional[str] = None,
    settings: Optional[AppSettings] = None,
    calibration: Optional[CalibrationConfig] = None,
) -> DocumentEvaluationReport:
    """Execute the end-to-end Phase 1 document processing and verification pipeline.

    Parameters
    ----------
    file_path : Path
        Path to the target input PDF file.
    original_filename : str, optional
        Original filename if different from file_path.name.
    settings : AppSettings, optional
        Configuration settings. Defaults loaded if None.
    calibration : CalibrationConfig, optional
        Threshold configuration. Defaults loaded if None.

    Returns
    -------
    DocumentEvaluationReport
        Complete evaluation report containing extracted canonical tables, page profiles,
        stitching events, arithmetic validation outcomes, and quality gate verification status.
    """
    job_id = str(uuid.uuid4())
    raw_name = original_filename or (file_path.name if isinstance(file_path, Path) else str(file_path))
    source_filename = sanitize_filename(raw_name)

    resolved_settings = settings if settings is not None else AppSettings()
    resolved_calibration = calibration if calibration is not None else CalibrationConfig.load_defaults()

    tracing_active = False
    if resolved_settings.enable_memory_measurement:
        if not tracemalloc.is_tracing():
            tracemalloc.start()
            tracing_active = True

    workspace_dir: Optional[Path] = None

    try:
        # Step 3: Validate input through security gate
        try:
            inspect_and_validate_pdf(file_path, resolved_settings)
        except FileNotFoundValidationError:
            return _build_controlled_failure(job_id, source_filename, ["FILE_NOT_FOUND"], tracing_active)
        except FileSizeExceededError:
            return _build_controlled_failure(job_id, source_filename, ["FILE_SIZE_EXCEEDED"], tracing_active)
        except InvalidPDFSignatureError:
            return _build_controlled_failure(job_id, source_filename, ["INVALID_PDF_SIGNATURE"], tracing_active)
        except InvalidFileTypeError:
            return _build_controlled_failure(job_id, source_filename, ["INVALID_FILE_TYPE"], tracing_active)
        except EncryptedPDFError:
            return _build_controlled_failure(job_id, source_filename, ["ENCRYPTED_PDF"], tracing_active)
        except CorruptPDFError:
            return _build_controlled_failure(job_id, source_filename, ["CORRUPT_PDF"], tracing_active)
        except PageCountExceededError:
            return _build_controlled_failure(job_id, source_filename, ["PAGE_COUNT_EXCEEDED"], tracing_active)
        except PathTraversalError:
            return _build_controlled_failure(job_id, source_filename, ["PATH_TRAVERSAL_DETECTED"], tracing_active)
        except SecurityGateError as sg_err:
            return _build_controlled_failure(job_id, source_filename, ["SECURITY_GATE_FAILED"], tracing_active)
        except (FileNotFoundError, ValueError):
            return _build_controlled_failure(job_id, source_filename, ["FILE_NOT_FOUND"], tracing_active)

        # Step 4: Create isolated job workspace
        workspace_dir = create_job_workspace(
            job_id=job_id,
            base_dir=resolved_settings.workspace_root,
            settings=resolved_settings,
        )

        # Step 5 & 6: Route all pages using safe sequential resource discipline
        page_profiles = route_document_pages(file_path, resolved_calibration)

        # Step 7 & 8: Extract supported native digital tables page by page
        pdf_handle: Optional[pdfplumber.PDF] = None
        page_results: list[PageExtractionResult] = []
        extracted_tables: list[CanonicalTable] = []

        try:
            pdf_handle = pdfplumber.open(str(file_path.resolve()))
            for profile in page_profiles:
                p_num = profile.page_number
                p_tables: list[CanonicalTable] = []

                if profile.page_type in (PageType.DIGITAL, PageType.HYBRID):
                    if p_num <= len(pdf_handle.pages):
                        plumber_page = pdf_handle.pages[p_num - 1]
                        p_tables = extract_tables_from_page(plumber_page, p_num)

                page_results.append(
                    PageExtractionResult(
                        page_number=p_num,
                        page_profile=profile,
                        tables=p_tables,
                        issues=[],
                        deferred_regions_count=profile.deferred_regions_count,
                        diagnostics={},
                    )
                )
                extracted_tables.extend(p_tables)
        finally:
            if pdf_handle is not None:
                pdf_handle.close()

        # Step 9 & 10: Multipage table reconstruction and stitching
        canonical_tables = reconstruct_multipage_tables(extracted_tables, resolved_calibration)

        # Step 11: Run structural checks
        for table in canonical_tables:
            is_valid_structure = (
                len(table.rows) > 0
                and len(table.normalized_headers) > 0
                and all(len(r) == len(table.normalized_headers) for r in table.rows)
            )
            table.structural_checks_passed = is_valid_structure

        # Collect stitch events from canonical tables
        stitch_events: list[StitchAuditEvent] = []
        for table in canonical_tables:
            stitch_events.extend(table.stitch_events)

        # Step 12, 13, 14, 15: Assemble report and run document quality gate
        report = DocumentEvaluationReport(
            job_id=job_id,
            source_filename=source_filename,
            execution_state=JobExecutionState.COMPLETED,
            verification_status=VerificationStatus.REVIEW_REQUIRED,
            status_reason_codes=[],
            limitation_disclaimers=[],
            page_profiles=page_profiles,
            page_results=page_results,
            canonical_tables=canonical_tables,
            stitch_events=stitch_events,
            validation_issues=[],
            correction_records=[],
            peak_python_heap_bytes=None,
        )

        # Evaluate arithmetic consistency and document-level quality gate
        report = evaluate_document_quality(report)

        # Memory measurement
        if resolved_settings.enable_memory_measurement:
            try:
                _, peak = tracemalloc.get_traced_memory()
                report.peak_python_heap_bytes = peak
            except Exception:
                pass

        return report

    except Exception as exc:
        logger.error("Unhandled exception during pipeline execution: %s", exc, exc_info=True)
        return _build_controlled_failure(job_id, source_filename, [REASON_EXECUTION_FAILED], tracing_active)

    finally:
        # Step 17 & 18: Guarantee cleanup of isolated workspace without deleting original file
        if workspace_dir is not None:
            cleanup_job_workspace(workspace_dir, file_path)


def _build_controlled_failure(
    job_id: str,
    source_filename: str,
    reason_codes: list[str],
    tracing_active: bool,
) -> DocumentEvaluationReport:
    """Build a standard DocumentEvaluationReport for operational execution failures."""
    peak_bytes = None
    if tracing_active:
        try:
            _, peak_bytes = tracemalloc.get_traced_memory()
        except Exception:
            pass

    return DocumentEvaluationReport(
        job_id=job_id,
        source_filename=source_filename,
        execution_state=JobExecutionState.FAILED,
        verification_status=VerificationStatus.FAILED,
        status_reason_codes=reason_codes,
        limitation_disclaimers=[MANDATORY_VERBATIM_DISCLAIMER],
        page_profiles=[],
        page_results=[],
        canonical_tables=[],
        stitch_events=[],
        validation_issues=[],
        correction_records=[],
        peak_python_heap_bytes=peak_bytes,
    )
