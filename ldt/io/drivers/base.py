from abc import ABC, abstractmethod

from ldt.io.protocols import PathProtocol

__all__ = ["BaseDriver"]


class BaseDriver(ABC):
    @abstractmethod
    def read(self, path: PathProtocol) -> dict:
        ...
    
    @abstractmethod
    def write(self, path: PathProtocol, data: dict):
        ...