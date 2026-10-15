MASTER DIRECTIVE
PROJECT: DOCUSTRUCT AI
TAGLINE: Extract. Verify. Correct. Deliver.

MODE:
AUTONOMOUS ENGINEERING IMPLEMENTATION

PHASE:
PHASE 1 — STEPS 1.1 THROUGH 1.6

TARGET:
WINDOWS 10/11, CPU-ONLY, 8–16 GB RAM

ENGINEERING METHOD:
INSPECT → PLAN → IMPLEMENT → INTEGRATE → TEST
→ DEBUG → VERIFY → REPORT

============================================================
SECTION 1 — ROLE, MISSION, AND ENGINEERING STANDARD
============================================================

Act as a senior Python architect, principal software engineer,
document-processing specialist, security-conscious backend
engineer, and experienced test engineer.

You are building DocuStruct AI, a deterministic-first document
table extraction and verification system.

The product must eventually convert digital and scanned
documents into structured, auditable tabular data while
preserving source evidence and identifying uncertain results.

Phase 1 establishes the foundation for that system.

This is a real engineering task, not a demonstration project.

Your objective is to create modular, typed, testable code with
explicit behavioral contracts and predictable error handling.

NON-NEGOTIABLE RULES:

1. Do not stop after producing a plan.
2. Do not merely print source code in chat when workspace
   file-editing tools are available.
3. Create and modify files directly in the opened project.
4. Integrate the modules into a functioning Phase 1 pipeline.
5. Execute the actual unit tests.
6. Fix genuine implementation failures.
7. Do not weaken meaningful tests simply to obtain a passing
   result.
8. Do not fabricate test outcomes, accuracy metrics, or
   benchmark results.
9. Do not claim that unimplemented features are complete.
10. Do not replace real extraction with hardcoded sample data.
11. Do not introduce an unnecessary framework or dependency.
12. Do not modify unrelated files.
13. Preserve existing useful work in the workspace.
14. Report unresolved defects honestly.

Make reasonable engineering decisions autonomously.

Ask the user only if a genuine external decision or blocker
cannot be resolved from this specification.

============================================================
SECTION 2 — STRICT PHASE 1 SCOPE
============================================================

Implement only the following:

STEP 1.1 — Configuration and calibration.
STEP 1.2 — Domain models and state contracts.
STEP 1.3 — PDF security and ingestion validation.
STEP 1.4 — Page classification and incremental routing.
STEP 1.5 — Native digital PDF table extraction.
STEP 1.6 — Conservative multipage table reconstruction.

Also implement:

- Deterministic numeric/text normalization.
- Arithmetic consistency evaluation where reliably applicable.
- Document-level quality gates.
- End-to-end Phase 1 pipeline orchestration.
- Synthetic PDF fixtures.
- Unit tests.
- A ground-truth regression evaluation harness.
- Windows-compatible developer documentation.

OUT OF SCOPE:

- OCR.
- Tesseract.
- RapidOCR.
- OpenCV-based OCR.
- LLMs or hosted AI APIs.
- Excel workbook generation.
- openpyxl.
- pandas.
- FastAPI.
- React or frontend code.
- Database persistence.
- Authentication.
- Redis.
- Celery.
- Cloud deployment.
- External Java, Ghostscript, Poppler, or libmagic binaries.

Do not add fake implementations of these future features.

Do not silently introduce an out-of-scope dependency to simplify
an implementation.

Keep clean interfaces so later phases can add OCR, Excel output,
LLM-assisted review, and an API/UI without rewriting the
Phase 1 domain models.

PHASE 1 INPUT POLICY:

Accept PDF documents only.

Recognize raster content embedded inside PDFs, but do not claim
that Phase 1 can extract tables from the embedded raster images.

Standalone JPEG and PNG ingestion is outside the current
implementation unless explicitly added to the approved scope
later.

============================================================
SECTION 3 — HARDWARE AND RESOURCE CONSTRAINTS
============================================================

Target environment:

- Windows 10/11.
- CPU-only execution.
- 8–16 GB RAM.
- No GPU requirement.
- No paid cloud infrastructure.
- Compatible Python environment, preferably Python 3.11 or
  another version explicitly verified by the implementation.

Use a modular monolith.

Use one document-processing worker:

max_workers = 1

Process pages sequentially.

Do not render every page into memory simultaneously.

Prefer native PDF text, word coordinates, vector lines, and
table geometry over page rendering.

Release page-specific resources once they are no longer needed.

Use try/finally or context managers for resource cleanup.

gc.collect() may be used selectively when appropriate, but do
not claim that it guarantees a particular RAM ceiling.

MEMORY MEASUREMENT:

Where configured, record Python memory measurements using
tracemalloc.

Document that tracemalloc does not capture all native-library
allocations or represent total operating-system process memory.

Do not call Python heap measurements total RAM measurements.

Do not report a peak memory guarantee without a reproducible
measurement supporting that claim.

============================================================
SECTION 4 — INSPECT THE EXISTING WORKSPACE FIRST
============================================================

Before modifying any files:

1. Inspect the current project root.
2. Identify existing source code and tests.
3. Check current Python and pytest availability.
4. Inspect existing dependency files.
5. Check Git status if Git is available.
6. Preserve useful existing implementation work.
7. Do not delete unrelated user files.
8. Avoid creating a duplicate nested project directory.
9. Use the existing DocuStruct AI project root where present.

Create an implementation checklist, then proceed immediately.

Do not spend the majority of the task producing plans or status
messages.

The final deliverable must be working files in the project
workspace.

============================================================
SECTION 5 — REQUIRED PROJECT STRUCTURE
============================================================

Use this Phase 1 project structure.

docustruct-ai/
├── .gitignore
├── README.md
└── backend/
    ├── pyproject.toml
    ├── requirements.txt
    ├── app/
    │   ├── __init__.py
    │   ├── pipeline.py
    │   ├── config/
    │   │   ├── __init__.py
    │   │   ├── settings.py
    │   │   ├── calibration.py
    │   │   └── thresholds.yaml
    │   ├── models/
    │   │   ├── __init__.py
    │   │   ├── state.py
    │   │   └── domain.py
    │   ├── ingestion/
    │   │   ├── __init__.py
    │   │   ├── security_gate.py
    │   │   └── page_router.py
    │   ├── extraction/
    │   │   ├── __init__.py
    │   │   ├── normalizer.py
    │   │   ├── digital_extractor.py
    │   │   └── table_reconstructor.py
    │   └── verification/
    │       ├── __init__.py
    │       └── quality_gate.py
    └── tests/
        ├── conftest.py
        ├── unit/
        │   ├── test_step_1_1_config.py
        │   ├── test_step_1_2_status_and_gates.py
        │   ├── test_normalizer_integrity.py
        │   ├── test_step_1_3_security_gate.py
        │   ├── test_step_1_4_page_router.py
        │   ├── test_step_1_5_digital_extractor.py
        │   ├── test_step_1_6_table_reconstructor.py
        │   └── test_phase1_pipeline.py
        └── evaluation/
            └── regression_harness.py

Add __init__.py files where required for package discovery.

The pipeline.py file is intentionally included to keep workflow
orchestration separate from extraction and verification logic.

Do not place the complete pipeline coordinator inside
quality_gate.py or execute complex processing during package
import in app/__init__.py.

All required implementation files must contain real,
functional code.

