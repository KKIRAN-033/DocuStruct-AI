---
phase: 2
plan: 2
wave: 1
depends_on: []
files_modified:
  - backend/app/extraction/normalizer.py
  - backend/app/extraction/__init__.py
autonomous: true
must_haves:
  truths:
    - "raw_value is never mutated or overwritten during normalization."
    - "Standard and Indian number groupings are normalized deterministically."
    - "Accounting negatives (-450.50, 450.50-, (450.50)) normalize to Decimal('-450.50')."
    - "Decimal values are never converted through binary float."
    - "Identifier leading zeros ('0012345') are strictly preserved."
    - "Valid numeric negatives (-450.50) do not trigger formula_risk_detected."
    - "Nonnumeric strings starting with =, +, -, @, \\t, \\r trigger formula_risk_detected without prepending apostrophes or mutating cell values."
  artifacts:
    - "backend/app/extraction/normalizer.py exists"
    - "backend/app/extraction/__init__.py exists"
---

# Plan 2.2: Deterministic Normalizer & Formula-Risk Boundary

## Objective
Implement `backend/app/extraction/normalizer.py` to provide meaning-preserving whitespace and numeric normalization, exact Decimal conversions, identifier leading-zero preservation, and formula-risk prefix detection without mutating source cell values, in compliance with MASTER_DIRECTIVE.md Section 12 and REQ-06.

## Context
- `MASTER_DIRECTIVE.md` (Section 12)
- `.gsd/SPEC.md` (Goal 2)
- `.gsd/REQUIREMENTS.md` (REQ-06, CON-03, CON-04)
- `.gsd/phases/2/RESEARCH.md`
- `backend/app/models/state.py`
- `backend/app/models/domain.py`

## Tasks

<task type="auto">
  <name>Implement text, whitespace, and numeric grouping normalizers</name>
  <files>
    backend/app/extraction/normalizer.py
    backend/app/extraction/__init__.py
  </files>
  <action>
    Create `backend/app/extraction/normalizer.py` with numeric parsing utilities:
    1. `normalize_whitespace(text: str) -> str`:
       - Strip leading and trailing whitespace.
       - Collapse multiple consecutive spaces/tabs into a single space if not within a preserved verbatim token.
    2. `parse_numeric_value(text: str) -> Optional[tuple[str, Decimal, DataType]]`:
       - Recognize clean integers (`DataType.INTEGER`).
       - Recognize decimal numbers with standard dot notation (`DataType.DECIMAL`).
       - Recognize high-precision decimals (>4 decimal places) as `DataType.HIGH_PRECISION_DECIMAL`.
       - Recognize standard grouping: e.g. `1,234,567.89` (comma followed by 3 digits).
       - Recognize Indian grouping: e.g. `12,34,567.89` (first comma at 3 digits from right, subsequent commas every 2 digits).
       - Recognize negative formats:
         * Leading minus: `-450.50`
         * Trailing minus: `450.50-`
         * Parenthesized accounting negative: `(450.50)`
       - Convert all recognized negatives to standard leading minus format (e.g. `"-450.50"`).
       - Return `(normalized_str, Decimal(normalized_str), data_type)`.
       - Reject malformed grouping (e.g. `12,345,67.89`): do not strip commas; return `None` so it is treated as a raw string.
       - NEVER use binary `float` for `Decimal` construction.
    3. Initialize `backend/app/extraction/__init__.py` with clean imports.

    AVOID: Stripping commas blindly with `.replace(",", "")` without verifying standard or Indian grouping regexes, as this corrupts malformed numeric strings and text.
  </action>
  <verify>
    powershell -Command "python -c 'from app.extraction.normalizer import parse_numeric_value; print(parse_numeric_value(\"(450.50)\"))'"
  </verify>
  <done>
    `parse_numeric_value` parses standard grouping, Indian grouping, parenthesized negatives, and trailing minus numbers into `(str, Decimal, DataType)` without float conversion.
  </done>
</task>

