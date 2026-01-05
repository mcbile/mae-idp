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
    THRESHOLD = 90  # minimum for "success" status


# Исключения — это покупатели, не вендоры
EXCLUDED_VENDORS = ["sicherheit nord"]

# VAT покупателей — исключить из результатов
EXCLUDED_VAT = ["DE135198442"]

# Паттерны которые НЕ являются номером счёта
EXCLUDED_INVOICE_PATTERNS = [
    r'Kunden[- ]?(?:Nr|No|Nummer|nummer)',
    r'Referenz[- ]?(?:Nr|No|Nummer|nummer)?',
    r'Account[- ]?(?:Nr|No|Nummer|nummer)',
    r'Vorgang[s]?[- ]?(?:Nr|No|Nummer|nummer)',
    r'Bestell[- ]?(?:Nr|No|Nummer|nummer)',
    r'Auftrags[- ]?(?:Nr|No|Nummer|nummer)',
]

# Валидация VAT по формату страны
VAT_FORMATS = {
    'DE': r'^DE\d{9}$',
    'AT': r'^ATU\d{8}$',
    'CH': r'^CHE[\d]{9}$',
    'PL': r'^PL\d{10}$',
    'CZ': r'^CZ\d{8,10}$',
    'NL': r'^NL\d{9}B\d{2}$',
    'BE': r'^BE[01]\d{9}$',
    'FR': r'^FR[A-Z0-9]{2}\d{9}$',
    'IE': r'^IE\d{7}[A-Z]{1,2}$',
    'IT': r'^IT\d{11}$',
    'ES': r'^ES[A-Z]\d{7}[A-Z0-9]$',
    'GB': r'^GB\d{9,12}$',
    'PT': r'^PT\d{9}$',
    'SE': r'^SE\d{12}$',
    'DK': r'^DK\d{8}$',
    'FI': r'^FI\d{8}$',
    'LT': r'^LT\d{9,12}$',
    'LV': r'^LV\d{11}$',
    'EE': r'^EE\d{9}$',
    'SK': r'^SK\d{10}$',
    'HU': r'^HU\d{8}$',
    'SI': r'^SI\d{8}$',
    'RO': r'^RO\d{2,10}$',
    'BG': r'^BG\d{9,10}$',
    'HR': r'^HR\d{11}$',
    'EL': r'^EL\d{9}$',
    'CY': r'^CY\d{8}[A-Z]$',
    'MT': r'^MT\d{8}$',
    'LU': r'^LU\d{8}$',
}


def validate_vat_format(vat: str) -> bool:
    """Проверяет соответствие VAT формату страны"""
    vat_clean = re.sub(r'[\s./-]', '', vat.upper())
    country = vat_clean[:2]
    if country == 'CH':
        country = vat_clean[:3]  # CHE для Швейцарии
    if country in VAT_FORMATS:
        return bool(re.match(VAT_FORMATS[country], vat_clean))
    # Для AT проверяем ATU
    if vat_clean[:3] == 'ATU':
        return bool(re.match(VAT_FORMATS.get('AT', ''), vat_clean))
    return False


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
            domain = match.group(1).title()
            # Проверяем что это не исключённый vendor
            if not any(excl in domain.lower() for excl in EXCLUDED_VENDORS):
                return domain

        # Try "from/von" patterns
        for pattern in [r'(?:von|from|verkauft von|sold by)[:\s]+([A-Z][a-zA-Z0-9\s&]+?)(?:\s*[,\n]|$)',
                        r'(?:Firma|Company)[:\s]+([A-Z][a-zA-Z0-9\s&]+?)(?:\s*[,\n]|$)']:
            match = re.search(pattern, text, re.I)
            if match:
                vendor = match.group(1).strip()
                # Проверяем что это не исключённый vendor
                if any(excl in vendor.lower() for excl in EXCLUDED_VENDORS):
                    continue
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
            r'Rechnungs[- ]?Nr[.:\s]*([A-Z0-9-]+)',
            r'Rechnung[- ]?(?:Nr|No|Nummer)[.:\s]*([A-Z0-9-]+)',
            r'Invoice[- ]?(?:Nr|No|Number)[.:\s]*([A-Z0-9-]+)',
            r'Beleg[- ]?(?:Nr|No|Nummer)[.:\s]*([A-Z0-9-]+)',
            r'INV[- ]?(?:Nr|No|Number)?[.:\s]*([A-Z0-9-]+)',
            r'RE[- ]?(?:Nr|No|Nummer)?[.:\s]*([A-Z0-9-]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                # Проверяем что это не исключённый паттерн
                match_start = max(0, match.start() - 20)
                context = text[match_start:match.start()]
                is_excluded = False
                for excl_pattern in EXCLUDED_INVOICE_PATTERNS:
                    if re.search(excl_pattern, context, re.I):
                        is_excluded = True
                        break
                if is_excluded:
                    continue

                inv_num = match.group(1).strip()
                if len(inv_num) >= 5:
                    return inv_num
        return None

    def extract_vat_id(self, text: str) -> Optional[str]:
        """Extract VAT ID from text"""
        patterns = [
            r'USt[.-]?(?:Id(?:Nr)?|Ident(?:Nr)?|Nr)[.:\s]*([A-Z]{2,3}\s*[\dA-Z][\d\sA-Z./-]{6,})',
            r'USt[.-]?ID[.:\s]*([A-Z]{2,3}\s*[\dA-Z][\d\sA-Z./-]{6,})',
            r'Umsatzsteuer[- ]?(?:Id(?:entifikations)?(?:nummer)?|Nr)[.:\s]*([A-Z]{2,3}\s*[\dA-Z][\d\sA-Z./-]{6,})',
            r'MwSt[.-]?(?:Id(?:Nr)?|Ident(?:Nr)?|Nr)[.:\s]*([A-Z]{2,3}\s*[\dA-Z][\d\sA-Z./-]{6,})',
            r'VAT[.\s-]*(?:ID|No|Number|Reg)?[.:\s]*([A-Z]{2,3}\s*[\dA-Z][\d\sA-Z./-]{6,})',
            r'VAT[- ]?ID[.:\s]*([A-Z]{2,3}\s*[\dA-Z][\d\sA-Z./-]{6,})',
            r'(?:UID|TVA|IVA|BTW|NIF|CIF)[.:\s-]*([A-Z]{2,3}\s*[\dA-Z][\d\sA-Z./-]{6,})',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                vat = re.sub(r'[\s./-]', '', match.group(1).upper())
                # Проверяем исключения
                if vat in EXCLUDED_VAT:
                    continue
                # Валидируем формат по стране
                if validate_vat_format(vat):
                    return vat
        return None

    def run_ocr(self, img, lang: str = 'deu+eng') -> str:
        """Run OCR on image"""
        import pytesseract
        processed = self.preprocess_for_ocr(img)
        return pytesseract.image_to_string(processed, lang=lang)
