---
phase: 3
plan: 3
wave: 2
depends_on: [3.1, 3.2]
files_modified:
  - backend/tests/unit/test_step_1_6_table_reconstructor.py
autonomous: true
must_haves:
  truths:
    - "Confirmed continuation stitches adjacent tables and updates row indices seamlessly."
    - "Rejected separate tables preserve both tables independently with audit reasons."
    - "Ambiguous column counts trigger STITCH_REVIEW_REQUIRED and preserve separate tables."
    - "1-row and 2-row repeated headers are stripped while logging stripped count."
    - "Legitimate duplicate rows are preserved without deduplication."
    - "Corrections from unapproved evidence sources are rejected."
    - "Algebraic inferences are stored only in inferred_candidate_value with ILLEGIBLE_OR_MISSING status."
  artifacts:
    - "backend/tests/unit/test_step_1_6_table_reconstructor.py exists"
---

# Plan 3.3: Phase 3 Unit Test Suite

## Objective
Author comprehensive unit tests in `backend/tests/unit/test_step_1_6_table_reconstructor.py` validating the 7 decision factors, multiline header stripping, multipage reconstruction, duplicate preservation, and evidence-gated cell corrections in accordance with MASTER_DIRECTIVE.md Sections 14 and 15 and REQ-08/REQ-09.

## Context
- `MASTER_DIRECTIVE.md` (Sections 14, 15, 20)
- `.gsd/SPEC.md` (Goals 2, 3)
- `.gsd/REQUIREMENTS.md` (REQ-08, REQ-09, REQ-13)
- `.gsd/phases/3/RESEARCH.md`
- `backend/app/extraction/table_reconstructor.py`
- `backend/app/models/domain.py`
- `backend/app/models/state.py`

## Tasks

<task type="auto">
  <name>Author unit tests for 7-factor evaluation and table stitching</name>
  <files>
    backend/tests/unit/test_step_1_6_table_reconstructor.py
  </files>
  <action>
    Create `backend/tests/unit/test_step_1_6_table_reconstructor.py` with test classes:
    1. `TestColumnOverlapAndGeometry`:
       - Overlap of identical column bounds returns 1.0.
       - Disjoint or non-overlapping column bounds return 0.0.
       - Tables on different page margins normalize correctly relative to table span.
    2. `TestHeaderSimilarityAndStripping`:
       - Single-row repeated header matching upper table is stripped (`stripped == 1`).
       - Two-row repeated header matching upper table is stripped (`stripped == 2`).
       - Data row that does not match header threshold is NOT stripped (`stripped == 0`).
    3. `Test7FactorDecisionEngine`:
       - Sequential pages with matching columns, overlap >= 0.75, type compatibility >= 0.85 -> `STITCH_CONFIRMED`.
       - Non-sequential pages (e.g. page 1 and page 3) -> `STITCH_REJECTED`.
       - Differing column counts with "Total" ending -> `STITCH_REJECTED`.
       - Differing column counts with plausible layout -> `STITCH_REVIEW_REQUIRED`.
       - Serial continuity ($1, 2, 3 \to 4, 5, 6$) supports confirmed stitch.
    4. `TestMultipageReconstruction`:
       - Two-page table continuation combines `source_pages=[1, 2]`.
       - Row indices in lower table are re-indexed to continue from upper table length.
       - Duplicate rows across pages are strictly preserved (no deduplication).
    
    AVOID: Asserting `assert True` or trivial checks; verify concrete row counts, cell accepted values, and enum values.
  </action>
  <verify>
    powershell -Command "pytest -v backend/tests/unit/test_step_1_6_table_reconstructor.py -k 'Test7FactorDecisionEngine or TestMultipageReconstruction'"
  </verify>
  <done>
    `test_step_1_6_table_reconstructor.py` passes 100% of test cases verifying stitching decisions, header stripping, and row re-indexing.
  </done>
</task>

<task type="auto">
  <name>Author unit tests for evidence-gated cell corrections and audit logging</name>
  <files>
    backend/tests/unit/test_step_1_6_table_reconstructor.py
  </files>
  <action>
    In `backend/tests/unit/test_step_1_6_table_reconstructor.py`, add test classes:
    1. `TestEvidenceGatedCorrections`:
       - Valid evidence source (`NATIVE_PDF_CHAR_STREAM`) updates `accepted_value` and sets status `CORRECTED_WITH_EVIDENCE`.
       - `raw_value` is strictly immutable during correction.
       - `CorrectionRecord` contains original raw value, accepted value, source, and decision.
       - Unapproved evidence source (e.g. `LLM_GUESS`, `HEURISTIC`) is rejected.
    2. `TestProhibitedAutoBalancingAndInference`:
       - Discrepancy (e.g. $100 + 200 = 350$) does NOT auto-modify $350 \to 300$.
       - Algebraic deduction sets `inferred_candidate_value`, leaves `accepted_value` unchanged, and sets status `ILLEGIBLE_OR_MISSING`.
       - `CorrectionRecord` records `inferred_candidate_only=True`.
    3. `TestStitchAuditEvents`:
       - Every stitch evaluation records `StitchAuditEvent` with upper/lower table IDs, pages, scores, and reasons.
  </action>
  <verify>
    powershell -Command "pytest -v backend/tests/unit/test_step_1_6_table_reconstructor.py"
  </verify>
  <done>
    `test_step_1_6_table_reconstructor.py` passes 100% of test cases covering evidence-gated corrections, forbidden auto-balancing, and audit logs.
  </done>
</task>

## Success Criteria
- [ ] All 7 decision factors tested with concrete table fixtures.
- [ ] Sliding-window header stripping (1 and 2 rows) validated.
- [ ] Non-deduplication of identical transaction rows proven.
- [ ] Evidence-gated correction contracts enforced against unapproved sources.
- [ ] Prohibition of auto-balancing totals verified.
- [ ] Zero unclosed file handles or warnings.
