"""
Phase 2 — Normalizer Tests

Covers whitespace normalisation, numeric parsing (standard,
Indian grouping, accounting negatives), identifier preservation,
formula-risk detection ordering, and cell-level normalisation.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.extraction.normalizer import (
    detect_formula_risk,
    is_likely_identifier,
    normalize_cell,
    normalize_whitespace,
    parse_numeric_value,
)
from app.models.state import DataType


# ─── Whitespace ──────────────────────────────────────────────────────────


class TestNormalizeWhitespace:
    def test_strips_leading_trailing(self):
        assert normalize_whitespace("  hello  ") == "hello"

    def test_collapses_internal(self):
        assert normalize_whitespace("hello   world") == "hello world"

    def test_mixed_whitespace(self):
        assert normalize_whitespace("\t hello \n world \t") == "hello world"

    def test_empty_string(self):
        assert normalize_whitespace("") == ""

    def test_only_whitespace(self):
        assert normalize_whitespace("   \t\n  ") == ""


# ─── Numeric Parsing ────────────────────────────────────────────────────


class TestParseNumericValue:
    # --- Plain numbers ---
    def test_plain_integer(self):
        norm, dec, dt = parse_numeric_value("42")
        assert dec == Decimal("42")
        assert dt == DataType.INTEGER

    def test_plain_decimal(self):
        norm, dec, dt = parse_numeric_value("3.14")
        assert dec == Decimal("3.14")
        assert dt == DataType.DECIMAL

    def test_negative_integer(self):
        norm, dec, dt = parse_numeric_value("-100")
        assert dec == Decimal("-100")

    def test_negative_decimal(self):
        norm, dec, dt = parse_numeric_value("-450.50")
        assert dec == Decimal("-450.50")
        assert dt == DataType.DECIMAL

    # --- Standard grouping ---
    def test_standard_grouped(self):
        norm, dec, dt = parse_numeric_value("1,234,567.89")
        assert dec == Decimal("1234567.89")
        assert norm == "1234567.89"

    def test_negative_standard_grouped(self):
        norm, dec, dt = parse_numeric_value("-1,234.56")
        assert dec == Decimal("-1234.56")

    # --- Indian grouping ---
    def test_indian_grouped(self):
        norm, dec, dt = parse_numeric_value("12,34,567.89")
        assert dec == Decimal("1234567.89")

    def test_indian_grouped_simple(self):
        norm, dec, dt = parse_numeric_value("1,00,000")
        assert dec == Decimal("100000")

    # --- Accounting negatives ---
    def test_parenthesised_negative(self):
        norm, dec, dt = parse_numeric_value("(450.50)")
        assert dec == Decimal("-450.50")
        assert norm == "-450.50"

    def test_trailing_minus(self):
        norm, dec, dt = parse_numeric_value("450.50-")
        assert dec == Decimal("-450.50")
        assert norm == "-450.50"

    def test_parenthesised_with_grouping(self):
        norm, dec, dt = parse_numeric_value("(1,234.56)")
        assert dec == Decimal("-1234.56")

    # --- High precision ---
    def test_high_precision(self):
        norm, dec, dt = parse_numeric_value("3.141592653")
        assert dt == DataType.HIGH_PRECISION_DECIMAL
        assert dec == Decimal("3.141592653")

    # --- Non-numeric ---
    def test_pure_text_returns_none(self):
        assert parse_numeric_value("hello") is None

    def test_malformed_grouping_returns_none(self):
        assert parse_numeric_value("1,23,45") is None

    def test_empty_returns_none(self):
        assert parse_numeric_value("") is None

    # --- Decimal precision (never binary float) ---
    def test_decimal_not_float(self):
        _, dec, _ = parse_numeric_value("0.1")
        assert isinstance(dec, Decimal)
        assert dec == Decimal("0.1")
        # Verify no binary float round-trip
        assert str(dec) == "0.1"


# ─── Identifier Detection ───────────────────────────────────────────────


class TestIsLikelyIdentifier:
    def test_leading_zero_digits(self):
        assert is_likely_identifier("0012345") is True

    def test_no_leading_zero(self):
        assert is_likely_identifier("12345") is False

    def test_header_keyword_match(self):
        assert is_likely_identifier("12345", "Invoice No.") is True

    def test_non_digit_not_identifier(self):
        assert is_likely_identifier("ABC123") is False


# ─── Formula-Risk Detection ─────────────────────────────────────────────


class TestDetectFormulaRisk:
    def test_equals_prefix(self):
        assert detect_formula_risk("=SUM(A1)", is_numeric=False) is True

    def test_plus_prefix(self):
        assert detect_formula_risk("+cmd", is_numeric=False) is True

    def test_at_prefix(self):
        assert detect_formula_risk("@SUM", is_numeric=False) is True

    def test_tab_prefix(self):
        assert detect_formula_risk("\tcmd", is_numeric=False) is True

    def test_numeric_negative_never_triggers(self):
        """Critical invariant: -450.50 is numeric, never formula risk."""
        assert detect_formula_risk("-450.50", is_numeric=True) is False

    def test_minus_prefix_non_numeric(self):
        """Non-numeric dash-prefixed text IS formula risk."""
        assert detect_formula_risk("-cmd|' '!A1", is_numeric=False) is True

    def test_normal_text_no_risk(self):
        assert detect_formula_risk("hello", is_numeric=False) is False

    def test_empty_no_risk(self):
        assert detect_formula_risk("", is_numeric=False) is False


# ─── Cell Normalisation ─────────────────────────────────────────────────


class TestNormalizeCell:
    def test_raw_value_immutable(self):
        raw = "  1,234.56  "
        result = normalize_cell(raw)
        assert result["raw_value"] == raw

    def test_numeric_cell(self):
        result = normalize_cell("1,234.56")
        assert result["numeric_decimal"] == Decimal("1234.56")
        assert result["data_type"] == DataType.DECIMAL
        assert result["formula_risk_detected"] is False

    def test_identifier_leading_zeros(self):
        result = normalize_cell("0012345", col_header="Account")
        assert result["data_type"] == DataType.IDENTIFIER
        assert result["normalized_value"] == "0012345"

    def test_empty_cell(self):
        result = normalize_cell("")
        assert result["data_type"] == DataType.EMPTY

    def test_formula_risk_string(self):
        result = normalize_cell("=SUM(A1:A10)")
        assert result["formula_risk_detected"] is True
        assert result["data_type"] == DataType.STRING

    def test_negative_number_no_formula_risk(self):
        """Critical: negative number must NOT trigger formula risk."""
        result = normalize_cell("-450.50")
        assert result["formula_risk_detected"] is False
        assert result["numeric_decimal"] == Decimal("-450.50")

    def test_parenthesised_accounting(self):
        result = normalize_cell("(1,234.56)")
        assert result["numeric_decimal"] == Decimal("-1234.56")
        assert result["formula_risk_detected"] is False

    def test_whitespace_only(self):
        result = normalize_cell("   \t  ")
        assert result["data_type"] == DataType.EMPTY
        assert result["normalized_value"] == ""
