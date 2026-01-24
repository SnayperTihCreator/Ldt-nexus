import json

from .base import BaseDriver
from ldt.io_drives.protocols import PathProtocol, SupportWrite, SupportRead

__all__ = ["JsonDriver"]


class JsonDriver(BaseDriver):
    def read(self, path: PathProtocol) -> dict:
        with path.open("r", encoding="utf-8") as file:
            return self.read_stream(file)
    
    def write(self, path: PathProtocol, data: dict):
        with path.open("w", encoding="utf-8") as file:
            self.write_stream(file, data)
    
    def read_stream(self, stream: SupportRead) -> dict:
        return json.load(stream)
    
    def write_stream(self, stream: SupportWrite, data: dict):
        json.dump(data, stream, ensure_ascii=False, indent=4)
