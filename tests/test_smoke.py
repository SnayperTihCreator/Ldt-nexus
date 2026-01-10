import pytest
from pathlib import Path
from ldt import NexusStore, NexusField, JsonDriver


# Тестовая модель
class MyConfig(NexusStore):
    name = NexusField("app.name", default="Nexus")
    version = NexusField("app.version", default=1)


def test_full_chain(tmp_path):
    """Проверка всей цепочки: Поле -> Стор -> Драйвер -> Файл"""
    config_path = tmp_path / "test.json"
    cfg = MyConfig(config_path, driver=JsonDriver())
    
    # 1. Проверка дефолтов
    assert cfg.name == "Nexus"
    
    # 2. Проверка записи и реактивности
    cfg.name = "LDT-App"
    assert cfg.value("app.name") == "LDT-App"
    
    # 3. Проверка сохранения (Sync)
    cfg.sync()
    assert config_path.exists()
    
    # 4. Проверка загрузки (Load)
    new_cfg = MyConfig(config_path, driver=JsonDriver())
    assert new_cfg.name == "LDT-App"


def test_signals_blocked(tmp_path):
    """Проверка блокировки сигналов"""
    cfg = MyConfig(tmp_path / "sig.json", driver=JsonDriver())
    
    changes = []
    MyConfig.name.connect(cfg, lambda x: changes.append(x))
    
    with cfg.blockSignals():
        cfg.name = "NewName"
    
    assert len(changes) == 0  # Сигнал не прошел
    assert cfg.name == "NewName"