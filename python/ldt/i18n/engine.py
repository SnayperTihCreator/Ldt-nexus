from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

from attrs import define, field
from cachetools import TTLCache

from ldt.nexus import LdtSettings

try:
    from psygnal import SignalGroup, Signal
    
    HAS_PSYGNAL = True
except ImportError:
    HAS_PSYGNAL = False


@define
class LdtTranslator:
    _folder: Optional[Path]
    _store: Optional[LdtSettings] = field(default=None, repr=False, init=False)
    _current_lang: str = field(default="en", init=False)
    _cache: TTLCache = field(init=False, factory=lambda: TTLCache(maxsize=10000, ttl=300))
    
    signals: Optional['SignalGroup'] = field(default=None, init=False)
    
    def __attrs_post_init__(self):
        self._folder = Path(self._folder)
        self._store = LdtSettings(self._folder, driver="memory")
        
        if HAS_PSYGNAL:
            class TranslatorSignals(SignalGroup):
                language_changed = Signal(str)
                loaded = Signal()
            
            self.signals = TranslatorSignals()
    
    def _load_single_file(self, file: Path):
        try:
            prefix, lang = file.stem.rsplit("_", 1)
            ext = file.suffix.lstrip(".")
            
            loader = LdtSettings(file, driver=ext)
            with self._store.localGroups(lang, prefix):
                for key in loader.allKeys():
                    self._store.setValue(key, loader.value(key))
        except Exception:
            pass
    
    def load(self, parallel: bool = True):
        if not self._folder.exists(): return
        
        files = [f for f in self._folder.iterdir() if not f.is_dir() and "_" in f.stem]
        
        if parallel and len(files) > 1:
            with ThreadPoolExecutor() as executor:
                executor.map(self._load_single_file, files)
        else:
            for file in files:
                self._load_single_file(file)
        
        if self.signals:
            self.signals.loaded.emit()
    
    def set_lang(self, lang: str):
        self._current_lang = lang
        self._cache.clear()
        
        if self.signals:
            self.signals.language_changed.emit(lang)
    
    def translate(self, key: str, context: Optional[str] = None, **kwargs) -> str:
        cache_key = f"{self._current_lang}:{key}:{context}"
        
        if cache_key in self._cache and not kwargs:
            return self._cache[cache_key]
        
        res_key = key
        search_paths = [f"{self._current_lang}.{key}.{context}", f"{self._current_lang}.{key}"] if context else [
            f"{self._current_lang}.{key}"]
        
        for p in search_paths:
            val = self._store.value(p)
            if val is not None and isinstance(val, str):
                res_key = val
                break
        
        result = res_key.format(**kwargs) if kwargs else res_key
        if not kwargs:
            self._cache[cache_key] = result
        
        return result
    
    def plural(self, key: str, n: int, **kwargs) -> str:
        # Для плюралов кэширование сложнее, поэтому идем в ядро напрямую[cite: 2]
        full_path = f"{self._current_lang}.{key}"
        data = self._store.value(full_path)
        
        if not isinstance(data, dict):
            return self.translate(key, **kwargs)
        
        str_n = str(n)
        if str_n in data:
            return str(data[str_n]).format(n=n, **kwargs)
        
        rule = self._get_simple_rule(n)
        pattern = data.get(rule, data.get("other", data.get("default", key)))
        return str(pattern).format(n=n, **kwargs)
    
    def tr(self, key: str, context: Optional[str] = None, **kwargs) -> str:
        return self.translate(key, context, **kwargs)
    
    def _get_simple_rule(self, n: int) -> str:
        n = abs(n)
        if self._current_lang == "ru":
            if n % 10 == 1 and n % 100 != 11: return "1"
            if 2 <= n % 10 <= 4 and (n % 100 < 10 or n % 100 >= 20): return "2"
            return "5"
        return "1" if n == 1 else "other"
