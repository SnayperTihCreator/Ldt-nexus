# 📂 LDT Nexus

**LDT Nexus** — это легковесный фреймворк для управления конфигурациями и состоянием приложения. Он превращает обычные JSON/YAML файлы в реактивные деревья данных с интерфейсом `pathlib`.

## ✨ Основные возможности
* **Dot-Notation**: Забудьте о `data["ui"]["theme"]["color"]`. Используйте `config.value("ui.theme.color")`.
* **NexusFields**: Описывайте настройки декларативно. Ваши переменные сами знают, как сохраняться и уведомлять об изменениях.
* **Type-Safe**: Автоматическое восстановление типов (`Path`, `datetime`, `QColor` и ваши собственные классы).
* **Zero-Dependency Core**: Минимальный размер. Внешние драйверы (YAML, TOML) подключаются только при необходимости.

---

## 📦 Установка

```bash
# Базовая версия (только JSON)
uv add ldt-nexus

# Полная версия (YAML, TOML, JSON5)
uv add ldt-nexus --extra all

```

---

## 🚀 Подробные примеры

### 1. Декларативная модель (Реактивность)

Самый удобный способ работы — создание класса-модели.

```python
from ldt import NexusStore, NexusField, JsonDriver

class AppSettings(NexusStore):
    # Поля с дефолтными значениями
    theme = NexusField("ui.theme", default="dark")
    volume = NexusField("audio.max_volume", default=80)
    last_file = NexusField("system.history.last_opened")

# Инициализация
cfg = AppSettings("config.json", driver=JsonDriver())

# Подписка на изменения конкретного поля
AppSettings.theme.connect(cfg, lambda val: print(f"Тема изменена на: {val}"))

# Автоматическая запись и уведомление
cfg.theme = "light"  # В консоли: "Тема изменена на: light"
cfg.sync()           # Сохранение на диск

```

### 2. Работа с группами (стиль QSettings)

Если вы переходите с Qt, вам будет привычен этот синтаксис:

```python
with cfg.group_context("database"):
    cfg.setValue("host", "localhost")
    cfg.setValue("port", 5432)
    
# Значение сохранится по пути "database.host"
print(cfg.value("database.host")) 

```

### 3. Кастомные сериализаторы

Научите Nexus работать с вашими классами.

```python
from ldt import LDT
from dataclasses import dataclass

@dataclass
class User:
    name: str
    role: str

@LDT.serializer(User)
def ser_user(u: User):
    return {"name": u.name, "role": u.role}

@LDT.deserializer(User)
def deser_user(data):
    return User(name=data["name"], role=data["role"])

# Теперь Nexus понимает этот тип данных
cfg.setValue("current_user", User("Admin", "root"))
user = cfg.value("current_user", type_cls=User)

```

### 4. Блокировка сигналов (Bulk Update)

Чтобы не спамить уведомлениями при массовой загрузке данных:

```python
with cfg.blockSignals():
    for i in range(100):
        cfg.setValue(f"item_{i}", i)
# Сигналы сработают только после выхода из блока, если это необходимо

```

---

## 🛠 Выбор драйвера (Optional Dependencies)

LDT Nexus поддерживает разные форматы через систему драйверов:

```python
from ldt.io_drives.drivers import JsonDriver, YamlDriver, TomlDriver

# Для YAML (требуется ldt-nexus[yaml])
cfg_yaml = NexusStore("config.yaml", driver=YamlDriver())

# Для TOML (требуется ldt-nexus[toml])
cfg_toml = NexusStore("config.toml", driver=TomlDriver())

```

---

## 🧪 Тестирование вашего проекта

Благодаря `PathProtocol`, вы можете легко тестировать свои конфиги, используя `tmp_path` в `pytest`:

```python
def test_settings(tmp_path):
    path = tmp_path / "test.json"
    cfg = AppSettings(path, driver=JsonDriver())
    cfg.theme = "blue"
    cfg.sync()
    assert path.exists()

```

---

## 🏗 Структура проекта

* `ldt.core`: Ядро обработки деревьев данных.
* `ldt.fields`: Реактивные дескрипторы.
* `ldt.io.store`: Основной интерфейс хранилища.
* `ldt.io.drivers`: Сменные модули сериализации.

---

## ⚖️ Лицензия

MIT
