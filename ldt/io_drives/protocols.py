from typing import Protocol, runtime_checkable
from io import IOBase


@runtime_checkable
class PathProtocol(Protocol):
    @property
    def parent(self) -> "PathProtocol": ...
    
    def mkdir(self, mode=..., parents=..., exist_ok=...): ...
    
    def __truediv__(self, other) -> "PathProtocol": ...
    
    def open(self, mode='r', buffering=-1, encoding=None,
             errors=None, newline=None) -> IOBase: ...
    
    def exists(self) -> bool: ...


class SupportRead(Protocol):
    def read(self) -> str: ...


class SupportWrite(Protocol):
    def write(self, data: str): ...
