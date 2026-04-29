import time
from ldt import LdtSettings  # Твоя новая версия на Rust


def benchmark():
    # Настройки
    settings = LdtSettings("bench.toml", "toml")
    iterations = 100_000
    
    print(f"🚀 Запуск теста: {iterations} операций...")
    
    # Тест 1: Массовая запись (Deep Write)
    start = time.perf_counter()
    for i in range(iterations):
        settings.setValue(f"Group_{i}/SubGroup/Key", f"Value_{i}")
    end = time.perf_counter()
    print(f"✅ Запись {iterations} вложенных ключей: {end - start:.4f} сек")
    
    # Тест 2: Массовое чтение (Deep Read)
    start = time.perf_counter()
    for i in range(iterations):
        _ = settings.value(f"Group_{i}/SubGroup/Key")
    end = time.perf_counter()
    print(f"✅ Чтение {iterations} ключей: {end - start:.4f} сек")
    
    # Тест 3: Синхронизация (IO)
    start = time.perf_counter()
    settings.sync()
    end = time.perf_counter()
    print(f"💾 Сохранение тяжелого TOML на диск: {end - start:.4f} сек")


if __name__ == "__main__":
    benchmark()