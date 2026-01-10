from .base import BaseDriver
from ldt.io.protocols import PathProtocol

__all__ = ["YamlDriver", "Json5Driver", "TomlDriver"]


class YamlDriver(BaseDriver):
    @staticmethod
    def _get_engine():
        try:
            import yaml
            return yaml
        except ImportError:
            raise ImportError("YamlDriver requires 'pyyaml'. Install it with: pip install ldt-nexus[yaml]")

    def read(self, path: PathProtocol) -> dict:
        yaml = self._get_engine()
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def write(self, path: PathProtocol, data: dict):
        yaml = self._get_engine()
        with path.open("w", encoding="utf-8") as f:
            yaml.dump(data, f, sort_keys=False, allow_unicode=True)


class Json5Driver(BaseDriver):
    @staticmethod
    def _get_engine():
        try:
            import json5
            return json5
        except ImportError:
            raise ImportError("Json5Driver requires 'json5'. Install it with: pip install ldt-nexus[json5]")

    def read(self, path: PathProtocol) -> dict:
        json5 = self._get_engine()
        with path.open("r", encoding="utf-8") as f:
            return json5.load(f)

    def write(self, path: PathProtocol, data: dict):
        json5 = self._get_engine()
        with path.open("w", encoding="utf-8") as f:
            json5.dump(data, f, quote_keys=True, indent=4, ensure_ascii=False)


class TomlDriver(BaseDriver):
    @staticmethod
    def _get_engine():
        try:
            import toml
            return toml
        except ImportError:
            raise ImportError("TomlDriver requires 'toml'. Install it with: pip install ldt-nexus[toml]")

    def read(self, path: PathProtocol) -> dict:
        toml = self._get_engine()
        with path.open("r", encoding="utf-8") as f:
            return toml.load(f)

    def write(self, path: PathProtocol, data: dict):
        toml = self._get_engine()
        with path.open("w", encoding="utf-8") as f:
            toml.dump(data, f)