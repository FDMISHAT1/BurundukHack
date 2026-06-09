import yaml
from engine.paths import LANG_DIR

_current_lang = "en"
_translations: dict[str, dict] = {}


def _flatten(data: dict, prefix: str = "") -> dict[str, str]:
    result = {}
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            result.update(_flatten(value, full_key))
        else:
            result[full_key] = str(value)
    return result


def load_lang(lang_code: str):
    global _current_lang, _translations
    _current_lang = lang_code

    if lang_code not in _translations:
        path = LANG_DIR / f"{lang_code}.yaml"
        if path.exists():
            with open(path, "r") as f:
                data = yaml.safe_load(f) or {}
            _translations[lang_code] = _flatten(data)
        else:
            _translations[lang_code] = {}

    # Always load English as fallback
    if "en" not in _translations:
        en_path = LANG_DIR / "en.yaml"
        if en_path.exists():
            with open(en_path, "r") as f:
                data = yaml.safe_load(f) or {}
            _translations["en"] = _flatten(data)
        else:
            _translations["en"] = {}


def t(key: str, **kwargs) -> str:
    lang_dict = _translations.get(_current_lang, {})
    text = lang_dict.get(key)
    if text is None:
        en_dict = _translations.get("en", {})
        text = en_dict.get(key)
    if text is None:
        return key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text


def get_lang() -> str:
    return _current_lang
