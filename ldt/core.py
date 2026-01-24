from pathlib import Path, PurePath

import attrs
from typing import Any, Optional, Type, Callable, ClassVar, Union, Self, TypeVar

from .errors import LDTError, ReadOnlyError

T = TypeVar("T")


@attrs.define
class LDT:
    _data: dict[str, Any] = attrs.field(factory=dict)
    _readonly: bool = attrs.field(default=False)
    
    _SERIALIZERS: ClassVar[dict[Type, Callable]] = {
        Path: lambda p: p.as_posix(),
        PurePath: lambda p: p.as_posix()
    }
    _DESERIALIZERS: ClassVar[dict[str, Callable]] = {}
    
    @classmethod
    def _get_full_name(cls, target_cls: Type) -> str:
        """Получает уникальный строковый идентификатор класса"""
        return f"{target_cls.__module__}.{target_cls.__name__}"
    
    # --- Декораторы регистрации ---
    
    @classmethod
    def serializer(cls, target_class: Type[T]):
        """Регистрирует функцию, превращающую объект класса в dict"""
        def wrapper(func: Callable[[T], dict[str, Any]]) -> Callable[[T], dict[str, Any]]:
            cls._SERIALIZERS[target_class] = func
            return func
        
        return wrapper
    
    @classmethod
    def deserializer(cls, target_class: Type[T]):
        """Регистрирует функцию, восстанавливающую объект из dict"""
        def wrapper(func: Callable[[dict[str, Any]], T]) -> Callable[[dict[str, Any]], T]:
            full_name = cls._get_full_name(target_class)
            cls._DESERIALIZERS[full_name] = func
            return func
        
        return wrapper
    
    # --- Управление состоянием ---
    
    def get_raw_branch(self, path: str) -> Optional[dict]:
        """Возвращает прямую ссылку на словарь ветки (без копирования)"""
        if not path: return self._data
        
        curr = self._data
        for k in path.split('.'):
            if isinstance(curr, dict) and k in curr:
                curr = curr[k]
            else:
                return None
        return curr if isinstance(curr, dict) else None
    
    def freeze(self):
        """Замораживает текущую ветку. Изменения станут невозможны."""
        self._readonly = True
    
    def set(self, key: str, value: Any) -> bool:
        if self._readonly:
            raise ReadOnlyError("Attempted to modify a frozen LDT branch.")
        
        new_val = self._serialize_recursive(value)
        
        keys = key.split('.')
        target = self._data
        for k in keys[:-1]:
            if k not in target or not isinstance(target[k], dict):
                target[k] = {}
            target = target[k]
        
        last_key = keys[-1]
        if target.get(last_key) == new_val:
            return False
        
        target[last_key] = new_val
        return True
    
    def get(self, path: str, target_cls: Optional[Type] = None, default: Any = None) -> Any:
        keys = path.split('.')
        val = self._data
        
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                return default
        
        if val is None:
            return default
        
        if isinstance(val, dict) and target_cls is None:
            dtype = val.get("_dtype")
            if dtype and dtype in self._DESERIALIZERS:
                return self._DESERIALIZERS[dtype](val)
            return LDT(data=val, readonly=self._readonly)
        
        return self._deserialize_recursive(val, target_cls)
    
    def delete(self, path: str):
        """
        Удаляет ключ по указанному пути (напр. 'settings.theme.color').
        Если ключ не найден, ничего не происходит.
        """
        if self._readonly:
            raise ReadOnlyError("Cannot delete keys from a frozen LDT branch.")
        
        keys = path.split('.')
        target = self._data
        
        # Идем до предпоследнего уровня
        for k in keys[:-1]:
            if isinstance(target, dict) and k in target:
                target = target[k]
            else:
                return  # Путь не существует
        
        # Удаляем финальный ключ
        if isinstance(target, dict) and keys[-1] in target:
            del target[keys[-1]]
    
    def clear(self):
        """Полностью очищает текущую ветку"""
        if self._readonly:
            raise ReadOnlyError("Branch is frozen.")
        self._data.clear()
    
    def update(self, data: dict | Self, deep: bool = False):
        """
        Обновляет данные.
        Если deep=True, вложенные словари будут объединяться, а не перезаписываться.
        """
        if self._readonly:
            raise ReadOnlyError("Branch is frozen.")
        
        source = data._data if isinstance(data, LDT) else data
        
        if not deep:
            for k, v in source.items():
                self._data[k] = self._serialize_recursive(v)
        else:
            self._deep_update(self._data, source)
    
    def _deep_update(self, base_dict: dict, source_dict: dict):
        for k, v in source_dict.items():
            if k in base_dict and isinstance(base_dict[k], dict) and isinstance(v, dict):
                self._deep_update(base_dict[k], v)
            else:
                base_dict[k] = self._serialize_recursive(v)
    
    def has(self, path: str) -> bool:
        """Проверяет наличие ключа по пути 'a.b.c'"""
        keys = path.split('.')
        val = self._data
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return False
        return True
    
    # --- Внутренняя логика ---
    
    def _serialize_recursive(self, obj: Any) -> Any:
        obj_type = type(obj)
        
        # FAST PATH: Самые частые типы проверяем первыми без вызова функций
        if obj_type in (str, int, float, bool, type(None)):
            return obj
        
        # CUSTOM SERIALIZERS
        if obj_type in self._SERIALIZERS:
            data = self._SERIALIZERS[obj_type](obj)
            if obj_type not in (Path, PurePath) and isinstance(data, dict):
                data["_dtype"] = self._get_full_name(obj_type)
            return data
        
        # CONTAINERS
        if obj_type is list:
            return [self._serialize_recursive(i) for i in obj]
        if obj_type is dict:
            return {k: self._serialize_recursive(v) for k, v in obj.items()}
        if isinstance(obj, LDT):
            return obj._data
        
        return obj
    
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
    
    def __contains__(self, key: str) -> bool:
        """Позволяет использовать оператор 'in' (только для верхнего уровня)"""
        return key in self._data
    
    def __or__(self, other: Union[dict, Self]) -> Self:
        import copy
        new_data = copy.deepcopy(self._data)
        new_ldt = LDT(data=new_data)
        new_ldt.update(other)
        return new_ldt
    
    def __ior__(self, other: Union[dict, Self]) -> Self:
        self.update(other)
        return self
    
    def __getitem__(self, key: str) -> Any:
        """Позволяет обращаться ldt['key.path']"""
        res = self.get(key)
        if res is None and not self.has(key):
            raise KeyError(key)
        return res
    
    def to_dict(self) -> dict:
        """Возвращает сырой словарь данных (для сохранения в JSON/Pydantic)"""
        return self._data
