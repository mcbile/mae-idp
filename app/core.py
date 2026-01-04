"""
MAE Core - Shared OCR processing logic
Used by both mae.py (web UI) and batch_rename.py (CLI)
"""

import re
from typing import Optional, List


class ConfidenceScore:
    """Weights for extraction confidence calculation"""
    VENDOR = 30
    INVOICE_NUMBER = 30
    INTERNAL_NUMBER = 30
    VAT_ID = 10  # optional
    THRESHOLD = 50  # minimum for "success" status


# Известные вендоры и их паттерны
KNOWN_VENDORS = {
    "Amazon": ["amazon", "amzn"],
    "DHL": ["dhl", "deutsche post"],
    "UPS": ["ups", "united parcel"],
    "FedEx": ["fedex", "federal express"],
    "Deutsche Telekom": ["telekom", "t-mobile"],
    "Vodafone": ["vodafone"],
    "O2": ["o2", "telefonica"],
    "IKEA": ["ikea"],
    "MediaMarkt": ["media markt", "mediamarkt"],
    "Saturn": ["saturn"],
    "Conrad": ["conrad"],
    "Reichelt": ["reichelt"],
    "RS Components": ["rs-online", "rs components"],
    "Mouser": ["mouser"],
    "DigiKey": ["digi-key", "digikey"],
    "Farnell": ["farnell"],
    "Würth": ["würth", "wuerth", "wurth"],
    "Hoffmann": ["hoffmann group", "hoffmann-group"],
    "Grainger": ["grainger"],
    "Mercateo": ["mercateo"],
    "Staples": ["staples"],
    "Office Depot": ["office depot"],
    "Viking": ["viking"],
    "Büroshop24": ["büroshop24", "bueroshop24"],
}


