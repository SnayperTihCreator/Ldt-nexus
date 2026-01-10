from typing import Any, Callable
from weakref import WeakKeyDictionary


class NexusField:
    def __init__(self, key: str, default: Any = None):
        self.key = key
        self.default = default
        self._instance_callbacks: WeakKeyDictionary = WeakKeyDictionary()
    
    def __get__(self, instance, owner):
        if instance is None:
            return self
        return instance.value(self.key, default=self.default)
    
    def __set__(self, instance, value):
        if instance is None:
            return
        was_changed = instance.setValue(self.key, value)
        if was_changed and not getattr(instance, "_signals_blocked", False):
            self._notify(instance, value)
    
    def _notify(self, instance, value):
        if instance in self._instance_callbacks:
            for cb in self._instance_callbacks[instance]:
                try:
                    cb(value)
                except Exception as e:
                    print(f"[NexusField] Error in callback for {self.key}: {e}")
    
    def connect(self, instance, callback: Callable):
        """Регистрация обработчика изменений"""
        if instance not in self._instance_callbacks:
            self._instance_callbacks[instance] = []
        
        if callback not in self._instance_callbacks[instance]:
            self._instance_callbacks[instance].append(callback)
    
    def disconnect(self, instance, callback: Callable):
        """Удаление обработчика"""
        if instance in self._instance_callbacks:
            if callback in self._instance_callbacks[instance]:
                self._instance_callbacks[instance].remove(callback)