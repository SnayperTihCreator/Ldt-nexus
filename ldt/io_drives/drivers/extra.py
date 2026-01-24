from .base import BaseDriver
from ldt.io_drives.protocols import PathProtocol, SupportRead, SupportWrite

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
        with path.open("r", encoding="utf-8") as file:
            return self.read_stream(file)

    def write(self, path: PathProtocol, data: dict):
        with path.open("w", encoding="utf-8") as file:
            self.write_stream(file, data)
    
    def write_stream(self, stream: SupportWrite, data: dict):
        yaml = self._get_engine()
        yaml.dump(data, stream, sort_keys=False, allow_unicode=True)
    
    def read_stream(self, stream: SupportRead) -> dict:
        yaml = self._get_engine()
        return yaml.safe_load(stream) or {}


class Json5Driver(BaseDriver):
    @staticmethod
    def _get_engine():
        try:
            import json5
            return json5
        except ImportError:
            raise ImportError("Json5Driver requires 'json5'. Install it with: pip install ldt-nexus[json5]")

    def read(self, path: PathProtocol) -> dict:
        with path.open("r", encoding="utf-8") as file:
            return self.read_stream(file)

    def write(self, path: PathProtocol, data: dict):
        with path.open("w", encoding="utf-8") as file:
            self.write_stream(file, data)
    
    def read_stream(self, stream: SupportRead) -> dict:
        json5 = self._get_engine()
        return json5.load(stream)
    
    def write_stream(self, stream: SupportWrite, data: dict):
        json5 = self._get_engine()
        json5.dump(data, stream, quote_keys=True, indent=4, ensure_ascii=False)


class TomlDriver(BaseDriver):
    @staticmethod
    def _get_engine():
        try:
            import toml
            return toml
        except ImportError:
            raise ImportError("TomlDriver requires 'toml'. Install it with: pip install ldt-nexus[toml]")

    def read(self, path: PathProtocol) -> dict:
        with path.open("r", encoding="utf-8") as file:
            return self.read_stream(file)

    def write(self, path: PathProtocol, data: dict):
        with path.open("w", encoding="utf-8") as file:
            self.write_stream(file, data)
    
    def read_stream(self, stream: SupportRead) -> dict:
        toml = self._get_engine()
        return toml.load(stream)
    
    def write_stream(self, stream: SupportWrite, data: dict):
        toml = self._get_engine()
        toml.dump(data, stream)
        
    