class BaseOCRProcessor:
    """Base class for OCR document processing"""

    def __init__(self):
        self.ocr_ok = self._check_ocr()
        self.qr_ok = self._check_qr()

    def _check_ocr(self) -> bool:
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    def _check_qr(self) -> bool:
        try:
            from pyzbar import pyzbar
            return True
        except Exception:
            return False

    def load_image(self, path):
        """Load image from file (PDF or image)"""
        import cv2
        import numpy as np

        ext = path.suffix.lower()
        if ext == ".pdf":
            from pdf2image import convert_from_path
            imgs = convert_from_path(path, dpi=300)
            if imgs:
                img = np.array(imgs[0])
                if len(img.shape) == 3:
                    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                return img
            return None
        else:
            return cv2.imread(str(path))

    def preprocess_for_ocr(self, img):
        """Preprocess image for OCR"""
        import cv2

        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img

        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary

    def extract_qr_codes(self, img) -> List[str]:
        """Extract data from QR codes and barcodes"""
        if not self.qr_ok:
            return []
        from pyzbar import pyzbar
        results = []
        for obj in pyzbar.decode(img):
            data = obj.data.decode('utf-8', errors='ignore')
            results.append(data)
        return results

    def extract_internal_from_qr(self, qr_data: List[str]) -> Optional[str]:
        """Extract internal number from QR data (format SN<...>)"""
        for data in qr_data:
            match = re.search(r'SN[<\[]?0*(\d+)[>\]]?', data, re.I)
            if match:
                return match.group(1)
            match = re.search(r'SN\s*:?\s*0*(\d+)', data, re.I)
            if match:
                return match.group(1)
        return None

    def extract_internal_from_corner(self, img) -> Optional[str]:
        """Extract handwritten number from top-right quarter of document"""
        import cv2
        import pytesseract

        h, w = img.shape[:2]
        corner = img[0:int(h*0.50), int(w*0.50):w]  # Top-right quarter (50% x 50%)

        if len(corner.shape) == 3:
            gray = cv2.cvtColor(corner, cv2.COLOR_BGR2GRAY)
        else:
            gray = corner

        gray = cv2.equalizeHist(gray)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789'
        text = pytesseract.image_to_string(binary, config=custom_config)

        numbers = re.findall(r'\d{4,}', text)
        if numbers:
            return str(int(numbers[0]))
        return None

    def _extract_region(self, img, region: str):
        """Extract header (top 20%) or footer (bottom 20%) from image"""
        h, w = img.shape[:2]
        if region == "header":
            return img[0:int(h*0.20), :]
        elif region == "footer":
            return img[int(h*0.80):h, :]
        return img

    def _ocr_region(self, img, region: str) -> str:
        """Run OCR on header or footer region"""
        import pytesseract
        region_img = self._extract_region(img, region)
        processed = self.preprocess_for_ocr(region_img)
        return pytesseract.image_to_string(processed, lang='deu+eng')

    def _find_vendor_in_text(self, text: str) -> Optional[str]:
        """Find vendor in text using patterns"""
        text_lower = text.lower()

        # Check known vendors
        for vendor_name, patterns in KNOWN_VENDORS.items():
            for pattern in patterns:
                if pattern in text_lower:
                    return vendor_name

        # Try email domain
        match = re.search(r'@([a-zA-Z0-9-]+)\.[a-z]{2,}', text)
        if match:
            return match.group(1).title()

        # Try "from/von" patterns
        for pattern in [r'(?:von|from|verkauft von|sold by)[:\s]+([A-Z][a-zA-Z0-9\s&]+?)(?:\s*[,\n]|$)',
                        r'(?:Firma|Company)[:\s]+([A-Z][a-zA-Z0-9\s&]+?)(?:\s*[,\n]|$)']:
            match = re.search(pattern, text, re.I)
            if match:
                vendor = match.group(1).strip()
                words = vendor.split()[:3]
                return " ".join(words)
        return None

    def extract_vendor(self, text: str, img=None) -> Optional[str]:
        """Extract vendor name - first from header, then footer, then full text"""
        # If image provided, try header first, then footer
        if img is not None:
            # Try header (top 20%)
            header_text = self._ocr_region(img, "header")
            vendor = self._find_vendor_in_text(header_text)
            if vendor:
                return vendor

            # Try footer (bottom 20%)
            footer_text = self._ocr_region(img, "footer")
            vendor = self._find_vendor_in_text(footer_text)
            if vendor:
                return vendor

        # Fallback to full text
        return self._find_vendor_in_text(text)

    def extract_invoice_number(self, text: str) -> Optional[str]:
        """Extract invoice number from text"""
        patterns = [
            r'Rechnungsnummer[:\s]*([A-Z0-9-]+)',
            r'Rechnung[- ]?(?:Nr|No|Nummer)[.:\s]*([A-Z0-9-]+)',
            r'Invoice[- ]?(?:Nr|No|Number)[.:\s]*([A-Z0-9-]+)',
            r'Beleg[- ]?(?:Nr|No|Nummer)[.:\s]*([A-Z0-9-]+)',
            r'Referenz(?:nummer)?[:\s]*([A-Z0-9-]+)',
            r'(?:Nr|No)[.:\s]+([A-Z]{2}[A-Z0-9]{8,})',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                inv_num = match.group(1).strip()
                if len(inv_num) >= 5:
                    return inv_num
        return None

    def extract_vat_id(self, text: str) -> Optional[str]:
        """Extract VAT ID from text"""
        patterns = [
            r'USt[.-]?(?:Id(?:Nr)?|Ident)[.:\s]*([A-Z]{2}\s*\d[\d\s]{7,})',
            r'VAT[.\s-]*(?:ID|No|Number)?[.:\s]*([A-Z]{2}\s*\d[\d\s]{7,})',
            r'(?:UID|TVA|IVA)[.:\s-]*([A-Z]{2}\s*\d[\d\s]{7,})',
            r'\b([A-Z]{2}\d{9,12})\b',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                vat = re.sub(r'\s+', '', match.group(1).upper())
                if len(vat) >= 9:
                    return vat
        return None

    def run_ocr(self, img, lang: str = 'deu+eng') -> str:
        """Run OCR on image"""
        import pytesseract
        processed = self.preprocess_for_ocr(img)
        return pytesseract.image_to_string(processed, lang=lang)
