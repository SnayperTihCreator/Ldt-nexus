from contextlib import contextmanager
from os import fspath, PathLike
from typing import Literal, Protocol, Any, ClassVar, runtime_checkable, Type, Self

from attrs import define, field

from . import _ldt_core

try:
    from psygnal import SignalGroup, Signal
    HAS_PSYGNAL = True
except ImportError:
    HAS_PSYGNAL = False

DriversInner = Literal["json", "json5", "toml", "yaml", "memory"]


@runtime_checkable
class BaseDriverProtocol(Protocol):
    def read(self, path: str) -> dict[str, Any]: ...
    
    def write(self, path: str, data: dict[str, Any]) -> None: ...


DriverArg = DriversInner | BaseDriverProtocol


@runtime_checkable
class EncoderProtocol(Protocol):
    def __call__(self, obj: Any) -> dict[str, Any]: ...


@runtime_checkable
class DecoderProtocol(Protocol):
    def __call__(self, data: dict[str, Any]) -> Any: ...


@runtime_checkable
class SerializableProtocol(Protocol):
    def __serialize__(self) -> dict[str, Any]: ...
    
    @classmethod
    def __deserialize__(cls, data: dict[str, Any]) -> Self: ...


@define
class LdtSettings:
    _encoders: ClassVar[dict[str, EncoderProtocol]] = {}
    _decoders: ClassVar[dict[str, DecoderProtocol]] = {}
    
    path: str | PathLike[str] = field()
    driver: DriverArg = field(default="json")
    _core: _ldt_core.LdtSettingEngine = field(init=False, repr=False)
    signals: Any = field(init=False, repr=False, default=None)
    _blocking_signals: bool = field(init=False, repr=False, default=False)
    
    def _should_emit(self, silent: bool) -> bool:
        if not HAS_PSYGNAL or self.signals is None:
            return False
        return not (silent or self._blocking_signals)
    
    @classmethod
    def register_encoder(cls, objType: Type, encoder: EncoderProtocol):
        cls._encoders[objType.__qualname__] = encoder
    
    @classmethod
    def register_decoder(cls, objType: Type, decoder: DecoderProtocol):
        cls._decoders[objType.__qualname__] = decoder
    
    @classmethod
    def as_encoder(cls, objType: Type):
        def wrapper(encoder: EncoderProtocol):
            cls.register_encoder(objType, encoder)
            return encoder
        
        return wrapper
    
    @classmethod
    def as_decoder(cls, objType: Type):
        def wrapper(decoder: DecoderProtocol):
            cls.register_decoder(objType, decoder)
            return decoder
        
        return wrapper
    
    @classmethod
    def register_type(cls, objType: Type[SerializableProtocol]):
        cls.register_encoder(objType, lambda obj: obj.__serialize__())
        cls.register_decoder(objType, objType.__deserialize__)
        return objType
    
    def _pack(self, obj: Any) -> Any:
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        
        if isinstance(obj, list):
            return [self._pack(el) for el in obj]
        if isinstance(obj, dict):
            return {k: self._pack(v) for k, v in obj.items()}
        
        name = obj.__class__.__qualname__
        if name in self._encoders:
            data = self._encoders[name](obj)
            if not isinstance(data, dict):
                raise TypeError(f"Encoder for {name} must return a dict, got {type(data)}")
            data["_tag"] = name
            return data
        raise TypeError(f"No encoder registered for type: {name}. Cannot serialize.")
    
    def _unpack(self, data: Any) -> Any:
        if not isinstance(data, dict):
            if isinstance(data, list):
                return [self._unpack(i) for i in data]
            return data
        
        if "_tag" in data:
            data_copy = data.copy()
            class_name = data_copy.pop("_tag")
            if class_name in self._decoders:
                return self._decoders[class_name](data_copy)
        
        return {k: self._unpack(v) for k, v in data.items()}
    
    def __attrs_post_init__(self):
        self._core = _ldt_core.LdtSettingEngine(fspath(self.path), self.driver)
        
        if not HAS_PSYGNAL: return
        
        class LdtSignals(SignalGroup):
            valueChanged = Signal(str, object)  # (key, value)
            cleared = Signal()
            deleted = Signal(str)  # (key)
        
        self.signals = LdtSignals()
    
    def setValue(self, key: str, value: Any, silent: bool = False):
        packed = self._pack(value)
        safe_key = key.replace(".", "/")
        self._core.set_value(safe_key, packed)
        
        if self._should_emit(silent):
            self.signals.valueChanged.emit(safe_key, value)
    
    def value(self, key: str, default: Any = None) -> Any:
        safe_key = key.replace(".", "/")
        raw = self._core.value(safe_key)
        if raw is None:
            return default
        return self._unpack(raw)
    
    def update(self, silent: bool = False, **mapping: Any):
        """
        Массовое обновление ключей.
        Принимает аргументы как dict или именованные параметры.
        """
        packed = self._pack(mapping)
        
        with self.blockSignals():
            for key, value in packed.items():
                self.setValue(key, value)
        
        if self._should_emit(silent):
            for key, value in mapping.items():
                self.signals.valueChanged.emit(key.replace(".", "/"), value)
    
    @contextmanager
    def localGroups(self, *names: str):
        for name in names:
            self.beginGroup(name)
        try:
            yield self
        finally:
            for _ in names:
                self.endGroup()
    
    @contextmanager
    def blockSignals(self):
        self._blocking_signals, blocking = True, self._blocking_signals
        try:
            yield self
        finally:
            self._blocking_signals = blocking
    
    def beginGroup(self, name: str):
        self._core.begin_group(name)
    
    def endGroup(self):
        self._core.end_group()
    
    def group(self) -> str:
        return self._core.group()
    
    def allKeys(self) -> list[str]:
        return self._core.all_keys()
    
    def childKeys(self) -> list[str]:
        return self._core.child_keys()
    
    def childGroups(self) -> list[str]:
        return self._core.child_groups()
    
    def contains(self, key: str) -> bool:
        return self._core.contains(key)
    
    def remove(self, key: str, silent: bool = False):
        safe_key = key.replace(".", "/")
        self._core.remove(safe_key)
        if self._should_emit(silent):
            self.signals.deleted.emit(safe_key)
    
    def clear(self, silent: bool = False):
        self._core.clear()
        if self._should_emit(silent):
            self.signals.cleared.emit()
    
    def sync(self) -> None:
        self._core.sync()
    
    def status(self) -> int:
        return self._core.status()
    
    def isWritable(self) -> bool:
        return self._core.is_writable()
    
    def fileName(self) -> str:
        return self._core.file_name()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.sync()