No TODO stubs.
No NotImplementedError placeholders.
No empty methods that pretend to implement features.
No hardcoded successful extraction responses.

============================================================
SECTION 6 — DEPENDENCY CONTRACT
============================================================

Create backend/requirements.txt with these direct dependencies:

pydantic>=2.7,<3.0
pydantic-settings>=2.2
PyYAML>=6.0
PyMuPDF>=1.24.0
pdfplumber>=0.11.0
rapidfuzz>=3.9.0
pytest>=8.2.0

No additional direct dependencies unless technically necessary
and explicitly justified.

Do not add OCR packages, Excel libraries, web frameworks, or
binary-dependent packages.

Create a valid backend/pyproject.toml containing:

- Project metadata.
- Python compatibility configuration.
- Package discovery configuration as appropriate.
- Pytest configuration.
- Reasonable development configuration.

Avoid conflicting or duplicated dependency declarations.

Use pathlib for filesystem paths.

Configuration paths must not depend on the process being
launched from one specific working directory.

Do not hardcode API keys, cloud credentials, or secrets.

============================================================
SECTION 7 — CONFIGURATION AND CALIBRATION
============================================================

Implement:

- app/config/settings.py
- app/config/calibration.py
- app/config/thresholds.yaml

Centralize these settings:

- Maximum file size: 25 MiB.
- Maximum PDF pages: 50.
- Maximum workers: 1.
- Workspace root.
- Permitted input type.
- Page classification thresholds.
- Table extraction thresholds.
- Stitching thresholds.
- Optional memory measurement.
- Relevant cleanup settings.

Use explicit units in names and documentation.

Use Pydantic settings or equivalent typed validation.

Reject invalid settings explicitly.

Malformed YAML must produce a clear configuration error.

Do not silently replace malformed configuration with arbitrary
defaults.

Provide sensible initial defaults with comments.

These defaults are engineering starting points, not proven
scientific thresholds.

All extraction thresholds and real-world accuracy metrics remain
UNMEASURED until evaluated against manually verified PDFs.

TESTS:

- Default settings.
- Valid environment overrides.
- Invalid configuration.
- Missing or malformed YAML.
- Threshold loading.
- Invalid threshold ranges.
- Loading configuration regardless of the current working
  directory.

============================================================
SECTION 8 — STATE ENUMERATIONS
============================================================

Implement in app/models/state.py.

Use string-backed enums where appropriate.

A. JobExecutionState

QUEUED
UNDERSTANDING
EXTRACTING
RECONSTRUCTING
VERIFYING
DIAGNOSING
CORRECTING
REVALIDATING
DELIVERING
COMPLETED
FAILED

B. VerificationStatus

VERIFIED
VERIFIED_WITH_WARNINGS
REVIEW_REQUIRED
FAILED

C. PageType

DIGITAL
SCANNED
HYBRID
EMPTY_OR_UNREADABLE

D. PageProcessingStatus

EXTRACTED
INCOMPLETE_DEFERRED_TO_OCR
EMPTY_PAGE
FAILED_PAGE

E. TablePresenceStatus

CONFIRMED_PRESENT
CONFIRMED_ABSENT
UNKNOWN_PENDING_OCR

F. ValidationOutcome

PASSED
PASSED_WITH_WARNINGS
FAILED_VALIDATION
NOT_APPLICABLE

G. StitchDecision

STITCH_CONFIRMED
STITCH_REJECTED
STITCH_REVIEW_REQUIRED

H. CellQualityStatus

EXTRACTED_AS_IS
CORROBORATED
CORRECTED_WITH_EVIDENCE
LOW_CONFIDENCE_WARNING
ANOMALY_FLAGGED
ILLEGIBLE_OR_MISSING

I. DataType

STRING
IDENTIFIER
INTEGER
DECIMAL
HIGH_PRECISION_DECIMAL
DATE
EMPTY

ORTHOGONALITY OF EXECUTION STATE AND DATA QUALITY:

Do not merge execution state and verification status into one status.
Keep the two status dimensions strictly orthogonal.

1. JobExecutionState.FAILED:
   Reserved exclusively for unrecoverable pipeline infrastructure
   or operational failures where processing cannot complete (e.g.
   file not found, corrupted PDF, password encryption, file size
   or page count limit exceeded, unhandled system error).

2. JobExecutionState.COMPLETED:
   The pipeline executed all applicable processing and routing steps
   to completion without encountering an unrecoverable operational abort.

3. VerificationStatus.REVIEW_REQUIRED:
   Processing completed successfully (JobExecutionState.COMPLETED),
   but extracted data is incomplete, ambiguous, or contains unresolved
   issues (e.g. scanned content deferred to OCR, hybrid deferred regions,
   ambiguous multipage stitching, source arithmetic discrepancies,
   or ambiguous calculation scopes).

4. VerificationStatus.FAILED:
   Applies only when:
   a) JobExecutionState == FAILED (operational abort); OR
   b) Processing completed (JobExecutionState.COMPLETED), every page
      was fully digitally inspected, zero deferred regions and zero
      scanned pages exist, and every page has TablePresenceStatus.CONFIRMED_ABSENT
      (with reason code NO_TABLES_FOUND).

Do not automatically treat every extraction limitation as a fatal
execution failure. A job can and should complete processing
successfully while receiving VerificationStatus.REVIEW_REQUIRED.

Use explicit transition checks if a mutable lifecycle object
is implemented.

Do not silently transition out of a terminal state.


============================================================
SECTION 9 — DOMAIN MODEL CONTRACTS
============================================================

Implement typed, validated Pydantic v2 models in domain.py.

Use consistent field names across every module.

Avoid duplicate representations of the same concept with
incompatible names.

A. BoundingBox

Fields:

x0: float
y0: float
x1: float
y1: float
page_width: float
page_height: float
coord_exact: bool

Computed normalized coordinates:

norm_x0
norm_x1
norm_y0
norm_y1

Validate page dimensions, coordinate order, and normalized
coordinate calculations.

Do not silently clamp malformed geometry.

Document whether coordinates use PDF points and whether they
are zero-based relative to the page.

B. CellRecord

Fields:

table_id: str
row_idx: int
col_idx: int
source_page: int
bbox: Optional[BoundingBox]
extraction_method: str
ocr_confidence: Optional[float]
raw_value: str
normalized_value: Optional[str]
numeric_decimal: Optional[Decimal]
accepted_value: str
inferred_candidate_value: Optional[str]
data_type: DataType
quality_status: CellQualityStatus
formula_risk_detected: bool
notes: list[str]

Contracts:

- raw_value is the exact original extracted text.
- Normalization must never overwrite raw_value.
- normalized_value contains meaning-preserving normalization.
- accepted_value is the value available to downstream phases.
- inferred_candidate_value is not an accepted correction.
- OCR confidence is optional because Phase 1 has no OCR.
- Decimal values must not be converted through float.
- Identifiers must preserve significant leading zeros.
- row_idx and col_idx must follow one documented indexing rule.
- Correction status must not be erased when an accepted
  correction exists.

C. StitchAuditEvent

Fields:

upper_table_id
lower_table_id
upper_page
lower_page
decision
header_similarity_score
col_overlap_ratio
type_compatibility_ratio
repeated_header_rows_stripped
reasons

Use explicit numeric bounds for similarity/overlap scores where
applicable.

D. ValidationIssue

