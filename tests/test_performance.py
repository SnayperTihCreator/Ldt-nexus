import pytest
import json
from ldt import LdtSettings

# Имитируем структуру данных
DATA_TO_WRITE = {"theme": "dark", "font_size": 14, "language": "ru"}


def test_nexus_write_speed(benchmark, tmp_path):
    """Тестируем скорость записи 1000 ключей в Nexus"""
    path = tmp_path / "nexus_bench.json"
    cfg = LdtSettings(path, driver="json")
    
    def run_write():
        with cfg.blockSignals():  # Блокируем сигналы для чистоты теста ядра
            for i in range(1000):
                cfg.setValue(f"group/item_{i}", DATA_TO_WRITE)
        cfg.sync()  # Форсируем запись на диск
    
    benchmark(run_write)


def test_python_json_write_speed(benchmark, tmp_path):
    """Тестируем скорость записи 1000 ключей через стандартный dict + json"""
    path = tmp_path / "standard_bench.json"
    
    def run_write():
        data = {}
        for i in range(1000):
            if "group" not in data: data["group"] = {}
            data["group"][f"item_{i}"] = DATA_TO_WRITE
        
        with open(path, "w") as f:
            json.dump(data, f)
    
    benchmark(run_write)


def test_nexus_read_speed(benchmark, settings_with_data):
    """Тестируем скорость чтения из Nexus (уже наполненного)"""
    
    def run_read():
        for i in range(1000):
            _ = settings_with_data.value(f"group/item_{i}")
    
    benchmark(run_read)


@pytest.fixture
def settings_with_data(tmp_path):
    path = tmp_path / "read_bench.json"
    cfg = LdtSettings(path)
    with cfg.blockSignals():
        for i in range(1000):
            cfg.setValue(f"group/item_{i}", DATA_TO_WRITE)
    cfg.sync()
    return cfg