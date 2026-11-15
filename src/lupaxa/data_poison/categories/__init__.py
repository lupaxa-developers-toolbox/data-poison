"""Importing this package registers the built-in catalogue."""

from __future__ import annotations

import importlib

_CATEGORY_MODULES = (
    "lupaxa.data_poison.categories.csv_doc",
    "lupaxa.data_poison.categories.dates",
    "lupaxa.data_poison.categories.emails",
    "lupaxa.data_poison.categories.filenames",
    "lupaxa.data_poison.categories.json_doc",
    "lupaxa.data_poison.categories.numbers",
    "lupaxa.data_poison.categories.unicode_text",
    "lupaxa.data_poison.categories.urls",
    "lupaxa.data_poison.categories.xml_doc",
)


def load_categories() -> None:
    """Import each category module. Python runs each module body only once."""
    for module_name in _CATEGORY_MODULES:
        importlib.import_module(module_name)