<task type="auto">
  <name>Implement identifier preservation, formula-risk detection, and normalize_cell</name>
  <files>
    backend/app/extraction/normalizer.py
    backend/app/extraction/__init__.py
  </files>
  <action>
    In `backend/app/extraction/normalizer.py`, implement:
    1. `is_likely_identifier(text: str, col_header: Optional[str] = None) -> bool`:
       - Check if `col_header` matches identifier keywords case-insensitively: `Account`, `Invoice`, `GSTIN`, `PAN`, `Aadhaar`, `Phone`, `ID`, `Code`, `Ref`, `No`.
       - Check if `text` has leading zeros (e.g. `re.match(r"^0\d+$", text)`).
       - If leading zeros are present, classify as `DataType.IDENTIFIER` to prevent numeric conversion from truncating zeros.
    2. `detect_formula_risk(text: str, is_numeric: bool) -> bool`:
       - If `is_numeric` is `True`, return `False` unconditionally (valid numeric negatives like `-450.50` MUST NOT trigger formula-risk).
       - If `is_numeric` is `False`, check if stripped `text` starts with any of: `=`, `+`, `-`, `@`, `\t` (tab), or `\r` (carriage return).
       - Return `True` if any prefix matches, `False` otherwise.
       - NEVER prepend an apostrophe (`'`) or mutate the input text.
    3. `normalize_cell(raw_text: str, col_header: Optional[str] = None) -> dict[str, Any]`:
       - Keep `raw_value = raw_text` immutable.
       - If `raw_text.strip() == ""`:
         * `normalized_value = ""`, `accepted_value = ""`, `numeric_decimal = None`, `data_type = DataType.EMPTY`, `formula_risk_detected = False`.
       - Else check `is_likely_identifier(clean_text, col_header)`:
         * If `True`: `normalized_value = clean_text`, `accepted_value = clean_text`, `numeric_decimal = None`, `data_type = DataType.IDENTIFIER`, check formula-risk with `is_numeric=False`.
       - Else attempt `parse_numeric_value(clean_text)`:
         * If parsed: `(norm_str, dec_val, dtype)`, `normalized_value = norm_str`, `accepted_value = norm_str`, `numeric_decimal = dec_val`, `data_type = dtype`, `formula_risk_detected = False`.
         * If not numeric: `normalized_value = clean_text`, `accepted_value = clean_text`, `numeric_decimal = None`, `data_type = DataType.STRING`, check formula-risk with `is_numeric=False`.
       - Return dict with keys: `raw_value`, `normalized_value`, `accepted_value`, `numeric_decimal`, `data_type`, `formula_risk_detected`.
    4. Export `normalize_cell`, `parse_numeric_value`, `normalize_whitespace`, `detect_formula_risk` in `backend/app/extraction/__init__.py`.

    AVOID: Prepending an apostrophe (`'`) to strings that trigger formula risk; spreadsheet escaping belongs exclusively at Phase 3 Excel export boundaries.
  </action>
  <verify>
    powershell -Command "python -c 'from app.extraction.normalizer import normalize_cell; c = normalize_cell(\"-450.50\"); print(c[\"formula_risk_detected\"] == False); f = normalize_cell(\"=SUM(A1:A5)\"); print(f[\"formula_risk_detected\"] == True)'"
  </verify>
  <done>
    `normalize_cell` preserves `raw_value`, preserves identifier leading zeros, flags nonnumeric formula prefixes, and does NOT flag valid numeric negatives.
  </done>
</task>

## Success Criteria
- [ ] Whitespace normalization implemented without altering meaningful content.
- [ ] Standard and Indian number groupings supported.
- [ ] Accounting negatives (`-450.50`, `450.50-`, `(450.50)`) correctly parsed into `Decimal`.
- [ ] Identifier columns preserve significant leading zeros (`0012345`).
- [ ] Formula-risk prefixes (`=`, `+`, `-`, `@`, `\t`, `\r`) flagged for nonnumeric cells.
- [ ] Valid numeric negatives strictly excluded from formula-risk flagging.
- [ ] No apostrophes prepended and no cell values mutated.
