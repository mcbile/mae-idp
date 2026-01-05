# Changelog

Все значимые изменения в проекте документируются в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/),
проект придерживается [Semantic Versioning](https://semver.org/lang/ru/).

---

## [Unreleased]

### Added
- **Batch processing в GUI** — новый таб для обработки всех файлов в папке одним кликом
  - API endpoints: `/api/batch/start`, `/api/batch/status`, `/api/batch/stop`
  - Progress bar с отображением текущего файла
  - Опция архивирования файлов после обработки
- **Structured logging** — JSON/pretty формат логов (`logging_config.py`)
- **OCR Cache** — кеширование результатов по SHA-256 hash файла (`cache.py`)
- **pytest** — добавлен в requirements.txt
- **Skeleton loader** — анимация загрузки при обработке файлов (shimmer effect)
- **Ручная коррекция** — inline editing для vendor, invoice, internal, VAT с автоматическим пересчётом confidence

### Changed
- **Export форматы** — заменён Excel экспорт на CSV, Markdown, TXT с dropdown выбором
- **Исправлен баг экспорта** — файлы больше не скачиваются как `.xlsx.txt`
- **Invoice паттерны** — добавлены Rechnungs-Nr, INV, RE; убраны Referenz и общий Nr/No
- **VAT паттерны** — добавлены MwSt, Umsatzsteuer, VAT-ID и др.
- **VAT валидация** — проверка формата по стране (DE, AT, CH, PL, GB и др.)
- **Исключения** — добавлены EXCLUDED_VENDORS, EXCLUDED_VAT, EXCLUDED_INVOICE_PATTERNS для фильтрации покупателей и ложных срабатываний (Kundennummer, Referenznummer и т.п.)

### Removed
- **Excel экспорт** — убран в пользу CSV/MD/TXT (pandas/openpyxl больше не используются для экспорта)

### Security
- **Rate limiting** — защита от DoS атак (10 файлов/мин на IP) через `slowapi`
- **Magic bytes validation** — проверка типа файла по содержимому, не только расширению
- **MAX_RESULTS** — ограничение роста списка результатов (FIFO, max 1000)
- **Thread-safe processed_files** — Lock для защиты от race condition в FolderWatcher

### Changed
- **Async OCR** — обработка OCR в thread pool (`run_in_executor`) для разблокировки event loop
- **Triple OCR fix** — оптимизация `extract_vendor`: теперь использует разбиение текста вместо 3x OCR вызовов (3x ускорение)
- **PDF optimization** — загрузка только первой страницы (`first_page=1, last_page=1`) — ~90% экономия RAM
- **CORS methods** — ограничены до GET, POST, DELETE (вместо "*")
- **UI: Sticky footer** — футер фиксированной высоты (80px), flexbox layout для стабильного отображения
- **UI: Компактный drop zone** — уменьшены отступы для выравнивания высоты табов
- **UI: Названия табов** — убраны эмодзи (Upload, Batch, Watch, Results)

---

## [1.5.0] - 2026-01-04

### Added
- **Онлайн версия** — деплой на Render.com (https://mae-idp.onrender.com)
- **Dockerfile** — Docker образ с Tesseract, Poppler, pyzbar
- **render.yaml** — конфиг для деплоя на Render.com
- **PORT env variable** — поддержка переменной окружения PORT для облачных платформ
- **Unit-тесты** — pytest тесты для core.py
- **main.py** — точка входа FastAPI для деплоя

### Fixed
- **XSS защита** — добавлена функция `escapeHtml()` для экранирования данных
- **Обработка ошибок fetch** — try/catch для `loadResults()` и `detectGDrive()`

### Changed
- **Ребрендинг** — переименование с "MAE PDF Parser" на "MAE-IDP"
- **README упрощён** — теперь для обычных пользователей (Download ZIP, без git)
- **pywebview закомментирован** — для совместимости с серверным деплоем
- **Переименована переменная `R` → `results`**
- **Удалён неиспользуемый `output_path`**

---

## [1.4.0] - 2026-01-03

### Added
- **Кроссплатформенность** — поддержка macOS и Linux помимо Windows
- **install.sh** — скрипт установки для macOS/Linux (автоопределение Homebrew, apt, dnf, pacman)
- **run.sh** — скрипт запуска для macOS/Linux
- **PWA поддержка** — приложение можно установить на iOS/Android как Progressive Web App
- **Мобильный доступ** — сервер теперь слушает на 0.0.0.0 для доступа с телефона в локальной сети
- **Safe-area-inset** — поддержка iPhone с вырезом (notch)
- **Apple touch icon** — иконка для добавления на домашний экран iOS

### Changed
- **setup_env.py** — полностью переписан для кроссплатформенной работы
- **README.md** — обновлён с инструкциями для Windows, macOS, Linux и мобильных устройств
- **index.html** — добавлены meta теги для PWA (viewport, apple-mobile-web-app, theme-color)

---

## [1.3.1] - 2026-01-03

### Fixed
- **Tesseract CMD** — теперь корректно устанавливается `pytesseract.pytesseract.tesseract_cmd`
- **Thread-unsafe parser** — добавлен `parser_lock` для защиты от параллельных вызовов
- **Race condition в FolderWatcher** — заменён `time.sleep(0.5)` на функцию `_wait_for_file_ready()` с polling
- **Утечка tkinter** — добавлен `try/finally` в `_browse_folder_sync()` для гарантированного уничтожения окна

---

## [1.3.0] - 2026-01-03

### Added
- Модульная архитектура: разделение на `core.py`, `mae.py`, `batch_rename.py`
- CLI инструмент `batch_rename.py` для пакетной обработки папок
- Базовый класс `BaseOCRProcessor` для переиспользования логики OCR
- Класс `ConfidenceScore` с весами для расчёта уверенности
- Автосортировка файлов по папкам вендоров (CLI)
- Папка `_ПРОВЕРИТЬ` для файлов требующих ручной проверки
- Excel отчёт с автошириной колонок
- Progress bar в CLI режиме
- Dry-run режим для предпросмотра без изменений
- CLAUDE.md с инструкциями для разработки
- CHANGELOG.md для отслеживания изменений
- BACKLOG.md для планирования задач

### Changed
- Рефакторинг: общая логика OCR вынесена в `core.py`
- `Parser` и `BatchProcessor` наследуют от `BaseOCRProcessor`
- Обновлён README.md с полной документацией

### Fixed
- Унификация расчёта Confidence между GUI и CLI

---

## [1.2.0] - 2026-01-02

### Added
- Мониторинг папок (Folder Watch) с watchdog
- Поддержка Google Drive Desktop автодетект
- Автоархивирование обработанных файлов с timestamp
- Сохранение конфигурации в `data/config.json`
- API endpoint `/api/detect-gdrive`
- API endpoint `/api/browse` с tkinter диалогом

### Changed
- Улучшен веб-интерфейс: статус watcher в header

---

## [1.1.0] - 2026-01-01

### Added
- Тёмная/светлая тема с переключателем
- Gradient дизайн интерфейса
- Статистика обработки (total, success, review, errors)
- Средний Confidence в результатах
- API endpoint `/api/open/{folder}` для открытия папок

### Changed
- Редизайн веб-интерфейса (Montserrat + JetBrains Mono)
- Улучшены стили таблицы результатов

---

## [1.0.0] - 2025-12-28

### Added
- Первый релиз
- FastAPI веб-сервер на порту 8766
- WebView GUI для Windows
- Drag & Drop загрузка файлов
- OCR распознавание через Tesseract (deu+eng)
- Извлечение QR-кодов и штрих-кодов (pyzbar)
- Извлечение: Vendor, Invoice Number, Internal Number, VAT ID
- Поддержка форматов: PDF, JPG, PNG, TIFF
- Экспорт результатов в Excel
- 24 известных вендора в базе
- Автоустановка через `install.bat`

---

## Типы изменений

- **Added** — новая функциональность
- **Changed** — изменения в существующей функциональности
- **Deprecated** — функциональность, которая будет удалена
- **Removed** — удалённая функциональность
- **Fixed** — исправления багов
- **Security** — исправления уязвимостей
