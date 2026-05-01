import pytest
import json
from pathlib import Path
from ldt.i18n import LdtTranslator


@pytest.fixture
def locale_dir(tmp_path):
    """Создает временную папку с файлами переводов разных форматов"""
    # Файл main_ru.json
    main_ru = {
        "welcome": {
            "login": "С возвращением, {name}!",
            "signup": "Добро пожаловать, {name}!"
        },
        "apples": {
            "0": "Пусто",
            "1": "{n} яблоко",
            "2": "{n} яблока",
            "5": "{n} яблок",
            "other": "{n} яблок"
        }
    }
    # Файл ui_en.json (имитация другого префикса и языка)
    ui_en = {
        "buttons": {
            "save": "Save Changes",
            "cancel": "Cancel"
        }
    }
    
    (tmp_path / "main_ru.json").write_text(json.dumps(main_ru), encoding="utf-8")
    (tmp_path / "ui_en.json").write_text(json.dumps(ui_en), encoding="utf-8")
    
    return tmp_path


@pytest.fixture
def translator(locale_dir):
    tr = LdtTranslator(locale_dir)
    tr.load()
    return tr


def test_load_and_prefixes(translator):
    """Проверяем, что файлы загрузились с правильными префиксами и языками"""
    translator.set_lang("ru")
    # Проверяем наличие ключа из main_ru
    assert translator.tr("main.welcome.login", name="Боб") == "С возвращением, Боб!"
    
    translator.set_lang("en")
    # Проверяем наличие ключа из ui_en
    assert translator.tr("ui.buttons.save") == "Save Changes"


def test_context_translation(translator):
    """Проверяем работу контекста (приоритетный путь поиска)"""
    translator.set_lang("ru")
    
    # С контекстом 'login'
    res_login = translator.tr("main.welcome", context="login", name="Алиса")
    assert res_login == "С возвращением, Алиса!"
    
    # С контекстом 'signup'
    res_signup = translator.tr("main.welcome", context="signup", name="Алиса")
    assert res_signup == "Добро пожаловать, Алиса!"


def test_plural_exact_match(translator):
    """Проверяем точное совпадение числа (0)"""
    translator.set_lang("ru")
    assert translator.plural("main.apples", 0) == "Пусто"


def test_plural_rules(translator):
    """Проверяем математические правила (1, 2, 5)"""
    translator.set_lang("ru")
    
    assert translator.plural("main.apples", 1) == "1 яблоко"
    assert translator.plural("main.apples", 22) == "22 яблока"
    assert translator.plural("main.apples", 11) == "11 яблок"
    assert translator.plural("main.apples", 100) == "100 яблок"


def test_missing_keys(translator):
    """Проверяем поведение при отсутствии ключей"""
    translator.set_lang("ru")
    # Должен вернуть сам ключ, если перевода нет
    assert translator.tr("non.existent.key") == "non.existent.key"


def test_wrong_file_format(tmp_path):
    """Проверяем, что файлы без подчеркивания игнорируются"""
    (tmp_path / "brokenfile.json").write_text('{"a": 1}')
    tr = LdtTranslator(tmp_path)
    tr.load()
    tr.set_lang("ru")
    # В памяти не должно быть этого ключа под префиксом ru или brokenfile
    assert tr.tr("brokenfile.a") == "brokenfile.a"