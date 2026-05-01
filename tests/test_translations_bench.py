import pytest
import json
from ldt.i18n import LdtTranslator


@pytest.fixture
def large_locale_dir(tmp_path):
    """Генерирует тяжелый файл перевода (10 000 ключей)"""
    data = {
        f"item_{i}": {
            "1": f"У вас {i} яблоко",
            "other": f"У вас {i} яблок"
        } for i in range(10000)
    }
    # Файл: bench_ru.json
    (tmp_path / "bench_ru.json").write_text(json.dumps(data), encoding="utf-8")
    return tmp_path


def test_nexus_translator_read_speed(benchmark, large_locale_dir):
    """Тест скорости чтения случайных ключей через Nexus Rust-ядро"""
    tr = LdtTranslator(large_locale_dir)
    tr.load()
    tr.set_lang("ru")
    
    def run_bench():
        # Читаем 1000 разных ключей
        for i in range(1000):
            _ = tr.tr(f"bench.item_{i}")
    
    benchmark(run_bench)


def test_python_dict_read_speed(benchmark, large_locale_dir):
    """Тест скорости чтения через стандартный dict (Python)"""
    with open(large_locale_dir / "bench_ru.json", "r", encoding="utf-8") as f:
        data = {"bench": json.load(f)}
    
    def run_bench():
        # Симулируем поиск lang -> prefix -> key
        for i in range(1000):
            _ = data.get("bench", {}).get(f"item_{i}")
    
    benchmark(run_bench)


def test_nexus_plural_speed(benchmark, large_locale_dir):
    """Тест скорости обработки множественных чисел в Nexus"""
    tr = LdtTranslator(large_locale_dir)
    tr.load()
    tr.set_lang("ru")
    
    def run_bench():
        for i in range(1000):
            # Прогон через логику категорий и форматирование
            _ = tr.plural(f"bench.item_{i}", i)
    
    benchmark(run_bench)
