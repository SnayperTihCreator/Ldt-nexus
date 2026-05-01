# 📂 LDT Nexus

**LDT Nexus** — это сверхбыстрое ядро на Rust для управления настройками и локализацией в Python-приложениях. Вдохновлено `QSettings`, но усилено асинхронностью, сигналами и высокой производительностью[cite: 4].

## ✨ Почему Nexus?
* **Rust Core**: Обработка данных и нормализация путей на стороне Rust.
* **Многопоточность**: Параллельная загрузка файлов конфигурации и переводов.
* **Реактивность**: Полная поддержка сигналов через `psygnal` для мгновенного обновления UI.
* **Гибкость драйверов**: Поддержка JSON, JSON5, TOML, YAML и Memory-режима из коробки.

---

## ⚙️ LdtSettings: Управление конфигурацией

`LdtSettings` — это основное хранилище, которое заменяет стандартные парсеры конфигов.

### Базовое использование
```python
from ldt.nexus import LdtSettings

# Автоматический sync() на диск при выходе из контекста
with LdtSettings("config.toml", driver="toml") as cfg:
    cfg.setValue("ui.theme", "dark")
    cfg.setValue("window.size", [1920, 1080])

# Доступ через группы (аналог QSettings)
with cfg.localGroups("editor", "font"):
    cfg.setValue("family", "Fira Code") # Итоговый ключ: editor/font/family
```

### Реактивность и Сигналы
Вы можете подписаться на изменения в конфиге, чтобы ваш код реагировал на них автоматически.

```python
cfg = LdtSettings("settings.json")

# Сигнал срабатывает при каждом изменении ключа
cfg.signals.valueChanged.connect(lambda key, val: print(f"Update: {key} = {val}"))

# Массовое обновление без лишних сигналов
with cfg.blockSignals():
    cfg.update(theme="light", language="ru")
```

---

## 🌍 LdtTranslator: Реактивная локализация

Новый модуль для работы с переводами, построенный на базе `LdtSettings` в памяти.

### Параллельная загрузка и кэширование
Переводчик умеет загружать десятки файлов локализации параллельно, используя все ядра процессора.

```python
from ldt.nexus.engine import LdtTranslator

translator = LdtTranslator("locales/")
translator.load(parallel=True) # Быстрая загрузка через ThreadPoolExecutor

# Использование сигналов смены языка
translator.signals.language_changed.connect(lambda lang: print(f"Язык изменен на {lang}"))

translator.set_lang("ru")
print(translator.tr("app.title")) # Поддержка контекста и переменных
```

### Поддержка Плюралов (Множественные числа)
```python
# 'apples': {'1': '{n} яблоко', '2': '{n} яблока', '5': '{n} яблок'}
print(translator.plural("apples", 21)) # 21 яблоко
```

---

## 🛠 Возможности ядра

| Особенность | Описание                                                                  |
| :--- |:--------------------------------------------------------------------------|
| **Normalizer** | Автоматическая замена `.` на `/` в путях на уровне Rust.                  |
| **Drivers** | JSON, JSON5, TOML, YAML, Memory.                                          |
| **Serializers** | Регистрация кастомных типов через `@LdtSettings.register_type`.           |
| **Caching** | Встроенный `TTLCache` в переводчике для мгновенного доступа к UI-строкам. |

---

## 🚀 Установка

```bash
# Базовая версия
pip install ldt-nexus

# С поддержкой сигналов
pip install ldt-nexus[signals]
```