Fields:

issue_id
table_id
source_page
row_idx
col_idx
issue_code
severity
description
expected_value
actual_value
resolved

Allow optional location fields for table-level issues.

E. CorrectionRecord

Fields:

audit_id
table_id
source_page
row_idx
col_idx
original_raw_value
proposed_value
accepted_value
inferred_candidate_only
evidence_source
evidence_summary
deterministic_check_passed
decision
resulting_cell_status

Use optional fields for cases without a concrete row or column.

Do not accept a correction without the evidence requirements
defined later in this specification.

F. PageProfile

Fields:

page_number
page_type
processing_status
table_presence
printable_char_count
garbled_char_ratio
image_coverage_ratio
vector_line_count
deferred_regions_count

Include only additional fields that support explainable routing.

Validate counts and applicable ratios.

G. CanonicalTable

This is the shared table contract used by extraction,
reconstruction, verification, and the pipeline.

Fields:

table_id: str
title: Optional[str]
source_pages: list[int]
page_bbox: Optional[BoundingBox]
original_headers: list[str]
normalized_headers: list[str]
header_row_count: int
column_types: list[DataType]
column_semantic_roles: list[str]
rows: list[list[CellRecord]]
extraction_method: str
stitch_events: list[StitchAuditEvent]
validation_issues: list[ValidationIssue]
correction_records: list[CorrectionRecord]
structural_checks_passed: bool
math_validation_outcome: ValidationOutcome
verification_status: VerificationStatus

Contracts:

- Use these field names consistently.
- Preserve legitimate ragged rows instead of silently padding
  or shifting source values.
- Keep original headers separate from normalized headers.
- Keep source page information for individual cells.
- Preserve individual cell coordinates when available.
- Do not silently discard duplicate rows.
- Document how repeated header rows are represented.
- Do not overwrite the raw source rows when stitching.
- Make any derived canonical representation traceable to
  source page/table identifiers.

H. PageExtractionResult

Fields:

page_number
page_profile
tables
issues
deferred_regions_count
diagnostics

The tables field must use a consistent CanonicalTable
representation.

I. DocumentEvaluationReport

Fields:

job_id: str
source_filename: str
execution_state: JobExecutionState
verification_status: VerificationStatus
status_reason_codes: list[str]
limitation_disclaimers: list[str]
page_profiles: list[PageProfile]
page_results: list[PageExtractionResult]
canonical_tables: list[CanonicalTable]
stitch_events: list[StitchAuditEvent]
validation_issues: list[ValidationIssue]
correction_records: list[CorrectionRecord]
peak_python_heap_bytes: Optional[int]

You may add narrowly useful fields for safe diagnostics or
document-level counts, provided they remain consistent with
this contract.

The report must be returned by the end-to-end pipeline.

If processing fails, the pipeline must still be capable of
returning a controlled failure report for expected operational
errors.

Do not expose confidential source contents in failure messages.

J. Model compatibility

Define models in an order that minimizes forward-reference
complexity.

If forward references are needed, resolve them explicitly.

Do not create circular import chains between domain models,
extraction, verification, and orchestration.

Test actual serialization and validation of representative
nested models.

============================================================
SECTION 10 — PDF SECURITY GATE
============================================================

Implement app/ingestion/security_gate.py.

Responsibilities:

1. Validate input existence.
2. Require a regular file.
3. Reject empty files.
4. Enforce the 25 MiB maximum.
5. Verify the PDF signature beginning with %PDF-.
6. Validate PDF structure with PyMuPDF.
7. Reject encrypted/password-protected PDFs unless an approved
   safe handling mechanism is implemented.
8. Reject invalid or unreadable documents.
9. Reject zero-page PDFs.
10. Reject documents exceeding 50 pages.
11. Sanitize filenames with pathlib.Path(filename).name.
12. Create isolated UUID-based job workspaces.
13. Prevent workspace path traversal.
14. Produce controlled, typed errors for expected failures.
15. Avoid logging source document contents.
16. Never delete the user's original input file.
17. Provide safe cleanup of any temporary processing data.

A valid signature does not prove that a file is harmless.

Do not claim that signature inspection is complete file
security validation.

Do not use libmagic, Poppler, Ghostscript, or Java.

File-handle discipline is mandatory on Windows.

Every PyMuPDF Document must be closed through a context manager
or a guaranteed try/finally block.

Every pdfplumber.PDF must be closed through a context manager
or a guaranteed try/finally block.

Do not leave open PDF handles during workspace cleanup.

Use UUID workspace names rather than using user filenames
directly as storage paths.

Use pathlib-based containment checks to prevent workspace
escape.

Do not follow a user-supplied path outside the permitted
workspace when handling derived output files.

TESTS:

- Missing file.
- Directory instead of a file.
- Empty file.
- Invalid signature.
- Corrupt PDF.
- Encrypted PDF.
- Zero-page document where reproducibly constructible.
- Oversized input.
- More than 50 pages.
- Filename path traversal.
- Valid PDF.
- Workspace isolation.
- Safe cleanup.
- File handles closed before cleanup.

============================================================
SECTION 11 — PAGE ROUTER AND RESOURCE DISCIPLINE
============================================================

Implement app/ingestion/page_router.py.

Classify PDF pages as:

DIGITAL
SCANNED
HYBRID
EMPTY_OR_UNREADABLE

Use deterministic, explainable signals:

- Native printable character count.
- Garbled-character ratio.
- Native text positions.
- Embedded image coverage.
- Vector-line count.
- Existence and distribution of native text blocks.
- Image and text region geometry.

Use configured thresholds.

Do not classify every page containing an image as scanned.

A digital page can contain logos, signatures, photographs,
charts, or scanned inserts.

A hybrid page can contain both native text and unprocessed
raster content.

A. DIGITAL PAGE

When the page has readable native content and no known deferred
raster regions requiring extraction:

- Extract available native content.
- Set processing status appropriately.
- Track whether tables were found.

B. SCANNED PAGE

When native extraction cannot establish the raster content:

processing_status = INCOMPLETE_DEFERRED_TO_OCR

table_presence = UNKNOWN_PENDING_OCR

SCANNED DOCUMENT RULES:

1. A document must not be classified as containing zero tables merely
   because Phase 1 does not implement OCR.
2. If the file is valid but its content is scanned and deferred to a
   future phase, record the page as INCOMPLETE_DEFERRED_TO_OCR.
3. Where Phase 1 cannot determine whether a scanned document contains
   tables, explicitly record that the presence of tables is UNKNOWN_PENDING_OCR.
4. If processing finishes successfully but relevant content remains
   unextracted, the document receives JobExecutionState.COMPLETED with
   VerificationStatus.REVIEW_REQUIRED (Reason: OCR_REQUIRED_FOR_SCANNED_CONTENT).
5. A document containing scanned pages must NEVER be classified as
   CONFIRMED_ABSENT or assigned VerificationStatus.FAILED under NO_TABLES_FOUND.


C. HYBRID PAGE

- Extract supported native content.
- Identify unprocessed raster regions where feasible.
- Set deferred_regions_count > 0 when raster regions remain
  unprocessed.
- Do not claim these raster regions contain no tables.

D. EMPTY PAGE

Use EMPTY_PAGE only when the page is genuinely empty under
the documented classification rules.

E. PAGE PROCESSING FAILURE

