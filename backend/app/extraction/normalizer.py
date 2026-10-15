"""
DocuStruct AI — Deterministic Normalizer & Formula-Risk Detection

Meaning-preserving normalisation of extracted cell text: whitespace
cleanup, numeric grouping (standard and Indian), accounting negatives,
exact Decimal conversion, identifier leading-zero preservation, and
formula-risk prefix detection.

Design invariants (from MASTER_DIRECTIVE.md Section 12):
    - ``raw_value`` is never mutated or overwritten.
    - ``Decimal`` values are constructed via ``Decimal(str)``, never
      through binary ``float``.
    - Valid numeric negatives (``-450.50``) never trigger formula-risk.
    - No apostrophes are prepended; cell values are never mutated
      solely for formula-risk detection.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from app.models.state import DataType


# ═══════════════════════════════════════════════════════════════════════════
# Whitespace normalisation
# ═══════════════════════════════════════════════════════════════════════════


def normalize_whitespace(text: str) -> str:
    """Strip leading/trailing whitespace and collapse internal runs.

    Returns the cleaned string without altering meaningful content.
    """
    return " ".join(text.split())


# ═══════════════════════════════════════════════════════════════════════════
# Numeric parsing
# ═══════════════════════════════════════════════════════════════════════════

# Standard grouping: 1,234 or 1,234,567.89
_RE_STANDARD_GROUPED = re.compile(
    r"^-?(?:\d{1,3})(?:,\d{3})*(?:\.\d+)?$"
)

# Indian grouping: 12,34,567.89 — first group from right is 3 digits,
# subsequent groups are 2 digits.
_RE_INDIAN_GROUPED = re.compile(
    r"^-?(?:\d{1,2})(?:,\d{2})*,\d{3}(?:\.\d+)?$"
)

# Plain decimal / integer (no grouping commas)
_RE_PLAIN_NUMBER = re.compile(
    r"^-?\d+(?:\.\d+)?$"
)

# Accounting trailing minus: 450.50-
_RE_TRAILING_MINUS = re.compile(
    r"^(\d[\d,]*(?:\.\d+)?)-$"
)

# Accounting parenthesised negative: (450.50) or (1,234.56)
_RE_PAREN_NEGATIVE = re.compile(
    r"^\((\d[\d,]*(?:\.\d+)?)\)$"
)


def _classify_decimal_type(decimal_str: str) -> DataType:
    """Determine whether a numeric string is INTEGER, DECIMAL, or
    HIGH_PRECISION_DECIMAL."""
    if "." in decimal_str:
        _, frac = decimal_str.rsplit(".", 1)
        if len(frac) > 4:
            return DataType.HIGH_PRECISION_DECIMAL
        return DataType.DECIMAL
    return DataType.INTEGER


def _strip_valid_grouping(text: str) -> Optional[str]:
    """Attempt to strip grouping commas if the pattern matches standard
    or Indian grouping.  Returns the bare numeric string or ``None``
    if the grouping is invalid/malformed."""
    # Check sign prefix
    sign = ""
    body = text
    if body.startswith("-"):
        sign = "-"
        body = body[1:]

    # Standard grouping first
    unsigned_candidate = sign + body
    if _RE_STANDARD_GROUPED.match(unsigned_candidate):
        return unsigned_candidate.replace(",", "")

    # Indian grouping
    if _RE_INDIAN_GROUPED.match(unsigned_candidate):
        return unsigned_candidate.replace(",", "")

    # Contains commas but doesn't match valid patterns → malformed
    if "," in body:
        return None

    return None  # No commas and not handled → shouldn't reach here


def parse_numeric_value(
    text: str,
) -> Optional[tuple[str, Decimal, DataType]]:
    """Attempt to parse a string as a numeric value.

    Parameters
    ----------
    text : str
        Whitespace-stripped candidate text.

    Returns
    -------
    tuple[str, Decimal, DataType] or None
        ``(normalised_string, Decimal_value, DataType)`` when
        successfully parsed, otherwise ``None``.
    """
    if not text:
        return None

    # --- 1. Parenthesised accounting negative: (450.50) ---
    m = _RE_PAREN_NEGATIVE.match(text)
    if m:
        inner = m.group(1)
        # Inner may contain grouping commas
        if "," in inner:
            stripped = _strip_valid_grouping(inner)
            if stripped is None:
                return None
            bare = stripped
        else:
            bare = inner
        norm_str = "-" + bare
        try:
            dec = Decimal(norm_str)
        except InvalidOperation:
            return None
        return (norm_str, dec, _classify_decimal_type(norm_str))

    # --- 2. Trailing minus: 450.50- ---
    m = _RE_TRAILING_MINUS.match(text)
    if m:
        body = m.group(1)
        if "," in body:
            stripped = _strip_valid_grouping(body)
            if stripped is None:
                return None
            bare = stripped
        else:
            bare = body
        norm_str = "-" + bare
        try:
            dec = Decimal(norm_str)
        except InvalidOperation:
            return None
        return (norm_str, dec, _classify_decimal_type(norm_str))

    # --- 3. Plain number (no commas) ---
    if _RE_PLAIN_NUMBER.match(text):
        try:
            dec = Decimal(text)
        except InvalidOperation:
            return None
        return (text, dec, _classify_decimal_type(text))

    # --- 4. Grouped number (standard or Indian) ---
    if "," in text:
        stripped = _strip_valid_grouping(text)
        if stripped is None:
            return None  # Malformed grouping
        try:
            dec = Decimal(stripped)
        except InvalidOperation:
            return None
        return (stripped, dec, _classify_decimal_type(stripped))

    return None


# ═══════════════════════════════════════════════════════════════════════════
# Identifier detection
# ═══════════════════════════════════════════════════════════════════════════

_IDENTIFIER_HEADERS = frozenset({
    "account", "invoice", "gstin", "pan", "aadhaar", "phone",
    "id", "code", "ref", "no", "no.",
})

_RE_LEADING_ZERO_DIGITS = re.compile(r"^0\d+$")


def is_likely_identifier(
    text: str,
    col_header: Optional[str] = None,
) -> bool:
    """Heuristic: is this cell value likely an identifier?

    Leading zeros in a purely-digit string are a strong signal.
    Header keywords provide additional context.
    """
    if _RE_LEADING_ZERO_DIGITS.match(text):
        return True
    if col_header is not None and text.isdigit():
        # Check each word in the header against known identifier keywords
        for word in col_header.strip().lower().replace(".", " ").split():
            if word in _IDENTIFIER_HEADERS:
                return True
    return False


# ═══════════════════════════════════════════════════════════════════════════
# Formula-risk detection
# ═══════════════════════════════════════════════════════════════════════════

_FORMULA_RISK_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def detect_formula_risk(text: str, is_numeric: bool) -> bool:
    """Check whether a cell value starts with a spreadsheet formula prefix.

    Parameters
    ----------
    text : str
        The (whitespace-stripped) cell text.
    is_numeric : bool
        ``True`` when the value has been successfully parsed as a
        number.  Numeric values **never** trigger formula-risk.

    Returns
    -------
    bool
        ``True`` when a formula-risk prefix is detected on a
        non-numeric cell.
    """
    if is_numeric:
        return False
    if not text:
        return False
    return text[0] in _FORMULA_RISK_PREFIXES


# ═══════════════════════════════════════════════════════════════════════════
# Cell-level normalisation entry point
# ═══════════════════════════════════════════════════════════════════════════


def normalize_cell(
    raw_text: str,
    col_header: Optional[str] = None,
) -> dict[str, Any]:
    """Normalise a single extracted cell value.

    Returns a dictionary suitable for constructing or updating a
    :class:`CellRecord`.

    Keys: ``raw_value``, ``normalized_value``, ``accepted_value``,
    ``numeric_decimal``, ``data_type``, ``formula_risk_detected``.
    """
    result: dict[str, Any] = {
        "raw_value": raw_text,
        "normalized_value": None,
        "accepted_value": "",
        "numeric_decimal": None,
        "data_type": DataType.STRING,
        "formula_risk_detected": False,
    }

    clean = normalize_whitespace(raw_text)

    # Empty
    if not clean:
        result["normalized_value"] = ""
        result["accepted_value"] = ""
        result["data_type"] = DataType.EMPTY
        return result

    # Identifier check (must precede numeric parsing to preserve
    # leading zeros like "0012345")
    if is_likely_identifier(clean, col_header):
        result["normalized_value"] = clean
        result["accepted_value"] = clean
        result["data_type"] = DataType.IDENTIFIER
        result["formula_risk_detected"] = detect_formula_risk(
            clean, is_numeric=False,
        )
        return result

    # Numeric parsing
    parsed = parse_numeric_value(clean)
    if parsed is not None:
        norm_str, dec_val, dtype = parsed
        result["normalized_value"] = norm_str
        result["accepted_value"] = norm_str
        result["numeric_decimal"] = dec_val
        result["data_type"] = dtype
        # Numeric values never trigger formula-risk
        result["formula_risk_detected"] = False
        return result

    # Plain string fallback
    result["normalized_value"] = clean
    result["accepted_value"] = clean
    result["data_type"] = DataType.STRING
    result["formula_risk_detected"] = detect_formula_risk(
        clean, is_numeric=False,
    )
    return result
