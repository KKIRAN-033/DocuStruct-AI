"""
DocuStruct AI — Unit Tests: Normalizer Integrity

Verifies deterministic cell normalization, standard and Indian grouping,
accounting negative formats, exact Decimal conversions without float
round-tripping, identifier leading-zero preservation, and formula-risk
boundary detection according to MASTER_DIRECTIVE.md Section 12.
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


# ─── Whitespace Normalization ────────────────────────────────────────────


class TestWhitespaceNormalization:
    def test_strip_whitespace(self):
        assert normalize_whitespace("   Sample Text   ") == "Sample Text"

    def test_collapse_internal_spaces(self):
        assert normalize_whitespace("DocuStruct   AI   Extraction") == "DocuStruct AI Extraction"

    def test_mixed_newline_tab_spaces(self):
        assert normalize_whitespace("Line 1\t\r\nLine 2") == "Line 1 Line 2"

    def test_empty_and_whitespace_only(self):
        assert normalize_whitespace("") == ""
        assert normalize_whitespace("   \t  \n ") == ""


# ─── TestNumericNormalization ────────────────────────────────────────────


class TestNumericNormalization:
    def test_standard_grouping(self):
        result = parse_numeric_value("1,234,567.89")
        assert result is not None
        norm_str, dec_val, dtype = result
        assert norm_str == "1234567.89"
        assert dec_val == Decimal("1234567.89")
        assert dtype == DataType.DECIMAL

    def test_indian_grouping(self):
        result = parse_numeric_value("12,34,567.89")
        assert result is not None
        norm_str, dec_val, dtype = result
        assert norm_str == "1234567.89"
        assert dec_val == Decimal("1234567.89")
        assert dtype == DataType.DECIMAL

    def test_indian_grouping_lakh(self):
        result = parse_numeric_value("1,00,000")
        assert result is not None
        norm_str, dec_val, dtype = result
        assert norm_str == "100000"
        assert dec_val == Decimal("100000")
        assert dtype == DataType.INTEGER

    def test_leading_minus(self):
        result = parse_numeric_value("-450.50")
        assert result is not None
        norm_str, dec_val, dtype = result
        assert norm_str == "-450.50"
        assert dec_val == Decimal("-450.50")
        assert dtype == DataType.DECIMAL

    def test_trailing_minus(self):
        result = parse_numeric_value("450.50-")
        assert result is not None
        norm_str, dec_val, dtype = result
        assert norm_str == "-450.50"
        assert dec_val == Decimal("-450.50")
        assert dtype == DataType.DECIMAL

    def test_accounting_parentheses(self):
        result = parse_numeric_value("(450.50)")
        assert result is not None
        norm_str, dec_val, dtype = result
        assert norm_str == "-450.50"
        assert dec_val == Decimal("-450.50")
        assert dtype == DataType.DECIMAL

    def test_accounting_parentheses_with_grouping(self):
        result = parse_numeric_value("(1,234.56)")
        assert result is not None
        norm_str, dec_val, dtype = result
        assert norm_str == "-1234.56"
        assert dec_val == Decimal("-1234.56")

    def test_high_precision_decimal(self):
        result = parse_numeric_value("0.0001234567")
        assert result is not None
        norm_str, dec_val, dtype = result
        assert dtype == DataType.HIGH_PRECISION_DECIMAL
        assert dec_val == Decimal("0.0001234567")

    def test_malformed_grouping_rejected(self):
        # 12,345,67.89 has improper 3-digit vs 2-digit placement
        result = parse_numeric_value("12,345,67.89")
        assert result is None


# ─── TestIdentifierPreservation ──────────────────────────────────────────


class TestIdentifierPreservation:
    def test_leading_zeros_preserved_as_identifier(self):
        cell = normalize_cell("0012345", col_header="Account")
        assert cell["data_type"] == DataType.IDENTIFIER
        assert cell["normalized_value"] == "0012345"
        assert cell["accepted_value"] == "0012345"
        assert cell["numeric_decimal"] is None

    def test_invoice_header_with_digits(self):
        cell = normalize_cell("12345", col_header="Invoice No.")
        assert cell["data_type"] == DataType.IDENTIFIER
        assert cell["normalized_value"] == "12345"

    def test_plain_number_under_non_identifier_header(self):
        cell = normalize_cell("12345", col_header="Quantity")
        assert cell["data_type"] == DataType.INTEGER
        assert cell["numeric_decimal"] == Decimal("12345")


# ─── TestFormulaRiskBoundary ─────────────────────────────────────────────


class TestFormulaRiskBoundary:
    @pytest.mark.parametrize("prefix", ["=", "+", "-", "@", "\t", "\r"])
    def test_formula_prefixes_flagged_on_strings(self, prefix: str):
        raw = f"{prefix}TEXT_COMMAND"
        assert detect_formula_risk(raw, is_numeric=False) is True
        cell = normalize_cell(raw)
        assert cell["formula_risk_detected"] is True
        assert cell["data_type"] == DataType.STRING

    def test_numeric_negatives_never_flag_formula_risk(self):
        # Critical MASTER_DIRECTIVE Section 12 requirement:
        # Numeric negatives must NEVER trigger formula-risk
        for neg_val in ["-450.50", "(450.50)", "450.50-", "-1,234.56"]:
            cell = normalize_cell(neg_val)
            assert cell["formula_risk_detected"] is False
            assert cell["numeric_decimal"] is not None
            assert cell["numeric_decimal"] < 0

    def test_no_apostrophes_prepended_and_no_mutation(self):
        formula_str = "=SUM(A1:B10)"
        cell = normalize_cell(formula_str)
        assert cell["formula_risk_detected"] is True
        assert cell["normalized_value"] == "=SUM(A1:B10)"
        assert not cell["normalized_value"].startswith("'")
        assert cell["accepted_value"] == "=SUM(A1:B10)"


# ─── TestImmutabilityAndDecimalSafety ────────────────────────────────────


class TestImmutabilityAndDecimalSafety:
    def test_raw_value_strictly_preserved(self):
        raw = "   (1,234.50)  "
        cell = normalize_cell(raw)
        assert cell["raw_value"] == raw
        assert cell["normalized_value"] == "-1234.50"
        assert cell["accepted_value"] == "-1234.50"

    def test_decimal_constructed_without_binary_float(self):
        # 0.1 cannot be represented accurately in binary float (0.1000000000000000055511...)
        cell = normalize_cell("0.1")
        dec = cell["numeric_decimal"]
        assert isinstance(dec, Decimal)
        assert dec == Decimal("0.1")
        assert str(dec) == "0.1"

    def test_large_number_precision(self):
        raw = "12345678901234567890.12"
        cell = normalize_cell(raw)
        dec = cell["numeric_decimal"]
        assert dec == Decimal("12345678901234567890.12")
        assert str(dec) == "12345678901234567890.12"
