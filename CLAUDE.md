# CLAUDE.md — Instructions for Claude Code

> **ОБЯЗАТЕЛЬНЫЕ ПРАВИЛА** — Следуй этим инструкциям при каждом изменении кода.

---

## Impact Analysis (MANDATORY)

**BEFORE any code change**, you must:

1. **Describe current state** — how code works now
2. **Describe proposed changes** — what exactly will change
3. **Explain impact on final code:**
   - Which files/functions affected
   - How behavior changes
   - Performance impact (if applicable)
   - Potential risks
4. **Get confirmation** from user before implementing

**RULE**:
Never make changes without explaining their impact on the final code.
User must understand WHAT changes and HOW it affects the system.

### Change Proposal Format

```markdown
### Current code:
[code fragment]

### Proposed code:
[code fragment]

### Impact:
- Files: [list of affected files]
- Functions: [list of affected functions]
- Performance: [description]
- Risks: [description]
```

## Language

**Всегда отвечай на русском языке.** All responses must be in Russian.

## CHANGELOG и BACKLOG — ОБЯЗАТЕЛЬНОЕ ведение

### CHANGELOG.md

**ОБЯЗАТЕЛЬНО** обновлять при КАЖДОМ изменении кода:

1. **После любого изменения** — добавить запись в секцию `[Unreleased]` или текущей версии
2. **Формат записи:**
   ```markdown
   ### Added/Changed/Fixed/Removed
   - Краткое описание изменения
   ```
3. **При релизе новой версии:**
   - Создать новую секцию `[X.Y.Z] - YYYY-MM-DD`
   - Перенести записи из `[Unreleased]`
   - Обновить версию в `mae.py` (Config.VERSION)
   - Обновить badge в `README.md`

### BACKLOG.md

**ОБЯЗАТЕЛЬНО** обновлять при работе с задачами:

1. **Новый баг/фича** — добавить в соответствующую секцию с `[ ]`
2. **Начало работы** — отметить `[~]` (в работе)
3. **Завершение** — отметить `[x]` и перенести в "Выполненные задачи"
4. **При релизе** — перенести выполненные задачи в CHANGELOG.md

### Приоритеты в BACKLOG

| Приоритет | Описание |
|-----------|----------|
| 🔴 Critical | Блокирующие баги, безопасность |
| 🟠 High | Важные фичи, значительные улучшения |
| 🟡 Medium | Улучшения UX, рефакторинг |
| 🟢 Low | Косметические изменения |

### Пример workflow

```
1. Пользователь: "Добавь поддержку multi-page PDF"
2. Claude: Проверяет BACKLOG.md — задача уже есть
3. Claude: Отмечает [~] в BACKLOG.md
4. Claude: Реализует фичу
5. Claude: Добавляет в CHANGELOG.md:
   ### Added
   - Поддержка multi-page PDF — обработка всех страниц
6. Claude: Отмечает [x] в BACKLOG.md
7. Claude: Переносит в "Выполненные задачи"
```

---

## Project Overview

MAE-IDP (Intelligent Document Processing) — кроссплатформенное приложение для интеллектуального распознавания документов (счетов, накладных). Автоматически извлекает данные из PDF, JPG, PNG, TIFF файлов используя OCR (Tesseract) и QR-коды.

**Версия:** 1.4.0
**Платформы:** Windows 10/11, macOS, Linux
**Язык:** Python 3.10+

## Tech Stack

- **Python 3.10+**
- **FastAPI 0.109.0** — веб-сервер
- **uvicorn 0.27.0** — ASGI сервер
- **pywebview 4.4.1** — GUI (WebView окно, опционально)
- **pytesseract 0.3.10** — OCR обработка
- **pdf2image 1.16.3** — конвертация PDF
- **opencv-python-headless 4.9.0.80** — обработка изображений
- **pyzbar 0.1.9** — распознавание QR/штрих-кодов
- **pandas 2.2.0 + openpyxl 3.1.2** — Excel экспорт
- **watchdog 3.0.0** — мониторинг файловой системы
- **Pillow 10.2.0** — работа с изображениями
- **numpy 1.26.3** — числовые операции
- **python-multipart 0.0.6** — загрузка файлов

**Внешние зависимости:**
- Tesseract-OCR 5.3.3
  - Windows: `C:\Program Files\Tesseract-OCR`
  - macOS: `/opt/homebrew/bin/tesseract` (Apple Silicon) или `/usr/local/bin/tesseract` (Intel)
  - Linux: `/usr/bin/tesseract`
- Poppler (для PDF → изображения)
  - Windows: `./poppler/`
  - macOS/Linux: через пакетный менеджер (Homebrew, apt, dnf, pacman)

## Build and Development Commands

```bash
# Установка — Windows
install.bat                    # Автоматическая установка

# Установка — macOS/Linux
chmod +x install.sh && ./install.sh

# Ручная установка зависимостей
pip install -r requirements.txt

# Запуск — Windows
run.bat                        # GUI приложение

# Запуск — macOS/Linux
./run.sh

# Запуск напрямую
python app/mae.py              # GUI (если pywebview) или веб-сервер

# CLI пакетная обработка
python app/batch_rename.py INPUT OUTPUT
python app/batch_rename.py INPUT OUTPUT --dry-run    # Только анализ
python app/batch_rename.py INPUT OUTPUT --no-report  # Без Excel отчёта
```

