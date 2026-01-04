# Changelog

Все значимые изменения в проекте документируются в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/),
проект придерживается [Semantic Versioning](https://semver.org/lang/ru/).

---

## [Unreleased]

### Added
- **Unit-тесты** — добавлены pytest тесты для core.py (extract_vendor, extract_invoice_number, extract_vat_id, extract_internal_from_qr)
- **CI/CD** — тесты теперь проходят в GitHub Actions
- **main.py** — точка входа FastAPI для деплоя
- **Dockerfile** — Docker образ с Tesseract, Poppler, pyzbar
- **render.yaml** — конфиг для деплоя на Render.com
- **PORT env variable** — поддержка переменной окружения PORT для облачных платформ

### Fixed
- **XSS защита** — добавлена функция `escapeHtml()` для экранирования данных в таблице результатов
- **Обработка ошибок fetch** — добавлены try/catch для `loadResults()` и `detectGDrive()`

### Changed
- **Ребрендинг** — переименование проекта с "MAE PDF Parser" на "MAE-IDP" (Intelligent Document Processing)
- **Переименована переменная `R` → `results`** — улучшена читаемость кода в index.html
- **Удалён неиспользуемый `output_path`** — очистка dead code в FolderWatcher
- **Версия в install.bat** — обновлена с 1.1.0 до 1.4.0
- **pywebview закомментирован** — в requirements.txt для совместимости с серверным деплоем

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
