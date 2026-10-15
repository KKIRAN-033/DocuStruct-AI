---
phase: 1
plan: 3
wave: 2
depends_on: [1.1, 1.2]
---

# Plan 1.3: PDF Ingestion Security Gate & Workspace Isolation

## Objective
Implement `app/ingestion/security_gate.py` to enforce file-level security validation (size limits, PDF signature, structure integrity, password/zero-page rejection), isolated UUID workspace creation, path-traversal prevention, and Windows-safe resource cleanup that never deletes original user inputs.

## Context
- `.gsd/SPEC.md`
- `.gsd/REQUIREMENTS.md` (REQ-04, REQ-13, NFR-02)
- `MASTER_DIRECTIVE.md` (Sections 10, 19)
- `.gsd/phases/1/RESEARCH.md`

## Tasks

<task type="auto">
  <name>Implement PDF file validation and security inspection</name>
  <files>
    backend/app/ingestion/security_gate.py
    backend/app/ingestion/__init__.py
  </files>
  <action>
    Create backend/app/ingestion/security_gate.py with typed exception hierarchy:
    - SecurityGateError(Exception)
    - FileNotFoundError / InvalidFileTypeError
    - FileSizeExceededError (over 25 MiB / 26,214,400 bytes)
    - InvalidPDFSignatureError (missing %PDF- header)
    - EncryptedPDFError (password-protected or encrypted PDF)
    - CorruptPDFError (fails PyMuPDF parsing)
    - PageCountExceededError (doc.page_count == 0 or doc.page_count > 50)
    - PathTraversalError (workspace escape attempt)

    Implement inspect_and_validate_pdf(file_path: Path, settings: AppSettings) -> dict:
    1. Check file_path exists and is a regular file.
    2. Check file size <= settings.max_file_size_bytes (25 MiB).
    3. Read header bytes (first 1024 bytes) to verify presence of b"%PDF-".
    4. Open with fitz.open() inside a strict try/finally block:
       - Check doc.is_encrypted or doc.needs_pass -> raise EncryptedPDFError.
       - Check doc.page_count == 0 -> raise PageCountExceededError("Zero-page PDF").
       - Check doc.page_count > settings.max_pdf_pages (50) -> raise PageCountExceededError.
       - Return metadata dict: page_count, format, is_encrypted, file_size_bytes.
       - finally: doc.close() guaranteed.
    5. Do not log confidential file contents.
  </action>
  <verify>
    powershell -Command "python -c 'from app.ingestion.security_gate import inspect_and_validate_pdf; print(inspect_and_validate_pdf)'"
  </verify>
  <done>
    PDF security checks reject missing, empty, oversized, non-PDF, encrypted, zero-page, and >50 page inputs; all fitz document handles are guaranteed closed in finally blocks.
  </done>
</task>

<task type="auto">
  <name>Implement workspace isolation, path sanitization, and cleanup</name>
  <files>
    backend/app/ingestion/security_gate.py
  </files>
  <action>
    Extend backend/app/ingestion/security_gate.py with workspace management:
    1. sanitize_filename(filename: str) -> str:
       Use pathlib.Path(filename).name, strip path separators and null bytes.
    2. create_job_workspace(job_id: str, base_dir: Path) -> Path:
       - Generate UUID-based job directory under base_dir: base_dir / str(job_id).
       - Validate containment: verify workspace.resolve().is_relative_to(base_dir.resolve()).
       - Create directory safely with exist_ok=False.
    3. cleanup_job_workspace(workspace_dir: Path, original_input_path: Optional[Path] = None) -> bool:
       - Explicit safety invariant: original_input_path must never be deleted.
       - Verify original_input_path is not inside workspace_dir before deletion; if it is, do not delete it.
       - Attempt removal of workspace_dir. If Windows file locking causes PermissionError, catch it, log safe diagnostic, and return False instead of crashing or falsely reporting success.
  </action>
  <verify>
    powershell -Command "python -c 'from app.ingestion.security_gate import sanitize_filename, create_job_workspace; print(sanitize_filename(\"../../test.pdf\"))'"
  </verify>
  <done>
    Filenames sanitized; workspaces isolated with UUIDs; path traversal rejected; cleanup safely handles Windows file locks and guarantees original input is never deleted.
  </done>
</task>

## Success Criteria
- [ ] Complete security gate validation chain implemented with typed exceptions.
- [ ] Explicit rejection of 25 MiB+, 50+ pages, zero-page, corrupt, and encrypted PDFs.
- [ ] UUID workspace isolation with path traversal checks.
- [ ] Original user input file strictly protected against deletion.
