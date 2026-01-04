"""
MAE Batch Rename - Пакетное переименование документов
Обрабатывает папку с файлами, извлекает данные через OCR и QR-коды,
переименовывает в формат: vendor_invoicenumber_interndocnumber
"""

import os
import sys
import re
import shutil
import logging
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List
import argparse

# Add app directory to path for imports
APP_DIR = Path(__file__).parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Setup paths
from setup_env import setup_all
setup_all()

# Core OCR processing
from core import BaseOCRProcessor, ConfidenceScore


@dataclass
class DocInfo:
    """Информация извлечённая из документа"""
    original_path: str
    vendor: Optional[str] = None
    invoice_number: Optional[str] = None
    internal_number: Optional[str] = None
    vat_id: Optional[str] = None
    new_filename: Optional[str] = None
    status: str = "pending"  # pending, success, review, error
    error: Optional[str] = None
    confidence: int = 0


class BatchProcessor(BaseOCRProcessor):
    """Batch document processor using shared OCR logic"""

    def process_file(self, path: Path) -> DocInfo:
        """Обрабатывает один файл"""
        info = DocInfo(original_path=str(path))

        if not self.ocr_ok:
            info.status = "error"
            info.error = "OCR (Tesseract) не установлен"
            return info

        try:
            # Загружаем изображение
            img = self.load_image(path)
            if img is None:
                info.status = "error"
                info.error = "Не удалось загрузить файл"
                return info

            # Извлекаем QR-коды
            qr_data = self.extract_qr_codes(img)

            # Ищем internal number в QR
            info.internal_number = self.extract_internal_from_qr(qr_data)

            # Если не нашли в QR, ищем в углу (рукописный)
            if not info.internal_number:
                info.internal_number = self.extract_internal_from_corner(img)

            # OCR using base class method
            text = self.run_ocr(img)

            # Извлекаем данные
            info.vendor = self.extract_vendor(text)
            info.invoice_number = self.extract_invoice_number(text)
            info.vat_id = self.extract_vat_id(text)

            # Подсчёт confidence (using shared weights)
            conf = 0
            if info.vendor:
                conf += ConfidenceScore.VENDOR
            if info.invoice_number:
                conf += ConfidenceScore.INVOICE_NUMBER
            if info.internal_number:
                conf += ConfidenceScore.INTERNAL_NUMBER
            if info.vat_id:
                conf += ConfidenceScore.VAT_ID
            info.confidence = min(conf, 100)

            # Формируем новое имя файла
            if info.confidence >= ConfidenceScore.THRESHOLD and info.vendor and info.invoice_number:
                # Очищаем имена от недопустимых символов
                vendor_clean = re.sub(r'[^\w\s-]', '', info.vendor).replace(' ', '')
                invoice_clean = re.sub(r'[^\w-]', '', info.invoice_number)
                internal_clean = re.sub(r'[^\d]', '', info.internal_number) if info.internal_number else "0"

                info.new_filename = f"{vendor_clean}_{invoice_clean}_{internal_clean}{path.suffix.lower()}"
                info.status = "success"
            else:
                info.status = "review"
                # Частичное имя для review
                parts = []
                parts.append(info.vendor or "UNKNOWN")
                parts.append(info.invoice_number or "UNKNOWN")
                parts.append(info.internal_number or "UNKNOWN")
                info.new_filename = f"{'_'.join(parts)}{path.suffix.lower()}"

        except Exception as e:
            info.status = "error"
            info.error = str(e)

        return info

    def process_folder(self, input_dir: Path, output_dir: Path,
                       move_files: bool = True,
                       progress_callback=None) -> List[DocInfo]:
        """Обрабатывает все файлы в папке"""

        # Создаём выходные папки
        output_dir.mkdir(parents=True, exist_ok=True)
        review_dir = output_dir / "_ПРОВЕРИТЬ"
        review_dir.mkdir(exist_ok=True)

        # Собираем файлы
        extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif'}
        files = [f for f in input_dir.rglob('*') if f.suffix.lower() in extensions]

        results = []
        total = len(files)

        for i, file_path in enumerate(files):
            if progress_callback:
                progress_callback(i + 1, total, file_path.name)

            # Обрабатываем файл
            info = self.process_file(file_path)
            results.append(info)

            if not move_files:
                continue

            # Перемещаем/копируем файл
            if info.status == "success" and info.vendor:
                # Создаём папку вендора
                vendor_dir = output_dir / info.vendor.replace(' ', '_')
                vendor_dir.mkdir(exist_ok=True)
                dest = vendor_dir / info.new_filename
            elif info.status == "review":
                dest = review_dir / info.new_filename
            else:
                # Ошибка - в review с оригинальным именем
                dest = review_dir / f"ERROR_{file_path.name}"

            # Избегаем перезаписи
            if dest.exists():
                stem = dest.stem
                suffix = dest.suffix
                counter = 1
                while dest.exists():
                    dest = dest.parent / f"{stem}_{counter}{suffix}"
                    counter += 1

            try:
                shutil.copy2(file_path, dest)
                info.new_filename = str(dest.relative_to(output_dir))
            except Exception as e:
                info.error = f"Ошибка копирования: {e}"

        return results

    def export_report(self, results: List[DocInfo], output_path: Path):
        """Экспортирует отчёт в Excel"""
        import pandas as pd

        data = []
        for r in results:
            data.append({
                "Оригинальный файл": Path(r.original_path).name,
                "Статус": r.status,
                "Vendor": r.vendor or "",
                "Invoice Number": r.invoice_number or "",
                "Internal Number": r.internal_number or "",
                "VAT ID": r.vat_id or "",
                "Новое имя": r.new_filename or "",
                "Confidence": f"{r.confidence}%",
                "Ошибка": r.error or ""
            })

        df = pd.DataFrame(data)

        # Сохраняем с форматированием
        from openpyxl.utils import get_column_letter
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Результаты')

            # Автоширина колонок
            worksheet = writer.sheets['Результаты']
            for i, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.column_dimensions[get_column_letter(i + 1)].width = min(max_len, 50)

        return output_path


