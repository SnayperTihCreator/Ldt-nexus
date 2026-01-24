from pathlib import Path
from typing import Optional, List, Type, Any, Union
from contextlib import contextmanager

from .protocols import PathProtocol
from ldt.core import LDT
from .drivers import BaseDriver, JsonDriver


class NexusStore:
    """
    Полнофункциональная замена QSettings на базе LDT и сменных драйверов.
    Использует collections.deque для эффективного управления стеком групп.
    """
    
    def __init__(self, file_path: Union[str, PathProtocol], driver: BaseDriver = None, preload: bool = True):
        self.path: PathProtocol = Path(file_path) if isinstance(file_path, str) else file_path
        self.driver = driver or JsonDriver()
        self.ldt = LDT()
        self._group_stack: list[str] = []
        self._cached_prefix = ""
        self._signals_blocked = False
        if preload:
            self.load()
    
    # --- Навигация и Группы ---
    
    def _update_prefix(self):
        self._cached_prefix = ".".join(self._group_stack)
    
    def beginGroup(self, prefix: str):
        if prefix:
            self._group_stack.append(prefix.strip('./').replace('/', '.'))
            self._update_prefix()
    
    def endGroup(self):
        if self._group_stack:
            self._group_stack.pop()
            self._update_prefix()
        else:
            print("[LDTSettings] Warning: endGroup() called without matching beginGroup()")
    
    def group(self) -> str:
        """Возвращает текущую активную группу (строкой)"""
        return "/".join(self._group_stack)
    
    @contextmanager
    def group_context(self, prefix: str):
        """Python-style контекстный менеджер для групп"""
        self.beginGroup(prefix)
        try:
            yield self
        finally:
            self.endGroup()
    
    @contextmanager
    def blockSignals(self):
        """Временно отключает уведомления NexusField"""
        self._signals_blocked = True
        try:
            yield self
        finally:
            self._signals_blocked = False
    
    # --- Основные операции с данными ---
    
    def setValue(self, key: str, value: Any) -> bool:
        """Возвращает True, если значение реально изменилось"""
        full_key = self._get_full_key(key)
        return self.ldt.set(full_key, value)
    
    def value(self, key: str, default: Any = None, type_cls: Optional[Type] = None) -> Any:
        full_key = self._get_full_key(key)
        return self.ldt.get(full_key, target_cls=type_cls, default=default)
    
    def contains(self, key: str) -> bool:
        full_key = self._get_full_key(key)
        return self.ldt.has(full_key)
    
    def remove(self, key: str):
        """Удаляет ключ или целую группу"""
        self.ldt.delete(self._get_full_key(key))
    
    def clear(self):
        """Полная очистка конфига"""
        self.ldt.clear()
    
    # --- Инспекция (Методы для итерации) ---
    
    def allKeys(self) -> List[str]:
        branch = self.ldt.get_raw_branch(self._cached_prefix)
        return [k for k, v in branch.items() if not isinstance(v, dict)] if branch else []
    
    def childGroups(self) -> List[str]:
        branch = self.ldt.get_raw_branch(self._cached_prefix)
        return [k for k, v in branch.items() if isinstance(v, dict)] if branch else []
    
    def childKeys(self) -> List[str]:
        """Аналог allKeys(), возвращает только ключи (не группы)"""
        return self.allKeys()
    
    # --- Синхронизация ---
    
    def sync(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.driver.write(self.path, self.ldt.to_dict())
        except Exception as e:
            print(f"[NexusStore] Sync error: {e}")
    
    def load(self):
        if not self.path.exists():
            return
        try:
            data = self.driver.read(self.path)
            with self.blockSignals():
                self.ldt.clear()
                self.ldt.update(data)
        except Exception as e:
            print(f"[NexusStore] Load error: {e}")
    
    # --- Внутренние утилиты ---
    
    def _get_full_key(self, key: str) -> str:
        clean_key = key.strip('./').replace('/', '.')
        if not self._cached_prefix:
            return clean_key
        return f"{self._cached_prefix}.{clean_key}"
    
    def _get_current_branch(self) -> Any:
        """Возвращает сырые данные текущей ветки согласно стеку групп"""
        curr = self.ldt.to_dict()
        for g in self._group_stack:
            if isinstance(curr, dict) and g in curr:
                curr = curr[g]
            else:
                return None
        return curr
