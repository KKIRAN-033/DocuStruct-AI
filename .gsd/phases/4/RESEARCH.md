# Phase 4 Technical Research: Deterministic Arithmetic Consistency & Document Quality Gate

## 1. Domain Overview & Problem Statement

Phase 4 implements the deterministic arithmetic evaluator and document quality gate in `backend/app/verification/quality_gate.py`, satisfying **REQ-10**, **REQ-11**, and **REQ-13** from `MASTER_DIRECTIVE.md` Sections 16 and 17.

In financial statement extraction, arithmetic consistency is an essential validation signal, but must be applied conservatively:
1. Arithmetic checks must use exact `Decimal` math, never binary `float`.
2. Total rows ("Total", "Grand Total", "Subtotal", "Sum") must be identified without confusing ordinary text cells with totals.
3. If an arithmetic discrepancy occurs ($100 + 200 = 350$), the system must NEVER auto-modify the printed numbers to force a balance; it must preserve source values and flag `SOURCE_ARITHMETIC_DISCREPANCY`.
4. Ambiguous totals must not be assumed verified; they generate `ARITHMETIC_SCOPE_AMBIGUOUS`.
5. Passing an arithmetic check does not prove every source cell is correct ("No False Corroboration").
6. The Document Quality Gate evaluates document verification status following strict conservative decision precedence and attaches the mandatory verbatim disclaimer.

---

## 2. Table Arithmetic Consistency Evaluator (Section 16)

### Public Interface
```python
def evaluate_table_arithmetic_consistency(
    table: CanonicalTable
) -> tuple[ValidationOutcome, list[ValidationIssue]]
```

### Total Row Detection
- Conservative matching: inspect the first 2 columns of each row (or columns with string/identifier type) for keywords:
  - `total`, `grand total`, `sub total`, `subtotal`, `sum`, `net total`, `total amount`.
- Must NOT match simply because "total" appears inside long descriptive text (e.g. "Total liability policy clause 4").
- Differentiate:
  - Grand Total: sums subtotals or all prior rows.
  - Subtotal: sums prior body rows up to preceding subtotal.

### Calculation Scope
- Identify numeric columns (`DataType.INTEGER`, `DataType.DECIMAL`, `DataType.HIGH_PRECISION_DECIMAL`).
- Exclude identifier columns (e.g. "Account No", "Quantity" if not being totaled).
- Sum body rows strictly using `Decimal`:
  $$\text{Expected} = \sum_{r \in \text{Contributing}} r[\text{col}].\text{numeric\_decimal} \quad (\text{treating None or empty as } 0)$$
- Compare $\text{Expected}$ against candidate total cell's `numeric_decimal`.

### Outcomes & Issues
- **PASSED**: At least one applicable check completed and all checks match printed totals.
- **FAILED_VALIDATION**: At least one applicable check detects a discrepancy.
  - Create `ValidationIssue` with `issue_code = "SOURCE_ARITHMETIC_DISCREPANCY"`.
  - Mark participating cell `ANOMALY_FLAGGED`.
  - Record `expected_value`, `actual_value`.
  - `resolved = False`.
- **NOT_APPLICABLE**: No verifiable total rows or columns exist in the table.
- **ARITHMETIC_SCOPE_AMBIGUOUS**: Table appears to have a total label, but contributing rows or columns cannot be reliably identified.

---

## 3. Document Quality Gate (Section 17)

### Public Interface
```python
def evaluate_document_quality(
    report: DocumentEvaluationReport
) -> DocumentEvaluationReport
```

### Conservative Decision Precedence Order
1. **Fatal Execution Failure:**
   - If `report.execution_state == JobExecutionState.FAILED` $\to$ `VerificationStatus.FAILED`.
2. **Zero-Table Digital Document:**
   - If every page was fully inspected, `deferred_regions_count == 0` across document, and every page is `TablePresenceStatus.CONFIRMED_ABSENT` $\to$ `VerificationStatus.FAILED` with reason code `NO_TABLES_FOUND`.
3. **Scanned Content / Deferred Regions:**
   - If any page has `PageType.SCANNED` or `PageProcessingStatus.INCOMPLETE_DEFERRED_TO_OCR` $\to$ `VerificationStatus.REVIEW_REQUIRED` with reason code `OCR_REQUIRED_FOR_SCANNED_CONTENT`.
   - If hybrid pages contain unprocessed deferred regions $\to$ `VerificationStatus.REVIEW_REQUIRED`.
4. **Unresolved Stitches / Structural Anomalies:**
   - If any stitch event has `StitchDecision.STITCH_REVIEW_REQUIRED` $\to$ `VerificationStatus.REVIEW_REQUIRED`.
   - If structural checks fail on any table $\to$ `VerificationStatus.REVIEW_REQUIRED`.
5. **Arithmetic Discrepancies & Ambiguities:**
   - If any table has `ValidationOutcome.FAILED_VALIDATION` or issues with `SOURCE_ARITHMETIC_DISCREPANCY` $\to$ `VerificationStatus.REVIEW_REQUIRED`.
   - If `ARITHMETIC_SCOPE_AMBIGUOUS` is present $\to$ `VerificationStatus.REVIEW_REQUIRED`.
6. **Warnings & Audited Corrections:**
   - If processing completed cleanly, but an evidence-backed correction was applied (`CORRECTED_WITH_EVIDENCE`), high-precision decimals exist, or arithmetic validation is `NOT_APPLICABLE` $\to$ `VerificationStatus.VERIFIED_WITH_WARNINGS`.
7. **Verified:**
   - If all pages inspected, no deferred regions, no anomalies, applicable math is `PASSED` $\to$ `VerificationStatus.VERIFIED`.

### Mandatory Verbatim Disclaimer
Every evaluated report receives the exact canonical disclaimer in `report.limitation_disclaimers`:
```
"Structural integrity and internal arithmetic consistency were verified. This does not independently prove every source cell is correct and cannot rule out offsetting cell errors or errors in non-numeric text."
```

---

## 4. Phase 4 File Architecture

```
backend/app/verification/
├── __init__.py               # Exports evaluate_table_arithmetic_consistency, evaluate_document_quality, MANDATORY_VERBATIM_DISCLAIMER
└── quality_gate.py           # Arithmetic validation, decision precedence, reason codes, and disclaimer attachment
backend/tests/unit/
└── test_quality_gate.py      # Unit tests for arithmetic evaluation, discrepancy reporting, and document quality gate
```
