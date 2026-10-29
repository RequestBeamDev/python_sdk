import ast
import re
from pathlib import Path

import pytest

from requestbeam import RequestBeam
from requestbeam.i18n import _MESSAGES, SUPPORTED_LOCALES, normalize_locale, translate

ROOT = Path(__file__).resolve().parents[1]
PROJECT_LOCALES = {
    "en", "de", "tr", "it", "es", "fr", "pt-BR", "ja", "ko", "zh-CN", "zh-TW", "ru"
}


def test_all_project_languages_have_complete_messages():
    assert set(SUPPORTED_LOCALES) == PROJECT_LOCALES
    assert set(_MESSAGES) == PROJECT_LOCALES
    for locale in SUPPORTED_LOCALES:
        assert set(_MESSAGES[locale]) == set(_MESSAGES["en"])
        assert all(isinstance(value, str) and value.strip() for value in _MESSAGES[locale].values())


@pytest.mark.parametrize("locale", sorted(PROJECT_LOCALES))
def test_client_reports_localized_validation(locale):
    with pytest.raises(ValueError) as error:
        RequestBeam(api_key="", locale=locale)
    assert str(error.value) == translate(locale, "missing_api_key")


@pytest.mark.parametrize("alias,canonical", [
    ("cn", "zh-CN"), ("tw", "zh-TW"), ("pt", "pt-BR"),
    ("zh_CN", "zh-CN"), ("zh_TW", "zh-TW"), ("pt_BR", "pt-BR"),
])
def test_project_route_aliases(alias, canonical):
    assert normalize_locale(alias) == canonical


def test_unknown_locale_is_not_silently_english():
    with pytest.raises(ValueError):
        normalize_locale("unknown-locale")


@pytest.mark.parametrize("locale", sorted(PROJECT_LOCALES))
def test_readme_links_and_python_examples(locale):
    path = ROOT / "README.md" if locale == "en" else ROOT / "docs" / f"README.{locale}.md"
    content = path.read_text(encoding="utf-8")
    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", content):
        if "://" not in target and not target.startswith("#"):
            assert (path.parent / target.split("#", 1)[0]).exists(), (path, target)
    snippets = re.findall(r"```python\n(.*?)```", content, re.DOTALL)
    assert snippets, path
    for snippet in snippets:
        ast.parse(snippet)
