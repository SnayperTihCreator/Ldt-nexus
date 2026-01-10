import json

from .base import BaseDriver
from ldt.io.protocols import PathProtocol

__all__ = ["JsonDriver"]


class JsonDriver(BaseDriver):
    def read(self, path: PathProtocol) -> dict:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    
    def write(self, path: PathProtocol, data: dict):
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f)