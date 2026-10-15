# DECISIONS.md — Architecture Decision Records

> **Purpose**: Log significant technical decisions and their rationale.

---

## Decisions

### [DECISION-001] Direct Specification Finalization from MASTER_DIRECTIVE.md

**Date**: 2026-10-15
**Status**: Accepted

#### Context
`MASTER_DIRECTIVE.md` was provided in the repository with 25 highly comprehensive, non-negotiable sections specifying the exact mission, domain contracts, dependencies, security rules, and architectural boundaries for DocuStruct AI Phase 1.

#### Decision
Adopt the specifications in `MASTER_DIRECTIVE.md` as the direct source of truth for `.gsd/SPEC.md`, marking it `FINALIZED` to unlock planning and execution immediately.

#### Rationale
The directive provides an exhaustive engineering contract with explicit invariants, leaving zero ambiguity regarding scope, allowed dependencies, memory limits, and target architecture.

#### Consequences
Development will adhere strictly to the Phase 1 scope: no OCR, no LLMs, no web frameworks, and no external binary dependencies.

---

### [DECISION-002] 5-Phase Decomposition for Milestone v1.0

**Date**: 2026-10-15
**Status**: Accepted

#### Context
GSD methodology recommends 3-5 phases per milestone to ensure clear deliverables and forward dependency flow.

#### Decision
Decompose DocuStruct AI Phase 1 into 5 phases:
1. Foundation, Domain Models & Ingestion Security
2. Page Routing, Normalization & Digital Extraction
3. Multipage Reconstruction & Evidence-Gated Corrections
4. Deterministic Arithmetic Consistency & Document Quality Gate
5. Pipeline Integration, Evaluation Harness & Developer Experience

#### Rationale
This layout respects the exact bottom-up dependency order (Config/Models → Ingestion/Extraction → Stitching → Quality Verification → Coordinator/Harness), enabling atomic unit testing and isolated verification at each milestone gate.

---

### [DECISION-003] Adoption of Four Final Specification Clarifications

**Date**: 2026-10-15
**Status**: Accepted

#### Context
Four final clarifications were applied to finalize the Phase 1 specification:
1. Clarifying verification semantics and limits of mathematical evidence.
2. Resolving the scanned-only document contradiction.
3. Making job execution failure and data-quality failure orthogonal.
4. Separating formula-risk detection from Excel export escaping.

#### Decision
Formally incorporate these clarifications in place in `MASTER_DIRECTIVE.md` and add explicit contract tests in `backend/tests/unit/test_quality_gate.py`, while verifying that existing requirements in `.gsd/REQUIREMENTS.md` (REQ-06, REQ-10, REQ-11) and core implementations remain fully aligned without changing the architecture, adding dependencies, or expanding scope:
- VERIFIED is defined conservatively; arithmetic consistency is decoupled from cell-level corroboration.
- Scanned-only documents yield `JobExecutionState.COMPLETED` and `VerificationStatus.REVIEW_REQUIRED` (never `FAILED` under `NO_TABLES_FOUND`).
- Execution failure (`FAILED`) vs data-quality review (`REVIEW_REQUIRED`) are strictly orthogonal.
- Formula-risk detection sets a boolean metadata flag; values are not mutated or prefixed with apostrophes in Phase 1.


#### Rationale
Guarantees mathematical integrity, prevents false failure on scanned documents, preserves source fidelity for downstream export, and cleanly separates pipeline execution from document quality.

---

*Last updated: 2026-10-15*
