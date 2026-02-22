import copy
from pathlib import Path, PurePath
from typing import Any, Optional, Type, Callable, ClassVar, Union, Self, TypeVar
from ._ldt import NativeLDT
from .errors import ReadOnlyError

T = TypeVar("T")


class LDT(NativeLDT):
    _SERIALIZERS: ClassVar[dict[Type, Callable]] = {
        Path: lambda p: p.as_posix(),
        PurePath: lambda p: p.as_posix()
    }
    _DESERIALIZERS: ClassVar[dict[str, Callable]] = {}
    
    def __init__(self, data: dict = None, readonly: bool = False):
        super().__init__()
    
    @classmethod
    def _get_full_name(cls, target_cls: Type) -> str:
        return f"{target_cls.__module__}.{target_cls.__name__}"
    
    @classmethod
    def serializer(cls, target_class: Type[T]):
        def wrapper(func):
            cls._SERIALIZERS[target_class] = func
            return func
        
        return wrapper
    
    @classmethod
    def deserializer(cls, target_class: Type[T]):
        def wrapper(func):
            full_name = cls._get_full_name(target_class)
            cls._DESERIALIZERS[full_name] = func
            return func
        
        return wrapper
    
    # --- Управление состоянием ---
    
    def freeze(self):
        self.readonly = True
    
    def get_raw_branch(self, path: str) -> Optional[dict]:
        # Rust get_path вернет ссылку на внутренний dict, если он там есть
        res = self.get_path(path)
        return res if isinstance(res, dict) else None
    
    def set(self, key: str, value: Any) -> bool:
        # serialize_recursive теперь в Rust
        new_val = self.serialize_recursive(value, self._SERIALIZERS)
        return self.set_path(key, new_val)
    
    def get(self, path: str, target_cls: Optional[Type] = None, default: Any = None) -> Any:
        val = self.get_path(path)
        if val is None:
            return default
        
        if isinstance(val, dict) and target_cls is None:
            dtype = val.get("_dtype")
            if dtype and dtype in self._DESERIALIZERS:
                return self._DESERIALIZERS[dtype](val)
            return LDT(data=val, readonly=self.readonly)
        
        return self._deserialize_recursive(val, target_cls)
    
    def delete(self, path: str):
        # Используем новый быстрый метод из Rust
        self.delete_path(path)
    
    def clear(self):
        if self.readonly:
            raise ReadOnlyError("Branch is frozen.")
        self.data.clear()
    
    def update(self, data: dict | Self, deep: bool = False):
        if self.readonly:
            raise ReadOnlyError("Branch is frozen.")
        
        source = data.data if isinstance(data, LDT) else data
        # Прогоняем весь source через Rust сериализатор
        serialized_source = self.serialize_recursive(source, self._SERIALIZERS)
        
        if not deep:
            self.data.update(serialized_source)
        else:
            self.deep_update_py(self.data, serialized_source)
    
    def has(self, path: str) -> bool:
        # В Rust get_path возвращает None, если пути нет
        return self.get_path(path) is not None
    
    def _deserialize_recursive(self, val: Any, target_cls: Optional[Type] = None) -> Any:
        if target_cls in (Path, PurePath) and isinstance(val, str):
            return target_cls(val)
        if isinstance(val, list):
            return [self._deserialize_recursive(i) for i in val]
        if isinstance(val, dict):
            dtype = val.get("_dtype")
            if dtype in self._DESERIALIZERS:
                return self._DESERIALIZERS[dtype](val)
            if target_cls:
                clean_data = {k: v for k, v in val.items() if k != "_dtype"}
                return target_cls(**clean_data)
        return val
    
    # --- Магия и операторы ---
    
    def to_dict(self) -> dict:
        return self.data
    
    def __contains__(self, key: str) -> bool:
        return self.has(key)
    
    def __getitem__(self, key: str) -> Any:
        res = self.get(key)
        if res is None and not self.has(key):
            raise KeyError(key)
        return res
    
    def __or__(self, other: Union[dict, Self]) -> Self:
        new_data = copy.deepcopy(self.data)
        new_ldt = LDT(data=new_data)
        new_ldt.update(other)
        return new_ldt
    
    def __ior__(self, other: Union[dict, Self]) -> Self:
        self.update(other)
        return self