Distinguish an unreadable or failed page from a fully inspected
page that contains no table.

Do not silently mark an unreadable page CONFIRMED_ABSENT.

A failure that prevents reliable document completion must be
represented as a controlled failure or unresolved review state,
according to the pipeline error contract.

MEMORY:

- Process pages sequentially.
- Close page and document handles.
- Release temporary page-specific objects.
- Do not cache large rendered page collections.
- Record Python heap measurements when enabled.

============================================================
SECTION 12 — NORMALIZATION AND FORMULA-RISK DETECTION
============================================================

Implement app/extraction/normalizer.py.

The normalizer must be deterministic and meaning-preserving.

Preserve these values separately:

raw_value
normalized_value
accepted_value
numeric_decimal
data_type
formula_risk_detected

Do not treat normalization as correction.

A. WHITESPACE NORMALIZATION

Support trimming leading/trailing whitespace.

Collapse internal repeated whitespace only where doing so does
not alter meaningful source content.

Keep raw_value immutable.

B. NUMERIC NORMALIZATION

Support valid:

- Standard grouping: 1,234,567.89
- Indian grouping: 12,34,567.89
- Leading negative: -450.50
- Trailing accounting negative: 450.50-
- Parenthesized negative: (450.50)
- Decimal values.
- Integers.
- High-precision decimal strings.

Examples:

Source:
(450.50)

Normalized:
-450.50

Accepted:
-450.50

Numeric Decimal:
Decimal("-450.50")

Raw source remains:
(450.50)

Normalization alone keeps:
CellQualityStatus.EXTRACTED_AS_IS

Do not strip commas from malformed grouping without validation.

Use decimal.Decimal and never convert through binary float.

Do not round numeric values.

C. IDENTIFIER PRESERVATION

Detect likely identifier columns using header semantics,
lexical patterns, and value shape.

Potential identifier header names include:

Account
Invoice
GSTIN
PAN
Aadhaar
Phone
ID
Code
Ref
No

Do not rely on an exact header match alone when it is ambiguous.

Preserve leading zeros:

"0012345"

as an identifier rather than a numeric quantity when the
column and value semantics support that classification.

Long identifiers must not be silently converted to numeric
values.

D. PRECISION CLASSIFICATION

Classify suitable numeric values as:

INTEGER
DECIMAL
HIGH_PRECISION_DECIMAL

Treat numeric values with more than 15 significant digits as
HIGH_PRECISION_DECIMAL according to the documented precision
policy.

Preserve the exact Decimal value and appropriate exact string.

Do not round or silently discard trailing digits.

Keep identifiers separate from high-precision measurements.

E. FORMULA-RISK BOUNDARY

Phase 1 does not generate Excel workbooks.

Apply these boundary rules:

1. String Classification & Risk Flagging:
   Phase 1 may classify strings, detect possible formula-injection
   risks, and record formula_risk_detected = True on the CellRecord.
   Candidate prefixes for non-numeric STRING or IDENTIFIER cells:
   =, +, -, @, tab (\t), carriage return (\r).

