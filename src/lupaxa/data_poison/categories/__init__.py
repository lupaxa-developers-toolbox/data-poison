"""Importing this package registers the built-in catalogue."""

from __future__ import annotations


def load_categories() -> None:
    """Import each category module. Python runs each module body only once."""
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
