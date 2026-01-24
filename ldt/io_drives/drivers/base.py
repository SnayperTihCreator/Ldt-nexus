from abc import ABC, abstractmethod
from typing import Protocol

from ldt.io_drives.protocols import PathProtocol, SupportRead, SupportWrite

__all__ = ["BaseDriver"]


class BaseDriver(ABC):
    @abstractmethod
    def read(self, path: PathProtocol) -> dict:
        ...
    
    @abstractmethod
    def write(self, path: PathProtocol, data: dict):
        ...
    
    @abstractmethod
    def read_stream(self, stream: SupportRead) -> dict: ...
    
    @abstractmethod
    def write_stream(self, stream: SupportWrite, data: dict): ...