2. No Export Escaping in Phase 1:
   Do not prefix raw_value, normalized_value, or accepted_value
   with an apostrophe (') solely for future Excel export.

3. Source and Value Preservation:
   Preserve source values and meaningful normalized values
   in the domain model without artificial formatting prefixes.

4. Deferral to Phase 3 Serialization:
   Apply actual formula-injection neutralization (such as apostrophe
   prepending) strictly at the Excel export serialization boundary in Phase 3.

5. Legitimate Negative Numbers:
   Valid numeric negatives (e.g. -450.50, (450.50), 450.50-) must be
   parsed as numeric decimals first and must NEVER be flagged as
   formula risks or escaped as untrusted text.

6. Dependency Hygiene:
   Keep Phase 1 100% free of unnecessary Excel dependencies
   (openpyxl, xlsxwriter, etc.).


F. MALFORMED INPUTS

Do not guess the intended meaning of malformed numeric strings.

Preserve source evidence and record an anomaly when necessary.

TESTS:

- Indian grouping.
- Standard grouping.
- Valid leading minus.
- Valid trailing minus.
- Accounting parentheses.
- Leading zeros.
- Identifier headers.
- High precision.
- Formula-like strings.
- Negative numeric values.
- Malformed grouping.
- Empty strings.
- Whitespace.
- Raw-value immutability.
- Decimal exactness.

============================================================
SECTION 13 — DIGITAL TABLE EXTRACTION
============================================================

Implement app/extraction/digital_extractor.py.

Use PyMuPDF and pdfplumber for native digital PDF extraction.

Do not use OCR.

Prefer the extraction approach best supported by the PDF's
native geometry.

FIRST STRATEGY:

Use pdfplumber's line-based table extraction when ruling-line
geometry supports it.

FALLBACK STRATEGY:

When ruling lines are absent, use native word positions and
normalized horizontal coordinate intervals to infer columns
conservatively.

Support, where native source evidence permits:

- Ruled tables.
- Borderless tables.
- Multiple tables on one page.
- Tables continuing across pages.
- Repeated headers.
- Wrapped text.
- Source page references.
- Cell bounding boxes.
- Table IDs.
- Column geometry.
- Extraction method metadata.
- Structural anomaly reporting.

Do not assume every aligned text block is a table.

Do not merge unrelated content because it happens to align.

Do not invent cells.

Do not shift cells into different columns merely to make rows
rectangular.

Do not silently drop blank-looking rows or columns when their
structural meaning is uncertain.

Preserve available raw cell text.

Use unique deterministic table identifiers within each job,
or stable job-scoped identifiers that avoid collisions.

Document whether source coordinates refer to PDF points.

Use defensive resource management.

Whenever a PDF is opened, guarantee closure even if extraction
raises an exception.

A pdfplumber PDF handle must never remain open during temporary
workspace cleanup.

A PyMuPDF Document handle must never remain open during
temporary workspace cleanup.

TESTS:

- Simple ruled table.
- Borderless table.
- Multiple tables on one page.
- Multiline/wrapped cells.
- Repeated headers.
- Multiple pages.
- Non-table digital page.
- Ragged rows.
- Ambiguous layout.
- Cell geometry.
- Source page references.
- Duplicate row preservation.
- Resource cleanup after extraction exceptions.

============================================================
SECTION 14 — CONSERVATIVE MULTIPAGE RECONSTRUCTION
============================================================

Implement app/extraction/table_reconstructor.py.

Use seven decision factors.

1. Column count and schema compatibility.
2. Table-relative normalized column overlap.
3. Repeated-header text similarity.
4. Column data-type compatibility.
5. Page-transition geometry.
6. Row-index continuity.
7. Duplicate data preservation.

Initial thresholds:

stitch_min_relative_col_overlap = 0.75

header_similarity_confirm = 0.85

stitch_min_type_compatibility = 0.85

Keep thresholds configurable.

Document that initial thresholds remain UNMEASURED until
evaluated on manually verified tables.

A. DIFFERING COLUMN COUNTS

Never invent columns, delete columns, or shift values
automatically to force a merge.

Use STITCH_REJECTED when independent evidence supports
separate tables, such as:

- Intervening heading or section text.
- Upper table ends with an explicit Grand Total.
- Incompatible headers and incompatible body types.
- Substantially different outer table spans.

Use STITCH_REVIEW_REQUIRED when continuation appears plausible
but differing column counts may result from extraction artifacts
such as:

- Missing vertical borders.
- Dropped empty columns.
- Merged cells.
- Misaligned native word coordinates.

Preserve both source tables separately when the decision
requires review.

B. TABLE-RELATIVE COLUMN OVERLAP

Normalize column intervals relative to each table's outer
horizontal span.

Do not compare absolute page coordinates alone.

Handle missing or degenerate boundaries safely.

C. MULTILINE REPEATED HEADERS

Compare the upper table's canonical header block with sliding
windows of 1, 2, or 3 leading rows of the lower table.

Strip repeated rows only when:

- The rows are at the top of the lower table.
- Header similarity reaches the configured threshold.
- Expected body data types provide supporting evidence.
- The rows are inconsistent with the corresponding body data
  pattern where relevant.
- No material contradictory evidence exists.

Record the number of removed repeated headers and the evidence
in StitchAuditEvent.

Never strip a row solely because it resembles another row.

D. TYPE COMPATIBILITY

Determine dominant column types from actual body-cell evidence.

Do not infer type compatibility from headers alone.

Dynamically handle empty or mixed-type columns.

E. PAGE-TRANSITION CONTEXT

Consider whether the upper table ends near the bottom content
zone and the lower table begins near the top content zone.

Check intervening text when available.

F. ROW CONTINUITY

Use serial numbers or row indexes when reliable.

A sequence continuing from N to N+1 supports continuation.

An index reset can support a new-table hypothesis but is not
sufficient by itself to reject a stitch.

G. DUPLICATE ROW PRESERVATION

Never deduplicate legitimate data rows solely because all cell
values equal a neighbouring row.

Identical data rows may be legitimate transactions.

H. STITCH DECISION

Return STITCH_CONFIRMED only when the mandatory compatibility
checks pass and no material contradictory evidence exists.

Return STITCH_REJECTED when evidence supports separate tables.

Return STITCH_REVIEW_REQUIRED when evidence is insufficient
or extraction artifacts may explain the disagreement.

Record an audit event for every evaluated adjacent-table pair.

TESTS:

- Confirmed continuation.
- Rejected separate tables.
- Ambiguous column count.
- Missing borders.
- Margin shifts.
- Multiline repeated headers.
- Header-like body rows.
- Serial sequence.
- Serial reset.
- Legitimate duplicate rows.
- Conflicting stitch signals.
- Audit event correctness.

============================================================
SECTION 15 — EVIDENCE-GATED CORRECTIONS
============================================================

Implement correction contracts without introducing LLMs.

Permitted deterministic evidence sources:

NATIVE_PDF_CHAR_STREAM
INDEPENDENT_WORD_COORDINATES
VECTOR_GRID_GEOMETRY

An accepted correction requires:

1. Independent deterministic source evidence.
2. A proposed value consistent with that evidence.
3. A passed deterministic validation.
4. An audit record.
5. CellQualityStatus.CORRECTED_WITH_EVIDENCE.
6. Preservation of original raw_value.
7. Preservation of the original and accepted values in the
   correction audit record.

Do not claim independence if both pieces of evidence are
merely the same underlying extraction result represented twice.

Do not accept a correction when sufficient evidence is absent.

Do not change a cell solely to make a total balance.

Example:

100 + 200 = 350

The system must preserve the printed values and report:

SOURCE_ARITHMETIC_DISCREPANCY

The system must not automatically replace 350 with 300.

For missing or illegible values:

- Never fabricate accepted values.
- Never overwrite the source with a subtraction result.
- An algebraic candidate may be stored only in
  inferred_candidate_value.
- Mark the appropriate cell ILLEGIBLE_OR_MISSING.
- Mark unresolved material issues for review.

Mathematical consistency alone must not mark all participating
cells CORROBORATED.

CORROBORATED should be used only when the cell has genuine
supporting evidence satisfying the implementation's documented
corroboration contract.

Every accepted value correction must retain its CorrectionRecord.

============================================================
SECTION 16 — DETERMINISTIC ARITHMETIC CONSISTENCY
============================================================

Implement the arithmetic evaluator in:

app/verification/quality_gate.py

Required public interface:

evaluate_table_arithmetic_consistency(
    table: CanonicalTable
) -> tuple[ValidationOutcome, list[ValidationIssue]]

The evaluator must use exact Decimal arithmetic.

It must not use float.

It must not modify raw source values.

A. PURPOSE

Validate arithmetic relationships only when the table structure
provides sufficient evidence for a reliable calculation.

Possible patterns include explicit summary rows such as:

Total
Grand Total
Sub Total
Subtotal
Sum

and clearly identifiable total columns where the table's
structure and semantic roles support a cross-foot check.

B. TOTAL ROW DETECTION

Use conservative, documented rules.

Do not trigger total-row detection merely because the word
"total" appears anywhere in an ordinary text field.

Consider:

- The position of the label cell.
- Header/column semantics.
- Numeric values in the candidate summary row.
- Whether preceding body rows can be reliably associated with
  the summary.
- Whether subtotals or intermediate summaries occur.
- Whether rows have already been categorized as headers,
  summaries, or body rows.

C. CALCULATION SCOPE

Calculate a total only when the relevant contributing rows and
numeric columns can be identified reliably.

Do not double-count subtotals and their contributing rows.

Do not assume every number column should be summed.

Do not assume tax, discount, balance, price, quantity, rate,
opening balance, and closing balance columns are interchangeable.

Do not run speculative arithmetic checks merely to make the
validation appear comprehensive.

D. RESULTS

Return PASSED when at least one clearly applicable arithmetic
check is completed and all applicable checks pass.

Return FAILED_VALIDATION when a reliable applicable check
detects a discrepancy.

Return NOT_APPLICABLE when there is no verifiable total or
cross-foot rule.

If the document appears to contain a total but the calculation
scope is materially ambiguous, create an appropriate unresolved
issue such as:

ARITHMETIC_SCOPE_AMBIGUOUS

The quality gate must not silently treat an ambiguous total
as verified.

If one applicable check fails, the overall applicable arithmetic
validation must not be reported as passed.

E. DISCREPANCY HANDLING

When the source contains:

100 + 200 = 350

Preserve all three printed values.

Create a ValidationIssue with:

issue_code = SOURCE_ARITHMETIC_DISCREPANCY

Include:

- Affected table and source page.
- Row/column when identifiable.
- Expected value.
- Actual printed value.
- Clear diagnostic description.
- resolved = False.

Mark the affected cell or cells ANOMALY_FLAGGED as appropriate.

Do not apply a correction automatically.

Return FAILED_VALIDATION.

F. NO FALSE CORROBORATION & LIMITS OF ARITHMETIC EVIDENCE

1. Distinguish Consistency from Source Verification:
   Mathematical consistency (internal arithmetic agreement) is distinct
   from independent source verification. A matching sum proves that the
   extracted numbers satisfy the arithmetic relationship; it does not
   independently prove that every individual extracted value matches the
   underlying physical document.

2. Risk of Offsetting Errors:
   Incorrect values can still produce a matching total, and multiple
   extraction errors may offset one another (e.g. +$50 and -$50). A matching
   sum cannot detect non-numeric errors or source document inaccuracies.

3. No False Cell Corroboration:
   Passing an arithmetic check confirms internal arithmetic agreement for
   that check only. Do not claim that a matching sum proves every individual
   extracted value is correct. Do not mark contributing body cells
   CORROBORATED solely because their sum matches a printed total.

4. Evidence Integrity:
   Do not invent independent evidence that the implemented extraction
   pipeline does not actually provide.


G. CELL STATUS

Do not turn normalized cells into corrected cells.

Do not erase previously retained correction audit records.

Do not mutate raw_value.

H. TESTS

Test:

- Correct total.
- Incorrect total.
- Negative numbers.
- Decimal precision.
- No total row.
- No total column.
- Multiple numeric columns.
- Empty contributing cells.
- Subtotals.
- Grand totals.
- Ambiguous calculation scope.
- Source values preserved after discrepancy.
- Exact Decimal comparisons.

============================================================
SECTION 17 — DOCUMENT QUALITY GATE
============================================================

Implement in:

app/verification/quality_gate.py

The gate evaluates a completed report using:

- Execution state.
- Page completeness.
- Deferred raster regions.
- Table existence.
- Structural integrity.
- Arithmetic outcomes.
- Unresolved validation issues.
- Stitch decisions.
- Correction records.
- Low-confidence and precision warnings.

Keep execution status separate from verification status.

A. VERIFIED

Define VERIFIED conservatively as successful extraction with structural
integrity, applicable consistency checks, and no unresolved issues,
subject to the explicitly documented limits of the available evidence.

Require all of the following:

- Execution completed (JobExecutionState.COMPLETED).
- Every page was fully inspected.
- No deferred OCR regions remain.
- Structural checks pass.
- No unresolved material anomalies exist.
- No cells have CORRECTED_WITH_EVIDENCE.
- No cells have LOW_CONFIDENCE_WARNING.
- No unresolved stitch-review events exist.
- Applicable math validation is PASSED.
- No other material issue prevents verification.

EVIDENCE LIMITATIONS & DISCLAIMER:

Clearly state that native PDF extraction and mathematical consistency checks
cannot guarantee complete cell-level correctness. Mathematical consistency
alone does not independently prove that every extracted value matches the
source document; incorrect values can still produce a matching total, and
multiple extraction errors may offset one another.

Every valid evaluation report must attach this mandatory verbatim disclaimer:

"Structural integrity and internal arithmetic consistency
were verified. This does not independently prove every source
cell is correct and cannot rule out offsetting cell errors or
errors in non-numeric text."

Do not claim that a matching sum proves every individual extracted value
is correct. Do not say that the entire document is factually correct.

B. VERIFIED_WITH_WARNINGS

Use when processing completed (JobExecutionState.COMPLETED), no unresolved
material issue remains, no deferred region remains, and one or more of
the following explicit quality-gate conditions applies:

- Math validation is NOT_APPLICABLE because the table structure contains
  no verifiable summary rows or applicable arithmetic relationships.
- An evidence-backed correction was applied and retained in the audit trail.
- High-precision numbers (>15 digits) need special downstream storage.
- A permitted low-confidence warning remains non-blocking under
  the documented policy.

Attach a clear explanation of the warning.
If an issue remains unresolved and materially affects trust,
use REVIEW_REQUIRED instead.


C. REVIEW_REQUIRED

Use when processing completed successfully (JobExecutionState.COMPLETED),
but data is incomplete, ambiguous, or contains unresolved issues:

- Scanned content has not been processed (OCR_REQUIRED_FOR_SCANNED_CONTENT).
- Hybrid pages contain deferred raster regions (DEFERRED_REGIONS_REMAIN).
- A table stitch remains ambiguous (STITCH_REVIEW_REQUIRED).
- Structural integrity cannot be established (STRUCTURAL_CHECKS_FAILED).
- A source arithmetic discrepancy exists (SOURCE_ARITHMETIC_DISCREPANCY).
- The calculation scope of an apparent total is ambiguous (ARITHMETIC_SCOPE_AMBIGUOUS).
- Relevant source evidence conflicts or a material parsing issue remains unresolved.

D. FAILED

Reserve VerificationStatus.FAILED strictly for two distinct conditions:

1. Operational Abort:
   JobExecutionState == FAILED (the pipeline could not finish processing
   due to a fatal operational condition, such as a corrupt or unsupported
   file, exceeded size/page limits, or a fatal system error). Reason:
   EXECUTION_FAILED.

2. Fully Inspected Zero-Table Digital Document:
   Execution completed successfully (JobExecutionState.COMPLETED), every
   page was fully digitally inspected, deferred_regions_count == 0 across
   the document, zero scanned pages exist, and every page has
   TablePresenceStatus.CONFIRMED_ABSENT. Reason: NO_TABLES_FOUND.

NON-NEGOTIABLE BOUNDARIES FOR FAILED:
- A document must not be classified as containing zero tables merely
  because Phase 1 does not implement OCR.
- Scanned content must NEVER receive VerificationStatus.FAILED under
  NO_TABLES_FOUND.
- Do not classify a page that could not be inspected as CONFIRMED_ABSENT.
- Do not classify a single empty page as a zero-table document if other
  pages contain extractable tables.

E. SCANNED-ONLY DOCUMENT

A document containing only scanned pages must be handled consistently
with the rule that job execution state and verification status are
orthogonal:

JobExecutionState = COMPLETED
VerificationStatus = REVIEW_REQUIRED

For every scanned page:
PageProcessingStatus = INCOMPLETE_DEFERRED_TO_OCR
TablePresenceStatus = UNKNOWN_PENDING_OCR

Reason:
OCR_REQUIRED_FOR_SCANNED_CONTENT

Where Phase 1 cannot determine whether a scanned document contains
tables, explicitly record that the presence of tables is UNKNOWN_PENDING_OCR,
not CONFIRMED_ABSENT.

F. HYBRID DOCUMENT

Extract supported native digital tables.
Keep deferred raster regions explicitly represented.
If any material region remains deferred:

JobExecutionState = COMPLETED
VerificationStatus = REVIEW_REQUIRED
Reason = DEFERRED_REGIONS_REMAIN

G. ZERO-TABLE DIGITAL DOCUMENT

Only after every page is fully digitally inspected, zero scanned pages
exist, zero deferred regions remain, and every page is CONFIRMED_ABSENT:

JobExecutionState = COMPLETED
VerificationStatus = FAILED
Reason = NO_TABLES_FOUND

H. CONSERVATIVE DECISION PRECEDENCE TABLE

The Document Quality Gate must evaluate status reasons in this exact
deterministic precedence order so page-level deferrals, table-level
issues, and genuine fatal failures do not produce contradictory results:

1. Fatal Execution State:
   report.execution_state == JobExecutionState.FAILED
   -> VerificationStatus.FAILED [EXECUTION_FAILED]

2. Fully Inspected Zero-Table Digital Document:
   total_tables == 0 AND all pages CONFIRMED_ABSENT AND zero scanned pages AND zero deferred regions
   -> VerificationStatus.FAILED [NO_TABLES_FOUND]

3. Scanned Content Present:
   Any page is SCANNED, INCOMPLETE_DEFERRED_TO_OCR, or UNKNOWN_PENDING_OCR
   -> VerificationStatus.REVIEW_REQUIRED [OCR_REQUIRED_FOR_SCANNED_CONTENT]

4. Deferred Regions Remain:
   total_deferred_regions > 0 on hybrid pages
   -> VerificationStatus.REVIEW_REQUIRED [DEFERRED_REGIONS_REMAIN]

5. Unresolved Stitch Reviews:
   Any stitch event has decision == STITCH_REVIEW_REQUIRED
   -> VerificationStatus.REVIEW_REQUIRED [STITCH_REVIEW_REQUIRED]

6. Arithmetic Discrepancies and Ambiguities:
   SOURCE_ARITHMETIC_DISCREPANCY or table math FAILED_VALIDATION
   -> VerificationStatus.REVIEW_REQUIRED [SOURCE_ARITHMETIC_DISCREPANCY]
   ARITHMETIC_SCOPE_AMBIGUOUS
   -> VerificationStatus.REVIEW_REQUIRED [ARITHMETIC_SCOPE_AMBIGUOUS]

7. Structural Integrity Failures:
   Any table fails structural checks
   -> VerificationStatus.REVIEW_REQUIRED [STRUCTURAL_CHECKS_FAILED]

8. Non-Blocking Warnings:
   Audited corrections applied OR high-precision decimals present OR all table math NOT_APPLICABLE
   -> VerificationStatus.VERIFIED_WITH_WARNINGS []

9. Clean Execution & Verified Math:
   Zero anomalies, zero deferrals, zero corrections, applicable math PASSED
   -> VerificationStatus.VERIFIED []

Do not allow a local table-level pass to override an unresolved
document-level issue.


============================================================
SECTION 18 — END-TO-END PIPELINE COORDINATOR
============================================================

Implement:

backend/app/pipeline.py

Required public entry point:

run_phase1_pipeline(
    file_path: Path,
    original_filename: Optional[str] = None,
    settings: Optional[AppSettings] = None,
    calibration: Optional[CalibrationConfig] = None,
) -> DocumentEvaluationReport

Use the actual settings and calibration types implemented in
the project.

The function must perform a complete Phase 1 run, not merely
call the security gate.

PIPELINE SEQUENCE:

1. Initialize job ID and controlled document-level metadata.
2. Load or validate settings and calibration.
3. Validate input through security_gate.
4. Create/manage the isolated job workspace.
5. Open and inspect the PDF using safe resource management.
6. Route each page through page_router.
7. Extract supported native digital tables.
8. Normalize extracted cells.
9. Evaluate adjacent page tables for conservative stitching.
10. Build canonical tables.
11. Run structural checks.
12. Run deterministic arithmetic validation where applicable.
13. Collect validation issues, stitch events, and correction
    records.
14. Evaluate final document quality.
15. Build DocumentEvaluationReport.
16. Release all temporary objects.
17. Close all resources.
18. Clean up temporary workspaces according to policy.
19. Return the final report.

The exact internal ordering may be refined when a dependency
requires a preliminary extraction step, but the final behavior
must satisfy all contracts.

PIPELINE INTEGRATION RULES:

- Keep modules independently testable.
- Do not put all business logic in pipeline.py.
- Do not put extraction logic inside quality_gate.py.
- Do not create circular imports.
- Domain models must remain independent of orchestration.
- pipeline.py may import the service modules it coordinates.
- Other modules should not import pipeline.py to perform their
  ordinary functions.
- Use dependency injection for settings and calibration when
  appropriate.
- Ensure module imports have no document-processing side effects.
- Do not depend on the current working directory.

ERROR HANDLING:

For expected operational errors, build and return an appropriate
DocumentEvaluationReport with:

execution_state = FAILED
verification_status = FAILED
an appropriate status_reason_codes entry
safe diagnostic information

Do not expose sensitive document text in diagnostic messages.

Do not convert every programming bug into a silent normal
result.

Unexpected exceptions must be handled according to a documented
error policy, safely recorded, and investigated during tests.

Do not claim a report is valid when pipeline processing
terminated before mandatory fields were populated.

RESOURCE MANAGEMENT:

The pipeline must guarantee closure of every PyMuPDF and
pdfplumber handle before workspace cleanup.

Use context managers or explicit try/finally blocks.

Test exceptions during extraction to prove cleanup still occurs.

Ensure a PDF input file is never deleted when cleaning the
isolated job workspace.

MEMORY:

When measurement is enabled, record the Python heap measurement
according to the documented measurement method.

Do not claim it represents all native-library allocations.

END-TO-END TESTS:

- Digital PDF with a valid table.
- Digital PDF with no extractable tables.
- Scanned-only PDF.
- Mixed digital/scanned PDF.
- Hybrid page with native content and image regions.
- Invalid input.
- Corrupt/encrypted input where reproducibly testable.
- Arithmetic discrepancy.
- Ambiguous multipage stitching.
- Cleanup following successful extraction.
- Cleanup following extraction failure.
- Correct final report fields.
- Correct separation of execution and verification states.

============================================================
SECTION 19 — WINDOWS FILE-HANDLE SAFETY
============================================================

This requirement applies across the entire codebase.

Windows can prevent a file or directory from being deleted
while an open handle still refers to the resource.

Therefore:

1. Always close fitz.Document resources.
2. Always close pdfplumber.PDF resources.
3. Use with-context managers where supported.
4. Otherwise use guaranteed try/finally closure.
5. Do not retain open PDF handles in long-lived model objects.
6. Do not clean workspaces while a PDF handle remains open.
7. Do not suppress PermissionError and then claim cleanup
   succeeded.
8. Test cleanup after normal execution and exceptions.
9. Use a workspace lifetime that is explicit and deterministic.
10. Never delete the original user-provided PDF.

Where full cleanup fails, record a safe diagnostic and report
that failure accurately.

============================================================
SECTION 20 — TEST FIXTURES AND UNIT TESTING
============================================================

Implement backend/tests/conftest.py.

Create reproducible synthetic PDF fixtures with PyMuPDF drawing
primitives and native text.

Prefer controlled test-generated PDFs over undocumented
external samples.

Construct fixtures for:

- Ruled tables.
- Borderless tables.
- Multiple tables.
- Multi-page continuation.
- Repeated headers.
- Duplicate rows.
- Numeric totals.
- Incorrect printed totals.
- Scanned-like image-only content.
- Hybrid text/image content.
- Empty pages.
- Invalid or corrupt input where practical.
- More than 50 pages.

Do not fabricate ground-truth accuracy claims from these tests.

REQUIRED TEST FILES:

test_step_1_1_config.py
test_step_1_2_status_and_gates.py
test_normalizer_integrity.py
test_step_1_3_security_gate.py
test_step_1_4_page_router.py
test_step_1_5_digital_extractor.py
test_step_1_6_table_reconstructor.py
test_phase1_pipeline.py

Use real behavior and meaningful assertions.

Do not make tests pass by returning hardcoded results for
particular fixture filenames.

Do not silently skip tests.

Do not lower meaningful thresholds during debugging simply to
hide defects.

When an edge case cannot be reproduced reliably, document that
limitation and test the closest deterministic equivalent.

============================================================
SECTION 21 — REGRESSION EVALUATION HARNESS
============================================================

Implement:

backend/tests/evaluation/regression_harness.py

The harness must be suitable for a future manually verified
ground-truth PDF corpus.

Provide a documented input format for evaluation cases.

Where applicable, evaluate:

- Expected versus extracted table counts.
- Expected versus extracted row/column structure.
- Expected source values versus extracted values.
- Page attribution.
- Stitch decisions.
- Known structural issues.
- Quality-gate decisions.

Do not assume every layout has reliable table boundaries.

Record mismatches with diagnostic information.

Provide real counts of cases evaluated, passed, and failed.

If no manual ground-truth corpus is available:

UNMEASURED

must be reported for real-world accuracy metrics.

Do not generate synthetic ground truth and present it as a
manually verified reference dataset.

Do not report synthetic fixture test results as real-world
OCR accuracy or real-world document-extraction accuracy.

The harness must be executable using documented commands.

============================================================
SECTION 22 — README AND DEVELOPER EXPERIENCE
============================================================

Create a useful root README.md.

Include:

- Product purpose.
- Phase 1 scope.
- Windows prerequisites.
- Python environment setup.
- Virtual environment creation.
- Dependency installation.
- Running unit tests.
- Running the evaluation harness.
- Using run_phase1_pipeline.
- Meaning of execution states.
- Meaning of verification statuses.
- Why scanned-only documents require OCR.
- Why arithmetic consistency is not proof of source truth.
- Difference between normalization and correction.
- Evidence-backed correction rules.
- Conservative stitching behavior.
- Current extraction limitations.
- Borderless-table risks.
- Wrapped-text risks.
- Custom-font mapping risks.
- Ground-truth evaluation instructions.
- Future phases, clearly marked as not implemented.

Use PowerShell-compatible commands.

Example workflow:

cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
pytest -v

Adapt commands if the actual environment requires another
tested invocation.

Document that thresholds and real-world accuracy metrics remain
UNMEASURED until tested against a manually verified corpus.

Create an appropriate .gitignore.

Ignore:

- Python cache files.
- Virtual environments.
- Temporary workspaces.
- Local settings containing secrets.
- Generated test artifacts.

Do not accidentally ignore source code, tests, configuration
templates, or required project documentation.

============================================================
SECTION 23 — IMPLEMENTATION AND DEBUGGING WORKFLOW
============================================================

Follow this workflow autonomously.

STEP A — INSPECT

Inspect existing files, Python environment, project root, and
repository status.

STEP B — FOUNDATIONS

Implement configuration, state enums, domain contracts,
and quality-gate interfaces.

STEP C — SECURITY AND ROUTING

Implement security_gate.py and page_router.py.

STEP D — NORMALIZATION

Implement numeric, text, identifier, precision, and formula-risk
logic.

STEP E — EXTRACTION

Implement real native digital PDF table extraction.

STEP F — RECONSTRUCTION

Implement conservative multipage evaluation and stitching.

STEP G — VERIFICATION

Implement structural and arithmetic checks plus document-level
quality-gate rules.

STEP H — INTEGRATION

Implement pipeline.py and ensure the complete workflow returns
a DocumentEvaluationReport.

STEP I — TEST IMPLEMENTATION

Implement unit tests, fixtures, and the evaluation harness.

STEP J — RUN TESTS

From the backend directory, run:

pytest -v

Use the actual available Python environment.

Install only the approved dependencies when necessary and
permitted by the environment.

Do not assume imports work merely because the files exist.

STEP K — DEBUG FAILURES

When a test fails:

1. Read the failure output.
2. Identify its root cause.
3. Fix the implementation or a genuinely incorrect test.
4. Keep the specified data and safety contracts intact.
5. Rerun the relevant test.
6. Rerun the complete test suite after significant changes.

Do not alter tests solely to obtain a green result.

Do not claim a failure is fixed until the relevant test has
actually passed.

STEP L — FINAL VALIDATION

Check:

- All required files exist.
- Imports resolve.
- Configuration loads.
- Pydantic models validate.
- Data contracts remain consistent across modules.
- The pipeline processes real synthetic PDFs.
- Arithmetic discrepancies are preserved and flagged.
- Scanned content is not falsely marked absent.
- Stitching decisions are auditable.
- Duplicate rows survive.
- Windows file handles close correctly.
- Temporary workspace cleanup behaves correctly.
- The quality gate evaluates the whole document.
- No unapproved dependencies were introduced.
- No TODO or fake implementation remains.
- No required test is silently skipped.
- No fabricated benchmark or accuracy claims exist.
- README commands match the implemented code.

STEP M — VERIFY AND REPORT

After completing implementation and test execution, report:

1. Final project structure.
2. Files created or modified.
3. Main functionality implemented.
4. End-to-end pipeline behavior.
5. Exact test command executed.
6. Actual passed, failed, and skipped test counts.
7. Any tests that could not execute and why.
8. Any environment constraints.
9. Known limitations.
10. Any incomplete requirement.
11. Confirmation that OCR, LLMs, Excel generation, and frontend
    remain outside Phase 1.
12. Ground-truth evaluation status.
13. Whether the implementation is ready for the next phase,
    and any blocking defects that remain.

Never report success without actual verification.

============================================================
SECTION 24 — NON-NEGOTIABLE ENGINEERING INVARIANTS
============================================================

PRESERVE THE SOURCE:

- raw_value remains immutable.
- Never fabricate source values.
- Never overwrite the original value during normalization.
- Never change a value solely to make arithmetic balance.
- Never discard an uncertain source row silently.

PRESERVE STRUCTURE:

- Never silently delete columns.
- Never shift cells without evidence.
- Never force an ambiguous multipage merge.
- Never deduplicate identical source rows solely by equality.

PRESERVE UNCERTAINTY:

- Never mark unprocessed raster content as confirmed absent.
- Never confuse execution completion with data verification.
- Never describe NOT_APPLICABLE as a passed arithmetic check.
- Never treat internal arithmetic agreement as independent
  proof of every source cell.
- Never treat a synthetic fixture pass as real-world accuracy.
- Never classify a scanned-only document as containing zero tables.
- Never prefix cell values with apostrophes solely for future Excel export.


PRESERVE AUDITABILITY:

- Accepted corrections require evidence.
- Corrections require audit records.
- Correction status must persist.
- Arithmetic discrepancies must remain visible.
- Stitch decisions must record their rationale.

PRESERVE SECURITY AND RESOURCES:

- Validate file type and PDF structure.
- Enforce file-size and page-count limits.
- Prevent path traversal.
- Close handles before workspace cleanup.
- Do not delete original input files.
- Do not log sensitive source contents.
- Avoid unsupported memory guarantees.

PRESERVE ENGINEERING QUALITY:

- No circular dependency design.
- No hidden configuration behavior.
- No unnecessary binary dependency.
- No placeholder feature presented as implemented.
- No test weakening designed only to obtain success.
- No false accuracy claims.
- No silent exception swallowing.

============================================================
SECTION 25 — FINAL EXECUTION DIRECTIVE
============================================================

Begin implementation now.

Inspect the currently opened DocuStruct AI workspace.

Implement the complete Phase 1 specification directly in the
workspace, including the pipeline coordinator.

Work through all steps autonomously:

inspect,
implement,
integrate,
test,
debug,
verify,
report.

Do not stop after generating a plan.

Do not stop after creating isolated modules.

Do not leave the user to manually connect the modules.

Do not generate a fake implementation simply to satisfy the
requested file tree.

Do not claim completion before the actual tests run.

If a tool or environment limitation prevents a required action,
continue the unblocked work and report the exact limitation.

The final deliverable must be a coherent Phase 1 codebase with
consistent contracts, a functioning orchestration entry point,
meaningful tests, and honest status reporting.

END OF MASTER DIRECTIVE