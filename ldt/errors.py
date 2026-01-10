class LDTError(Exception):
    """Базовое исключение для системы LDT"""
    pass


class ReadOnlyError(LDTError):
    """Вызывается при попытке изменить замороженную ветку"""
    pass
