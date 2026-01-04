"""
Unit tests for MAE Core - regex extraction functions
These tests don't require external dependencies (Tesseract, Poppler)
"""

import pytest
import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

from core import (
    ConfidenceScore,
    KNOWN_VENDORS,
    BaseOCRProcessor,
)


class TestConfidenceScore:
    """Test ConfidenceScore constants"""

    def test_weights_sum_to_100(self):
        """All weights should sum to 100"""
        total = (
            ConfidenceScore.VENDOR
            + ConfidenceScore.INVOICE_NUMBER
            + ConfidenceScore.INTERNAL_NUMBER
            + ConfidenceScore.VAT_ID
        )
        assert total == 100

    def test_threshold_is_reasonable(self):
        """Threshold should be between 0 and 100"""
        assert 0 < ConfidenceScore.THRESHOLD < 100


class TestKnownVendors:
    """Test KNOWN_VENDORS dictionary"""

    def test_vendors_not_empty(self):
        """Should have known vendors"""
        assert len(KNOWN_VENDORS) > 0

    def test_all_vendors_have_patterns(self):
        """Each vendor should have at least one pattern"""
        for vendor, patterns in KNOWN_VENDORS.items():
            assert len(patterns) > 0, f"{vendor} has no patterns"

    def test_patterns_are_lowercase(self):
        """All patterns should be lowercase for matching"""
        for vendor, patterns in KNOWN_VENDORS.items():
            for pattern in patterns:
                assert pattern == pattern.lower(), f"{vendor}: pattern '{pattern}' not lowercase"


class TestExtractVendor:
    """Test extract_vendor function"""

    @pytest.fixture
    def processor(self):
        """Create processor without OCR check"""
        proc = object.__new__(BaseOCRProcessor)
        proc.ocr_ok = False
        proc.qr_ok = False
        return proc

    def test_known_vendor_amazon(self, processor):
        """Should detect Amazon"""
        text = "Bestellung bei Amazon.de"
        result = processor.extract_vendor(text)
        assert result == "Amazon"

    def test_known_vendor_dhl(self, processor):
        """Should detect DHL"""
        text = "Sendungsverfolgung DHL Express"
        result = processor.extract_vendor(text)
        assert result == "DHL"

    def test_known_vendor_case_insensitive(self, processor):
        """Should detect vendors case-insensitively"""
        text = "RECHNUNG VON IKEA"
        result = processor.extract_vendor(text)
        assert result == "IKEA"

    def test_extract_from_email(self, processor):
        """Should extract vendor from email domain"""
        text = "Kontakt: info@testcompany.com"
        result = processor.extract_vendor(text)
        assert result == "Testcompany"

    def test_no_vendor_found(self, processor):
        """Should return None when no vendor found"""
        text = "Lorem ipsum dolor sit amet"
        result = processor.extract_vendor(text)
        assert result is None


class TestExtractInvoiceNumber:
    """Test extract_invoice_number function"""

    @pytest.fixture
    def processor(self):
        proc = object.__new__(BaseOCRProcessor)
        proc.ocr_ok = False
        proc.qr_ok = False
        return proc

    def test_rechnungsnummer(self, processor):
        """Should extract German invoice number"""
        text = "Rechnungsnummer: INV-2024-001234"
        result = processor.extract_invoice_number(text)
        assert result == "INV-2024-001234"

    def test_rechnung_nr(self, processor):
        """Should extract Rechnung-Nr format"""
        text = "Rechnung Nr. 12345678"
        result = processor.extract_invoice_number(text)
        assert result == "12345678"

    def test_invoice_number_english(self, processor):
        """Should extract English invoice number"""
        text = "Invoice Number: ABC123456"
        result = processor.extract_invoice_number(text)
        assert result == "ABC123456"

    def test_beleg_nummer(self, processor):
        """Should extract Beleg-Nummer format"""
        text = "Beleg-Nr: DOC-99887766"
        result = processor.extract_invoice_number(text)
        assert result == "DOC-99887766"

    def test_too_short_number_ignored(self, processor):
        """Should ignore numbers shorter than 5 chars"""
        text = "Rechnung Nr: 1234"
        result = processor.extract_invoice_number(text)
        assert result is None

    def test_no_invoice_found(self, processor):
        """Should return None when no invoice number found"""
        text = "Vielen Dank für Ihre Bestellung"
        result = processor.extract_invoice_number(text)
        assert result is None


class TestExtractVatId:
    """Test extract_vat_id function"""

    @pytest.fixture
    def processor(self):
        proc = object.__new__(BaseOCRProcessor)
        proc.ocr_ok = False
        proc.qr_ok = False
        return proc

    def test_german_ust_id(self, processor):
        """Should extract German USt-IdNr"""
        text = "USt-IdNr: DE123456789"
        result = processor.extract_vat_id(text)
        assert result == "DE123456789"

    def test_vat_id_with_spaces(self, processor):
        """Should normalize VAT ID with spaces"""
        text = "VAT ID: DE 123 456 789"
        result = processor.extract_vat_id(text)
        assert result == "DE123456789"

    def test_german_uid_format(self, processor):
        """Should extract German UID"""
        text = "UID: DE123456789"
        result = processor.extract_vat_id(text)
        assert result == "DE123456789"

    def test_standalone_vat_format(self, processor):
        """Should extract standalone VAT format"""
        text = "Steuernummer FR12345678901"
        result = processor.extract_vat_id(text)
        assert result == "FR12345678901"

    def test_no_vat_found(self, processor):
        """Should return None when no VAT ID found"""
        text = "Keine Steuernummer vorhanden"
        result = processor.extract_vat_id(text)
        assert result is None


class TestExtractInternalFromQr:
    """Test extract_internal_from_qr function"""

    @pytest.fixture
    def processor(self):
        proc = object.__new__(BaseOCRProcessor)
        proc.ocr_ok = False
        proc.qr_ok = False
        return proc

    def test_sn_with_brackets(self, processor):
        """Should extract SN with angle brackets"""
        qr_data = ["SN<00012345>"]
        result = processor.extract_internal_from_qr(qr_data)
        assert result == "12345"

    def test_sn_with_square_brackets(self, processor):
        """Should extract SN with square brackets"""
        qr_data = ["SN[00067890]"]
        result = processor.extract_internal_from_qr(qr_data)
        assert result == "67890"

    def test_sn_with_colon(self, processor):
        """Should extract SN with colon format"""
        qr_data = ["SN: 00099999"]
        result = processor.extract_internal_from_qr(qr_data)
        assert result == "99999"

    def test_sn_strips_leading_zeros(self, processor):
        """Should strip leading zeros"""
        qr_data = ["SN<00000123>"]
        result = processor.extract_internal_from_qr(qr_data)
        assert result == "123"

    def test_multiple_qr_codes(self, processor):
        """Should find SN in multiple QR codes"""
        qr_data = ["Some other data", "SN<00054321>", "More data"]
        result = processor.extract_internal_from_qr(qr_data)
        assert result == "54321"

    def test_no_sn_found(self, processor):
        """Should return None when no SN found"""
        qr_data = ["Random QR data", "No serial here"]
        result = processor.extract_internal_from_qr(qr_data)
        assert result is None

    def test_empty_qr_data(self, processor):
        """Should handle empty QR data"""
        qr_data = []
        result = processor.extract_internal_from_qr(qr_data)
        assert result is None
