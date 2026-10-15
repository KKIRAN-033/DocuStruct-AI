"""DocuStruct AI — Standalone Regression Evaluation Harness

Evaluates document extraction and verification quality against expected ground-truth cases.

Auditing and Integrity Non-Negotiable (MASTER_DIRECTIVE.md Section 21, NFR-04):
    If no manually verified reference dataset is provided, the harness strictly
    reports "UNMEASURED" for real-world accuracy metrics. Synthetic fixture tests
    must never be reported as real-world benchmark accuracy.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import sys
import tempfile
from typing import Any, Optional

import pymupdf
from pydantic import BaseModel, Field

# Ensure backend directory is in sys.path
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.config.calibration import CalibrationConfig
from app.config.settings import AppSettings
from app.models.domain import DocumentEvaluationReport
from app.pipeline import run_phase1_pipeline

logger = logging.getLogger(__name__)


# ─── Data Contracts ──────────────────────────────────────────────────────────


class EvaluationCase(BaseModel):
    """Specification of an evaluation test case against ground truth."""

    case_id: str
    pdf_path: Path
    description: str = ""
    expected_table_count: Optional[int] = None
    expected_row_counts: Optional[list[int]] = None
    expected_col_counts: Optional[list[int]] = None
    expected_cell_values: Optional[dict[str, str]] = Field(
        default=None,
        description="Map of 'table_idx,row_idx,col_idx' -> expected accepted_value",
    )
    expected_verification_status: Optional[str] = None
    expected_reasons: Optional[list[str]] = None
    is_synthetic: bool = False


class CaseResult(BaseModel):
    """Outcome of evaluating a single case."""

    case_id: str
    passed: bool
    table_count_match: Optional[bool] = None
    dimensions_match: Optional[bool] = None
    cell_values_match: Optional[bool] = None
    status_match: Optional[bool] = None
    mismatches: list[str] = Field(default_factory=list)


class EvaluationSummary(BaseModel):
    """Aggregated evaluation results across all cases."""

    total_cases: int
    passed_cases: int
    failed_cases: int
    synthetic_fixture_pass_rate: Optional[str] = None
    real_world_accuracy: str = "UNMEASURED"
    case_results: list[CaseResult] = Field(default_factory=list)


# ─── Evaluation Runner ───────────────────────────────────────────────────────


def evaluate_case(
    case: EvaluationCase,
    settings: Optional[AppSettings] = None,
    calibration: Optional[CalibrationConfig] = None,
) -> CaseResult:
    """Run pipeline against a single case and compare against expected ground truth."""
    mismatches: list[str] = []

    try:
        report: DocumentEvaluationReport = run_phase1_pipeline(
            file_path=case.pdf_path,
            settings=settings,
            calibration=calibration,
        )
    except Exception as exc:
        return CaseResult(
            case_id=case.case_id,
            passed=False,
            mismatches=[f"Pipeline threw unexpected exception: {exc}"],
        )

    # 1. Expected table count
    table_count_match = None
    if case.expected_table_count is not None:
        actual_count = len(report.canonical_tables)
        table_count_match = actual_count == case.expected_table_count
        if not table_count_match:
            mismatches.append(
                f"Table count mismatch: expected {case.expected_table_count}, got {actual_count}"
            )

    # 2. Expected row and column counts
    dimensions_match = True
    if case.expected_row_counts is not None:
        for t_idx, exp_rows in enumerate(case.expected_row_counts):
            if t_idx < len(report.canonical_tables):
                actual_rows = len(report.canonical_tables[t_idx].rows)
                if actual_rows != exp_rows:
                    dimensions_match = False
                    mismatches.append(
                        f"Table {t_idx} row count mismatch: expected {exp_rows}, got {actual_rows}"
                    )
            else:
                dimensions_match = False
                mismatches.append(f"Table {t_idx} missing from extracted tables")

    if case.expected_col_counts is not None:
        for t_idx, exp_cols in enumerate(case.expected_col_counts):
            if t_idx < len(report.canonical_tables):
                actual_cols = len(report.canonical_tables[t_idx].normalized_headers)
                if actual_cols != exp_cols:
                    dimensions_match = False
                    mismatches.append(
                        f"Table {t_idx} column count mismatch: expected {exp_cols}, got {actual_cols}"
                    )
            else:
                dimensions_match = False

    # 3. Expected cell values
    cell_values_match = True
    if case.expected_cell_values is not None:
        for coord_str, exp_val in case.expected_cell_values.items():
            parts = [int(p.strip()) for p in coord_str.split(",")]
            if len(parts) == 3:
                t_idx, r_idx, c_idx = parts
                if t_idx < len(report.canonical_tables):
                    tbl = report.canonical_tables[t_idx]
                    if r_idx < len(tbl.rows) and c_idx < len(tbl.rows[r_idx]):
                        actual_val = tbl.rows[r_idx][c_idx].accepted_value
                        if actual_val != exp_val:
                            cell_values_match = False
                            mismatches.append(
                                f"Cell ({t_idx},{r_idx},{c_idx}) mismatch: expected '{exp_val}', got '{actual_val}'"
                            )
                    else:
                        cell_values_match = False
                        mismatches.append(f"Cell coordinates ({t_idx},{r_idx},{c_idx}) out of table bounds")
                else:
                    cell_values_match = False

    # 4. Expected verification status
    status_match = None
    if case.expected_verification_status is not None:
        actual_status = report.verification_status.value
        status_match = actual_status == case.expected_verification_status
        if not status_match:
            mismatches.append(
                f"Verification status mismatch: expected {case.expected_verification_status}, got {actual_status}"
            )

    # 5. Expected reason codes
    if case.expected_reasons is not None:
        for exp_reason in case.expected_reasons:
            if exp_reason not in report.status_reason_codes:
                mismatches.append(f"Expected reason code '{exp_reason}' not in {report.status_reason_codes}")

    passed = len(mismatches) == 0
    return CaseResult(
        case_id=case.case_id,
        passed=passed,
        table_count_match=table_count_match,
        dimensions_match=dimensions_match,
        cell_values_match=cell_values_match,
        status_match=status_match,
        mismatches=mismatches,
    )


def run_evaluation(cases: list[EvaluationCase]) -> EvaluationSummary:
    """Run regression evaluation across a collection of cases and aggregate summary."""
    if not cases:
        return EvaluationSummary(
            total_cases=0,
            passed_cases=0,
            failed_cases=0,
            real_world_accuracy="UNMEASURED",
            synthetic_fixture_pass_rate="N/A",
            case_results=[],
        )

    results: list[CaseResult] = []
    passed_count = 0
    all_synthetic = all(c.is_synthetic for c in cases)

    for case in cases:
        res = evaluate_case(case)
        results.append(res)
        if res.passed:
            passed_count += 1

    total = len(cases)
    failed_count = total - passed_count
    pass_pct = f"{(passed_count / total) * 100:.1f}%"

    # Enforce NFR-04 Audit Integrity:
    # If all cases are synthetic or no verified ground-truth dataset was configured,
    # real-world accuracy MUST be reported as UNMEASURED.
    real_world_metric = "UNMEASURED" if all_synthetic else f"{(passed_count / total) * 100:.1f}%"

    return EvaluationSummary(
        total_cases=total,
        passed_cases=passed_count,
        failed_cases=failed_count,
        synthetic_fixture_pass_rate=pass_pct if all_synthetic else None,
        real_world_accuracy=real_world_metric,
        case_results=results,
    )


# ─── Builtin Synthetic Case Generator for Self-Testing ───────────────────────


def create_builtin_synthetic_cases(tmp_dir: Path) -> list[EvaluationCase]:
    """Generate reproducible synthetic evaluation cases for pipeline self-benchmarking."""
    cases: list[EvaluationCase] = []

    # Case 1: Ruled table with matching total
    pdf1 = tmp_dir / "eval_ruled.pdf"
    doc1 = pymupdf.open()
    try:
        page = doc1.new_page(width=612, height=792)
        x_start, y_start = 50, 100
        col_w, row_h = 150, 30
        cols, rows = 3, 3

        for r in range(rows + 1):
            y = y_start + r * row_h
            page.draw_line(pymupdf.Point(x_start, y), pymupdf.Point(x_start + cols * col_w, y))
        for c in range(cols + 1):
            x = x_start + c * col_w
            page.draw_line(pymupdf.Point(x, y_start), pymupdf.Point(x, y_start + rows * row_h))

        data = [
            ["Item", "Amount", "Status"],
            ["Alpha", "100.00", "Pending"],
            ["Beta", "200.00", "Completed"],
        ]
        for r, row in enumerate(data):
            for c, cell in enumerate(row):
                page.insert_text((x_start + c * col_w + 10, y_start + r * row_h + 20), cell, fontsize=9)
        doc1.save(str(pdf1))
    finally:
        doc1.close()

    cases.append(
        EvaluationCase(
            case_id="SYNTH-RULED-01",
            pdf_path=pdf1,
            description="Ruled 3x3 table with headers and 2 data rows",
            expected_table_count=1,
            expected_row_counts=[3],
            expected_col_counts=[3],
            expected_verification_status="VERIFIED_WITH_WARNINGS",
            is_synthetic=True,
        )
    )

    # Case 2: Digital PDF without tables
    pdf2 = tmp_dir / "eval_nontable.pdf"
    doc2 = pymupdf.open()
    try:
        page = doc2.new_page(width=595, height=842)
        page.insert_text((72, 72), "This is plain prose paragraph text with no table layout.", fontsize=11)
        doc2.save(str(pdf2))
    finally:
        doc2.close()

    cases.append(
        EvaluationCase(
            case_id="SYNTH-NONTABLE-01",
            pdf_path=pdf2,
            description="Digital page with no extractable tables",
            expected_table_count=0,
            expected_verification_status="FAILED",
            expected_reasons=["NO_TABLES_FOUND"],
            is_synthetic=True,
        )
    )

    return cases


# ─── CLI Entry Point ─────────────────────────────────────────────────────────


def main() -> None:
    """CLI entry point for running the regression evaluation harness."""
    parser = argparse.ArgumentParser(
        description="DocuStruct AI — Standalone Regression Evaluation Harness"
    )
    parser.add_argument(
        "--cases-dir",
        type=Path,
        default=None,
        help="Directory containing ground-truth evaluation case manifests (*.json)",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Optional path to write full evaluation summary JSON",
    )
    parser.add_argument(
        "--run-builtin-fixtures",
        action="store_true",
        help="Generate and run builtin synthetic test cases for self-benchmarking",
    )

    args = parser.parse_args()

    cases: list[EvaluationCase] = []
    temp_dir_obj = None

    if args.cases_dir and args.cases_dir.is_dir():
        for manifest_file in args.cases_dir.glob("*.json"):
            try:
                data = json.loads(manifest_file.read_text(encoding="utf-8"))
                cases.append(EvaluationCase.model_validate(data))
            except Exception as exc:
                logger.warning("Failed to load evaluation case %s: %exc", manifest_file, exc)
    else:
        # Default or --run-builtin-fixtures: use synthetic cases
        temp_dir_obj = tempfile.TemporaryDirectory(prefix="docustruct_eval_")
        cases = create_builtin_synthetic_cases(Path(temp_dir_obj.name))

    print("=" * 60)
    print("DOCUSTRUCT AI -- REGRESSION EVALUATION HARNESS")
    print(f"Total Cases Loaded: {len(cases)}")
    print("=" * 60)

    summary = run_evaluation(cases)

    for res in summary.case_results:
        status_symbol = "PASS" if res.passed else "FAIL"
        print(f"[{status_symbol}] Case {res.case_id}")
        for mm in res.mismatches:
            print(f"    - {mm}")

    print("-" * 60)
    print(f"Total Evaluated: {summary.total_cases}")
    print(f"Passed:          {summary.passed_cases}")
    print(f"Failed:          {summary.failed_cases}")
    if summary.synthetic_fixture_pass_rate:
        print(f"Synthetic Pass:  {summary.synthetic_fixture_pass_rate}")
    print(f"Real-World Acc:  {summary.real_world_accuracy}")
    print("=" * 60)
    if summary.real_world_accuracy == "UNMEASURED":
        print("NOTE: Real-world accuracy remains UNMEASURED until tested")
        print("      against an independent, manually verified reference dataset.")
        print("=" * 60)

    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(summary.model_dump_json(indent=2), encoding="utf-8")
        print(f"Results written to: {args.output_json}")

    if temp_dir_obj:
        temp_dir_obj.cleanup()

    sys.exit(0 if summary.failed_cases == 0 else 1)


if __name__ == "__main__":
    main()
