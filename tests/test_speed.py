import pytest
from pathlib import Path
from ldt import LdtSettings


# Тестовый класс для проверки сериализации
@LdtSettings.register_type
class MockUser:
    def __init__(self, name: str):
        self.name = name
    
    def __serialize__(self):
        return {"name": self.name}
    
    @classmethod
    def __deserialize__(cls, data):
        return cls(data["name"])


@pytest.fixture
def settings(tmp_path):
    path = tmp_path / "test_config.json"
    return LdtSettings(path, driver="json")


def test_set_and_value(settings):
    settings.setValue("key", "value")
    assert settings.value("key") == "value"


def test_dot_notation(settings):
    settings.setValue("ui.theme.color", "red")
    assert settings.value("ui/theme/color") == "red"
    assert settings.value("ui.theme.color") == "red"


def test_update(settings):
    settings.update(a=1, b=2, c=3)
    assert settings.value("a") == 1
    assert settings.value("b") == 2
    assert settings.value("c") == 3


def test_contains_and_remove(settings):
    settings.setValue("temp", 100)
    assert settings.contains("temp") is True
    settings.remove("temp")
    assert settings.contains("temp") is False


def test_all_keys(settings):
    settings.setValue("a.b", 1)
    settings.setValue("c", 2)
    keys = settings.allKeys()
    assert "a/b" in keys
    assert "c" in keys


def test_local_group(settings):
    with settings.localGroups("network"):
        settings.setValue("port", 8080)
    assert settings.value("network/port") == 8080


def test_block_signals(settings):
    with settings.blockSignals():
        assert settings._blocking_signals is True
    assert settings._blocking_signals is False


def test_serialization(settings):
    user = MockUser("Alice")
    settings.setValue("admin", user)
    restored = settings.value("admin")
    assert isinstance(restored, MockUser)
    assert restored.name == "Alice"


def test_context_manager_sync(tmp_path):
    path = tmp_path / "sync_test.json"
    with LdtSettings(path) as cfg:
        cfg.setValue("auto", "save")
    
    new_cfg = LdtSettings(path)
    assert new_cfg.value("auto") == "save"


def test_signals_emit(settings):
    if not settings.signals:
        pytest.skip("psygnal not installed")
    
    received = []
    settings.signals.valueChanged.connect(lambda k, v: received.append((k, v)))
    
    settings.setValue("signal.test", 123)
    assert len(received) == 1
    assert received[0] == ("signal/test", 123)