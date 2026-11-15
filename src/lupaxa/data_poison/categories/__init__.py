"""Importing this package registers the built-in catalogue."""

from __future__ import annotations

_LOADED = False


def load_categories() -> None:
    """Import each category module once. Import side effects register cases."""
    global _LOADED
    if _LOADED:
        return
    from lupaxa.data_poison.categories import (
        csv_doc,
        dates,
        emails,
        filenames,
        json_doc,
        numbers,
        unicode_text,
        urls,
        xml_doc,
    )

    del csv_doc, dates, emails, filenames, json_doc, numbers, unicode_text, urls, xml_doc
    _LOADED = True