## Architecture

### Модули

| Файл | Назначение |
|------|------------|
| `app/mae.py` | Веб-приложение (FastAPI + WebView GUI) |
| `app/core.py` | Базовый класс OCR обработки |
| `app/batch_rename.py` | CLI инструмент пакетной обработки |
| `app/setup_env.py` | Настройка окружения (Tesseract, Poppler) — кроссплатформенный |
| `app/templates/index.html` | Веб-интерфейс (Vanilla JS, PWA-ready) |

### Иерархия классов

```
BaseOCRProcessor (core.py)
├── Parser (mae.py)        — для веб-интерфейса
└── BatchProcessor (batch_rename.py) — для CLI
```

### Ключевые классы

**ConfidenceScore** (`core.py`) — веса для расчёта уверенности:
```python
VENDOR = 30
INVOICE_NUMBER = 30
INTERNAL_NUMBER = 30
VAT_ID = 10  # optional
THRESHOLD = 50  # минимум для "success"
```

**ParsedDoc** (`mae.py`) — результат парсинга:
```python
@dataclass
class ParsedDoc:
    filename: str
    status: str  # pending, success, review, error
    vendor: Optional[str]
    invoice_number: Optional[str]
    internal_number: Optional[str]
    vat_id: Optional[str]
    confidence: int
    error: Optional[str]
    timestamp: Optional[str]
```

**DocInfo** (`batch_rename.py`) — результат для CLI:
```python
@dataclass
class DocInfo:
    original_path: str
    vendor: Optional[str]
    invoice_number: Optional[str]
    internal_number: Optional[str]
    vat_id: Optional[str]
    new_filename: Optional[str]
    status: str  # pending, success, review, error
    error: Optional[str]
    confidence: int
```

**FolderWatcher** (`mae.py`) — мониторинг папки:
- Использует watchdog для отслеживания новых файлов
- Функция `_wait_for_file_ready()` ждёт завершения записи файла (polling)
- Автоматически обрабатывает и архивирует файлы с умным именованием

### API Endpoints

| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/` | HTML интерфейс |
| GET | `/static/{filename}` | Статические файлы из templates |
| GET | `/api/status` | Статус OCR и Watcher |
| POST | `/api/parse` | Загрузить и обработать файл |
| GET | `/api/results` | Получить все результаты |
| DELETE | `/api/results` | Очистить результаты |
| POST | `/api/export` | Экспорт в Excel |
| POST | `/api/watcher/start` | Запустить мониторинг |
| POST | `/api/watcher/stop` | Остановить мониторинг |
| GET | `/api/browse` | Диалог выбора папки (tkinter) |
| GET | `/api/detect-gdrive` | Поиск Google Drive |
| GET | `/api/open/{folder}` | Открыть папку (кроссплатформенно) |

## File Structure

```
mae-idp/
├── app/
│   ├── mae.py              # Веб-приложение (FastAPI + WebView)
│   ├── core.py             # Общая логика OCR (BaseOCRProcessor)
│   ├── batch_rename.py     # CLI инструмент
│   ├── setup_env.py        # Настройка окружения (кроссплатформенный)
│   └── templates/
│       └── index.html      # Веб-интерфейс (PWA-ready)
├── data/
│   ├── input/              # Входящие документы (временные)
│   ├── output/             # Excel отчёты
│   ├── archive/            # Обработанные файлы
│   └── config.json         # Настройки приложения (создаётся автоматически)
├── poppler/                # Poppler библиотека (только Windows)
├── install.bat             # Автоустановка (Windows)
├── install.sh              # Автоустановка (macOS/Linux)
├── run.bat                 # Запуск GUI (Windows)
├── run.sh                  # Запуск (macOS/Linux)
├── batch_rename.bat        # Запуск CLI (Windows)
├── requirements.txt        # Python зависимости
├── README.md               # Документация пользователя
├── CLAUDE.md               # Инструкции для Claude (этот файл)
├── CHANGELOG.md            # История изменений (ОБЯЗАТЕЛЬНО вести!)
└── BACKLOG.md              # Список задач (ОБЯЗАТЕЛЬНО вести!)
```

## Key Constants

```python
# mae.py
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
HOST = "0.0.0.0"  # Доступ из локальной сети (для мобильных)
PORT = 8766

# core.py - Confidence weights
VENDOR = 30
INVOICE_NUMBER = 30
INTERNAL_NUMBER = 30
VAT_ID = 10
THRESHOLD = 50

