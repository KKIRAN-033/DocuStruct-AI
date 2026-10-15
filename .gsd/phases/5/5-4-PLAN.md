---
phase: 5
plan: 4
wave: 2
depends_on: [5.1, 5.2]
files_modified:
  - README.md
  - .gitignore
autonomous: true
must_haves:
  truths:
    - "README.md provides complete project documentation matching all Section 22 requirements."
    - "Future phases are clearly marked as unbuilt."
    - "PowerShell-compatible environment setup and test commands are documented."
    - "Meaning of execution states, verification statuses, disclaimers, and UNMEASURED accuracy are documented."
    - ".gitignore covers cache, venv, workspaces, and test artifacts without ignoring code or docs."
  artifacts:
    - "README.md exists and is comprehensive"
    - ".gitignore is refined"
---

# Plan 5.4: Developer Documentation & Project Configuration

## Objective
Author comprehensive developer documentation in root `README.md` and refine `.gitignore` to satisfy all requirements of MASTER_DIRECTIVE.md Section 22 and REQ-13/NFR-04.

## Context
- `MASTER_DIRECTIVE.md` (Section 22)
- `.gsd/SPEC.md` (Goal 5)
- `.gsd/REQUIREMENTS.md` (REQ-13, NFR-04)
- `.gsd/phases/5/RESEARCH.md`
- `README.md`
- `.gitignore`

## Tasks

<task type="auto">
  <name>Author root README.md</name>
  <files>
    README.md
  </files>
  <action>
    Create root `README.md` containing:
    1. Title, Tagline ("Extract. Verify. Correct. Deliver."), and Overview.
    2. Phase 1 Architecture & Scope:
       - What is implemented in Phase 1 (Steps 1.1 through 1.6).
       - Explicit callout of unbuilt future phases (OCR engines, LLM post-processing, vision models, REST API, Web UI).
    3. Windows Environment Setup:
       - Windows 10/11, Python 3.11 target (compatible with >=3.10, <3.13), 8-16 GB RAM, CPU-only.
       - Exact PowerShell setup commands:
         ```powershell
         python -m venv .venv
         .\.venv\Scripts\Activate.ps1
         python -m pip install -r backend/requirements.txt
         ```
    4. Running Unit Tests:
       ```powershell
       python -m pytest -v backend/tests
       ```
    5. Running the Ground-Truth Evaluation Harness:
       ```powershell
       python -m tests.evaluation.regression_harness
       ```
       - Explain why uncalibrated real-world accuracy metrics remain `UNMEASURED`.
    6. Architecture & Behavioral Contracts:
       - Separation of `JobExecutionState` and `VerificationStatus`.
       - Mandatory Verbatim Disclaimer and why arithmetic consistency does not prove source truth.
       - Normalization vs. Evidence-Gated Correction.
       - Conservative Multipage Table Stitching (7 factors).
       - Extraction limitations (borderless tables, wrapped text, custom fonts).
       - Windows file-handle safety.
  </action>
  <verify>
    powershell -Command "Test-Path README.md"
  </verify>
  <done>
    `README.md` provides complete, professional, and accurate developer documentation.
  </done>
</task>

<task type="auto">
  <name>Refine .gitignore configuration</name>
  <files>
    .gitignore
  </files>
  <action>
    Review and update `.gitignore` to ensure it ignores:
    - Python bytecode: `__pycache__/`, `*.py[cod]`
    - Virtual environments: `.venv/`, `venv/`, `env/`
    - Temporary test/runtime workspaces: `docustruct_workspaces/`, `*.tmp`
    - IDE and OS caches: `.idea/`, `.vscode/`, `Thumbs.db`, `.DS_Store`
    - Pytest and coverage artifacts: `.pytest_cache/`, `.coverage`, `htmlcov/`
    - Local secrets and environment files: `.env`, `local_settings.yaml`
    Confirm no source code, tests, configuration templates, or GSD files are ignored.
  </action>
  <verify>
    powershell -Command "git status --ignored"
  </verify>
  <done>
    `.gitignore` properly excludes temporary and environment files while tracking all necessary project artifacts.
  </done>
</task>

## Success Criteria
- [ ] Root `README.md` covers all required sections with tested PowerShell commands.
- [ ] Future phases clearly documented as not implemented.
- [ ] Core architecture contracts and reason codes thoroughly documented.
- [ ] `.gitignore` refined and verified.
