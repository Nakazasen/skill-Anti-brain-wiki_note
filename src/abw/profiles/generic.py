from __future__ import annotations

from .base import ConflictProfile


PROFILE = ConflictProfile(
    name="generic",
    synonyms={},
    comparable_numeric_keys=frozenset(
        {
            "version",
            "date_effective",
        }
    ),
    ignore_numeric_contexts=frozenset(
        {
            "page",
            "line",
            "manifest",
            "section",
            "year",
            "copyright",
            "source",
            "ref",
            "timestamp",
            "id",
        }
    ),
)