def main():
    parser = argparse.ArgumentParser(
        description='Пакетное переименование документов',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Примеры:
  python batch_rename.py "D:\\Invoices" "D:\\Sorted"
  python batch_rename.py "C:\\Users\\User\\Google Drive\\Invoices" "C:\\Users\\User\\Documents\\Sorted"
        '''
    )

    parser.add_argument('input_dir', help='Папка с исходными файлами')
    parser.add_argument('output_dir', help='Папка для результатов')
    parser.add_argument('--dry-run', action='store_true',
                        help='Только анализ, без копирования файлов')
    parser.add_argument('--no-report', action='store_true',
                        help='Не создавать Excel отчёт')

    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    if not input_dir.exists():
        logger.error("Папка не найдена: %s", input_dir)
        print(f"ОШИБКА: Папка не найдена: {input_dir}")
        sys.exit(1)

    logger.info("Запуск обработки: %s -> %s", input_dir, output_dir)

    print("=" * 60)
    print("MAE Batch Rename - Пакетное переименование документов")
    print("=" * 60)
    print(f"Входная папка:  {input_dir}")
    print(f"Выходная папка: {output_dir}")
    print(f"Режим: {'Анализ (dry-run)' if args.dry_run else 'Обработка + копирование'}")
    print("=" * 60)

    processor = BatchProcessor()

    # Проверяем зависимости
    print(f"\nOCR (Tesseract): {'✓ OK' if processor.ocr_ok else '✗ НЕ УСТАНОВЛЕН'}")
    print(f"QR Reader:       {'✓ OK' if processor.qr_ok else '✗ НЕ УСТАНОВЛЕН (pip install pyzbar)'}")

    if not processor.ocr_ok:
        print("\nОШИБКА: Tesseract OCR не установлен!")
        print("Установите: https://github.com/UB-Mannheim/tesseract/wiki")
        sys.exit(1)

    print("\nОбработка файлов...")
    print("-" * 60)

    def progress(current, total, filename):
        pct = int(current / total * 100)
        bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
        print(f"\r[{bar}] {current}/{total} ({pct}%) - {filename[:40]:<40}", end="", flush=True)

    results = processor.process_folder(
        input_dir,
        output_dir,
        move_files=not args.dry_run,
        progress_callback=progress
    )

    print("\n" + "-" * 60)

    # Статистика
    success = sum(1 for r in results if r.status == "success")
    review = sum(1 for r in results if r.status == "review")
    errors = sum(1 for r in results if r.status == "error")
    total = len(results)

    print(f"\nРЕЗУЛЬТАТЫ:")
    print(f"  Всего файлов:    {total}")
    if total:
        print(f"  ✓ Успешно:       {success} ({success/total*100:.1f}%)")
        print(f"  ⚠ На проверку:   {review} ({review/total*100:.1f}%)")
        print(f"  ✗ Ошибки:        {errors} ({errors/total*100:.1f}%)")
    else:
        logger.warning("Нет файлов для обработки")

    # Экспорт отчёта
    if not args.no_report and results:
        report_path = output_dir / f"отчёт_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
        processor.export_report(results, report_path)
        print(f"\n📊 Отчёт сохранён: {report_path}")

    print(f"\n📁 Результаты в папке: {output_dir}")
    if review > 0:
        print(f"⚠  Файлы на проверку: {output_dir / '_ПРОВЕРИТЬ'}")

    print("\nГотово!")


if __name__ == "__main__":
    main()
