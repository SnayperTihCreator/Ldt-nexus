import pytest
from ldt import LDT
from pathlib import Path


def test_perf_get_deep(benchmark):
    """Замер скорости глубокого поиска по дереву"""
    data = {"a": {"b": {"c": {"d": {"e": {"f": {"g": "hello"}}}}}}}
    ldt = LDT(data=data)
    
    # benchmark() вызовет функцию тысячи раз
    result = benchmark(lambda: ldt.get("a.b.c.d.e.f.g"))
    assert result == "hello"


def test_perf_set_deep(benchmark):
    """Замер скорости глубокой вставки"""
    ldt = LDT()
    
    def do_set():
        ldt.set("very.deep.path.to.my.value", 123)
    
    benchmark(do_set)


def test_perf_serialize_massive(benchmark):
    """Замер скорости сериализации 1000 объектов Path"""
    ldt = LDT()
    # Создаем список из 1000 путей
    massive_data = [Path(f"/home/user/file_{i}.txt") for i in range(1000)]
    
    # Проверяем, как Rust переваривает массу объектов
    benchmark(lambda: ldt.set("massive", massive_data))


def test_perf_deep_update(benchmark):
    """Замер скорости слияния больших словарей"""
    base = {f"key_{i}": {"sub": i} for i in range(500)}
    other = {f"key_{i}": {"sub": i + 1} for i in range(500)}
    ldt = LDT(data=base)
    
    benchmark(lambda: ldt.update(other, deep=True))