# Supported extensions
EXTENSIONS = ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif']
```

## OCR Processing Pipeline

1. **Загрузка** — `load_image(path)` загружает PDF/изображение
2. **QR-коды** — `extract_qr_codes(img)` извлекает данные из QR/штрих-кодов
3. **Internal из QR** — `extract_internal_from_qr(qr_data)` ищет формат SN...
4. **Internal из угла** — `extract_internal_from_corner(img)` ищет рукописный номер (top-right 15%×25%)
5. **OCR** — `run_ocr(img)` распознаёт текст (Tesseract, deu+eng)
6. **Vendor** — `extract_vendor(text)` ищет известных вендоров или извлекает из email
7. **Invoice** — `extract_invoice_number(text)` ищет номер счёта
8. **VAT ID** — `extract_vat_id(text)` ищет идентификатор НДС

## Known Vendors (KNOWN_VENDORS)

24 компании с паттернами для поиска:
Amazon, DHL, UPS, FedEx, Deutsche Telekom, Vodafone, O2, IKEA, MediaMarkt, Saturn, Conrad, Reichelt, RS Components, Mouser, DigiKey, Farnell, Würth, Hoffmann, Grainger, Mercateo, Staples, Office Depot, Viking, Büroshop24

## Common Patterns

**Regex для извлечения данных:**

```python
# Internal number из QR
r'SN[<\[]?0*(\d+)[>\]]?'
r'SN\s*:?\s*0*(\d+)'

# Invoice number
r'Rechnungsnummer[:\s]*([A-Z0-9-]+)'
r'Rechnung[- ]?(?:Nr|No|Nummer)[.:\s]*([A-Z0-9-]+)'
r'Invoice[- ]?(?:Nr|No|Number)[.:\s]*([A-Z0-9-]+)'
r'Beleg[- ]?(?:Nr|No|Nummer)[.:\s]*([A-Z0-9-]+)'
r'Referenz(?:nummer)?[:\s]*([A-Z0-9-]+)'

# VAT ID
r'USt[.-]?(?:Id(?:Nr)?|Ident)[.:\s]*([A-Z]{2}\s*\d[\d\s]{7,})'
r'VAT[.\s-]*(?:ID|No|Number)?[.:\s]*([A-Z]{2}\s*\d[\d\s]{7,})'
r'(?:UID|TVA|IVA)[.:\s-]*([A-Z]{2}\s*\d[\d\s]{7,})'
```

## Thread Safety

Приложение использует несколько механизмов для thread-safety:

```python
# mae.py
parser_lock = threading.Lock()  # Защита OCR парсера
results_lock = threading.Lock() # Защита списка результатов
_executor = ThreadPoolExecutor(max_workers=2)  # Для блокирующих операций
```

## Archive Naming

Функция `generate_archive_name()` создаёт имена архивных файлов:
- **Успех**: `Vendor_InvoiceNumber_InternalNumber.ext`
- **Review** (частичное): `warn_Vendor_InvoiceNumber_InternalNumber.ext`
- **Fallback**: `warn_YYYYMMDD_HHMMSS_originalname.ext`

## Development Tips

### Добавление нового вендора

В `core.py` добавить в `KNOWN_VENDORS`:
```python
"NewVendor": ["newvendor", "new vendor", "nv"],
```

### Добавление нового паттерна для invoice

В `core.py` в `extract_invoice_number()` добавить паттерн:
```python
patterns = [
    # ... existing patterns
    r'NewPattern[:\s]*([A-Z0-9-]+)',
]
```

### Тестирование OCR

```python
from app.core import BaseOCRProcessor
processor = BaseOCRProcessor()
img = processor.load_image(Path("test.pdf"))
text = processor.run_ocr(img)
print(text)
```

### Кроссплатформенное открытие папок

Функция `_open_path()` в `mae.py` использует:
- Windows: `os.startfile()`
- macOS: `subprocess.run(["open", path])`
- Linux: `subprocess.run(["xdg-open", path])`

## Known Issues

1. **Только первая страница PDF** — `core.py:78` обрабатывает только первую страницу. См. BACKLOG.md → Multi-page PDF.

2. **FolderWatcher.output_path не используется** — поле сохраняется, но никак не применяется.

## Security Notes

- Валидация расширений файлов
- Проверка размера файла (50MB лимит)
- Path traversal защита через `PurePath().name`
- Thread-safe доступ к парсеру через Lock
- Нет rate limiting (возможен DoS) — см. BACKLOG.md

## Deployment (Docker / Render)

### Docker

```bash
# Сборка образа
docker build -t mae-idp .

# Запуск контейнера
docker run -p 8766:8766 mae-idp
```

**Dockerfile** включает:
- Python 3.12-slim
- Tesseract OCR (deu, eng)
- Poppler-utils
- libzbar0

### Render.com

1. Подключи репозиторий на [render.com](https://render.com)
2. Render автоматически обнаружит `render.yaml`
3. Нажми "Create Web Service"

**Важно:**
- `pywebview` закомментирован в requirements.txt (не работает в headless)
- PORT берётся из переменной окружения: `int(os.environ.get("PORT", 8766))`

### Файлы деплоя

| Файл | Назначение |
|------|------------|
| `Dockerfile` | Docker образ с системными зависимостями |
| `render.yaml` | Конфиг для Render.com |
| `runtime.txt` | Версия Python для PaaS |
| `main.py` | Точка входа для ASGI серверов |
