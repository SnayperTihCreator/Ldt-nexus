from pathlib import Path
from typing import Optional, List, Type, Any, Union
from contextlib import contextmanager

from .protocols import PathProtocol
from ldt.core import LDT
from .drivers import BaseDriver, JsonDriver


class NexusStore:
    def __init__(self, file_path: Union[str, PathProtocol], driver: BaseDriver = None, preload: bool = True):
        self.path: PathProtocol = Path(file_path) if isinstance(file_path, str) else file_path
        self.driver = driver or JsonDriver()
        self.ldt = LDT()
        self._group_stack: list[str] = []
        self._cached_prefix = ""  # Кэш префикса (строка)
        self._signals_blocked = False
        if preload:
            self.load()
    
    # --- Навигация и Группы (Все сохранено) ---
    
    def _update_prefix(self):
        self._cached_prefix = ".".join(self._group_stack)
    
    def beginGroup(self, prefix: str):
        if prefix:
            # strip и replace делаем один раз при входе
            clean = prefix.strip('./').replace('/', '.')
            self._group_stack.append(clean)
            self._update_prefix()
    
    def endGroup(self):
        if self._group_stack:
            self._group_stack.pop()
            self._update_prefix()
        else:
            print("[NexusStore] Warning: endGroup() called without matching beginGroup()")
    
    def group(self) -> str:
        # Твой старый метод возврата строки через "/"
        return "/".join(self._group_stack)
    
    @contextmanager
    def group_context(self, prefix: str):
        self.beginGroup(prefix)
        try:
            yield self
        finally:
            self.endGroup()
    
    @contextmanager
    def blockSignals(self):
        self._signals_blocked = True
        try:
            yield self
        finally:
            self._signals_blocked = False
    
    def setValue(self, key: str, value: Any) -> bool:
        return self.ldt.set(self._get_full_key(key), value)
    
    def value(self, key: str, default: Any = None, type_cls: Optional[Type] = None) -> Any:
        return self.ldt.get(self._get_full_key(key), target_cls=type_cls, default=default)
    
    def contains(self, key: str) -> bool:
        return self.ldt.has(self._get_full_key(key))
    
    def remove(self, key: str):
        self.ldt.delete(self._get_full_key(key))
    
    def clear(self):
        self.ldt.clear()
    
    def allKeys(self) -> List[str]:
        return self.ldt.list_keys(self._cached_prefix)
    
    def childGroups(self) -> List[str]:
        return self.ldt.list_groups(self._cached_prefix)
    
    def childKeys(self) -> List[str]:
        return self.allKeys()
    
    def sync(self):
        try:
            # Стандартный Pathlib mkdir
            self.path.parent.mkdir(parents=True, exist_ok=True)
            # Передаем напрямую data (PyDict)
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
    
    def _get_full_key(self, key: str) -> str:
        clean_key = key.strip('./').replace('/', '.')
        if not self._cached_prefix:
            return clean_key
        return f"{self._cached_prefix}.{clean_key}"
    
    def _get_current_branch(self) -> Any:
        """Использует Rust метод для получения ветки вместо цикла Python"""
        return self.ldt.get_raw_branch(self._cached_prefix)